# EVACYL — Decimocuarta entrega

*Evaluación que conecta · Futuro que transforma*

Aplicación de escritorio para gestionar la evaluación por competencias
(criterios de evaluación, alumnado, instrumentos de evaluación, cálculo
de calificaciones, exportación a Excel, currículo oficial, informes de
alumno, etc.) curso por curso, materia por materia. Todos los datos
quedan en tu ordenador — no se envía nada a internet.

## Qué cambia respecto a la entrega anterior

- **Corregido el campo de peso engañoso en "¿Qué criterios evalúa este
  instrumento?"**: antes, un criterio sin marcar mostraba un porcentaje
  (el peso global del instrumento) aunque ese instrumento no evaluara
  ese criterio. Ahora se muestra un guion (—) cuando no está marcado,
  para no dar la falsa impresión de que ya tiene un peso asignado.

- **Nuevo: informe de calificaciones por alumno.** En la pestaña
  "📊 Calificaciones" de cada evaluación (1EVA/2EVA/3EVA) y de FINAL, el
  botón "📄 Generar informe de alumno…" abre un diálogo donde eliges:
  - Un alumno concreto, o toda la clase de golpe (un archivo por alumno).
  - Formato PDF o Word (.docx).

  El informe incluye nombre y apellidos, la evaluación, la nota de cada
  criterio (numérica y cualitativa), y el desglose por instrumento de
  evaluación con sus pesos — pensado para que el alumno o su familia
  entiendan de dónde sale cada nota, también de cara a reclamaciones.
  En FINAL, el informe desglosa además cada criterio por evaluación
  (1EVA/2EVA/3EVA) junto al resultado combinado.

El modelo de datos no ha cambiado: puedes seguir usando el mismo
`curso.db` que ya tenías.

## Importante: nuevas dependencias

Esta entrega añade dos librerías nuevas (para generar PDF y Word). Si ya
tenías el proyecto instalado, vuelve a ejecutar:
```
pip install -r requirements.txt
```
antes de abrir la aplicación, o el informe no se podrá generar.

## Instalación en Windows

1. Instala Python si no lo tienes: ve a https://www.python.org/downloads/
   y descarga la última versión. **Importante:** durante la instalación,
   marca la casilla "Add Python to PATH" antes de pulsar "Install Now".

2. Descomprime esta carpeta del proyecto **en una ubicación nueva**
   (no la mezcles con una entrega anterior).

3. Abre el "Símbolo del sistema" (cmd) o "PowerShell" y navega a esa carpeta:
   ```
   cd C:\Aplicaciones\EVACYL
   ```

4. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```

5. Ejecuta la aplicación:
   ```
   python main.py
   ```

## Notas para probarlo

- Puedes reutilizar el `curso.db` de la entrega anterior, pero recuerda
  instalar las dependencias nuevas (ver arriba) antes de abrir la app.
- Abre un instrumento con varios criterios y comprueba que los que NO
  están marcados muestran "—" en el peso, no un número.
- En "📊 Calificaciones" de una evaluación, pulsa "📄 Generar informe de
  alumno…": prueba primero con un alumno concreto en PDF, luego con
  "Toda la clase" en Word, y revisa el contenido de los archivos
  generados.
- Haz lo mismo en FINAL y comprueba que el informe desglosa cada
  criterio por 1EVA/2EVA/3EVA además de la nota combinada.

## Estructura del proyecto

```
evaluacion_app/
├── main.py                          ← arranque de la aplicación (4 pantallas)
├── recursos/
│   ├── fondo.png                    ← imagen de fondo de inicio y materias (EVACYL)
│   ├── logo.png                     ← logo completo, usado en la pantalla de bienvenida
│   ├── logo_ies.png                 ← logo del IES Virgen de la Calle (colaboración)
│   └── icono_app.ico                ← icono de la aplicación (Windows)
├── datos_curriculares/
│   └── curriculo_lomloe_cyl.json    ← currículo oficial: Primaria, Secundaria, Bachillerato
├── core/
│   ├── database.py                  ← lógica de datos (SQLite) y motor de
│   │                                   cálculo de calificaciones
│   ├── calificacion.py              ← calificación cualitativa, color y validación 0-10
│   ├── exportacion.py               ← generación de Excel (normal y traspuesta)
│   ├── importacion.py               ← lectura de Excel y de texto pegado
│   ├── plantillas.py                ← generación de plantillas de ejemplo
│   ├── curriculo.py                 ← acceso al currículo oficial y referencias normativas
│   ├── configuracion.py             ← recuerda la carpeta de trabajo entre ejecuciones
│   ├── rutas_app.py                 ← resolución de rutas (normal y empaquetada con PyInstaller)
│   ├── respaldo.py                  ← copias de seguridad automáticas de curso.db
│   ├── estadisticas.py              ← conteo y % de IN/SU/BI/NT/SB
│   ├── informe_alumno.py            ← recopilación de datos para el informe de un alumno
│   ├── informe_pdf.py               ← generación del informe en PDF
│   └── informe_docx.py              ← generación del informe en Word
├── ui/
│   ├── estilos.py                    ← paleta azul-verde EVACYL, colores por pestaña, columna y cabecera
│   ├── widgets_comunes.py            ← tabla con borrado por teclado, ventana con fondo,
│   │                                   cabeceras coloreadas, botón de ayuda, sección plegable
│   ├── grafico_barras.py             ← gráfico de barras (un alumno o toda la clase agrupada)
│   ├── ventana_bienvenida.py         ← pantalla de presentación (logo, autor, licencia, colaboración IES)
│   ├── ventana_carpeta_docente.py    ← elegir/recordar la carpeta de trabajo
│   ├── ventana_inicio.py             ← lista de cursos académicos dentro de la carpeta
│   ├── ventana_curso.py               ← pantalla de materias dentro de un curso (con copias de seguridad)
│   ├── ventana_materia.py             ← pestañas: Alumnos, Criterios, 1EVA...FINAL
│   ├── panel_alumnos.py               ← gestión de alumnado de la materia
│   ├── panel_criterios.py             ← gestión de criterios de la materia
│   ├── dialogo_asistente_curricular.py ← asistente etapa/curso/materia
│   ├── panel_evaluacion.py            ← sub-pestañas Calificaciones / Instrumentos / Estadísticas / Trazabilidad
│   ├── panel_instrumentos.py          ← lista de instrumentos de una evaluación
│   ├── panel_detalle_instrumento.py   ← configuración y notas de un instrumento
│   ├── panel_estadisticas.py          ← tabla IN/SU/BI/NT/SB y gráfico por alumno o por clase
│   ├── panel_trazabilidad.py          ← qué IE evalúa cada criterio / en qué evaluación se evaluó
│   ├── dialogo_informes.py            ← generación de informes de alumno (PDF/Word, individual o de clase)
│   ├── panel_final.py                 ← panel de FINAL (Calificaciones / Evaluaciones / Estadísticas / Trazabilidad)
│   └── panel_evaluaciones_final.py    ← pesos de 1EVA/2EVA/3EVA para FINAL
├── empaquetado.spec                 ← configuración de PyInstaller (genera EVACYL.exe)
├── instalador_windows.iss           ← script de Inno Setup (genera el instalador final)
├── COMO_GENERAR_INSTALADOR.md       ← guía paso a paso para crear el instalador
└── requirements.txt
```

## ¿Quieres distribuirla como instalador de Windows?

Si quieres compartir la aplicación con otros docentes como un instalador
normal (doble clic, sin Python ni cmd), sigue la guía
`COMO_GENERAR_INSTALADOR.md` incluida en esta misma carpeta. Resumen:

1. `pyinstaller empaquetado.spec` genera `EVACYL.exe` con todo lo
   necesario, incluido el nuevo icono.
2. Inno Setup (gratuito) convierte ese `.exe` en un instalador completo,
   con icono propio, accesos directos y desinstalador.

## Si algo no funciona

Cuéntamelo con el mensaje de error exacto que te aparezca en la consola
(la ventana negra de cmd/PowerShell) y lo arreglamos.
