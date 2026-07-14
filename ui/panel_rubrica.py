"""
Panel de configuración de una Rúbrica (IE de tipo RUBRICA).

Se divide en tres secciones, mostradas como sub-pestañas:

  1. Niveles de logro: el docente define la escala (Excelente=10,
     Notable=7.5...). Se pueden añadir, editar y reordenar.

  2. Criterios e indicadores: lista de los criterios vinculados a esta
     rúbrica, con un campo de texto opcional por criterio donde el
     docente describe el indicador de logro concreto para esta actividad.

  3. Grupos de alumnos: el docente agrupa a los alumnos de la materia.
     Los alumnos sin grupo aparecen en una lista a la izquierda; los
     grupos creados aparecen a la derecha. Se pueden crear grupos, añadir
     y quitar alumnos, y renombrarlos.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database import BaseDatosCurso, InstrumentoEvaluacion, Materia
from ui.widgets_comunes import BotonAyuda

TEXTO_AYUDA_NIVELES = (
    "Define la escala de calificación de esta rúbrica: cuántos niveles tiene, "
    "cómo se llaman y qué nota numérica corresponde a cada uno.\n\n"
    "Ejemplos:\n"
    "• Excelente=10 / Notable=7.5 / Suficiente=5 / Insuficiente=2.5\n"
    "• Nivel 4=10 / Nivel 3=7 / Nivel 2=5 / Nivel 1=3\n\n"
    "El orden importa: el primer nivel de la lista es el más alto. "
    "Puedes reordenarlos con los botones ▲▼."
)

TEXTO_AYUDA_INDICADORES = (
    "Para cada criterio marcado en esta rúbrica, puedes escribir un "
    "indicador de logro: una descripción concreta de qué se evalúa "
    "en esta actividad para ese criterio.\n\n"
    "Es opcional: si lo dejas en blanco, el criterio se evaluará "
    "directamente por niveles sin descripción adicional."
)

TEXTO_AYUDA_GRUPOS = (
    "Agrupa a los alumnos para esta rúbrica. Cada grupo recibirá una "
    "calificación conjunta en la pantalla de calificación, que podrás "
    "ajustar individualmente para cada miembro si lo necesitas.\n\n"
    "Los alumnos sin grupo aparecen a la izquierda. Selecciona uno o "
    "varios y pulsa «➡» para añadirlos al grupo seleccionado a la derecha, "
    "o crea un grupo nuevo con «➕ Nuevo grupo».\n\n"
    "Los alumnos que no pertenezcan a ningún grupo no tendrán nota en "
    "esta rúbrica."
)


class PanelRubrica(QWidget):
    """Panel completo de configuración de una rúbrica (niveles,
    indicadores y grupos). Se muestra en la pantalla de detalle del IE
    cuando su tipo es RUBRICA.
    """

    def __init__(
        self, base_datos: BaseDatosCurso, materia: Materia,
        instrumento: InstrumentoEvaluacion
    ):
        super().__init__()
        self.base_datos = base_datos
        self.materia = materia
        self.instrumento = instrumento

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.sub_pestanas = QTabWidget()
        layout.addWidget(self.sub_pestanas)

        self._panel_niveles = _PanelNiveles(base_datos, instrumento)
        self._panel_indicadores = _PanelIndicadores(base_datos, materia, instrumento)
        self._panel_grupos = _PanelGrupos(base_datos, materia, instrumento)

        self.sub_pestanas.addTab(self._panel_niveles, "🏆 Niveles de logro")
        self.sub_pestanas.addTab(self._panel_indicadores, "📝 Indicadores")
        self.sub_pestanas.addTab(self._panel_grupos, "👥 Grupos")

    def refrescar(self):
        self._panel_niveles.refrescar()
        self._panel_indicadores.refrescar()
        self._panel_grupos.refrescar()


# ---------------------------------------------------------------------------
# Sub-panel 1: Niveles de logro
# ---------------------------------------------------------------------------

class _PanelNiveles(QWidget):

    def __init__(self, base_datos: BaseDatosCurso, instrumento: InstrumentoEvaluacion):
        super().__init__()
        self.base_datos = base_datos
        self.instrumento = instrumento
        self._actualizando = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        fila_titulo = QHBoxLayout()
        fila_titulo.addWidget(QLabel("Define la escala de calificación de esta rúbrica:"))
        fila_titulo.addStretch()
        fila_titulo.addWidget(BotonAyuda("Ayuda — Niveles de logro", TEXTO_AYUDA_NIVELES))
        layout.addLayout(fila_titulo)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["Etiqueta", "Nota numérica (0-10)", ""])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(1, 160)
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(2, 80)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabla)

        fila_botones = QHBoxLayout()
        boton_anadir = QPushButton("➕ Añadir nivel")
        boton_anadir.clicked.connect(self._anadir_nivel)
        fila_botones.addWidget(boton_anadir)
        fila_botones.addStretch()
        layout.addLayout(fila_botones)

        self.refrescar()

    def refrescar(self):
        self._actualizando = True
        niveles = self.base_datos.listar_rubrica_niveles(self.instrumento.id)
        self.tabla.setRowCount(len(niveles))
        for fila, nivel in enumerate(niveles):
            # Etiqueta editable
            campo_etiqueta = QLineEdit(nivel.etiqueta)
            campo_etiqueta.setFrame(False)
            campo_etiqueta.editingFinished.connect(
                lambda nid=nivel.id, campo=campo_etiqueta, val=nivel.valor_numerico:
                    self._guardar_nivel(nid, campo.text(), val)
            )
            self.tabla.setCellWidget(fila, 0, campo_etiqueta)

            # Nota numérica editable
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 10.0)
            spin.setDecimals(2)
            spin.setValue(nivel.valor_numerico)
            spin.setFrame(False)
            spin.editingFinished.connect(
                lambda nid=nivel.id, etiqueta=nivel.etiqueta, s=spin:
                    self._guardar_nivel(nid, etiqueta, s.value())
            )
            self.tabla.setCellWidget(fila, 1, spin)

            # Botón eliminar
            boton_eliminar = QPushButton("🗑")
            boton_eliminar.setFixedWidth(36)
            boton_eliminar.clicked.connect(
                lambda checked=False, nid=nivel.id: self._eliminar_nivel(nid)
            )
            self.tabla.setCellWidget(fila, 2, boton_eliminar)

        self._actualizando = False

    def _guardar_nivel(self, nivel_id: int, etiqueta: str, valor: float):
        if not etiqueta.strip():
            return
        self.base_datos.actualizar_rubrica_nivel(nivel_id, etiqueta, valor)

    def _eliminar_nivel(self, nivel_id: int):
        respuesta = QMessageBox.question(
            self, "Eliminar nivel",
            "¿Eliminar este nivel de logro? Las notas de grupo/alumno que usaran "
            "este nivel quedarán sin nivel asignado.",
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        self.base_datos.eliminar_rubrica_nivel(nivel_id)
        self.refrescar()

    def _anadir_nivel(self):
        etiqueta, ok = QInputDialog.getText(self, "Nuevo nivel", "Etiqueta del nivel:")
        if not ok or not etiqueta.strip():
            return
        valor, ok2 = QInputDialog.getDouble(
            self, "Valor numérico", f"Nota numérica para «{etiqueta.strip()}» (0-10):",
            5.0, 0.0, 10.0, 2
        )
        if not ok2:
            return
        niveles = self.base_datos.listar_rubrica_niveles(self.instrumento.id)
        orden = len(niveles) + 1
        self.base_datos.agregar_rubrica_nivel(self.instrumento.id, etiqueta.strip(), valor, orden)
        self.refrescar()

    def showEvent(self, event):
        super().showEvent(event)
        self.refrescar()


# ---------------------------------------------------------------------------
# Sub-panel 2: Indicadores de logro por criterio
# ---------------------------------------------------------------------------

class _PanelIndicadores(QWidget):

    def __init__(
        self, base_datos: BaseDatosCurso, materia: Materia,
        instrumento: InstrumentoEvaluacion
    ):
        super().__init__()
        self.base_datos = base_datos
        self.materia = materia
        self.instrumento = instrumento

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        fila_titulo = QHBoxLayout()
        fila_titulo.addWidget(QLabel("Indicadores de logro por criterio (opcionales):"))
        fila_titulo.addStretch()
        fila_titulo.addWidget(BotonAyuda("Ayuda — Indicadores", TEXTO_AYUDA_INDICADORES))
        layout.addLayout(fila_titulo)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(2)
        self.tabla.setHorizontalHeaderLabels(["Criterio", "Indicador de logro (opcional)"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(0, 100)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabla)

        self.refrescar()

    def refrescar(self):
        # Solo los criterios marcados en este IE
        relaciones = self.base_datos.listar_criterios_de_instrumento(self.instrumento.id)
        criterios_marcados_ids = {r.criterio_id for r in relaciones}
        criterios = [c for c in self.base_datos.listar_criterios(self.materia.id)
                     if c.id in criterios_marcados_ids]

        self.tabla.setRowCount(len(criterios))
        for fila, criterio in enumerate(criterios):
            item_codigo = QTableWidgetItem(criterio.codigo)
            item_codigo.setFlags(item_codigo.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tabla.setItem(fila, 0, item_codigo)

            indicador_actual = self.base_datos.obtener_rubrica_indicador(
                self.instrumento.id, criterio.id
            )
            campo = QLineEdit(indicador_actual)
            campo.setPlaceholderText("Describe aquí el indicador de logro para esta actividad…")
            campo.setFrame(False)
            campo.editingFinished.connect(
                lambda cid=criterio.id, c=campo:
                    self.base_datos.guardar_rubrica_indicador(self.instrumento.id, cid, c.text())
            )
            self.tabla.setCellWidget(fila, 1, campo)

        self.tabla.setMinimumHeight(min(32 * (len(criterios) + 1) + 10, 300))

    def showEvent(self, event):
        super().showEvent(event)
        self.refrescar()


# ---------------------------------------------------------------------------
# Sub-panel 3: Grupos de alumnos
# ---------------------------------------------------------------------------

class _PanelGrupos(QWidget):

    def __init__(
        self, base_datos: BaseDatosCurso, materia: Materia,
        instrumento: InstrumentoEvaluacion
    ):
        super().__init__()
        self.base_datos = base_datos
        self.materia = materia
        self.instrumento = instrumento

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        fila_titulo = QHBoxLayout()
        fila_titulo.addWidget(QLabel("Asigna los alumnos a grupos para esta rúbrica:"))
        fila_titulo.addStretch()
        fila_titulo.addWidget(BotonAyuda("Ayuda — Grupos", TEXTO_AYUDA_GRUPOS))
        layout.addLayout(fila_titulo)

        # Zona principal: sin grupo (izq) | botones | grupos (der)
        zona = QHBoxLayout()

        # -- Sin grupo --
        grupo_sin = QGroupBox("Sin grupo")
        layout_sin = QVBoxLayout(grupo_sin)
        self.lista_sin_grupo = QListWidget()
        self.lista_sin_grupo.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout_sin.addWidget(self.lista_sin_grupo)
        zona.addWidget(grupo_sin, stretch=2)

        # -- Botones centrales --
        botones_centro = QVBoxLayout()
        botones_centro.addStretch()
        boton_anadir_al_grupo = QPushButton("➡")
        boton_anadir_al_grupo.setToolTip("Añadir al grupo seleccionado")
        boton_anadir_al_grupo.clicked.connect(self._anadir_al_grupo)
        botones_centro.addWidget(boton_anadir_al_grupo)
        boton_quitar_del_grupo = QPushButton("⬅")
        boton_quitar_del_grupo.setToolTip("Quitar del grupo (vuelve a «Sin grupo»)")
        boton_quitar_del_grupo.clicked.connect(self._quitar_del_grupo)
        botones_centro.addWidget(boton_quitar_del_grupo)
        botones_centro.addStretch()
        zona.addLayout(botones_centro)

        # -- Grupos --
        grupo_grupos = QGroupBox("Grupos")
        layout_grupos = QVBoxLayout(grupo_grupos)

        fila_nuevo_grupo = QHBoxLayout()
        boton_nuevo_grupo = QPushButton("➕ Nuevo grupo")
        boton_nuevo_grupo.clicked.connect(self._crear_grupo)
        fila_nuevo_grupo.addWidget(boton_nuevo_grupo)
        boton_renombrar = QPushButton("✏️ Renombrar")
        boton_renombrar.clicked.connect(self._renombrar_grupo)
        fila_nuevo_grupo.addWidget(boton_renombrar)
        boton_eliminar_grupo = QPushButton("🗑 Eliminar")
        boton_eliminar_grupo.clicked.connect(self._eliminar_grupo)
        fila_nuevo_grupo.addWidget(boton_eliminar_grupo)
        layout_grupos.addLayout(fila_nuevo_grupo)

        self.lista_grupos = QListWidget()
        self.lista_grupos.currentItemChanged.connect(self._al_cambiar_grupo)
        layout_grupos.addWidget(self.lista_grupos)

        self.lista_miembros = QListWidget()
        self.lista_miembros.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.lista_miembros.setMaximumHeight(120)
        layout_grupos.addWidget(QLabel("Miembros del grupo seleccionado:"))
        layout_grupos.addWidget(self.lista_miembros)

        zona.addWidget(grupo_grupos, stretch=3)
        layout.addLayout(zona)

        self.refrescar()

    def refrescar(self):
        # Sin grupo
        sin_grupo = self.base_datos.alumnos_sin_grupo(self.instrumento.id, self.materia.id)
        self.lista_sin_grupo.clear()
        for alumno in sin_grupo:
            item = QListWidgetItem(f"{alumno.apellidos}, {alumno.nombre}".strip(", "))
            item.setData(Qt.ItemDataRole.UserRole, alumno.id)
            self.lista_sin_grupo.addItem(item)

        # Grupos
        grupo_actual_id = None
        item_actual = self.lista_grupos.currentItem()
        if item_actual:
            grupo_actual_id = item_actual.data(Qt.ItemDataRole.UserRole)

        grupos = self.base_datos.listar_rubrica_grupos(self.instrumento.id)
        self.lista_grupos.clear()
        indice_restaurar = 0
        for idx, grupo in enumerate(grupos):
            miembros = self.base_datos.alumnos_de_grupo(grupo.id)
            item = QListWidgetItem(f"{grupo.nombre}  ({len(miembros)} alumnos)")
            item.setData(Qt.ItemDataRole.UserRole, grupo.id)
            self.lista_grupos.addItem(item)
            if grupo.id == grupo_actual_id:
                indice_restaurar = idx

        if grupos:
            self.lista_grupos.setCurrentRow(indice_restaurar)
        self._refrescar_miembros()

    def _refrescar_miembros(self):
        self.lista_miembros.clear()
        item_actual = self.lista_grupos.currentItem()
        if item_actual is None:
            return
        grupo_id = item_actual.data(Qt.ItemDataRole.UserRole)
        for alumno in self.base_datos.alumnos_de_grupo(grupo_id):
            item = QListWidgetItem(f"{alumno.apellidos}, {alumno.nombre}".strip(", "))
            item.setData(Qt.ItemDataRole.UserRole, alumno.id)
            self.lista_miembros.addItem(item)

    def _al_cambiar_grupo(self, _nuevo, _anterior):
        self._refrescar_miembros()

    def _grupo_seleccionado_id(self) -> int | None:
        item = self.lista_grupos.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _crear_grupo(self):
        nombre, ok = QInputDialog.getText(self, "Nuevo grupo", "Nombre del grupo:")
        if not ok or not nombre.strip():
            return
        self.base_datos.agregar_rubrica_grupo(self.instrumento.id, nombre.strip())
        self.refrescar()

    def _renombrar_grupo(self):
        grupo_id = self._grupo_seleccionado_id()
        if grupo_id is None:
            return
        item = self.lista_grupos.currentItem()
        nombre_actual = item.text().split("  (")[0]
        nombre_nuevo, ok = QInputDialog.getText(
            self, "Renombrar grupo", "Nuevo nombre:", text=nombre_actual
        )
        if not ok or not nombre_nuevo.strip():
            return
        self.base_datos.renombrar_rubrica_grupo(grupo_id, nombre_nuevo.strip())
        self.refrescar()

    def _eliminar_grupo(self):
        grupo_id = self._grupo_seleccionado_id()
        if grupo_id is None:
            return
        respuesta = QMessageBox.question(
            self, "Eliminar grupo",
            "¿Eliminar este grupo? Los alumnos volverán a «Sin grupo» y se borrarán "
            "las notas de este grupo en la rúbrica.",
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        self.base_datos.eliminar_rubrica_grupo(grupo_id)
        self.refrescar()

    def _anadir_al_grupo(self):
        grupo_id = self._grupo_seleccionado_id()
        if grupo_id is None:
            QMessageBox.information(self, "Sin grupo", "Selecciona primero un grupo a la derecha.")
            return
        seleccionados = self.lista_sin_grupo.selectedItems()
        if not seleccionados:
            return
        for item in seleccionados:
            alumno_id = item.data(Qt.ItemDataRole.UserRole)
            self.base_datos.agregar_alumno_a_grupo(grupo_id, alumno_id)
        self.refrescar()

    def _quitar_del_grupo(self):
        grupo_id = self._grupo_seleccionado_id()
        if grupo_id is None:
            return
        seleccionados = self.lista_miembros.selectedItems()
        if not seleccionados:
            return
        for item in seleccionados:
            alumno_id = item.data(Qt.ItemDataRole.UserRole)
            self.base_datos.quitar_alumno_de_grupo(grupo_id, alumno_id)
        self.refrescar()

    def showEvent(self, event):
        super().showEvent(event)
        self.refrescar()
