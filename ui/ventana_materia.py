"""
Ventana de una materia. Pestañas:
  - Alumnos    (lista única de la materia)
  - Criterios  (lista única de la materia)
  - 1EVA / 2EVA / 3EVA: instrumentos de evaluación propios y calificaciones
    calculadas a partir de ellos.
  - FINAL: sin instrumentos propios; agrega 1EVA/2EVA/3EVA con un peso
    editable (por defecto 1/1/1) y se recalcula siempre automáticamente.

Tiene una barra superior con un botón "Inicio" para volver a la pantalla
de bienvenida (cierra esta ventana y la del curso, si la hubiera).
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QPushButton, QTabWidget, QVBoxLayout, QWidget

from core.database import BaseDatosCurso, Materia
from ui.estilos import hoja_estilos_pestanas_materia
from ui.panel_alumnos import PanelAlumnos
from ui.panel_criterios import PanelCriterios
from ui.panel_evaluacion import PanelEvaluacion
from ui.panel_final import PanelFinal


class VentanaMateria(QMainWindow):
    def __init__(self, base_datos: BaseDatosCurso, materia: Materia):
        super().__init__()
        self.base_datos = base_datos
        self.materia = materia
        self._accion_ir_a_inicio = None

        self.setWindowTitle(f"Materia — {materia.nombre}")
        self.resize(1050, 680)

        contenedor = QWidget()
        layout_raiz = QVBoxLayout(contenedor)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)
        self.setCentralWidget(contenedor)

        barra_superior = QWidget()
        barra_superior.setObjectName("barraSuperior")
        layout_barra = QHBoxLayout(barra_superior)
        layout_barra.setContentsMargins(12, 8, 12, 8)

        boton_inicio = QPushButton("🏠 Inicio")
        boton_inicio.setObjectName("botonSecundario")
        boton_inicio.clicked.connect(self._ir_a_inicio)
        layout_barra.addWidget(boton_inicio)
        layout_barra.addStretch()
        layout_raiz.addWidget(barra_superior)

        self.pestanas = QTabWidget()
        self.pestanas.setStyleSheet(hoja_estilos_pestanas_materia())
        layout_raiz.addWidget(self.pestanas)

        self.panel_alumnos = PanelAlumnos(base_datos, materia)
        self.panel_criterios = PanelCriterios(base_datos, materia)
        self.pestanas.addTab(self.panel_alumnos, "👥 Alumnos")
        self.pestanas.addTab(self.panel_criterios, "📋 Criterios")

        ICONOS_EVALUACION = {"1EVA": "1️⃣", "2EVA": "2️⃣", "3EVA": "3️⃣", "FINAL": "🏁"}
        self.paneles_refrescables: list = []
        for evaluacion in self.base_datos.listar_evaluaciones(materia.id):
            icono = ICONOS_EVALUACION.get(evaluacion.nombre, "")
            if evaluacion.nombre == "FINAL":
                panel = PanelFinal(base_datos, materia)
            else:
                panel = PanelEvaluacion(base_datos, materia, evaluacion)
            self.paneles_refrescables.append(panel)
            self.pestanas.addTab(panel, f"{icono} {evaluacion.nombre}".strip())

        # Cuando se cambia de pestaña, refrescamos todo: así si el docente
        # añadió alumnos/criterios o cambió notas en otras pestañas, todo lo
        # demás lo refleja al momento (incluido FINAL, que depende de las
        # otras tres evaluaciones).
        self.pestanas.currentChanged.connect(self._al_cambiar_pestana)

    def conectar_ir_a_inicio(self, funcion_callback):
        """Define qué hacer al pulsar "Inicio". Se inyecta desde quien crea
        esta ventana (ver ventana_curso.py), para no depender de main.py."""
        self._accion_ir_a_inicio = funcion_callback

    def _ir_a_inicio(self):
        if self._accion_ir_a_inicio is not None:
            self._accion_ir_a_inicio()

    def _al_cambiar_pestana(self, _indice: int):
        self.panel_alumnos.refrescar()
        self.panel_criterios.refrescar()
        for panel in self.paneles_refrescables:
            panel.refrescar()
