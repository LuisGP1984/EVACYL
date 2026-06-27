"""
Diálogo para crear una materia nueva copiando la estructura (criterios,
y opcionalmente instrumentos de evaluación) de una materia ya
existente — del mismo curso académico, o de cualquier otro curso
académico dentro de la misma carpeta del docente. Nunca copia
alumnado ni notas.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from core.database import BaseDatosCurso, Materia

NOMBRE_ARCHIVO_BD = "curso.db"

NIVEL_SOLO_CRITERIOS = "criterios"
NIVEL_CRITERIOS_E_INSTRUMENTOS = "instrumentos"


def _cursos_disponibles(carpeta_docente: Path) -> list[Path]:
    """Subcarpetas de la carpeta del docente que tienen un curso.db
    dentro, ordenadas por nombre (normalmente el nombre del curso
    académico, ej. "2024-2025").
    """
    if not carpeta_docente.exists():
        return []
    return sorted(
        subcarpeta
        for subcarpeta in carpeta_docente.iterdir()
        if subcarpeta.is_dir() and (subcarpeta / NOMBRE_ARCHIVO_BD).exists()
    )


class DialogoNuevaMateria(QDialog):
    """Pide el nombre de la materia nueva, y si se quiere copiar la
    estructura (criterios, o criterios+instrumentos) de otra materia
    ya existente, posiblemente de otro curso académico.
    """

    def __init__(self, ruta_bd_actual: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva materia")
        self.setMinimumWidth(440)
        self.ruta_bd_actual = ruta_bd_actual
        self.carpeta_docente = ruta_bd_actual.parent.parent

        self.nombre_materia: str = ""
        self.copiar_desde: tuple[Path, str] | None = None
        self.nivel_copia: str = NIVEL_SOLO_CRITERIOS

        layout = QVBoxLayout(self)

        explicacion = QLabel(
            "Puedes empezar la materia vacía, o copiar la estructura (criterios y, si "
            "quieres, también los instrumentos de evaluación) de una materia que ya tengas "
            "hecha — de este curso académico o de cualquier otro. Nunca se copia el "
            "alumnado ni ninguna nota: la materia nueva siempre empieza sin alumnos."
        )
        explicacion.setWordWrap(True)
        layout.addWidget(explicacion)

        formulario = QFormLayout()
        formulario.setVerticalSpacing(14)
        formulario.setContentsMargins(0, 12, 0, 8)

        self.campo_nombre = QLineEdit()
        self.campo_nombre.setMinimumHeight(32)
        self.campo_nombre.setPlaceholderText("ej. Tecnología 1ºESO B")
        formulario.addRow("Nombre de la materia:", self.campo_nombre)

        layout.addLayout(formulario)

        self.radio_vacia = QRadioButton("Empezar vacía (sin criterios ni instrumentos)")
        self.radio_vacia.setChecked(True)
        self.radio_vacia.toggled.connect(self._actualizar_estado_copia)
        layout.addWidget(self.radio_vacia)

        self.radio_copiar = QRadioButton("Copiar la estructura de una materia existente")
        self.radio_copiar.toggled.connect(self._actualizar_estado_copia)
        layout.addWidget(self.radio_copiar)

        contenedor_copia = QWidget()
        formulario_copia = QFormLayout(contenedor_copia)
        formulario_copia.setVerticalSpacing(14)
        formulario_copia.setContentsMargins(24, 8, 0, 8)

        self.combo_curso = QComboBox()
        self.combo_curso.setMinimumHeight(32)
        self.combo_curso.currentIndexChanged.connect(self._al_cambiar_curso_origen)
        formulario_copia.addRow("Curso académico origen:", self.combo_curso)

        self.combo_materia_origen = QComboBox()
        self.combo_materia_origen.setMinimumHeight(32)
        formulario_copia.addRow("Materia a copiar:", self.combo_materia_origen)

        self.radio_solo_criterios = QRadioButton("Solo criterios y pesos")
        self.radio_solo_criterios.setChecked(True)
        self.radio_instrumentos = QRadioButton(
            "Criterios + instrumentos de evaluación (con sus pesos y pruebas)"
        )
        formulario_copia.addRow("Qué copiar:", self.radio_solo_criterios)
        formulario_copia.addRow("", self.radio_instrumentos)

        layout.addWidget(contenedor_copia)
        self.contenedor_copia = contenedor_copia

        self._poblar_combo_cursos()
        self._actualizar_estado_copia()

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Crear")
        botones.accepted.connect(self._al_aceptar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _poblar_combo_cursos(self):
        self.combo_curso.clear()
        cursos = _cursos_disponibles(self.carpeta_docente)
        indice_actual = -1
        for indice, carpeta_curso in enumerate(cursos):
            ruta_bd = carpeta_curso / NOMBRE_ARCHIVO_BD
            etiqueta = carpeta_curso.name
            if ruta_bd == self.ruta_bd_actual:
                etiqueta += "  (este curso)"
                indice_actual = indice
            self.combo_curso.addItem(etiqueta, ruta_bd)
        if indice_actual >= 0:
            self.combo_curso.setCurrentIndex(indice_actual)
        self._al_cambiar_curso_origen()

    def _al_cambiar_curso_origen(self, _indice: int = -1):
        ruta_bd_origen = self.combo_curso.currentData()
        self.combo_materia_origen.clear()
        if ruta_bd_origen is None:
            return
        try:
            base_datos_origen = BaseDatosCurso(ruta_bd_origen)
            for materia in base_datos_origen.listar_materias():
                self.combo_materia_origen.addItem(materia.nombre, materia.nombre)
            base_datos_origen.cerrar()
        except Exception:  # noqa: BLE001
            pass

    def _actualizar_estado_copia(self):
        self.contenedor_copia.setEnabled(self.radio_copiar.isChecked())

    def _al_aceptar(self):
        nombre = self.campo_nombre.text().strip()
        if not nombre:
            self.campo_nombre.setFocus()
            return

        self.nombre_materia = nombre

        if self.radio_copiar.isChecked():
            ruta_bd_origen = self.combo_curso.currentData()
            nombre_materia_origen = self.combo_materia_origen.currentData()
            if ruta_bd_origen is None or nombre_materia_origen is None:
                return
            self.copiar_desde = (ruta_bd_origen, nombre_materia_origen)
            self.nivel_copia = (
                NIVEL_CRITERIOS_E_INSTRUMENTOS if self.radio_instrumentos.isChecked() else NIVEL_SOLO_CRITERIOS
            )
        else:
            self.copiar_desde = None

        self.accept()
