# EVACYL

**Evaluación que conecta · Futuro que transforma**

Aplicación de escritorio para Windows que ayuda al profesorado a gestionar la evaluación por competencias (LOMLOE) en Castilla y León: define criterios de evaluación, instrumentos de evaluación, calcula automáticamente las calificaciones, exporta a Excel y genera informes individuales para el alumnado.

Cubre **Educación Primaria, Educación Secundaria Obligatoria, Bachillerato** y **Educación Secundaria para Personas Adultas (ESPA)**.

## 📥 Descarga e instalación

1. Ve a la sección [**Releases**](../../releases) de este repositorio.
2. Descarga el archivo `Instalador_EVACYL.exe` de la última versión.
3. Ejecútalo y sigue el asistente de instalación (no requiere permisos de administrador).
4. Al terminar, encontrarás **EVACYL** en el menú de inicio de Windows.

📖 También puedes descargar la **guía del docente en PDF** desde la misma sección de Releases, con explicaciones paso a paso e imágenes de cada pantalla.

## ✨ Qué incluye

- Currículo oficial de Castilla y León integrado: los criterios de evaluación se pueden rellenar automáticamente eligiendo etapa, curso y materia (o ámbito y módulo, en el caso de ESPA), sin tener que copiarlos a mano.
- Cuatro tipos de instrumentos de evaluación: manual, examen, media aritmética y media ponderada.
- Cálculo automático de calificaciones por criterio y nota final, con redistribución dinámica de pesos cuando varios instrumentos evalúan el mismo criterio.
- Estadísticas del grupo y gráficos comparativos.
- Trazabilidad: qué instrumento evalúa cada criterio, y en qué evaluación.
- Exportación a Excel.
- Informes individuales de alumno en PDF y Word, pensados también para posibles reclamaciones.
- Copias de seguridad automáticas y sistema de deshacer.
- Todos los datos se guardan en tu propio ordenador — la aplicación no necesita conexión a internet.

## 🛠️ Para desarrolladores

El código fuente completo está en este repositorio. Si quieres ejecutarlo directamente con Python en lugar de usar el instalador:

```
pip install -r requirements.txt
python main.py
```

Si quieres generar tú mismo el `.exe` y el instalador, consulta [`COMO_GENERAR_INSTALADOR.md`](COMO_GENERAR_INSTALADOR.md).

## 👤 Autor

**Luis González Posada**
📧 luis.gonpos@educa.jcyl.es

Con la colaboración del IES Virgen de la Calle, en Palencia.

## 📄 Licencia

Esta obra puede reutilizarse citando al autor y sin fines lucrativos (CC BY-NC).
