# Walkthrough: TV Player 2 Desasistido (Onboarding, Autodirección, Emojis y Banner Neón)

He implementado con éxito la solución definitiva para un **modo desasistido (zero-configuration)** en el nuevo **TV Player 2**. Esto permite guiar paso a paso al usuario para activar el bloqueo nativo de publicidad (uBlock Origin), automatizar el inicio de reproducción, mantener la pantalla completa nativa sin cortes entre canciones y añadir interacciones en caliente (emojis y comunicados).

---

## Flujo de Trabajo Desasistido (Unattended Flow)

1. **Pantalla de Onboarding**:
   Al abrir la dirección rápida `http://localhost:8000/player2` en el navegador del televisor por primera vez:
   * Si no está instalado el script de sincronización, se presenta una pantalla de diseño futurista con pasos claros:
     * **Paso 1**: Instalar AdBlock (Direct Link).
     * **Paso 2**: Instalar Violentmonkey (Direct Link).
     * **Paso 3**: Instalar Script de QrMusic (Botón interactivo directo a `qrmusic_userscript.user.js` en una nueva pestaña).
     * **Paso 4**: Presionar **F11** o hacer clic en el botón principal para entrar a Pantalla Completa.

2. **Detección Automática de Instalación**:
   * Tan pronto como el usuario instala el Userscript (Paso 3), el script inyecta un identificador especial en la página.
   * La pantalla de configuración detecta esto de forma asíncrona y cambia su estado instantáneamente a:
     * **"✨ ¡Listo para Empezar! Esperando canciones en cola..."**

3. **Autodirección Interactiva y Transición Suave (SPA)**:
   * El TV se deja en esa pantalla de espera.
   * Cuando un cliente o el administrador agrega una canción, el WebSocket recibe el evento `play_song` y **redirecciona automáticamente el navegador del televisor a YouTube** (`https://www.youtube.com/watch?v={VIDEO_ID}`).
   * **Mejora de Pantalla Completa Permanente**: Para evitar perder el modo F11 al pasar de una canción a otra (las redirecciones de página completa causan que el navegador cancele el fullscreen), hemos implementado transiciones internas utilizando la API del reproductor de YouTube (`loadVideoById`). El video cambia instantáneamente en la misma pestaña **sin recargar la página**, manteniendo el fullscreen y el audio de forma ininterrumpida.

4. **Retorno a Inicio al Vaciar la Cola**:
   * Cuando la canción finaliza, el Userscript llama al servidor para avanzar a la siguiente.
   * Si el servidor responde que la cola está vacía (`204 No Content`), el Userscript **redirecciona automáticamente la pantalla de regreso a la página de bienvenida** (`http://localhost:8000/player2`).
   * Esto crea un bucle infinito desasistido perfecto para el bar.

5. **Interacción y Efectos en Pantalla**:
   * **Reacciones Flotantes**: Los emojis enviados por los usuarios en la app móvil se capturan por WebSocket y flotan desde el fondo hacia arriba de la pantalla de la TV de forma translúcida, animada y aleatoria (efecto marca de agua).
   * **Banner de Administración Neón**: Los comunicados y alertas del administrador se muestran en un banner flotante centrado con estética de neón fucsia y desenfoque de cristal (glassmorphism), y se desvanecen automáticamente tras 10 segundos.

---

## Cambios Realizados

### 1. Archivos Frontend
- **[MODIFY] [player2.html](file:///c:/Users/MSI/Documents/QrMusic/static/player2.html)**: Se renombró el botón de lanzamiento a `Abrir el Reproductor (TV Mode)` y se habilitó la apertura en pestañas separadas (`target="_blank"`) para facilitar la instalación del script sin romper la navegación.
- **[MODIFY] [qrmusic_userscript.user.js](file:///c:/Users/MSI/Documents/QrMusic/static/qrmusic_userscript.user.js)**:
  - Se añadió la lógica de la API de YouTube (`loadVideoById`) para evitar salidas inesperadas de la pantalla completa.
  - Se implementó la vinculación del WebSocket para las reacciones flotantes y comunicados administrativos.
  - Se inyectaron los estilos CSS del banner neón fucsia y las animaciones `@keyframes floatUp` de emojis.

### 2. Archivos del Servidor (FastAPI)
- **[MODIFY] [main.py](file:///c:/Users/MSI/Documents/QrMusic/main.py)**: Se agregó e importó `CORSMiddleware` para habilitar peticiones cross-origin desde la interfaz de YouTube hacia la API local de QrMusic sin bloqueos de seguridad del navegador.
