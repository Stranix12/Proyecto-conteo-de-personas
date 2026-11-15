# Guion para demostración final de hasta tres minutos

La demostración incluida muestra capturas de pantalla reales del aplicativo,
editadas para eliminar esperas. Usa material de prueba. Para una grabación de
campo, sustituye ese material por la cámara del computador y comprueba el
conteo manualmente. No uses un teléfono para grabar la demostración.

| Tiempo | Acción y explicación |
| --- | --- |
| 0 a 20 s | Mostrar en VS Code la estructura, `requirements.txt`, el detector y PostgreSQL configurado sin revelar `.env` |
| 20 a 45 s | Abrir el navegador, explicar las fuentes, el aforo y el umbral; procesar la imagen de dos personas |
| 45 a 85 s | Iniciar cámara del computador y mostrar recuadros y conteo frente a una referencia manual; si no hay cámara, declarar la prueba con video |
| 85 a 110 s | Cambiar aforo a uno con dos personas visibles y mostrar alerta; restablecer aforo |
| 110 a 135 s | Detener, revisar historial y exportar CSV; explicar máximo y promedio de lecturas |
| 135 a 160 s | Mostrar ejecución de las pruebas y explicar cambio HOG a YOLOX y sus límites |
| 160 a 175 s | Mostrar informe y archivos; indicar enlaces reales de Drive y GitHub cuando existan |

## Publicación posterior

1. Grabar pantalla desde el computador sin exponer claves ni datos ajenos.
2. Comprobar duración inferior a tres minutos y reproducción del MP4.
3. Subir el MP4 a Drive y conceder visualización al destinatario previsto.
4. Abrir el enlace con una sesión de prueba para verificar el acceso.
5. Incorporar el enlace real al apartado de entregables del informe.
6. Publicar el código en GitHub cuando se retome esa parte; excluir `.env`,
   `.venv`, datos PostgreSQL y archivos temporales.
