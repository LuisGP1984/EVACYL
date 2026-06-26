"""
Panel "📈 Estadísticas" de una evaluación o de FINAL: una tabla con el
número y porcentaje de alumnos en cada categoría cualitativa (IN/SU/BI/
NT/SB), y un gráfico de barras con las notas —de un alumno elegido, o de
todos los alumnos a la vez agrupados— en cada instrumento de evaluación
(para 1EVA/2EVA/3EVA) o en cada evaluación (para FINAL).
"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.calificacion import color_hex_nota
from core.estadisticas import calcular_estadisticas
from ui.grafico_barras import GraficoBarras
from ui.widgets_comunes import BotonAyuda

TEXTO_AYUDA_ESTADISTICAS = (
    "Esta pestaña resume las calificaciones del grupo:\n\n"
    "• La tabla de arriba muestra cuántos alumnos (y qué porcentaje) caen en cada "
    "categoría cualitativa: IN, SU, BI, NT, SB. Los alumnos sin nota final todavía no "
    "se incluyen en el porcentaje.\n\n"
    "• El gráfico de abajo muestra las notas en cada instrumento de evaluación (o en cada "
    "evaluación, en el caso de FINAL). Puedes elegir un alumno concreto, o «Todos los "
    "alumnos» para comparar a todo el grupo de un vistazo, agrupados por instrumento o "
    "evaluación. Las barras discontinuas indican que no hay nota."
)

# Un valor "típico" de cada categoría, solo para elegir el color de fondo
# de la columna correspondiente en la tabla resumen.
_VALOR_REPRESENTATIVO_CATEGORIA = {"IN": 2.5, "SU": 5.5, "BI": 6.5, "NT": 8.0, "SB": 9.5}

_OPCION_TODOS_LOS_ALUMNOS = "__TODOS__"


class PanelEstadisticas(QWidget):
    """Panel genérico de estadísticas. Quien lo use debe proporcionar:
      - obtener_notas_finales() -> {alumno_id: nota|None}
      - obtener_lista_alumnos() -> [(alumno_id, etiqueta), ...]
      - obtener_datos_grafico_alumno(alumno_id) -> (etiquetas, valores)
        para alimentar el gráfico de un solo alumno
      - obtener_datos_grafico_todos() -> (etiquetas, nombres_alumnos, valores_por_alumno)
        para alimentar el gráfico agrupado de todos los alumnos
    """

    def __init__(
        self,
        titulo: str,
        obtener_notas_finales,
        obtener_lista_alumnos,
        obtener_datos_grafico_alumno,
        etiqueta_grafico: str,
        obtener_datos_grafico_todos=None,
    ):
        super().__init__()
        self._obtener_notas_finales = obtener_notas_finales
        self._obtener_lista_alumnos = obtener_lista_alumnos
        self._obtener_datos_grafico_alumno = obtener_datos_grafico_alumno
        self._obtener_datos_grafico_todos = obtener_datos_grafico_todos
        self._etiqueta_grafico = etiqueta_grafico

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        fila_titulo = QHBoxLayout()
        etiqueta_titulo = QLabel(titulo)
        etiqueta_titulo.setObjectName("subtitulo")
        fila_titulo.addWidget(etiqueta_titulo)
        fila_titulo.addStretch()
        fila_titulo.addWidget(BotonAyuda("Ayuda — Estadísticas", TEXTO_AYUDA_ESTADISTICAS))
        layout.addLayout(fila_titulo)

        self.tabla_resumen = QTableWidget()
        self.tabla_resumen.setColumnCount(5)
        self.tabla_resumen.setHorizontalHeaderLabels(["IN", "SU", "BI", "NT", "SB"])
        self.tabla_resumen.setRowCount(2)
        self.tabla_resumen.setVerticalHeaderLabels(["Nº de alumnos", "% del total"])
        self.tabla_resumen.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_resumen.setMaximumHeight(110)
        self.tabla_resumen.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabla_resumen)

        self.etiqueta_totales = QLabel("")
        self.etiqueta_totales.setStyleSheet("color: #5B6B82;")
        layout.addWidget(self.etiqueta_totales)

        fila_selector = QHBoxLayout()
        fila_selector.addWidget(QLabel(f"Ver notas por {etiqueta_grafico} de:"))
        self.combo_alumno = QComboBox()
        if self._obtener_datos_grafico_todos is not None:
            self.combo_alumno.addItem("👥 Todos los alumnos", _OPCION_TODOS_LOS_ALUMNOS)
        self.combo_alumno.currentIndexChanged.connect(self._al_cambiar_alumno_seleccionado)
        fila_selector.addWidget(self.combo_alumno)
        fila_selector.addStretch()
        layout.addLayout(fila_selector)

        self.grafico = GraficoBarras()
        layout.addWidget(self.grafico)

        self.refrescar()

    def refrescar(self):
        notas_finales = self._obtener_notas_finales()
        estadisticas = calcular_estadisticas(notas_finales)

        for columna, categoria_stat in enumerate(estadisticas.categorias):
            item_cantidad = QTableWidgetItem(str(categoria_stat.cantidad))
            item_porcentaje = QTableWidgetItem(f"{categoria_stat.porcentaje:g}%")
            valor_tipico = _VALOR_REPRESENTATIVO_CATEGORIA[categoria_stat.categoria]
            color_hex = color_hex_nota(valor_tipico)
            if color_hex:
                color = QColor(f"#{color_hex}")
                item_cantidad.setBackground(color)
                item_porcentaje.setBackground(color)
            self.tabla_resumen.setItem(0, columna, item_cantidad)
            self.tabla_resumen.setItem(1, columna, item_porcentaje)

        self.etiqueta_totales.setText(
            f"Total con nota final: {estadisticas.total_con_nota}    ·    "
            f"Sin nota todavía: {estadisticas.total_sin_nota}"
        )

        seleccion_actual = self.combo_alumno.currentData()
        self.combo_alumno.blockSignals(True)
        self.combo_alumno.clear()
        if self._obtener_datos_grafico_todos is not None:
            self.combo_alumno.addItem("👥 Todos los alumnos", _OPCION_TODOS_LOS_ALUMNOS)
        for alumno_id, etiqueta in self._obtener_lista_alumnos():
            self.combo_alumno.addItem(etiqueta, alumno_id)
        if seleccion_actual is not None:
            indice = self.combo_alumno.findData(seleccion_actual)
            if indice >= 0:
                self.combo_alumno.setCurrentIndex(indice)
        self.combo_alumno.blockSignals(False)

        self._actualizar_grafico()

    def _al_cambiar_alumno_seleccionado(self, _indice: int):
        self._actualizar_grafico()

    def _actualizar_grafico(self):
        seleccion = self.combo_alumno.currentData()
        if seleccion is None:
            self.grafico.establecer_datos([], [], "")
            return

        if seleccion == _OPCION_TODOS_LOS_ALUMNOS:
            etiquetas, nombres_alumnos, valores_por_alumno = self._obtener_datos_grafico_todos()
            self.grafico.establecer_datos_agrupados(
                etiquetas, nombres_alumnos, valores_por_alumno, "Notas de todo el alumnado"
            )
            return

        etiquetas, valores = self._obtener_datos_grafico_alumno(seleccion)
        nombre_alumno = self.combo_alumno.currentText()
        self.grafico.establecer_datos(etiquetas, valores, f"Notas de {nombre_alumno}")
