# Automatización de la actualización de mapas de Dengue

Este es el script para automatizar la actualización y exportación de los mapas de dengue a través de QGIS.

## Instalación y ejecución

### Requisitos

- QGIS >= 3.40.10
- Proyecto de QGIS:  QGIS_Dengue

---

###  Ejecutar script 

1.- Localizamos la carpeta de nuestro proyecto y abrimos el archivo llamado: dengue.qgz
<img width="950" height="601" alt="image" src="https://github.com/user-attachments/assets/9799957c-d155-4ce6-ae52-de1643c71124" />

2.- Una vez abierto, seleccionamos el icono de Python en la barra superior de herramientas.
<img width="1303" height="128" alt="image" src="https://github.com/user-attachments/assets/470cb786-9af0-4e00-8e1b-50cbecd81311" />

3.- En la parte inferior se abrirá la consola de python, y debemos de dar clic en la opción de mostrar editor.
<img width="852" height="171" alt="image" src="https://github.com/user-attachments/assets/83b5dffa-e3f6-45fb-9184-cb40a635d8b5" />

4.- Se abrirá un cuadro de lado derecho, seleccionamos la opción de abrir script.
<img width="549" height="145" alt="image" src="https://github.com/user-attachments/assets/8a9c0751-391c-47c3-8a6c-130531595903" />

5. En el cuadro de búsqueda seleccionamos el Script del repositorio. Una vez abierto, se tiene que modificar el número de la semana que vamos a construir.
<img width="655" height="96" alt="image" src="https://github.com/user-attachments/assets/33ca6906-a328-4d45-9088-f1fa28f0d603" />

6.- Después de modificar la semana, se da clic en el botón de "ejecutar script".
<img width="405" height="74" alt="image" src="https://github.com/user-attachments/assets/99200b00-4bb6-4b69-91af-dddcdc041931" />

7.- Dejamos que acabe el script y este exportará las imágenes en formato png en la ubicación: C:\QGIS_Mapas_Dengue

### Consideraciones y modificaciones.

**Una vez terminado la ejecución del script, es importante que no se guarden los cambios generados por dicho código dentro del proyecto, ya que este actuliza los nombres de las capas y esto puede ocasionar un error en ejecuciones futuras al no encontrar las capas definidas dentro del script.**

En caso de que se requiera cambiar el año; Antes de ejecutar el script, se debe de entrar en la pestaña  **Proyecto>Composiciones>dengue2024b**
<img width="653" height="501" alt="image" src="https://github.com/user-attachments/assets/91bb641b-31d4-4215-8f76-f4199e5e0b41" />

Se abrirá la ventana de la composición, aquí se debe seleccionar la leyenda que se quiere actulizar:
<img width="1273" height="582" alt="image" src="https://github.com/user-attachments/assets/5b166d32-91e4-4af2-8001-731bd4ef85b0" />
Al igual que la otra leyenda.




