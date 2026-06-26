"""
Panel de una evaluación concreta (1EVA, 2EVA o 3EVA — FINAL usa su propio
panel, ver panel_final.py).

El alumnado y los criterios se heredan de la materia (pestañas "Alumnos"
y "Criterios"); aquí no se editan. Sub-pestañas:

  - Calificaciones: tabla con la nota de cada criterio (calculada a
    partir de los instrumentos de evaluación) y la nota final de la
    materia, por alumno. Cada celda muestra la nota numérica y, entre
    paréntesis, la calificación cualitativa (IN/SU/BI/NT/SB), con un
    color de fondo en degradado rojo (nota baja) a verde (nota alta).
    Es de solo lectura: el resultado de agregar todos los instrumentos.
  - Instrumentos de Evaluación: donde se crean los IE y se introducen
    las notas que alimentan el cálculo anterior.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.calificacion import calificacion_cualitativa, color_hex_nota
from core.database import BaseDatosCurso, Evaluacion, Materia
from core.exportacion import exportar_evaluacion
from ui.dialogo_informes import DialogoGenerarInformes, generar_informe_evaluacion_individual
from ui.estilos import COLOR_COLUMNA_IDENTIDAD
from ui.panel_instrumentos import PanelInstrumentos
from ui.panel_estadisticas import PanelEstadisticas
from ui.panel_trazabilidad import PanelTrazabilidadEvaluacion
from ui.widgets_comunes import BotonAyuda
from ui.widgets_comunes import aplicar_cabeceras_por_bloque as _aplicar_cabeceras_por_bloque

COLOR_TEXTO_NO_EVALUADO = QColor("#A6B3C2")
COLOR_FONDO_IDENTIDAD = QColor(COLOR_COLUMNA_IDENTIDAD)

TEXTO_AYUDA_CALIFICACIONES = (
    "Esta tabla muestra el resultado calculado, sin que tengas que introducir nada aquí "
    "directamente: la nota de cada criterio se calcula combinando los instrumentos de "
    "evaluación que lo evalúan (pestaña «📝 Instrumentos de Evaluación»), y la nota final "
    "de la materia combina todos los criterios según su peso.\n\n"
    "Si no ves ninguna nota, lo más probable es que todavía no hayas creado ningún "
    "instrumento, o que no le hayas asignado ningún criterio.\n\n"
    "Puedes exportar esta tabla a Excel con el botón «📥 Exportar a Excel…», en dos "
    "formatos (hoja normal y traspuesta) para entregar a Jefatura de Estudios."
)


def _formatear_numero(valor: float | None) -> str:
    """Formatea una nota 0-10 con dos decimales y coma española. Cadena
    vacía si no hay nota.
    """
    if valor is None:
        return ""
    return f"{valor:.2f}".replace(".", ",")


def _color_para_nota(valor: float | None) -> QColor | None:
    color_hex = color_hex_nota(valor)
    return QColor(f"#{color_hex}") if color_hex else None


def _formatear_celda_nota(valor: float | None) -> tuple[str, QColor | None]:
    """Usado para las celdas de CRITERIO: solo nota numérica con dos
    decimales y el color degradado de fondo. (texto vacío, None) si no
    hay nota.
    """
    return _formatear_numero(valor), _color_para_nota(valor)


class TablaCalificaciones(QWidget):
    """Alumnos en filas; una columna por criterio de la materia con su nota
    calculada (0-10) en esta evaluación, y una última columna con la nota
    final de la materia. Todo en solo lectura: el resultado se edita desde
    la sub-pestaña de Instrumentos.
    """

    def __init__(self, base_datos: BaseDatosCurso, materia: Materia, evaluacion: Evaluacion):
        super().__init__()
        self.base_datos = base_datos
        self.materia = materia
        self.evaluacion = evaluacion

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        fila_titulo = QHBoxLayout()
        titulo = QLabel("📊 Calificaciones")
        titulo.setObjectName("subtitulo")
        fila_titulo.addWidget(titulo)
        fila_titulo.addStretch()
        fila_titulo.addWidget(BotonAyuda("Ayuda — Calificaciones", TEXTO_AYUDA_CALIFICACIONES))
        layout.addLayout(fila_titulo)

        self.aviso_sin_instrumentos = QLabel("")
        self.aviso_sin_instrumentos.setWordWrap(True)
        self.aviso_sin_instrumentos.setStyleSheet(
            "background-color: #FBE9CC; color: #5B4424; border-left: 4px solid #E8A33D; "
            "border-radius: 6px; padding: 10px;"
        )
        self.aviso_sin_instrumentos.setVisible(False)
        layout.addWidget(self.aviso_sin_instrumentos)

        self.tabla = QTableWidget()
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabla)

        nota = QLabel(
            "Las notas de cada criterio se calculan a partir de los instrumentos de "
            "evaluación (pestaña «📝 Instrumentos de Evaluación») y se muestran con dos "
            "decimales. Al final, dos columnas: la nota numérica de la materia y su "
            "calificación cualitativa (IN/SU/BI/NT/SB). Las celdas en blanco indican que "
            "el alumno/a todavía no tiene ninguna nota en ese criterio."
        )
        nota.setWordWrap(True)
        nota.setStyleSheet("color: #5B6B82;")
        layout.addWidget(nota)

        fila_botones = QHBoxLayout()
        boton_exportar = QPushButton("📥 Exportar a Excel…")
        boton_exportar.clicked.connect(self.exportar_a_excel)
        fila_botones.addWidget(boton_exportar)

        boton_informe = QPushButton("📄 Generar informe de alumno…")
        boton_informe.setObjectName("botonSecundario")
        boton_informe.clicked.connect(self.abrir_dialogo_informes)
        fila_botones.addWidget(boton_informe)

        fila_botones.addStretch()
        layout.addLayout(fila_botones)

        self.refrescar()

    def exportar_a_excel(self):
        nombre_sugerido = f"{self.materia.nombre} - {self.evaluacion.nombre}.xlsx"
        ruta_texto, _ = QFileDialog.getSaveFileName(
            self, "Exportar calificaciones a Excel", nombre_sugerido, filter="Excel (*.xlsx)"
        )
        if not ruta_texto:
            return
        ruta = Path(ruta_texto)
        if ruta.suffix.lower() != ".xlsx":
            ruta = ruta.with_suffix(".xlsx")
        try:
            exportar_evaluacion(self.base_datos, self.materia, self.evaluacion, ruta)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "No se pudo exportar", str(exc))
            return
        QMessageBox.information(self, "Exportación completada", f"Archivo guardado en:\n{ruta}")

    def abrir_dialogo_informes(self):
        vista = self.base_datos.listar_alumnos_para_evaluacion(self.materia.id, self.evaluacion.nombre)
        lista_alumnos = [
            (alumno.id, f"{alumno.apellidos}, {alumno.nombre}".strip(", "))
            for alumno, evaluable in vista
            if evaluable
        ]
        if not lista_alumnos:
            QMessageBox.information(
                self, "Sin alumnado", "No hay alumnado evaluable todavía en esta evaluación."
            )
            return

        def generar_uno(alumno_id, formato, carpeta_destino):
            return generar_informe_evaluacion_individual(
                self.base_datos, self.materia, self.evaluacion, alumno_id, formato, carpeta_destino
            )

        dialogo = DialogoGenerarInformes(
            f"Generar informe — {self.evaluacion.nombre}", lista_alumnos, generar_uno, self
        )
        dialogo.exec()

    def refrescar(self):
        instrumentos = self.base_datos.listar_instrumentos(self.evaluacion.id)
        if not instrumentos:
            self.aviso_sin_instrumentos.setText(
                "⚠️ Todavía no has creado ningún Instrumento de Evaluación (IE) en esta "
                "evaluación, así que no hay notas que mostrar. Un IE es la prueba o "
                "actividad con la que calificas a tu alumnado (un examen, una rúbrica de "
                "observación, varios trabajos...). Ve a la pestaña «📝 Instrumentos de "
                "Evaluación» para crear el primero."
            )
            self.aviso_sin_instrumentos.setVisible(True)
        else:
            self.aviso_sin_instrumentos.setVisible(False)

        criterios = self.base_datos.listar_criterios(self.materia.id)
        vista_alumnos = self.base_datos.listar_alumnos_para_evaluacion(
            self.materia.id, self.evaluacion.nombre
        )

        encabezados = (
            ["Apellidos", "Nombre"]
            + [c.codigo for c in criterios]
            + ["NOTA FINAL", "CALIFICACIÓN"]
        )
        self.tabla.setColumnCount(len(encabezados))
        self.tabla.setRowCount(len(vista_alumnos))
        col_final_numero = 2 + len(criterios)
        col_final_letra = col_final_numero + 1
        _aplicar_cabeceras_por_bloque(self.tabla, encabezados, col_final_numero)
        cabecera = self.tabla.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        cabecera.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in range(2, col_final_numero):
            cabecera.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.tabla.setColumnWidth(col, 70)
        cabecera.setSectionResizeMode(col_final_numero, QHeaderView.ResizeMode.Fixed)
        cabecera.setSectionResizeMode(col_final_letra, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(col_final_numero, 100)
        self.tabla.setColumnWidth(col_final_letra, 110)

        notas_criterio = self.base_datos.calcular_notas_criterios_evaluacion(
            self.evaluacion.id, self.materia.id
        )
        notas_materia = self.base_datos.calcular_notas_materia_evaluacion(
            self.evaluacion.id, self.materia.id
        )

        for fila, (alumno, evaluable_aqui) in enumerate(vista_alumnos):
            item_apellidos = QTableWidgetItem(alumno.apellidos)
            item_nombre = QTableWidgetItem(alumno.nombre)
            item_apellidos.setBackground(COLOR_FONDO_IDENTIDAD)
            item_nombre.setBackground(COLOR_FONDO_IDENTIDAD)
            self.tabla.setItem(fila, 0, item_apellidos)
            self.tabla.setItem(fila, 1, item_nombre)

            if not evaluable_aqui:
                for col in range(2, len(encabezados)):
                    item = QTableWidgetItem("— no evaluado/a aún —" if col == 2 else "")
                    item.setForeground(COLOR_TEXTO_NO_EVALUADO)
                    self.tabla.setItem(fila, col, item)
                item_apellidos.setForeground(COLOR_TEXTO_NO_EVALUADO)
                item_nombre.setForeground(COLOR_TEXTO_NO_EVALUADO)
                continue

            for indice_criterio, criterio in enumerate(criterios):
                valor = notas_criterio.get((criterio.id, alumno.id))
                texto, color = _formatear_celda_nota(valor)
                item = QTableWidgetItem(texto)
                if color is not None:
                    item.setBackground(color)
                self.tabla.setItem(fila, 2 + indice_criterio, item)

            valor_final = notas_materia.get(alumno.id)
            color_final = _color_para_nota(valor_final)

            item_numero_final = QTableWidgetItem(_formatear_numero(valor_final))
            item_letra_final = QTableWidgetItem(calificacion_cualitativa(valor_final))
            for item in (item_numero_final, item_letra_final):
                if color_final is not None:
                    item.setBackground(color_final)
                fuente = item.font()
                fuente.setBold(True)
                item.setFont(fuente)
            self.tabla.setItem(fila, col_final_numero, item_numero_final)
            self.tabla.setItem(fila, col_final_letra, item_letra_final)


class PanelEvaluacion(QWidget):
    """Panel completo de una evaluación: sub-pestañas "Calificaciones"
    (resultado calculado), "Instrumentos de Evaluación" (donde se
    introducen las notas) y "Estadísticas" (resumen IN/SU/BI/NT/SB y
    gráfico de notas por instrumento de un alumno).
    """

    def __init__(self, base_datos: BaseDatosCurso, materia: Materia, evaluacion: Evaluacion):
        super().__init__()
        self.base_datos = base_datos
        self.materia = materia
        self.evaluacion = evaluacion

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.sub_pestanas = QTabWidget()
        layout.addWidget(self.sub_pestanas)

        self.tabla_calificaciones = TablaCalificaciones(base_datos, materia, evaluacion)
        self.sub_pestanas.addTab(self.tabla_calificaciones, "📊 Calificaciones")

        self.panel_instrumentos = PanelInstrumentos(base_datos, materia, evaluacion)
        self.sub_pestanas.addTab(self.panel_instrumentos, "📝 Instrumentos de Evaluación")

        self.panel_estadisticas = PanelEstadisticas(
            titulo="📈 Estadísticas de la evaluación",
            obtener_notas_finales=self._obtener_notas_finales_para_estadisticas,
            obtener_lista_alumnos=self._obtener_lista_alumnos_evaluables,
            obtener_datos_grafico_alumno=self._obtener_datos_grafico_alumno,
            etiqueta_grafico="instrumento de evaluación",
            obtener_datos_grafico_todos=self._obtener_datos_grafico_todos,
        )
        self.sub_pestanas.addTab(self.panel_estadisticas, "📈 Estadísticas")

        self.panel_trazabilidad = PanelTrazabilidadEvaluacion(base_datos, materia, evaluacion)
        self.sub_pestanas.addTab(self.panel_trazabilidad, "🔗 Trazabilidad")

        self.sub_pestanas.currentChanged.connect(self._al_cambiar_sub_pestana)

    def _obtener_notas_finales_para_estadisticas(self) -> dict[int, float | None]:
        return self.base_datos.calcular_notas_materia_evaluacion(self.evaluacion.id, self.materia.id)

    def _obtener_lista_alumnos_evaluables(self) -> list[tuple[int, str]]:
        vista = self.base_datos.listar_alumnos_para_evaluacion(self.materia.id, self.evaluacion.nombre)
        return [
            (alumno.id, f"{alumno.apellidos}, {alumno.nombre}".strip(", "))
            for alumno, evaluable_aqui in vista
            if evaluable_aqui
        ]

    def _obtener_datos_grafico_alumno(self, alumno_id: int) -> tuple[list[str], list[float | None]]:
        instrumentos = self.base_datos.listar_instrumentos(self.evaluacion.id)
        etiquetas = [instrumento.nombre for instrumento in instrumentos]
        valores = [
            self.base_datos.nota_representativa_instrumento_para_alumno(instrumento, alumno_id)
            for instrumento in instrumentos
        ]
        return etiquetas, valores

    def _obtener_datos_grafico_todos(self) -> tuple[list[str], list[str], list[list[float | None]]]:
        instrumentos = self.base_datos.listar_instrumentos(self.evaluacion.id)
        etiquetas = [instrumento.nombre for instrumento in instrumentos]
        alumnos_evaluables = self._obtener_lista_alumnos_evaluables()
        nombres_alumnos = [etiqueta for _alumno_id, etiqueta in alumnos_evaluables]
        valores_por_alumno = [
            [
                self.base_datos.nota_representativa_instrumento_para_alumno(instrumento, alumno_id)
                for instrumento in instrumentos
            ]
            for alumno_id, _etiqueta in alumnos_evaluables
        ]
        return etiquetas, nombres_alumnos, valores_por_alumno

    def _al_cambiar_sub_pestana(self, _indice: int):
        self.tabla_calificaciones.refrescar()
        if self.sub_pestanas.currentWidget() is self.panel_estadisticas:
            self.panel_estadisticas.refrescar()
        elif self.sub_pestanas.currentWidget() is self.panel_trazabilidad:
            self.panel_trazabilidad.refrescar()

    def refrescar(self):
        self.tabla_calificaciones.refrescar()
        self.panel_instrumentos.refrescar_todo()
        self.panel_estadisticas.refrescar()
        self.panel_trazabilidad.refrescar()
