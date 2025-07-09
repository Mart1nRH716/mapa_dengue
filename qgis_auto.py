from qgis.core import QgsProject, edit, QgsSymbol, QgsRendererRange, QgsGraduatedSymbolRenderer, QgsStyle, QgsLayoutExporter
from qgis.utils import iface
from PyQt5.QtCore import QVariant, QSize
from PyQt5.QtGui import QColor
import pyodbc
import traceback
import numpy as np
import os

try:
    # ============= CONFIGURACIÓN DE VARIABLES =============
    SEMANA_EPIDEMIOLOGICA = 45  # Colocar la semana epidemiológica actual
    
    # Configuración de exportación
    NOMBRE_LAYOUT = "dengue2024b"  # Nombre del layout en QGIS
    CARPETA_EXPORTACION = r"C:\Exports\Atlas_Dengue_" + str(SEMANA_EPIDEMIOLOGICA)  # Carptera donde se guardarán las imágenes exportadas
    
    # ============= CONEXIÓN A BASE DE DATOS =============
    # Configuración con PyODBC
    server = 'MTO02438WSAGC01'
    database = 'Dengue'
    username = 'sa'
    password = 'Im550123'
    driver = 'ODBC Driver 11 for SQL Server'
    
    connection_string = (
        f'DRIVER={driver};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'UID={username};'
        f'PWD={password}'
    )
    
    #Conectar y obtener datos
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    
    # Consultar los datos de la vista 
    query = "SELECT cvegeo, ESTIMADOS FROM dbo.vs_Dengue"
    cursor.execute(query)
    
    # Crear diccionario con los resultados
    dengue_data = {}
    for row in cursor:
        cvegeo = str(row.cvegeo).strip() if row.cvegeo else None
        if cvegeo:
            dengue_data[cvegeo] = row.ESTIMADOS
    
    print(f"Se obtuvieron {len(dengue_data)} registros desde SQL Server")
    
    # Obtener la capa 'denguemun' del QGIS
    denguemun_layer = QgsProject.instance().mapLayersByName("denguemun")
    if not denguemun_layer:
        raise ValueError("No existe capa 'denguemun'")
    denguemun_layer = denguemun_layer[0]
    
    # Actualizar la capa
    updated_features = 0
    valores_actualizados = []
    
    with edit(denguemun_layer):
        for feature in denguemun_layer.getFeatures():
            cvegeo = str(feature['CVEGEO']).strip()
            if cvegeo in dengue_data:
                estimados = dengue_data[cvegeo]
                estimados = int(estimados)
                feature['casostot'] = estimados
                denguemun_layer.updateFeature(feature)
                valores_actualizados.append(estimados)
                updated_features += 1
    
    success_msg = f"Actualizados {updated_features} registros en 'denguemun'"
    print(success_msg)
    iface.messageBar().pushSuccess("Éxito", success_msg)
    
    # Crear clasificación automática en 5 clases (0-1 + 4 clases automáticas)
    if valores_actualizados:
        valores_array = np.array([int(v) for v in valores_actualizados if v is not None])
        
        # Filtrar valores mayores a 1 para las 4 clases automáticas
        valores_mayores_1 = valores_array[valores_array > 1]
        
        if len(valores_mayores_1) > 0:
            # Calcular percentiles para 4 clases
            percentiles = [25, 50, 75, 100]
            rangos_auto = np.percentile(valores_mayores_1, percentiles)
            
            # Crear rangos para las 5 clases
            rangos = []
            
            # Clase 1: 0-1
            rangos.append((0, 1, "0 - 1"))
            
            # Clase 2: 1 - primer cuartil
            rangos.append((1, rangos_auto[0], f"1 - {rangos_auto[0]:.1f}"))
            
            # Clase 3: primer cuartil - mediana
            rangos.append((rangos_auto[0], rangos_auto[1], f"{rangos_auto[0]:.1f} - {rangos_auto[1]:.1f}"))
            
            # Clase 4: mediana - tercer cuartil
            rangos.append((rangos_auto[1], rangos_auto[2], f"{rangos_auto[1]:.1f} - {rangos_auto[2]:.1f}"))
            
            # Clase 5: tercer cuartil - máximo
            rangos.append((rangos_auto[2], rangos_auto[3], f"{rangos_auto[2]:.1f} - {rangos_auto[3]:.1f}"))
            
            colores = [
                QColor(255, 255, 255),    # Blanco para 0-1
                QColor(255, 245, 240),    # Color carne muy claro
                QColor(252, 164, 134),    # Color carne
                QColor(234, 55, 42),     # color rojo
                QColor(103, 0, 13)      # Vino 
            ]
            
            # Crear los rangos de símbolos
            symbol_ranges = []
            for i, (min_val, max_val, label) in enumerate(rangos):
                # Crear símbolo con color específico
                symbol = QgsSymbol.defaultSymbol(denguemun_layer.geometryType())
                symbol.setColor(colores[i])
                symbol.setOpacity(0.8)
                
                # Crear rango
                rango = QgsRendererRange(min_val, max_val, symbol, label)
                symbol_ranges.append(rango)
            
            # Crear el renderer graduado
            renderer = QgsGraduatedSymbolRenderer('casostot', symbol_ranges)
            renderer.setMode(QgsGraduatedSymbolRenderer.Custom)
            
            # Aplicar el renderer a la capa
            denguemun_layer.setRenderer(renderer)
            
            # Información sobre la clasificación
            print("\n--- CLASIFICACIÓN APLICADA ---")
            print("Número de clases: 5")
            print("Clases creadas:")
            for i, (min_val, max_val, label) in enumerate(rangos):
                print(f"  Clase {i+1}: {label}")
            
            # Mostrar estadísticas
            print(f"\nEstadísticas de los datos:")
            print(f"Mínimo: {np.min(valores_array):.2f}")
            print(f"Máximo: {np.max(valores_array):.2f}")
            print(f"Media: {np.mean(valores_array):.2f}")
            print(f"Mediana: {np.median(valores_array):.2f}")
            print(f"Valores > 1: {len(valores_mayores_1)}")
            print(f"Valores 0-1: {len(valores_array) - len(valores_mayores_1)}")
            
        else:
            print("No hay valores mayores a 1 para crear clasificación automática")
    
    # Refrescar la capa
    denguemun_layer.triggerRepaint()
    iface.layerTreeView().refreshLayerSymbology(denguemun_layer.id())
    
    clasificacion_msg = "Clasificación automática aplicada: 5 clases"
    print(clasificacion_msg)
    iface.messageBar().pushSuccess("Clasificación", clasificacion_msg)
    
    # ============= EXPORTAR ATLAS =============
    print(f"\n--- EXPORTANDO ATLAS - SEMANA {SEMANA_EPIDEMIOLOGICA} ---")
    
    # Obtener el proyecto y el layout
    project = QgsProject.instance()
    layout_manager = project.layoutManager()
    
    # Buscar el layout del atlas
    layout = layout_manager.layoutByName(NOMBRE_LAYOUT)
    if not layout:
        print(f"Error: No se encontró el layout '{NOMBRE_LAYOUT}'")
        print("Layouts disponibles:")
        for layout_item in layout_manager.layouts():
            print(f"  - {layout_item.name()}")
        raise ValueError(f"Layout '{NOMBRE_LAYOUT}' no encontrado")
    
    # Verificar que sea un atlas
    atlas = layout.atlas()
    if not atlas.enabled():
        print("El atlas no está habilitado.")
        atlas.setEnabled(True)
    
    # CONFIGURAR EL ATLAS CORRECTAMENTE
    # Obtener la capa de cobertura
    delega_layer = None
    for layer in project.mapLayers().values():
        if layer.name() == "Delega":
            delega_layer = layer
            break
    
    if not delega_layer:
        raise ValueError("No se encontró la capa 'Delega'")
    
    # Configurar la capa de cobertura del atlas
    atlas.setCoverageLayer(delega_layer)
    
    # Limpiar cualquier filtro existente
    atlas.setFilterExpression("")
    
    # Configurar otras opciones del atlas
    atlas.setHideCoverage(False)  # Mostrar la capa de cobertura
    atlas.setSortFeatures(True)   # Ordenar características
    
    # Usar el primer campo disponible para ordenar 
    fields = delega_layer.fields()
    if fields.count() > 0:
        sort_field = fields.at(0).name()
        atlas.setSortExpression(f'"{sort_field}"')
        atlas.setSortAscending(True)
        print(f"Ordenando atlas por campo: {sort_field}")
    
    # Actualizar el atlas
    atlas.updateFeatures()
    
    # Verificar configuración del atlas
    print(f"Atlas habilitado: {atlas.enabled()}")
    print(f"Capa de cobertura: {atlas.coverageLayer().name() if atlas.coverageLayer() else 'No definida'}")
    print(f"Número de páginas: {atlas.count()}")
    print(f"Expresión de filtro: '{atlas.filterExpression()}'")
    print(f"Ordenar características: {atlas.sortFeatures()}")
    
    if atlas.count() == 0:
        print(f"Características en capa Delega: {delega_layer.featureCount()}")
        print(f"Capa válida: {delega_layer.isValid()}")
        print(f"Geometrías válidas:")
        
        feature_count = 0
        valid_geom_count = 0
        for feature in delega_layer.getFeatures():
            feature_count += 1
            if feature.hasGeometry() and not feature.geometry().isEmpty():
                valid_geom_count += 1
            if feature_count <= 5:  # Mostrar solo las primeras 5 características
                geom_info = "válida" if feature.hasGeometry() and not feature.geometry().isEmpty() else "inválida"
                print(f"  Feature {feature.id()}: geometría {geom_info}")
        
        print(f"Total características: {feature_count}")
        print(f"Geometrías válidas: {valid_geom_count}")
        
        # Intentar configurar manualmente el atlas
        print("Intentando reconfigurar el atlas...")
        # Deshabilitar y volver a habilitar
        atlas.setEnabled(False)
        atlas.setEnabled(True)
        atlas.setCoverageLayer(delega_layer)
        atlas.updateFeatures()
        
        print(f"Páginas después de reconfiguración: {atlas.count()}")
    
    # Verificar que el atlas tenga páginas antes de exportar
    if atlas.count() == 0:
        raise ValueError("El atlas no tiene páginas configuradas.")
    
    # Actualizar el texto con la semana epidemiológica
    text_updated = False
    for item in layout.items():
        if hasattr(item, 'text') and 'Semanas' in item.text():
            texto_original = item.text()
            import re
            texto_nuevo = re.sub(r'(\d+)\s+a\s+la\s+\d+', f'\\1 a la {SEMANA_EPIDEMIOLOGICA}', texto_original)
            item.setText(texto_nuevo)
            text_updated = True
            print(f"Texto nuevo: '{texto_nuevo}'")
            break
    
    if not text_updated:
        print("Advertencia: No se encontró texto con 'Semanas' para actualizar")
    
    # Crear carpeta si no existe
    if not os.path.exists(CARPETA_EXPORTACION):
        os.makedirs(CARPETA_EXPORTACION)
        print(f"Carpeta creada: {CARPETA_EXPORTACION}")
    
    # Configurar exportador
    exporter = QgsLayoutExporter(layout)
    
    # Configurar las opciones de exportación para PNG
    export_settings = QgsLayoutExporter.ImageExportSettings()
    export_settings.dpi = 300
    export_settings.imageSize = QSize() 
    export_settings.cropToContents = False
    export_settings.generateWorldFile = False
    
    # Nombre del archivo base con la semana
    nombre_base = f"Atlas_Dengue_Semana_{SEMANA_EPIDEMIOLOGICA}"
    
    # Exportar el atlas como
    print(f"Exportando atlas como PNG a: {CARPETA_EXPORTACION}")
    print(f"Número de páginas a exportar: {atlas.count()}")
    
    # Para atlas PNG, necesitamos iterar página por página
    atlas.beginRender()
    
    export_count = 0
    failed_exports = 0
    
    try:
        for i in range(atlas.count()):
            atlas.seekTo(i)
            feature_name = ""
            try:
                # Obtener la capa de cobertura y la característica actual
                coverage_layer = atlas.coverageLayer()
                if coverage_layer:
                    # Obtener todas las características y buscar la actual por índice
                    features = list(coverage_layer.getFeatures())
                    if i < len(features):
                        current_feature = features[i]
                        
                        # Intentar obtener un nombre identificativo de la característica
                        fields = current_feature.fields()
                        for field in fields:
                            field_name = field.name()
                            if field_name.lower() in ['nombre', 'name', 'estado', 'delegacion', 'region']:
                                feature_value = str(current_feature[field_name]).replace(' ', '_').replace('/', '_')
                                feature_name = f"_{feature_value}"
                                break
                        
                        if not feature_name:
                            # Si no encuentra un campo específico, usar el ID
                            feature_name = f"_ID_{current_feature.id()}"
            
            except Exception as e:
                print(f"Advertencia: No se pudo obtener nombre de característica para página {i+1}: {str(e)}")
                feature_name = f"_Pagina_{i+1}"
            
            # Crear nombre de archivo
            nombre_archivo = f"{nombre_base}_Pagina_{i+1}{feature_name}.png"
            ruta_archivo = os.path.join(CARPETA_EXPORTACION, nombre_archivo)
            result = exporter.exportToImage(ruta_archivo, export_settings)
            
            if result == QgsLayoutExporter.Success:
                export_count += 1
                print(f"Página {i+1}/{atlas.count()} exportada: {nombre_archivo}")
            else:
                failed_exports += 1
                print(f"Error exportando página {i+1}: código {result}")
    
    finally:
        atlas.endRender()
    
    if export_count > 0:
        export_msg = f"Atlas exportado: {export_count} páginas PNG creadas"
        print(f"\n{export_msg}")
        iface.messageBar().pushSuccess("Exportación", export_msg)
        print(f"Ubicación: {CARPETA_EXPORTACION}")
        print(f"Semana epidemiológica: {SEMANA_EPIDEMIOLOGICA}")
        print(f"Páginas exportadas: {export_count}")
        print(f"Páginas fallidas: {failed_exports}")
        print(f"Formato: PNG con {export_settings.dpi} DPI")
        
    else:
        error_msg = f"Error: No se pudo exportar ninguna página del atlas"
        print(error_msg)
        iface.messageBar().pushCritical("Error Exportación", error_msg)

except pyodbc.Error as e:
    error_msg = f"Error de conexión ODBC: {str(e)}"
    print(error_msg)
    iface.messageBar().pushCritical("Error SQL", error_msg)

except Exception as e:
    error_msg = f"Error general: {str(e)}\n{traceback.format_exc()}"
    print(error_msg)
    iface.messageBar().pushCritical("Error", error_msg)

finally:
    if 'conn' in locals():
        conn.close()
