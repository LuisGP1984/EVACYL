"""
Panel "Evaluaciones" de la pestaña FINAL. Permite configurar el modo
de cálculo de la nota final de curso de esta materia.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database import BaseDatosCurso, Materia
from ui.widgets_comunes import TablaConBorrado, BotonAyuda

TEXTO_AYUDA = (
    "Elige cómo se calcula la nota FINAL de cada criterio a partir de sus notas en "
    "1EVA, 2EVA y 3EVA:\n\n"
    "• Evaluación continua: la evaluación más reciente con nota pesa muchísimo más "
    "que las anteriores (1/1000/1000000). Es el modelo LOMLOE puro: lo que importa "
    "es el nivel alcanzado al final del curso.\n\n"
    "• Media aritmética: todas las evaluaciones donde hay nota cuentan igual, sin "
    "importar cuándo se hicieron. Útil cuando cada evaluación cubre contenidos "
    "distintos (Prehistoria, Edad Media, Edad Contemporánea...).\n\n"
    "• Promedios porcentuales: tú defines el peso de cada evaluación. Si pones "
    "1/2/3, la primera evaluación vale 1/6, la segunda 2/6 y la tercera 3/6. "
    "Si un criterio no tiene nota en alguna evaluación, el peso de esa evaluación "
    "se redistribuye entre las que sí la tienen.\n\n"
    "• Personalizado por criterio: cada criterio puede tener su propio modo. "
    "Útil cuando en la misma materia unos criterios son competenciales (evaluación "
    "continua) y otros están ligados a contenidos concretos de cada trimestre "
    "(media aritmética). Si algún criterio elige «Promedios porcentuales», usará "
    "los pesos definidos en la sección de arriba.\n\n"
    "En todos los modos, si un criterio solo tiene nota en una evaluación, esa "
    "evaluación recibe automáticamente el 100% del peso para ese criterio."
)

ETIQUETAS_MODO = {
    "CONTINUA": "Evaluación continua",
    "MEDIA": "Media aritmética",
    "PORCENTUAL": "Promedios porcentuales",
    "PERSONALIZADO": "Personalizado por criterio",
}

# En modo PERSONALIZADO, "Igual que la materia" (HEREDADO) no aparece
# porque la materia no tiene un único modo que heredar.
ETIQUETAS_MODO_CRITERIO_PERSONALIZADO = {
    "CONTINUA": "Evaluación continua",
    "MEDIA": "Media aritmética",
    "PORCENTUAL": "Promedios porcentuales (usa los pesos de arriba)",
}

ICONOS_EVALUACION = {"1EVA": "1️⃣", "2EVA": "2️⃣", "3EVA": "3️⃣"}


class SeccionColapsable(QWidget):
    """Sección con título clicable que colapsa/expande su contenido."""

    def __init__(self, titulo: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._boton = QPushButton(f"▼  {titulo}")
        self._boton.setCheckable(True)
        self._boton.setChecked(True)
        self._boton.setStyleSheet(
            "text-align: left; padding: 6px 10px; font-weight: 600; "
            "color: #1A2E44; "
            "border: 1px solid #B0BEC5; border-radius: 4px; background: #E8EEF4;"
        )
        self._boton.clicked.connect(self._al_clicar)
        layout.addWidget(self._boton)

        self._contenedor = QWidget()
        self.layout_contenido = QVBoxLayout(self._contenedor)
        self.layout_contenido.setContentsMargins(0, 6, 0, 0)
        layout.addWidget(self._contenedor)

    def _al_clicar(self, expandido: bool):
        self._contenedor.setVisible(expandido)
        texto_base = self._boton.text()[3:]  # quita el icono actual
        self._boton.setText(f"{'▼' if expandido else '▶'}  {texto_base}")


class PanelEvaluacionesFinal(QWidget):

    def __init__(self, base_datos: BaseDatosCurso, materia: Materia):
        super().__init__()
        self.base_datos = base_datos
        self.materia = materia
        self._actualizando_desde_codigo = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        fila_titulo = QHBoxLayout()
        titulo = QLabel("⚖️ Modo de cálculo de la nota FINAL")
        titulo.setObjectName("subtitulo")
        fila_titulo.addWidget(titulo)
        fila_titulo.addStretch()
        fila_titulo.addWidget(BotonAyuda("Ayuda — Modo de cálculo FINAL", TEXTO_AYUDA))
        layout.addLayout(fila_titulo)

        # -- Selector de modo (radio buttons) --
        grupo_modo = QGroupBox("Modo de cálculo")
        layout_modo = QVBoxLayout(grupo_modo)
        layout_modo.setSpacing(8)
        self._botones_modo = QButtonGroup(self)
        for modo, etiqueta in ETIQUETAS_MODO.items():
            rb = QRadioButton(etiqueta)
            rb.setProperty("modo", modo)
            self._botones_modo.addButton(rb)
            layout_modo.addWidget(rb)
        self._botones_modo.buttonClicked.connect(self._al_cambiar_modo)
        layout.addWidget(grupo_modo)

        # -- Sección colapsable de pesos por evaluación --
        self._seccion_pesos = SeccionColapsable("Peso de cada evaluación (valores relativos)")
        self._tabla_pesos = TablaConBorrado()
        self._tabla_pesos.setColumnCount(2)
        self._tabla_pesos.setHorizontalHeaderLabels(["Evaluación", "Peso"])
        self._tabla_pesos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla_pesos.setAlternatingRowColors(True)
        self._tabla_pesos.setMaximumHeight(160)
        self._tabla_pesos.itemChanged.connect(self._al_cambiar_peso_evaluacion)
        self._seccion_pesos.layout_contenido.addWidget(self._tabla_pesos)
        layout.addWidget(self._seccion_pesos)

        # -- Tabla de modos por criterio (visible en PERSONALIZADO) --
        self._grupo_criterios = QGroupBox("Modo por criterio")
        layout_criterios = QVBoxLayout(self._grupo_criterios)

        nota_porcentual = QLabel(
            "ℹ️ Si un criterio usa «Promedios porcentuales», se aplican los pesos "
            "definidos en la sección de arriba."
        )
        nota_porcentual.setWordWrap(True)
        nota_porcentual.setStyleSheet("color: #5B6B82; font-size: 11px; padding: 2px 0 6px 0;")
        layout_criterios.addWidget(nota_porcentual)

        self._tabla_criterios = QTableWidget()
        self._tabla_criterios.setColumnCount(2)
        self._tabla_criterios.setHorizontalHeaderLabels(["Criterio", "Modo"])
        self._tabla_criterios.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._tabla_criterios.setColumnWidth(0, 100)
        self._tabla_criterios.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._tabla_criterios.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout_criterios.addWidget(self._tabla_criterios)
        layout.addWidget(self._grupo_criterios)

        # -- Deshacer último cambio de peso --
        self._ultimo_cambio_peso = None
        fila_deshacer = QHBoxLayout()
        self.boton_deshacer_peso = QPushButton("↩️ Deshacer último cambio de peso")
        self.boton_deshacer_peso.setObjectName("botonSecundario")
        self.boton_deshacer_peso.setVisible(False)
        self.boton_deshacer_peso.clicked.connect(self._deshacer_ultimo_cambio_peso)
        fila_deshacer.addWidget(self.boton_deshacer_peso)
        fila_deshacer.addStretch()
        layout.addLayout(fila_deshacer)

        layout.addStretch()
        self.refrescar()

    def refrescar(self):
        self._actualizando_desde_codigo = True
        modo = self.base_datos.obtener_modo_calculo_final(self.materia.id)

        # Radio button correcto
        for boton in self._botones_modo.buttons():
            if boton.property("modo") == modo:
                boton.setChecked(True)
                break

        # Tabla de pesos por evaluación
        pesos = self.base_datos.obtener_pesos_evaluaciones_final(self.materia.id)
        nombres = self.base_datos.NOMBRES_EVALUACIONES_PARA_FINAL
        self._tabla_pesos.setRowCount(len(nombres))
        for fila, nombre in enumerate(nombres):
            icono = ICONOS_EVALUACION.get(nombre, "")
            item_nombre = QTableWidgetItem(f"{icono} {nombre}".strip())
            item_nombre.setFlags(item_nombre.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_nombre.setData(Qt.ItemDataRole.UserRole, nombre)
            item_peso = QTableWidgetItem(str(pesos[nombre]))
            self._tabla_pesos.setItem(fila, 0, item_nombre)
            self._tabla_pesos.setItem(fila, 1, item_peso)

        # Tabla de modos por criterio: en PERSONALIZADO no se ofrece HEREDADO
        criterios = self.base_datos.listar_criterios(self.materia.id)
        self._tabla_criterios.setRowCount(len(criterios))
        for fila, criterio in enumerate(criterios):
            item_codigo = QTableWidgetItem(criterio.codigo)
            item_codigo.setData(Qt.ItemDataRole.UserRole, criterio.id)
            self._tabla_criterios.setItem(fila, 0, item_codigo)

            combo = QComboBox()
            for modo_c, etiqueta_c in ETIQUETAS_MODO_CRITERIO_PERSONALIZADO.items():
                combo.addItem(etiqueta_c, modo_c)

            # Si el criterio tiene HEREDADO, lo tratamos como MEDIA
            # (valor más neutral) ahora que HEREDADO no aparece en la lista
            modo_criterio = criterio.modo_calculo_final
            if modo_criterio == "HEREDADO":
                modo_criterio = "MEDIA"
                self.base_datos.actualizar_modo_calculo_criterio(criterio.id, "MEDIA")

            indice = combo.findData(modo_criterio)
            if indice >= 0:
                combo.setCurrentIndex(indice)
            combo.currentIndexChanged.connect(
                lambda _idx, cid=criterio.id, cb=combo: self._al_cambiar_modo_criterio(cid, cb)
            )
            self._tabla_criterios.setCellWidget(fila, 1, combo)

        # Visibilidad de secciones según el modo
        self._seccion_pesos.setVisible(modo in ("PORCENTUAL", "PERSONALIZADO"))
        self._grupo_criterios.setVisible(modo == "PERSONALIZADO")

        self._actualizando_desde_codigo = False

    def _al_cambiar_modo(self, boton: QRadioButton):
        if self._actualizando_desde_codigo:
            return
        modo = boton.property("modo")
        self.base_datos.actualizar_modo_calculo_final(self.materia.id, modo)
        self.refrescar()

    def _al_cambiar_peso_evaluacion(self, item: QTableWidgetItem):
        if self._actualizando_desde_codigo:
            return
        fila = item.row()
        item_nombre = self._tabla_pesos.item(fila, 0)
        item_peso = self._tabla_pesos.item(fila, 1)
        if item_nombre is None:
            return
        nombre_evaluacion = item_nombre.data(Qt.ItemDataRole.UserRole)
        texto_peso = item_peso.text() if item_peso else "1"
        try:
            peso = float(texto_peso.replace(",", ".")) if texto_peso.strip() != "" else 1.0
        except ValueError:
            QMessageBox.warning(self, "Peso no válido", "El peso debe ser un número. Se usará 1.")
            peso = 1.0

        peso_anterior = self.base_datos.obtener_pesos_evaluaciones_final(self.materia.id).get(nombre_evaluacion, 1.0)
        if peso != peso_anterior:
            self._ultimo_cambio_peso = (nombre_evaluacion, peso_anterior)
            self.boton_deshacer_peso.setText(f"↩️ Deshacer cambio de peso de {nombre_evaluacion}")
            self.boton_deshacer_peso.setVisible(True)

        self.base_datos.actualizar_peso_evaluacion_final(self.materia.id, nombre_evaluacion, peso)
        self.refrescar()

    def _al_cambiar_modo_criterio(self, criterio_id: int, combo: QComboBox):
        if self._actualizando_desde_codigo:
            return
        modo = combo.currentData()
        self.base_datos.actualizar_modo_calculo_criterio(criterio_id, modo)

    def _deshacer_ultimo_cambio_peso(self):
        if self._ultimo_cambio_peso is None:
            return
        nombre_evaluacion, peso_anterior = self._ultimo_cambio_peso
        self.base_datos.actualizar_peso_evaluacion_final(self.materia.id, nombre_evaluacion, peso_anterior)
        self._ultimo_cambio_peso = None
        self.boton_deshacer_peso.setVisible(False)
        self.refrescar()
