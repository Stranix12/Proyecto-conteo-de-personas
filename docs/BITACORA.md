# Bitácora de construcción

Fecha de ejecución: 10 de noviembre de 2026. Esta bitácora describe cambios
comprobados durante la construcción local; no simula una historia de commits.

| Paso | Cambio realizado | Motivo y comprobación |
| --- | --- | --- |
| 1 | Se revisaron las tres páginas de la guía de UNEMI | Se identificaron Django, OpenCV, PostgreSQL, las tres sesiones y los entregables |
| 2 | Se creó el proyecto Django con `config` y `counter` | Separar configuración, dominio, detección e interfaz |
| 3 | Se inicializó PostgreSQL portátil en puerto 55432 | Cumplir la base obligatoria sin sustituirla por SQLite; escucha solo local |
| 4 | Se construyó el flujo de captura y envío de imágenes | El navegador captura; Django procesa; no se conserva el video original |
| 5 | Se ensayó HOG con SVM | La imagen de dos personas devolvió una; resultado guardado en `comparacion_hog.json` |
| 6 | Se abrió el proyecto en Visual Studio Code y se sustituyó el detector por YOLOX | La misma imagen devolvió dos; ONNX ejecutado con `cv2.dnn` en CPU |
| 7 | Se ajustó el umbral de 0.5 SVM a 0.35 YOLOX | Son escalas distintas; API e interfaz ahora aceptan de 0.1 a 0.95; migración 0002 |
| 8 | Se añadió letterbox RGB 640 por 640 y NMS | Evitar deformación y duplicados; filtrar únicamente la clase persona |
| 9 | Se añadió persistencia por sesión, CSV y alerta de aforo | Una lectura por imagen procesada; pruebas de ORM, exportación y alerta |
| 10 | Se endurecieron validaciones y cierre de sesión | Rechazo de imágenes corruptas, tamaño excesivo, NaN, métodos indebidos y lecturas tardías |
| 11 | Se coordinaron los cierres y la cancelación durante la creación | Una promesa compartida coordina Detener y fin de video; una sesión que llega tarde se cierra; prueba JavaScript aprobada |
| 12 | Se verificó la interfaz con imagen, video y pantallas pequeñas | Capturas reales en `evidencias`; video controlado con cambios entre cero y dos |
| 13 | Se corrigió la consulta del historial con `order_by` explícito | La agregación no garantizaba el orden; nueva prueba verifica sesiones recientes primero |
| 14 | Se corrigió el singular de persona al configurar aforo de uno | Ajuste visible en la etiqueta del indicador |
| 15 | Se consolidaron 22 pruebas y cinco variantes controladas | Todas las pruebas aprobaron; los resultados no se generalizan a un laboratorio real |
| 16 | Se añadieron README, configuración de VS Code, manual e informe PDF | Facilitar instalación, revisión, ejecución y mantenimiento |
| 17 | Se separó la reproducción nativa de cámara y video de la inferencia | El video permanece visible; las cajas se actualizan en un SVG con la misma proporción y se retiran tras 1.2 segundos sin datos |
| 18 | Se reemplazó la espera fija de 350 ms por un intervalo objetivo de 250 ms | Hasta cuatro detecciones por segundo sin solicitudes simultáneas; temporizador eliminado al detener |
| 19 | Se ampliaron las pruebas JavaScript a siete y se verificó video controlado de 30 FPS | Reproducción activa y visible mientras cambian las detecciones; prueba de cámara física pendiente |
| 20 | Se corrigió replaceChildren sobre una capa SVG inexistente en la plantilla anterior | Se crea la capa automáticamente, la liberación de dispositivos no depende de ella y dos pruebas nuevas elevan la suite JavaScript a nueve; verificación con plantilla antigua real sin error |

Los ejecutables de PostgreSQL y el entorno de Python se mantienen fuera del
paquete fuente. El modelo y la imagen de ejemplo conservan su atribución.
La publicación externa queda separada del desarrollo local.
