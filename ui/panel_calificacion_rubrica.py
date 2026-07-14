"""
Panel de calificación de una Rúbrica.

Flujo:
  1. El docente elige el grupo desde un desplegable.
  2. Ve una tabla donde:
       - Filas = criterios marcados en este IE (con indicador si lo tiene).
       - Primera columna = calificación del GRUPO: selector de nivel + ajuste.
       - Columnas siguientes = un miembro del grupo por columna: selector de
         nivel propio (por defecto "Igual que el grupo") + ajuste individual.
  3. Al cambiar cualquier valor, se guarda inmediatamente en la BD y se
     propagan las notas al sistema existente (nota_criterio_instrumento_alumno).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database import BaseDatosCurso, InstrumentoEvaluacion, Materia
from ui.widgets_comunes import BotonAyuda

TEXTO_AYUDA = (
    "Califica cada criterio para el grupo seleccionado:\n\n"
    "• La columna «Grupo» asigna el nivel y la nota a TODOS los miembros "
    "del grupo a la vez.\n\n"
    "• Las columnas individuales permiten ajustar la calificación de un "
    "alumno concreto si su aportación fue distinta a la del grupo. "
    "Si dejas el nivel en «Igual que el grupo», ese alumno hereda "
    "automáticamente la nota del grupo.\n\n"
    "• Si defines un nivel pero quieres ajustar la nota numérica (por "
    "ejemplo, «Notable» pero con un 8 en vez del 7.5 por defecto), "
    "edita el campo numérico junto al nivel.\n\n"
    "Los cambios se guardan automáticamente."
)

OPCION_IGUAL_QUE_GRUPO = "__GRUPO__"


class PanelCalificacionRubrica(QWidget):

    def __init__(
        self, base_datos: BaseDatosCurso, materia: Materia,
        instrumento: InstrumentoEvaluacion
    ):
        super().__init__()
        self.base_datos = base_datos
        self.materia = materia
        self.instrumento = instrumento
        self._actualizando = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # -- Cabecera --
        fila_cabecera = QHBoxLayout()
        fila_cabecera.addWidget(QLabel("Grupo:"))
        self.combo_grupo = QComboBox()
        self.combo_grupo.setMinimumWidth(180)
        self.combo_grupo.currentIndexChanged.connect(self._al_cambiar_grupo)
        fila_cabecera.addWidget(self.combo_grupo)
        fila_cabecera.addStretch()
        fila_cabecera.addWidget(BotonAyuda("Ayuda — Calificación de rúbrica", TEXTO_AYUDA))
        layout.addLayout(fila_cabecera)

        self.etiqueta_sin_grupos = QLabel(
            "⚠️ Todavía no hay grupos definidos para esta rúbrica. "
            "Ve a la pestaña «👥 Grupos» para crear los grupos y asignar alumnos."
        )
        self.etiqueta_sin_grupos.setWordWrap(True)
        self.etiqueta_sin_grupos.setStyleSheet(
            "background: #FDF3E7; color: #7A1B08; border-left: 4px solid #E68415; "
            "border-radius: 4px; padding: 8px;"
        )
        layout.addWidget(self.etiqueta_sin_grupos)

        self.tabla = QTableWidget()
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.verticalHeader().setDefaultSectionSize(58)
        layout.addWidget(self.tabla)

        self._cargar_grupos()

    # -- carga inicial -------------------------------------------------------

    def _cargar_grupos(self):
        grupos = self.base_datos.listar_rubrica_grupos(self.instrumento.id)
        self._actualizando = True
        self.combo_grupo.clear()
        for grupo in grupos:
            self.combo_grupo.addItem(grupo.nombre, grupo.id)
        self._actualizando = False

        tiene_grupos = bool(grupos)
        self.etiqueta_sin_grupos.setVisible(not tiene_grupos)
        self.combo_grupo.setVisible(tiene_grupos)
        self.tabla.setVisible(tiene_grupos)

        if tiene_grupos:
            self._construir_tabla()

    def _al_cambiar_grupo(self, _indice: int):
        if not self._actualizando:
            self._construir_tabla()

    # -- construcción de la tabla --------------------------------------------

    def _construir_tabla(self):
        grupo_id = self.combo_grupo.currentData()
        if grupo_id is None:
            return

        self._actualizando = True

        niveles = self.base_datos.listar_rubrica_niveles(self.instrumento.id)
        relaciones = self.base_datos.listar_criterios_de_instrumento(self.instrumento.id)
        criterios_ids = {r.criterio_id for r in relaciones}
        criterios = [c for c in self.base_datos.listar_criterios(self.materia.id)
                     if c.id in criterios_ids]
        miembros = self.base_datos.alumnos_de_grupo(grupo_id)

        if not niveles:
            self.tabla.setRowCount(1)
            self.tabla.setColumnCount(1)
            self.tabla.setHorizontalHeaderLabels([""])
            item = QTableWidgetItem(
                "⚠️ Define primero los niveles de logro en la pestaña «🏆 Niveles de logro»."
            )
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tabla.setItem(0, 0, item)
            self._actualizando = False
            return

        # Columnas: Criterio | Grupo | Miembro1 | Miembro2 ...
        encabezados = ["Criterio", f"🎯 {self.combo_grupo.currentText()}"] + \
                      [f"{a.apellidos}\n{a.nombre}" for a in miembros]
        self.tabla.setColumnCount(len(encabezados))
        self.tabla.setHorizontalHeaderLabels(encabezados)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(0, 100)
        for col in range(1, len(encabezados)):
            self.tabla.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        self.tabla.setRowCount(len(criterios))

        for fila, criterio in enumerate(criterios):
            # -- Columna 0: código + indicador --
            indicador = self.base_datos.obtener_rubrica_indicador(self.instrumento.id, criterio.id)
            texto_criterio = criterio.codigo
            if indicador:
                texto_criterio += f"\n{indicador}"
            item_cod = QTableWidgetItem(texto_criterio)
            item_cod.setFlags(item_cod.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tabla.setItem(fila, 0, item_cod)

            # -- Columna 1: calificación del grupo --
            nota_grupo = self.base_datos.obtener_nota_grupo_rubrica(grupo_id, criterio.id)
            celda_grupo = self._crear_celda_nivel(
                niveles, nota_grupo.nivel_id if nota_grupo else None,
                nota_grupo.nota_ajustada if nota_grupo else None,
                es_grupo=True,
                grupo_id=grupo_id, criterio_id=criterio.id,
                alumno_id=None, nivel_grupo_id=None
            )
            self.tabla.setCellWidget(fila, 1, celda_grupo)

            # -- Columnas siguientes: ajuste individual por miembro --
            for col_offset, alumno in enumerate(miembros, start=2):
                cur = self.base_datos.conexion.execute(
                    "SELECT nivel_id, nota_ajustada FROM rubrica_nota_alumno "
                    "WHERE grupo_id = ? AND alumno_id = ? AND criterio_id = ?;",
                    (grupo_id, alumno.id, criterio.id)
                )
                fila_alumno = cur.fetchone()
                nivel_alumno = fila_alumno[0] if fila_alumno else None
                ajuste_alumno = fila_alumno[1] if fila_alumno else None

                nivel_grupo_id = nota_grupo.nivel_id if nota_grupo else None
                celda_alumno = self._crear_celda_nivel(
                    niveles, nivel_alumno, ajuste_alumno,
                    es_grupo=False,
                    grupo_id=grupo_id, criterio_id=criterio.id,
                    alumno_id=alumno.id, nivel_grupo_id=nivel_grupo_id
                )
                self.tabla.setCellWidget(fila, col_offset, celda_alumno)

        self._actualizando = False

    def _crear_celda_nivel(
        self, niveles, nivel_id_actual, nota_ajustada_actual,
        es_grupo: bool, grupo_id: int, criterio_id: int,
        alumno_id: int | None, nivel_grupo_id: int | None
    ) -> QWidget:
        """Crea el widget de una celda: combo de niveles + etiqueta + spinbox de ajuste."""
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        combo = QComboBox()
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        if not es_grupo:
            combo.addItem("↑ Igual que el grupo", OPCION_IGUAL_QUE_GRUPO)

        for nivel in niveles:
            combo.addItem(f"{nivel.etiqueta}  ({nivel.valor_numerico:g})", nivel.id)

        if nivel_id_actual is None:
            combo.setCurrentIndex(0)
        else:
            indice = combo.findData(nivel_id_actual)
            if indice >= 0:
                combo.setCurrentIndex(indice)

        # Etiqueta y spinbox de ajuste — siempre visibles, claramente opcionales
        etiqueta_ajuste = QLabel("Ajuste:")
        etiqueta_ajuste.setStyleSheet("color: #8A7A6E; font-size: 11px;")

        spin = QDoubleSpinBox()
        spin.setRange(0.0, 10.0)
        spin.setDecimals(2)
        spin.setFixedWidth(68)
        spin.setToolTip(
            "Ajuste numérico opcional: si lo dejas en 0, se usa la nota del nivel elegido. "
            "Si introduces un valor, ese valor sustituye a la nota del nivel."
        )
        spin.setValue(nota_ajustada_actual if nota_ajustada_actual is not None else 0.0)
        spin.setSpecialValueText("—")

        def _al_cambiar(
            _=None, c=combo, s=spin,
            gid=grupo_id, cid=criterio_id, aid=alumno_id, eg=es_grupo
        ):
            if self._actualizando:
                return
            nivel_elegido = c.currentData()
            nota_ajustada = s.value() if s.value() > 0.0 else None

            if eg:
                nivel_id = nivel_elegido if nivel_elegido != OPCION_IGUAL_QUE_GRUPO else None
                self.base_datos.guardar_nota_grupo_rubrica(gid, cid, nivel_id, nota_ajustada)
            else:
                if nivel_elegido == OPCION_IGUAL_QUE_GRUPO:
                    self.base_datos.guardar_nota_alumno_rubrica(gid, aid, cid, None, None)
                else:
                    self.base_datos.guardar_nota_alumno_rubrica(gid, aid, cid, nivel_elegido, nota_ajustada)

            self.base_datos.propagar_notas_rubrica_a_criterios(self.instrumento.id, self.materia.id)

        combo.currentIndexChanged.connect(_al_cambiar)
        spin.editingFinished.connect(_al_cambiar)

        layout.addWidget(combo)
        layout.addWidget(etiqueta_ajuste)
        layout.addWidget(spin)
        return contenedor

    def refrescar(self):
        self._cargar_grupos()
