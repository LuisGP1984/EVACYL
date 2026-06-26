# Cómo generar el instalador de Windows

Esta guía explica cómo convertir la aplicación en un instalador normal
de Windows (`Instalador_EVACYL.exe`), que cualquier compañero docente
pueda ejecutar con doble clic, sin tocar cmd ni instalar Python. Se hace
en **tu** ordenador, una sola vez por cada versión nueva que quieras
distribuir; el resultado ya es autónomo.

Son dos fases: primero PyInstaller convierte el código Python en un
`.exe`; después Inno Setup empaqueta ese `.exe` en un instalador de
verdad (con icono, accesos directos y desinstalador).

## Fase 1 — Generar el ejecutable con PyInstaller

1. Asegúrate de que la aplicación funciona normalmente con
   `python main.py` antes de empezar (si hay un error aquí, también lo
   habrá en el empaquetado).

2. Instala PyInstaller (solo la primera vez):
   ```
   pip install pyinstaller
   ```

3. Desde la carpeta del proyecto (`evaluacion_app`), ejecuta:
   ```
   pyinstaller empaquetado.spec
   ```

4. Espera a que termine (puede tardar uno o dos minutos). Al acabar,
   tendrás una carpeta nueva:
   ```
   dist\EVACYL\
   ```
   Dentro está `EVACYL.exe` junto con todo lo que necesita para
   funcionar (incluida la imagen de fondo, el logo y el currículo
   oficial — el archivo `.spec` ya se encarga de incluirlos).

5. **Prueba este `.exe` antes de seguir**: haz doble clic en
   `dist\EVACYL\EVACYL.exe` y comprueba que la aplicación arranca y
   funciona igual que con `python main.py`. Si algo falla aquí, es más
   fácil solucionarlo antes de pasar a la fase 2.

## Fase 2 — Crear el instalador con Inno Setup

1. Descarga e instala Inno Setup (gratuito): busca "Inno Setup download"
   o ve directamente a https://jrsoftware.org/isdl.php — descarga la
   última versión estable e instálala con las opciones por defecto.

2. Abre el archivo `instalador_windows.iss` (que está en la carpeta del
   proyecto) con Inno Setup: clic derecho sobre el archivo →
   "Abrir con" → "Inno Setup Compiler" (o ábrelo primero y luego
   "Archivo → Abrir" dentro del programa).

3. Dentro de Inno Setup, pulsa el botón **"Compile"** (o el menú
   "Build → Compile", o simplemente `Ctrl+F9`).

4. Si todo va bien, en unos segundos aparecerá un mensaje de éxito y se
   habrá creado una carpeta nueva:
   ```
   instalador_salida\Instalador_EVACYL.exe
   ```

Ese archivo es **el instalador final**. Puedes enviarlo a cualquier
compañero docente: al ejecutarlo, verá un asistente de instalación
normal de Windows (elegir carpeta, crear acceso directo en el escritorio
si quiere, etc.), y al terminar tendrá la aplicación en su menú de
inicio, con icono propio, lista para usar — sin haber tocado Python ni
la línea de comandos en ningún momento.

## Si quieres cambiar la versión más adelante

Cuando yo te dé una nueva entrega de la aplicación y quieras generar un
instalador actualizado:

1. Sustituye los archivos del proyecto por los nuevos (como siempre).
2. Repite la Fase 1 (`pyinstaller empaquetado.spec`).
3. Repite la Fase 2 (abrir el `.iss` y pulsar Compile).

Si quieres que el número de versión se vea distinto en cada entrega
(por ejemplo, "1.1", "1.2"...), puedes cambiar la línea
`#define MiVersion "1.0"` al principio de `instalador_windows.iss` antes
de compilar.

## Solución de problemas habituales

- **"No se encuentra el módulo PySide6" al ejecutar el .exe generado**:
  asegúrate de haber instalado las dependencias (`pip install -r
  requirements.txt`) en el mismo entorno de Python desde el que ejecutas
  PyInstaller.
- **El icono no aparece o aparece genérico**: comprueba que el archivo
  `recursos/icono_app.ico` existe en la carpeta del proyecto antes de
  ejecutar `pyinstaller empaquetado.spec`.
- **Falla "no se encuentra recursos/fondo.png" al abrir el .exe
  generado**: significa que el `.spec` no incluyó la carpeta `recursos`
  correctamente; revisa que ejecutas `pyinstaller empaquetado.spec`
  exactamente como se indica (no `pyinstaller main.py` directamente, que
  no usa esta configuración).
- **Inno Setup da error "no se encuentra dist\EVACYL"**: significa que
  la Fase 1 no se completó correctamente antes de pasar a la Fase 2.
  Repite la Fase 1 y comprueba que la carpeta `dist\...` existe y tiene
  el `.exe` dentro.
