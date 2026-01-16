from qgis.core import QgsProject, edit, QgsSymbol, QgsRendererRange, QgsGraduatedSymbolRenderer, QgsClassificationJenks, QgsLayoutExporter, QgsLayoutItemLegend, QgsLayoutPoint, QgsUnitTypes, QgsLayoutSize
from qgis.utils import iface
from PyQt5.QtCore import QVariant, QSize
from PyQt5.QtGui import QColor
import pyodbc
import traceback
import numpy as np
import csv
import os

try:
	# ============= CONFIGURACIÓN DE VARIABLES =============
	SEMANA_EPIDEMIOLOGICA = 53  # Colocar la semana epidemiológica actual
	RESOLUCION_IMAGENES = 150
	# Configuración de exportación
	NOMBRE_LAYOUT = "dengue2024b"  # Nombre del layout en QGIS
	CARPETA_EXPORTACION = r"C:\QGIS_Mapas_Dengue\Atlas_Dengue_" + str(SEMANA_EPIDEMIOLOGICA)  # Carptera donde se guardarán las imágenes exportadas
	
	# ============= CONEXIÓN A BASE DE DATOS =============
	# Configuración con PyODBC
	server = 'localhost'
	database = 'Dengue'
	driver = 'ODBC Driver 11 for SQL Server'
	
	connection_string = (
		f'DRIVER={driver};'
		f'SERVER={server};'
		f'DATABASE={database};'
		'Trusted_Connection=yes;'
		# f'UID={username};'
		# f'PWD={password}'
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

	# Primero inicializar TODOS los municipios a 0
	with edit(denguemun_layer):
		for feature in denguemun_layer.getFeatures():
			feature['casostot'] = 0
			denguemun_layer.updateFeature(feature)

	print("Todos los municipios inicializados a 0")
	
	with edit(denguemun_layer):
		for feature in denguemun_layer.getFeatures():
			cvegeo = str(feature['CVEGEO']).strip()
			if cvegeo in dengue_data:
				estimados = dengue_data[cvegeo]
				estimados = int(estimados) if estimados is not None else 0
				feature['casostot'] = estimados
				denguemun_layer.updateFeature(feature)
				valores_actualizados.append(estimados)
				updated_features += 1
			else:
				valores_actualizados.append(0)
	
	success_msg = f"Actualizados {updated_features} registros en 'denguemun'"
	print(success_msg)
	iface.messageBar().pushSuccess("Éxito", success_msg)
	
	# Crear clasificación automática en 5 clases (0-1 + 4 clases automáticas)
	if valores_actualizados:
		valores_array = np.array([int(v) for v in valores_actualizados if v is not None])
		
		print(f"\n--- ESTADÍSTICAS DE LOS DATOS ---")
		print(f"Total de municipios: {len(valores_array)}")
		print(f"Mínimo: {np.min(valores_array):.2f}")
		print(f"Máximo: {np.max(valores_array):.2f}")
		print(f"Media: {np.mean(valores_array):.2f}")
		print(f"Mediana: {np.median(valores_array):.2f}")
		
		# Aplicar Jenks a TODOS los valores para obtener 4 clases
		valores_todos = valores_array.tolist()
		clasificador = QgsClassificationJenks()
		clasificador.setLabelFormat("%1 - %2")

		# Calcular 4 cortes de Jenks para el conjunto completo
		rangos_jenks_4 = clasificador.classes(valores_todos, 4)
		
		print("\n--- CLASIFICACIÓN JENKS ORIGINAL (4 clases) ---")
		for i, rango in enumerate(rangos_jenks_4):
			lower = int(rango.lowerBound())
			upper = int(rango.upperBound())
			count = len(valores_array[(valores_array >= lower) & (valores_array <= upper)])
			print(f"Clase {i+1}: {lower} - {upper} [{count}]")
		
		colores = [
			QColor(255, 255, 255),    # Blanco para 0-1 (clase manual)
			QColor(255, 245, 240),    # Color carne muy claro
			QColor(252, 164, 134),    # Color carne
			QColor(234, 55, 42),      # color rojo
			QColor(103, 0, 13)        # Vino 
		]
		
		# Crear los rangos de símbolos
		symbol_ranges = []
		
		# CLASE 1: 0-1 (MANUAL)
		symbol = QgsSymbol.defaultSymbol(denguemun_layer.geometryType())
		symbol.setColor(colores[0])
		symbol.setOpacity(0.8)
		symbol.symbolLayer(0).setStrokeColor(QColor(200, 200, 200))
		symbol.symbolLayer(0).setStrokeWidth(0.1)
		
		# Contar cuántos valores están en 0-1
		count_0_1 = len(valores_array[valores_array <= 1])
		label = f"0 - 1 [{count_0_1}]"
		
		rango = QgsRendererRange(0, 1, symbol, label)
		symbol_ranges.append(rango)
		
		# CLASE 2: Primera clase de Jenks, pero editada para empezar en 1
		symbol = QgsSymbol.defaultSymbol(denguemun_layer.geometryType())
		symbol.setColor(colores[1])
		symbol.setOpacity(0.8)
		symbol.symbolLayer(0).setStrokeColor(QColor(200, 200, 200))
		symbol.symbolLayer(0).setStrokeWidth(0.1)
		
		# Tomar el límite superior de la primera clase de Jenks
		primer_corte_superior = int(rangos_jenks_4[0].upperBound())
		
		# Si el primer corte de Jenks es 1 o menos, usar el segundo corte
		if primer_corte_superior <= 1:
			primer_corte_superior = int(rangos_jenks_4[1].upperBound())
		
		# Contar valores en el rango 1 - primer_corte_superior
		count_clase_2 = len(valores_array[(valores_array > 1) & 
										(valores_array <= primer_corte_superior)])
		
		label = f"1 - {primer_corte_superior} [{count_clase_2}]"
		
		rango = QgsRendererRange(1, primer_corte_superior, symbol, label)
		symbol_ranges.append(rango)
		
		# CLASES 3, 4 y 5: Las clases 2, 3 y 4 de Jenks
		for i in range(1, 4):  # (clases Jenks 2, 3, 4)
			symbol = QgsSymbol.defaultSymbol(denguemun_layer.geometryType())
			symbol.setColor(colores[i + 1])
			symbol.setOpacity(0.8)
			symbol.symbolLayer(0).setStrokeColor(QColor(200, 200, 200))
			symbol.symbolLayer(0).setStrokeWidth(0.1)
			
			lower_val = int(rangos_jenks_4[i].lowerBound())
			upper_val = int(rangos_jenks_4[i].upperBound())
			
			# Asegurar que no haya solapamientos con la clase anterior
			if lower_val < primer_corte_superior:
				lower_val = primer_corte_superior
			
			# Contar valores en este rango
			count = len(valores_array[(valores_array > lower_val) & 
									(valores_array <= upper_val)])
			
			# Si hay solapamiento, ajustar el conteo
			if lower_val == primer_corte_superior:
				count = len(valores_array[(valores_array > primer_corte_superior) & 
										(valores_array <= upper_val)])
			
			label = f"{lower_val} - {upper_val} [{count}]"
			
			rango = QgsRendererRange(lower_val, upper_val, symbol, label)
			symbol_ranges.append(rango)

		# Crear el renderer graduado
		renderer = QgsGraduatedSymbolRenderer('casostot', symbol_ranges)
		renderer.setMode(QgsGraduatedSymbolRenderer.Custom)
		
		# Aplicar el renderer a la capa
		denguemun_layer.setRenderer(renderer)
		denguemun_layer.triggerRepaint()

		iface.layerTreeView().refreshLayerSymbology(denguemun_layer.id())
		denguemun_layer.dataProvider().reloadData()
		QgsProject.instance().reloadAllLayers()

		# Información sobre la clasificación
		print("\n--- CLASIFICACIÓN FINAL APLICADA ---")
		print("Número de clases: 5 (0-1 manual + 4 Jenks editadas)")
		print("Clases creadas:")
		for rango in symbol_ranges:
			print(f"  {rango.label()}")
		
		# Verificar distribución
		print(f"\nVerificación de distribución:")
		total_conteo = 0
		for rango in symbol_ranges:
			# Extraer el conteo de la etiqueta
			label_text = rango.label()
			if '[' in label_text:
				count_str = label_text.split('[')[1].split(']')[0]
				count = int(count_str)
				total_conteo += count
				print(f"  {label_text}")
		
		print(f"Total municipios en clases: {total_conteo}")
		print(f"Total municipios reales: {len(valores_array)}")
		
		valores_mayores_1 = valores_array[valores_array > 1]
		print(f"Valores > 1: {len(valores_mayores_1)}")
		print(f"Valores 0-1: {len(valores_array) - len(valores_mayores_1)}")
		
	else:
		print("No hay valores para crear clasificación automática")
	
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

	

	legend = QgsLayoutItemLegend(layout)
	legend.setAutoUpdateModel(False)

	model = legend.model()
	root = model.rootGroup()


	# Lista para guardar los nodos a eliminar
	nodos_a_eliminar = []

	for child in root.children():
		if child.name() == "denguemun":
			layer = child.layer()
			if layer:
				# Contar las features de la capa
				feature_count = layer.featureCount()
				child.setName(f"Casos por municipio [{feature_count}]")
			else:
				child.setName("Casos por municipio")
		
		if child.name() == "tercernivel":
			child.setName("UAME*")

		if child.name() == "segundonivel":
			child.setName("2do Nivel")

		if child.name() == "primernivel":
			child.setName("1er Nivel")	
		
		# NO eliminar aquí, solo guardar para eliminar después
		if child.name() in ["Delega", "cuums", "unidapoyo"]:
			nodos_a_eliminar.append(child)


	for nodo in nodos_a_eliminar:
		model.rootGroup().removeChildNode(nodo)

	legend.attemptMove(QgsLayoutPoint(7, 87, QgsUnitTypes.LayoutMillimeters))
	legend.attemptResize(QgsLayoutSize(50, 80, QgsUnitTypes.LayoutMillimeters))

	legend.setBoxSpace(2)
	legend.setSymbolWidth(8)
	legend.setSymbolHeight(5)
	legend.setColumnCount(1)

	# Mantener desactivado el auto-update para que conserve tus cambios
	legend.setAutoUpdateModel(False)
	legend.updateFilterByMap(True)
	layout.addLayoutItem(legend)



	for item in layout.items():
		if isinstance(item, QgsLayoutItemLegend) and item is not legend:
			layout.removeLayoutItem(item)

	layout.refresh()
	atlas.updateFeatures()


	# Crear carpeta si no existe
	if not os.path.exists(CARPETA_EXPORTACION):
		os.makedirs(CARPETA_EXPORTACION)
		print(f"Carpeta creada: {CARPETA_EXPORTACION}")

	# Guardar los datos de la consulta en un csv:
	ruta_csv = f'{CARPETA_EXPORTACION}\dengue_consulta_{SEMANA_EPIDEMIOLOGICA}.csv'
	with open(ruta_csv, mode='w', newline='', encoding='utf-8') as f:
		writer = csv.writer(f)

		# Encabezados
		writer.writerow(['cvegeo', 'ESTIMADOS'])

		# Filas
		for clave, valor in dengue_data.items():
			writer.writerow([clave, valor])

		print(f"CSV generado en: {ruta_csv}")
	
	# Configurar exportador
	exporter = QgsLayoutExporter(layout)
	
	# Configurar las opciones de exportación para PNG
	export_settings = QgsLayoutExporter.ImageExportSettings()
	export_settings.dpi = RESOLUCION_IMAGENES
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