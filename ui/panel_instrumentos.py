"""
Panel "Instrumentos de Evaluación" de una evaluación concreta (1EVA, 2EVA
o 3EVA — FINAL no tiene instrumentos propios). Muestra la lista de IE
creados, su tipo y su peso, avisa si los pesos no suman 100%, y permite
entrar en el detalle de cada uno (criterios, pruebas, notas).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database import (
    BaseDatosCurso,
    Evaluacion,
    Materia,
    TIPO_EXAMEN,
    TIPO_MANUAL,
    TIPO_MEDIA_ARITMETICA,
    TIPO_MEDIA_PONDERADA,
    TIPO_RUBRICA,
    TIPOS_INSTRUMENTO,
)
from ui.panel_detalle_instrumento import PanelDetalleInstrumento

ETIQUETAS_TIPO = {
    TIPO_MANUAL: "Manual",
    TIPO_MEDIA_ARITMETICA: "Varias pruebas — media aritmética",
    TIPO_MEDIA_PONDERADA: "Varias pruebas — media ponderada",
    TIPO_EXAMEN: "Examen",
    TIPO_RUBRICA: "Rúbrica",
}

ICONOS_TIPO = {
    TIPO_MANUAL: "✍️",
    TIPO_MEDIA_ARITMETICA: "📐",
    TIPO_MEDIA_PONDERADA: "⚖️",
    TIPO_EXAMEN: "📄",
    TIPO_RUBRICA: "🏆",
}

DESCRIPCIONES_TIPO = {
    TIPO_MANUAL: "Introduces directamente la nota (0-10) de cada criterio para cada alumno/a. "
    "Útil para rúbricas de observación, trabajos valorados de forma global, etc.",
    TIPO_MEDIA_ARITMETICA: "Añades varias pruebas (las que quieras) y la app calcula la media "
    "simple de sus notas. Útil para varios controles cortos que pesan lo mismo.",
    TIPO_MEDIA_PONDERADA: "Como la media aritmética, pero cada prueba tiene su propio peso "
    "(deben sumar 100% entre todas). Útil cuando unas pruebas valen más que otras.",
    TIPO_EXAMEN: "Introduces la nota de un examen sobre la puntuación máxima que tú indiques "
    "(10, 8, 9...) y la app la reescala automáticamente a la escala 0-10.",
    TIPO_RUBRICA: "Defines niveles de logro (Excelente, Notable...) con su nota numérica, "
    "indicadores opcionales por criterio, y grupos de alumnos. La calificación de cada "
    "grupo se propaga automáticamente a sus miembros, con ajuste individual si lo necesitas.",
}


class DialogoNuevoInstrumento(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo instrumento de evaluación")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        formulario = QFormLayout()
        formulario.setVerticalSpacing(14)
        formulario.setContentsMargins(0, 8, 0, 8)

        self.campo_nombre = QLineEdit()
        self.campo_nombre.setMinimumHeight(32)
        formulario.addRow("Nombre:", self.campo_nombre)

        self.combo_tipo = QComboBox()
        self.combo_tipo.setMinimumHeight(32)
        for tipo in TIPOS_INSTRUMENTO:
            self.combo_tipo.addItem(f"{ICONOS_TIPO[tipo]} {ETIQUETAS_TIPO[tipo]}", tipo)
        self.combo_tipo.currentIndexChanged.connect(self._actualizar_descripcion)
        formulario.addRow("Tipo:", self.combo_tipo)

        layout.addLayout(formulario)

        self.etiqueta_descripcion = QLabel("")
        self.etiqueta_descripcion.setWordWrap(True)
        self.etiqueta_descripcion.setStyleSheet(
            "color: #2E7D4F; background-color: #EAF6EE; border-radius: 6px; padding: 8px;"
        )
        layout.addWidget(self.etiqueta_descripcion)
        self._actualizar_descripcion()

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _actualizar_descripcion(self):
        tipo = self.combo_tipo.currentData()
        self.etiqueta_descripcion.setText(DESCRIPCIONES_TIPO.get(tipo, ""))

    def datos(self) -> tuple[str, str]:
        return self.campo_nombre.text().strip(), self.combo_tipo.currentData()


class PanelInstrumentos(QWidget):
    COLUMNAS = ["Nombre", "Tipo", "Peso (%)"]

    def __init__(self, base_datos: BaseDatosCurso, materia: Materia, evaluacion: Evaluacion):
        super().__init__()
        self.base_datos = base_datos
        self.materia = materia
        self.evaluacion = evaluacion
        self._actualizando_desde_codigo = False

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)

        self.apilado = QStackedWidget()
        layout_raiz.addWidget(self.apilado)

        # -- página 0: lista de instrumentos --
        self.pagina_lista = QWidget()
        layout = QVBoxLayout(self.pagina_lista)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        titulo = QLabel("📝 Instrumentos de evaluación")
        titulo.setObjectName("subtitulo")
        layout.addWidget(titulo)

        explicacion = QLabel(
            "Un <b>Instrumento de Evaluación (IE)</b> es cada prueba o actividad con la que "
            "calificas a tu alumnado: un examen, una rúbrica de observación, un trabajo, "
            "varios controles cortos... Para que aparezcan notas en «📊 Calificaciones», "
            "primero necesitas crear aquí al menos un IE, marcar qué criterios evalúa y "
            "rellenar las notas del alumnado dentro de él."
        )
        explicacion.setWordWrap(True)
        explicacion.setStyleSheet(
            "background-color: #EAF6EE; color: #1B5E3A; border-radius: 6px; padding: 10px;"
        )
        layout.addWidget(explicacion)

        self.etiqueta_suma_pesos = QLabel("")
        layout.addWidget(self.etiqueta_suma_pesos)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.itemChanged.connect(self._al_cambiar_celda)
        self.tabla.itemDoubleClicked.connect(lambda _item: self.abrir_instrumento_seleccionado())
        layout.addWidget(self.tabla)

        ayuda = QLabel(
            "Doble clic en un instrumento para configurar sus criterios, pruebas y notas. "
            "Si solo hay un instrumento, su peso se fija en 100% automáticamente."
        )
        ayuda.setWordWrap(True)
        ayuda.setStyleSheet("color: #5B6B82;")
        layout.addWidget(ayuda)

        fila_botones = QHBoxLayout()
        boton_crear = QPushButton("➕ Crear instrumento")
        boton_crear.clicked.connect(self.crear_instrumento)
        fila_botones.addWidget(boton_crear)

        boton_abrir = QPushButton("🔍 Abrir seleccionado")
        boton_abrir.setObjectName("botonSecundario")
        boton_abrir.clicked.connect(self.abrir_instrumento_seleccionado)
        fila_botones.addWidget(boton_abrir)

        boton_eliminar = QPushButton("🗑️ Eliminar seleccionado")
        boton_eliminar.setObjectName("botonPeligro")
        boton_eliminar.clicked.connect(self.eliminar_instrumento_seleccionado)
        fila_botones.addWidget(boton_eliminar)

        self._ultima_captura_eliminacion = None
        self.boton_deshacer = QPushButton("↩️ Deshacer")
        self.boton_deshacer.setObjectName("botonSecundario")
        self.boton_deshacer.setEnabled(False)
        self.boton_deshacer.clicked.connect(self.deshacer_ultima_eliminacion)
        fila_botones.addWidget(self.boton_deshacer)

        # Último cambio de PESO de un instrumento (distinto del deshacer
        # de eliminación de arriba).
        self._ultimo_cambio_peso = None  # (instrumento_id, peso_anterior) | None
        self.boton_deshacer_peso = QPushButton("↩️ Deshacer último cambio de peso")
        self.boton_deshacer_peso.setObjectName("botonSecundario")
        self.boton_deshacer_peso.setVisible(False)
        self.boton_deshacer_peso.clicked.connect(self._deshacer_ultimo_cambio_peso)
        fila_botones.addWidget(self.boton_deshacer_peso)

        fila_botones.addStretch()
        layout.addLayout(fila_botones)

        self.apilado.addWidget(self.pagina_lista)

        self.refrescar()

    def _deshacer_ultimo_cambio_peso(self):
        if self._ultimo_cambio_peso is None:
            return
        instrumento_id, peso_anterior = self._ultimo_cambio_peso
        instrumento_actual = next(
            (i for i in self.base_datos.listar_instrumentos(self.evaluacion.id) if i.id == instrumento_id),
            None,
        )
        if instrumento_actual is not None:
            self.base_datos.actualizar_instrumento(
                instrumento_id, instrumento_actual.nombre, peso_anterior, instrumento_actual.nota_maxima
            )
        self._ultimo_cambio_peso = None
        self.boton_deshacer_peso.setVisible(False)
        self.refrescar()

    # -- lista ------------------------------------------------------------

    def refrescar(self):
        self._actualizando_desde_codigo = True
        instrumentos = self.base_datos.listar_instrumentos(self.evaluacion.id)
        self.tabla.setRowCount(len(instrumentos))
        for fila, instrumento in enumerate(instrumentos):
            item_nombre = QTableWidgetItem(instrumento.nombre)
            item_nombre.setData(Qt.ItemDataRole.UserRole, instrumento.id)
            item_tipo = QTableWidgetItem(
                f"{ICONOS_TIPO.get(instrumento.tipo, '')} {ETIQUETAS_TIPO.get(instrumento.tipo, instrumento.tipo)}"
            )
            item_tipo.setFlags(item_tipo.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_peso = QTableWidgetItem(str(instrumento.peso))

            self.tabla.setItem(fila, 0, item_nombre)
            self.tabla.setItem(fila, 1, item_tipo)
            self.tabla.setItem(fila, 2, item_peso)
        self._actualizando_desde_codigo = False

        suma = self.base_datos.suma_pesos_instrumentos(self.evaluacion.id)
        if not instrumentos:
            self.etiqueta_suma_pesos.setText("Todavía no hay instrumentos de evaluación creados.")
            self.etiqueta_suma_pesos.setStyleSheet("color: #5B6B82;")
        elif abs(suma - 100.0) < 0.01:
            self.etiqueta_suma_pesos.setText(f"Suma de pesos: {suma:.1f}% ✓")
            self.etiqueta_suma_pesos.setStyleSheet("color: #2E7D32; font-weight: bold;")
        else:
            self.etiqueta_suma_pesos.setText(
                f"⚠ Suma de pesos: {suma:.1f}% — los pesos de todos los instrumentos deben sumar 100%."
            )
            self.etiqueta_suma_pesos.setStyleSheet("color: #B23B3B; font-weight: bold;")

    def _al_cambiar_celda(self, item: QTableWidgetItem):
        if self._actualizando_desde_codigo:
            return
        fila = item.row()
        item_nombre = self.tabla.item(fila, 0)
        item_peso = self.tabla.item(fila, 2)
        if item_nombre is None:
            return
        instrumento_id = item_nombre.data(Qt.ItemDataRole.UserRole)
        if instrumento_id is None:
            return

        instrumento = next(
            (i for i in self.base_datos.listar_instrumentos(self.evaluacion.id) if i.id == instrumento_id),
            None,
        )
        if instrumento is None:
            return

        nombre = item_nombre.text()
        texto_peso = item_peso.text() if item_peso else "0"
        try:
            peso = float(texto_peso.replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "Peso no válido", "El peso debe ser un número. Se usará 0.")
            peso = 0.0

        if peso != instrumento.peso:
            self._ultimo_cambio_peso = (instrumento_id, instrumento.peso)
            self.boton_deshacer_peso.setText(f"↩️ Deshacer cambio de peso de «{instrumento.nombre}»")
            self.boton_deshacer_peso.setVisible(True)

        try:
            self.base_datos.actualizar_instrumento(instrumento_id, nombre, peso, instrumento.nota_maxima)
        except ValueError as exc:
            QMessageBox.warning(self, "Dato no válido", str(exc))
        self.refrescar()

    # -- acciones -----------------------------------------------------------

    def crear_instrumento(self):
        dialogo = DialogoNuevoInstrumento(self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        nombre, tipo = dialogo.datos()
        if not nombre:
            QMessageBox.warning(self, "Falta el nombre", "Escribe un nombre para el instrumento.")
            return
        self.base_datos.crear_instrumento(self.evaluacion.id, nombre, tipo)
        self.refrescar()

    def eliminar_instrumento_seleccionado(self):
        fila = self.tabla.currentRow()
        if fila < 0:
            QMessageBox.information(self, "Sin selección", "Selecciona primero un instrumento.")
            return
        item_nombre = self.tabla.item(fila, 0)
        instrumento_id = item_nombre.data(Qt.ItemDataRole.UserRole) if item_nombre else None
        if instrumento_id is None:
            return
        nombre_instrumento = item_nombre.text()
        respuesta = QMessageBox.question(
            self,
            "Confirmar eliminación",
            "Esto borrará el instrumento y todas sus notas. Podrás deshacerlo justo "
            "después si te equivocas. ¿Continuar?",
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        self._ultima_captura_eliminacion = self.base_datos.eliminar_instrumento_con_deshacer(instrumento_id)
        self.boton_deshacer.setEnabled(self._ultima_captura_eliminacion is not None)
        self.boton_deshacer.setText(f"↩️ Deshacer eliminación de «{nombre_instrumento}»")
        self.refrescar()

    def deshacer_ultima_eliminacion(self):
        if self._ultima_captura_eliminacion is None:
            return
        self.base_datos.restaurar_eliminacion(self._ultima_captura_eliminacion)
        self._ultima_captura_eliminacion = None
        self.boton_deshacer.setEnabled(False)
        self.boton_deshacer.setText("↩️ Deshacer")
        self.refrescar()

    def abrir_instrumento_seleccionado(self):
        fila = self.tabla.currentRow()
        if fila < 0:
            QMessageBox.information(self, "Sin selección", "Selecciona primero un instrumento.")
            return
        item_nombre = self.tabla.item(fila, 0)
        instrumento_id = item_nombre.data(Qt.ItemDataRole.UserRole) if item_nombre else None
        if instrumento_id is None:
            return
        instrumento = next(
            (i for i in self.base_datos.listar_instrumentos(self.evaluacion.id) if i.id == instrumento_id),
            None,
        )
        if instrumento is None:
            return

        panel_detalle = PanelDetalleInstrumento(
            self.base_datos, self.materia, instrumento, self.evaluacion.nombre, self._volver_a_lista
        )
        # Sustituimos cualquier página de detalle anterior por la nueva.
        while self.apilado.count() > 1:
            widget_viejo = self.apilado.widget(1)
            self.apilado.removeWidget(widget_viejo)
            widget_viejo.deleteLater()
        self.apilado.addWidget(panel_detalle)
        self.apilado.setCurrentWidget(panel_detalle)

    def _volver_a_lista(self):
        self.apilado.setCurrentWidget(self.pagina_lista)
        self.refrescar()

    def refrescar_todo(self):
        """Refresca tanto la lista como, si está abierto, el panel de detalle."""
        if self.apilado.currentWidget() is self.pagina_lista:
            self.refrescar()
