"""
Ventana de un curso: muestra el listado de materias dentro del curso.db
abierto, y permite crear materias nuevas, renombrarlas, eliminarlas o
entrar en una de ellas para trabajar con sus evaluaciones.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.database import BaseDatosCurso, Materia
from core.respaldo import listar_copias_seguridad, restaurar_copia_seguridad
from ui.ventana_materia import VentanaMateria
from ui.widgets_comunes import BotonAyuda, VentanaConFondo

TEXTO_AYUDA_CURSO = (
    "Una <b>materia</b> agrupa todo lo necesario para evaluar una asignatura concreta de "
    "un grupo (por ejemplo, «Tecnología 1ºESO A»): su alumnado, sus criterios de "
    "evaluación, y las 4 evaluaciones (1EVA, 2EVA, 3EVA y FINAL) con sus notas.\n\n"
    "Si impartes la misma asignatura en dos grupos distintos (1ºESO A y 1ºESO B), crea dos "
    "materias separadas: cada una con su propio alumnado, aunque puedan compartir el mismo "
    "currículo oficial al rellenar los criterios.\n\n"
    "Pulsa «➕ Crear nueva materia» para empezar una, o haz doble clic en una materia de la "
    "lista para entrar en ella."
)


class DialogoCopiasSeguridad(QDialog):
    """Lista las copias de seguridad disponibles para este curso y
    permite restaurar la seleccionada.
    """

    def __init__(self, ruta_bd: Path, parent=None):
        super().__init__(parent)
        self.ruta_bd = ruta_bd
        self.copia_a_restaurar: Path | None = None

        self.setWindowTitle("🛡️ Copias de seguridad de este curso")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        explicacion = QLabel(
            "Cada vez que abres este curso, se guarda automáticamente una copia de "
            "seguridad antes de tocar nada. Si algo ha ido mal (datos borrados por error, "
            "un archivo dañado...), puedes volver a una copia anterior aquí.\n\n"
            "Al restaurar, el estado actual también se guarda como una copia más, así que "
            "no se pierde nada de forma irreversible."
        )
        explicacion.setWordWrap(True)
        layout.addWidget(explicacion)

        self.lista = QListWidget()
        copias = listar_copias_seguridad(ruta_bd)
        if not copias:
            item = QListWidgetItem("(Todavía no hay copias de seguridad de este curso)")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.lista.addItem(item)
        else:
            for copia in copias:
                # Nombre de archivo: curso_2025-09-15_10-30-00_123456.db
                partes = copia.stem.replace("curso_", "").split("_")
                if len(partes) >= 2:
                    fecha_legible = f"{partes[0]} a las {partes[1].replace('-', ':')}"
                else:
                    fecha_legible = copia.stem
                item = QListWidgetItem(f"📅 {fecha_legible}")
                item.setData(1, copia)
                self.lista.addItem(item)
        layout.addWidget(self.lista)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Restaurar esta copia")
        botones.accepted.connect(self._al_aceptar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _al_aceptar(self):
        item = self.lista.currentItem()
        if item is None:
            QMessageBox.information(self, "Sin selección", "Selecciona primero una copia de la lista.")
            return
        copia = item.data(1)
        if copia is None:
            return
        respuesta = QMessageBox.question(
            self,
            "Confirmar restauración",
            "Esto sustituirá los datos actuales del curso por los de esta copia de "
            "seguridad. El estado actual también quedará guardado como copia, por si "
            "necesitas deshacer esto. ¿Continuar?",
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        self.copia_a_restaurar = copia
        self.accept()


class VentanaCurso(VentanaConFondo):
    def __init__(self, base_datos: BaseDatosCurso, ruta_bd: Path):
        super().__init__()
        self.base_datos = base_datos
        self.ruta_bd = ruta_bd
        self._accion_ir_a_inicio = None

        self.setWindowTitle(f"Curso — {ruta_bd.parent.name}")
        self.resize(560, 420)

        contenedor = QWidget()
        contenedor.setObjectName("fondoTransparente")
        self.setCentralWidget(contenedor)
        layout_exterior = QVBoxLayout(contenedor)
        layout_exterior.setContentsMargins(24, 24, 24, 24)

        fila_superior = QHBoxLayout()
        boton_inicio = QPushButton("🏠 Inicio")
        boton_inicio.setObjectName("botonSecundario")
        boton_inicio.clicked.connect(self._ir_a_inicio)
        fila_superior.addWidget(boton_inicio)

        boton_copias = QPushButton("🛡️ Copias de seguridad")
        boton_copias.setObjectName("botonSecundario")
        boton_copias.clicked.connect(self.abrir_copias_seguridad)
        fila_superior.addWidget(boton_copias)

        fila_superior.addStretch()
        layout_exterior.addLayout(fila_superior)

        panel = QWidget()
        panel.setObjectName("panelSobreFondo")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout_exterior.addWidget(panel)

        etiqueta_ruta = QLabel(f"Archivo del curso: {ruta_bd}")
        etiqueta_ruta.setStyleSheet("color: gray;")
        layout.addWidget(etiqueta_ruta)

        fila_titulo = QHBoxLayout()
        titulo = QLabel("📚 Materias")
        titulo.setObjectName("subtitulo")
        fila_titulo.addWidget(titulo)
        fila_titulo.addStretch()
        fila_titulo.addWidget(BotonAyuda("Ayuda — Materias", TEXTO_AYUDA_CURSO))
        layout.addLayout(fila_titulo)

        self.lista_materias = QListWidget()
        self.lista_materias.itemDoubleClicked.connect(self.entrar_en_materia_seleccionada)
        layout.addWidget(self.lista_materias)

        fila_botones = QWidget()
        layout_botones = QVBoxLayout(fila_botones)
        layout_botones.setContentsMargins(0, 0, 0, 0)

        boton_crear = QPushButton("➕ Crear nueva materia")
        boton_crear.clicked.connect(self.crear_materia)
        layout_botones.addWidget(boton_crear)

        boton_entrar = QPushButton("🔍 Entrar en la materia seleccionada")
        boton_entrar.clicked.connect(self.entrar_en_materia_seleccionada)
        layout_botones.addWidget(boton_entrar)

        boton_renombrar = QPushButton("✏️ Renombrar materia seleccionada")
        boton_renombrar.clicked.connect(self.renombrar_materia_seleccionada)
        layout_botones.addWidget(boton_renombrar)

        boton_eliminar = QPushButton("🗑️ Eliminar materia seleccionada")
        boton_eliminar.clicked.connect(self.eliminar_materia_seleccionada)
        layout_botones.addWidget(boton_eliminar)

        layout.addWidget(fila_botones)

        self.ventanas_materia_abiertas: list[VentanaMateria] = []

        self.refrescar_lista_materias()

    def conectar_ir_a_inicio(self, funcion_callback):
        """Define qué hacer al pulsar "Inicio" (cierra esta ventana y vuelve
        a la pantalla de bienvenida). Se inyecta desde main.py."""
        self._accion_ir_a_inicio = funcion_callback

    def _ir_a_inicio(self):
        for ventana_materia in self.ventanas_materia_abiertas:
            ventana_materia.close()
        if self._accion_ir_a_inicio is not None:
            self._accion_ir_a_inicio()
        self.close()

    # -- helpers -------------------------------------------------------

    def refrescar_lista_materias(self):
        self.lista_materias.clear()
        for materia in self.base_datos.listar_materias():
            item = QListWidgetItem(materia.nombre)
            item.setData(1, materia.id)
            self.lista_materias.addItem(item)

    def _materia_seleccionada(self) -> Materia | None:
        item = self.lista_materias.currentItem()
        if item is None:
            QMessageBox.information(self, "Sin selección", "Selecciona primero una materia.")
            return None
        materia_id = item.data(1)
        for materia in self.base_datos.listar_materias():
            if materia.id == materia_id:
                return materia
        return None

    # -- acciones -------------------------------------------------------

    def crear_materia(self):
        nombre, ok = QInputDialog.getText(
            self, "Nueva materia", "Nombre de la materia (ej. Tecnología 1ºESO):"
        )
        if not ok or not nombre.strip():
            return
        try:
            self.base_datos.crear_materia(nombre)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "No se pudo crear la materia", str(exc))
            return
        self.refrescar_lista_materias()

    def entrar_en_materia_seleccionada(self):
        materia = self._materia_seleccionada()
        if materia is None:
            return
        ventana_materia = VentanaMateria(self.base_datos, materia)
        ventana_materia.conectar_ir_a_inicio(self._ir_a_inicio)
        ventana_materia.showMaximized()
        self.ventanas_materia_abiertas.append(ventana_materia)

    def renombrar_materia_seleccionada(self):
        materia = self._materia_seleccionada()
        if materia is None:
            return
        nuevo_nombre, ok = QInputDialog.getText(
            self, "Renombrar materia", "Nuevo nombre:", text=materia.nombre
        )
        if not ok or not nuevo_nombre.strip():
            return
        try:
            self.base_datos.renombrar_materia(materia.id, nuevo_nombre)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "No se pudo renombrar", str(exc))
            return
        self.refrescar_lista_materias()

    def eliminar_materia_seleccionada(self):
        materia = self._materia_seleccionada()
        if materia is None:
            return
        respuesta = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"Esto borrará la materia «{materia.nombre}» y TODOS sus datos "
            "(alumnos, criterios, notas de sus 4 evaluaciones). "
            "Esta acción no se puede deshacer.\n\n¿Continuar?",
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        self.base_datos.eliminar_materia(materia.id)
        self.refrescar_lista_materias()

    def abrir_copias_seguridad(self):
        dialogo = DialogoCopiasSeguridad(self.ruta_bd, self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        copia_elegida = dialogo.copia_a_restaurar
        if copia_elegida is None:
            return

        ok = restaurar_copia_seguridad(copia_elegida, self.ruta_bd)
        if not ok:
            QMessageBox.critical(
                self, "No se pudo restaurar", "No se pudo completar la restauración de la copia."
            )
            return

        # Los datos en disco ya son los restaurados, pero la conexión
        # BaseDatosCurso actual y las ventanas abiertas siguen reflejando
        # el estado anterior en memoria. Cerramos todo y volvemos a abrir
        # el curso desde cero para que todo se recargue correctamente.
        for ventana_materia in self.ventanas_materia_abiertas:
            ventana_materia.close()
        self.base_datos.cerrar()

        nueva_base_datos = BaseDatosCurso(self.ruta_bd)
        nueva_ventana = VentanaCurso(nueva_base_datos, self.ruta_bd)
        nueva_ventana.conectar_ir_a_inicio(self._accion_ir_a_inicio)
        nueva_ventana.showMaximized()
        self._ventana_recargada_tras_restaurar = nueva_ventana  # evita que el GC la cierre
        QMessageBox.information(
            nueva_ventana,
            "Restauración completada",
            "Se ha restaurado la copia de seguridad seleccionada.",
        )
        self.close()
