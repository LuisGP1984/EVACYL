"""
Asistente para rellenar automáticamente los criterios de evaluación de
una materia a partir del currículo oficial LOMLOE de Castilla y León.

Flujo:
  1. El docente elige la etapa (Primaria, Secundaria, Bachillerato,
     ESPA, Diversificación).
  2. Se le pide el curso.
  3. Después, la materia/área (o ámbito) dentro de ese curso.
  4. Al confirmar, se devuelven los códigos de criterio para que quien
     use este diálogo los inserte en la base de datos.

No incluye una opción "manual": si el docente no quiere usar el
asistente para una materia en concreto, simplemente cancela este
diálogo y sigue añadiendo los criterios uno a uno desde la propia
pestaña de Criterios, donde ya existe esa opción — tenerla aquí
también sería redundante.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

from core.curriculo import (
    ETIQUETAS_ETAPA,
    criterios_de_materia,
    cursos_de_etapa,
    etapas_disponibles,
    etiquetas_niveles,
    materias_de_curso,
    referencia_normativa,
)


class DialogoAsistenteCurricular(QDialog):
    """Diálogo de selección etapa -> curso -> materia. Tras aceptar,
    `resultado()` devuelve (etapa, curso, materia, lista_codigos).
    Si el docente cancela el diálogo, quien lo usa simplemente no debe
    hacer nada (no hay resultado "manual" que gestionar aquí).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rellenar criterios desde el currículo oficial")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        ayuda = QLabel(
            "Elige tu etapa educativa y la app rellenará automáticamente los "
            "criterios de evaluación oficiales de Castilla y León para la materia "
            "que indiques."
        )
        ayuda.setWordWrap(True)
        layout.addWidget(ayuda)

        formulario = QFormLayout()
        formulario.setVerticalSpacing(14)
        formulario.setContentsMargins(0, 8, 0, 8)

        ALTURA_MINIMA_COMBO = 32

        self.combo_etapa = QComboBox()
        self.combo_etapa.setMinimumHeight(ALTURA_MINIMA_COMBO)
        for etapa in ["PRIMARIA", "SECUNDARIA", "BACHILLERATO", "ESPA", "DIVERSIFICACION"]:
            disponible = etapa in etapas_disponibles()
            etiqueta = ETIQUETAS_ETAPA[etapa]
            if not disponible:
                etiqueta += "  (aún no disponible)"
            self.combo_etapa.addItem(etiqueta, etapa)
        self.combo_etapa.currentIndexChanged.connect(self._al_cambiar_etapa)
        formulario.addRow("Etapa:", self.combo_etapa)

        self.etiqueta_normativa = QLabel("")
        self.etiqueta_normativa.setWordWrap(True)
        self.etiqueta_normativa.setStyleSheet("color: #5B6B82; font-size: 11px; font-style: italic;")
        layout.addWidget(self.etiqueta_normativa)

        self.combo_curso = QComboBox()
        self.combo_curso.setMinimumHeight(ALTURA_MINIMA_COMBO)
        self.combo_curso.currentIndexChanged.connect(self._al_cambiar_curso)
        self.etiqueta_nivel1 = QLabel("Curso:")
        formulario.addRow(self.etiqueta_nivel1, self.combo_curso)

        self.combo_materia = QComboBox()
        self.combo_materia.setMinimumHeight(ALTURA_MINIMA_COMBO)
        self.combo_materia.currentIndexChanged.connect(self._actualizar_resumen)
        self.etiqueta_nivel2 = QLabel("Materia / Área:")
        formulario.addRow(self.etiqueta_nivel2, self.combo_materia)

        layout.addLayout(formulario)

        self.etiqueta_resumen = QLabel("")
        self.etiqueta_resumen.setWordWrap(True)
        self.etiqueta_resumen.setStyleSheet("color: #2E7D4F; font-weight: 600;")
        layout.addWidget(self.etiqueta_resumen)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._al_aceptar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        self._etapa_seleccionada = self.combo_etapa.itemData(0)
        self._curso_seleccionado = None
        self._materia_seleccionada = None
        self._codigos_resultado: list[str] = []

        self._al_cambiar_etapa(0)

    # -- lógica en cascada -------------------------------------------------

    def _al_cambiar_etapa(self, _indice: int):
        etapa = self.combo_etapa.currentData()
        self._etapa_seleccionada = etapa

        etiqueta_nivel1, etiqueta_nivel2 = etiquetas_niveles(etapa)
        self.etiqueta_nivel1.setText(f"{etiqueta_nivel1}:")
        self.etiqueta_nivel2.setText(f"{etiqueta_nivel2}:")

        self.combo_curso.clear()
        self.combo_materia.clear()
        self.etiqueta_resumen.setText("")
        self.etiqueta_normativa.setText(f"📖 Fuente: {referencia_normativa(etapa)}")

        if etapa not in etapas_disponibles():
            self.etiqueta_resumen.setText(
                "Esta etapa todavía no tiene el currículo cargado en la aplicación. "
                "Si quieres usar esta materia, cancela este asistente y añade los "
                "criterios uno a uno desde el botón «➕ Añadir criterio»."
            )
            self.combo_curso.setEnabled(False)
            self.combo_materia.setEnabled(False)
            return

        self.combo_curso.setEnabled(True)
        self.combo_materia.setEnabled(True)
        for curso in cursos_de_etapa(etapa):
            self.combo_curso.addItem(curso, curso)

    def _al_cambiar_curso(self, _indice: int):
        etapa = self._etapa_seleccionada
        curso = self.combo_curso.currentData()
        self.combo_materia.clear()
        if curso is None:
            return
        for materia in materias_de_curso(etapa, curso):
            self.combo_materia.addItem(materia, materia)
        self._actualizar_resumen()

    def _actualizar_resumen(self):
        etapa = self._etapa_seleccionada
        curso = self.combo_curso.currentData()
        materia = self.combo_materia.currentData()
        if not curso or not materia:
            self.etiqueta_resumen.setText("")
            return
        codigos = criterios_de_materia(etapa, curso, materia)
        if codigos:
            self.etiqueta_resumen.setText(
                f"Se rellenarán {len(codigos)} criterios de evaluación oficiales "
                f"para «{materia}» — {curso}, con peso 1 cada uno (ajustable después)."
            )
        else:
            self.etiqueta_resumen.setText(
                "No se han encontrado criterios para esta combinación. Revisa la selección."
            )

    # -- aceptar -------------------------------------------------------

    def _al_aceptar(self):
        etapa = self._etapa_seleccionada
        curso = self.combo_curso.currentData()
        materia = self.combo_materia.currentData()
        if not curso or not materia:
            QMessageBox.warning(self, "Selección incompleta", "Elige un curso y una materia.")
            return

        codigos = criterios_de_materia(etapa, curso, materia)
        if not codigos:
            QMessageBox.warning(
                self, "Sin datos", "No se han encontrado criterios para esta combinación."
            )
            return

        self._etapa_seleccionada = etapa
        self._curso_seleccionado = curso
        self._materia_seleccionada = materia
        self._codigos_resultado = codigos
        self.accept()

    # -- resultado -------------------------------------------------------

    def resultado(self) -> tuple[str | None, str | None, str | None, list[str]]:
        return (
            self._etapa_seleccionada,
            self._curso_seleccionado,
            self._materia_seleccionada,
            self._codigos_resultado,
        )
