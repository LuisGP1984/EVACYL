"""
Panel "Criterios" de una materia: lista única de criterios de evaluación
(código + peso) para toda la materia, compartida por las 4 evaluaciones.
Se introducen una sola vez por materia.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database import BaseDatosCurso, Materia
from core.importacion import (
    filas_desde_excel,
    filas_desde_texto_pegado,
    normalizar_filas_criterios,
)
from core.plantillas import generar_plantilla_criterios
from ui.dialogo_asistente_curricular import DialogoAsistenteCurricular
from ui.widgets_comunes import BotonAyuda, TablaConBorrado

TEXTO_AYUDA = (
    "En esta pestaña defines los criterios de evaluación de la materia (código + peso), "
    "una sola vez para toda ella: los heredan 1EVA, 2EVA, 3EVA y FINAL.\n\n"
    "Tres formas de rellenarlos:\n"
    "• «📚 Rellenar desde currículo oficial…»: eliges etapa, curso y materia/área (o "
    "ámbito y módulo, en el caso de ESPA), y se rellenan automáticamente los criterios "
    "oficiales de Castilla y León, con peso 1 (ajustable después). El currículo está "
    "extraído del Anexo III de los Decretos 38/2022 (Primaria), 39/2022 (Secundaria) y "
    "40/2022 (Bachillerato), y del Decreto 10/2025 (Educación Secundaria para Personas "
    "Adultas).\n"
    "• A mano, con «➕ Añadir criterio».\n"
    "• Pegando desde Excel (Ctrl+V) o importando un archivo .xlsx — usa «⬇️ Descargar "
    "plantilla de ejemplo…» si no conoces el formato esperado.\n\n"
    "El peso de cada criterio determina cuánto cuenta en la nota final de la materia."
)


class PanelCriterios(QWidget):
    COLUMNAS = ["Código (ej. 1.1)", "Peso"]

    def __init__(self, base_datos: BaseDatosCurso, materia: Materia):
        super().__init__()
        self.base_datos = base_datos
        self.materia = materia
        self._actualizando_desde_codigo = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        fila_titulo = QHBoxLayout()
        titulo = QLabel("📋 Criterios de evaluación de la materia")
        titulo.setObjectName("subtitulo")
        fila_titulo.addWidget(titulo)
        fila_titulo.addStretch()
        fila_titulo.addWidget(BotonAyuda("Ayuda — Criterios", TEXTO_AYUDA))
        layout.addLayout(fila_titulo)

        ayuda = QLabel(
            "Esta lista es única para toda la materia: se define una sola vez y la "
            "comparten 1EVA, 2EVA, 3EVA y FINAL con el mismo código y el mismo peso."
        )
        ayuda.setWordWrap(True)
        ayuda.setStyleSheet("color: #5B6B82;")
        layout.addWidget(ayuda)

        self.tabla = TablaConBorrado()
        self.tabla.setColumnCount(len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.itemChanged.connect(self._al_cambiar_celda)
        layout.addWidget(self.tabla)

        atajo_pegar = QShortcut(QKeySequence.StandardKey.Paste, self.tabla)
        atajo_pegar.activated.connect(self.pegar_desde_portapapeles)

        fila_botones = QHBoxLayout()

        boton_curriculo = QPushButton("📚 Rellenar desde currículo oficial…")
        boton_curriculo.clicked.connect(self.abrir_asistente_curricular)
        fila_botones.addWidget(boton_curriculo)

        boton_anadir = QPushButton("➕ Añadir criterio")
        boton_anadir.clicked.connect(self.anadir_criterio)
        fila_botones.addWidget(boton_anadir)

        boton_pegar = QPushButton("📋 Pegar desde Excel (Ctrl+V)")
        boton_pegar.setObjectName("botonSecundario")
        boton_pegar.clicked.connect(self.pegar_desde_portapapeles)
        fila_botones.addWidget(boton_pegar)

        boton_importar = QPushButton("📂 Importar archivo .xlsx…")
        boton_importar.setObjectName("botonSecundario")
        boton_importar.clicked.connect(self.importar_desde_archivo)
        fila_botones.addWidget(boton_importar)

        boton_plantilla = QPushButton("⬇️ Descargar plantilla de ejemplo…")
        boton_plantilla.setObjectName("botonSecundario")
        boton_plantilla.clicked.connect(self.descargar_plantilla)
        fila_botones.addWidget(boton_plantilla)

        boton_eliminar = QPushButton("🗑️ Eliminar seleccionado")
        boton_eliminar.setObjectName("botonPeligro")
        boton_eliminar.clicked.connect(self.eliminar_criterio_seleccionado)
        fila_botones.addWidget(boton_eliminar)

        self._ultima_captura_eliminacion = None
        self.boton_deshacer = QPushButton("↩️ Deshacer")
        self.boton_deshacer.setObjectName("botonSecundario")
        self.boton_deshacer.setEnabled(False)
        self.boton_deshacer.clicked.connect(self.deshacer_ultima_eliminacion)
        fila_botones.addWidget(self.boton_deshacer)

        fila_botones.addStretch()
        layout.addLayout(fila_botones)

        self.refrescar()

    def refrescar(self):
        self._actualizando_desde_codigo = True
        criterios = self.base_datos.listar_criterios(self.materia.id)
        self.tabla.setRowCount(len(criterios))
        for fila, criterio in enumerate(criterios):
            item_codigo = QTableWidgetItem(criterio.codigo)
            item_codigo.setData(Qt.ItemDataRole.UserRole, criterio.id)
            item_peso = QTableWidgetItem(str(criterio.peso))
            self.tabla.setItem(fila, 0, item_codigo)
            self.tabla.setItem(fila, 1, item_peso)
        self._actualizando_desde_codigo = False

    def _al_cambiar_celda(self, item: QTableWidgetItem):
        if self._actualizando_desde_codigo:
            return
        fila = item.row()
        item_codigo = self.tabla.item(fila, 0)
        item_peso = self.tabla.item(fila, 1)
        if item_codigo is None:
            return
        criterio_id = item_codigo.data(Qt.ItemDataRole.UserRole)
        if criterio_id is None:
            return
        codigo = item_codigo.text()
        texto_peso = item_peso.text() if item_peso else "1"
        try:
            peso = float(texto_peso.replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "Peso no válido", "El peso debe ser un número. Se usará 1.")
            peso = 1.0
        try:
            self.base_datos.actualizar_criterio(criterio_id, codigo, peso)
        except ValueError as exc:
            QMessageBox.warning(self, "Dato no válido", str(exc))
        self.refrescar()

    def anadir_criterio(self):
        criterios_actuales = self.base_datos.listar_criterios(self.materia.id)
        codigo_sugerido = f"{len(criterios_actuales) + 1}.1"
        self.base_datos.agregar_criterio(self.materia.id, codigo_sugerido, 1.0)
        self.refrescar()

    def eliminar_criterio_seleccionado(self):
        fila = self.tabla.currentRow()
        if fila < 0:
            QMessageBox.information(self, "Sin selección", "Selecciona primero una fila.")
            return
        item_codigo = self.tabla.item(fila, 0)
        criterio_id = item_codigo.data(Qt.ItemDataRole.UserRole) if item_codigo else None
        if criterio_id is None:
            return
        codigo = item_codigo.text()
        self._ultima_captura_eliminacion = self.base_datos.eliminar_criterio_con_deshacer(criterio_id)
        self.boton_deshacer.setEnabled(self._ultima_captura_eliminacion is not None)
        self.boton_deshacer.setText(f"↩️ Deshacer eliminación de «{codigo}»")
        self.refrescar()

    def deshacer_ultima_eliminacion(self):
        if self._ultima_captura_eliminacion is None:
            return
        self.base_datos.restaurar_eliminacion(self._ultima_captura_eliminacion)
        self._ultima_captura_eliminacion = None
        self.boton_deshacer.setEnabled(False)
        self.boton_deshacer.setText("↩️ Deshacer")
        self.refrescar()

    def pegar_desde_portapapeles(self):
        texto = QApplication.clipboard().text()
        if not texto.strip():
            QMessageBox.information(
                self, "Portapapeles vacío", "Copia primero las celdas en Excel y vuelve a intentarlo."
            )
            return
        filas = filas_desde_texto_pegado(texto)
        criterios_nuevos = normalizar_filas_criterios(filas)
        self._importar_lista(criterios_nuevos)

    def importar_desde_archivo(self):
        ruta_archivo, _ = QFileDialog.getOpenFileName(
            self, "Selecciona el archivo Excel con los criterios", filter="Excel (*.xlsx)"
        )
        if not ruta_archivo:
            return
        try:
            filas = filas_desde_excel(ruta_archivo)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "No se pudo leer el archivo", str(exc))
            return
        criterios_nuevos = normalizar_filas_criterios(filas)
        self._importar_lista(criterios_nuevos)

    def _importar_lista(self, criterios_nuevos: list[tuple[str, float]]):
        if not criterios_nuevos:
            QMessageBox.information(
                self, "Nada que importar", "No se ha reconocido ningún criterio en los datos."
            )
            return
        insertados = self.base_datos.agregar_criterios_en_lote(self.materia.id, criterios_nuevos)
        self.refrescar()
        QMessageBox.information(self, "Importación completada", f"Se han añadido {insertados} criterios.")

    def descargar_plantilla(self):
        ruta_texto, _ = QFileDialog.getSaveFileName(
            self, "Guardar plantilla de criterios", "plantilla_criterios.xlsx", filter="Excel (*.xlsx)"
        )
        if not ruta_texto:
            return
        ruta = Path(ruta_texto)
        if ruta.suffix.lower() != ".xlsx":
            ruta = ruta.with_suffix(".xlsx")
        try:
            generar_plantilla_criterios(ruta)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "No se pudo generar la plantilla", str(exc))
            return
        QMessageBox.information(
            self,
            "Plantilla guardada",
            f"Archivo guardado en:\n{ruta}\n\n"
            "Tiene dos columnas: Código y Peso, con algunas filas de ejemplo siguiendo la "
            "nomenclatura LOMLOE (competencia.criterio). Sustitúyelas por tus criterios "
            "reales y luego usa «Importar archivo .xlsx…».",
        )

    def abrir_asistente_curricular(self):
        dialogo = DialogoAsistenteCurricular(self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        if dialogo.es_opcion_manual():
            return  # el docente ha elegido introducirlos él mismo: no hay nada que rellenar

        etapa, curso, materia, codigos = dialogo.resultado()
        if not codigos:
            return

        criterios_existentes = self.base_datos.listar_criterios(self.materia.id)
        if criterios_existentes:
            codigos_existentes = {c.codigo for c in criterios_existentes}
            codigos_oficiales = set(codigos)
            coincidentes = codigos_existentes & codigos_oficiales
            solo_existentes = codigos_existentes - codigos_oficiales
            solo_oficiales = codigos_oficiales - codigos_existentes

            if solo_existentes:
                # Hay criterios actuales que NO están en el currículo oficial
                # elegido: lo más probable es que sean manuales, de otra
                # materia/curso, o de una etapa distinta. Avisamos con detalle
                # en vez de un aviso genérico de "ya hay criterios".
                mensaje = (
                    f"Esta materia ya tiene {len(criterios_existentes)} criterios, pero "
                    f"{len(solo_existentes)} de ellos no coinciden con los de «{materia}» "
                    f"({curso}): {', '.join(sorted(solo_existentes)[:8])}"
                    + ("…" if len(solo_existentes) > 8 else "")
                    + ".\n\n"
                )
                if coincidentes:
                    mensaje += (
                        f"Sí coinciden {len(coincidentes)} códigos, que no se duplicarán. "
                    )
                if solo_oficiales:
                    mensaje += (
                        f"Se añadirán {len(solo_oficiales)} criterios oficiales nuevos que "
                        "todavía no tenías. "
                    )
                mensaje += (
                    "\n\nLos criterios que no coinciden NO se eliminarán automáticamente; "
                    "si quieres que la materia quede exactamente como el currículo oficial, "
                    "tendrás que borrarlos tú a mano después.\n\n¿Continuar?"
                )
            else:
                mensaje = (
                    f"Esta materia ya tiene {len(criterios_existentes)} criterios, todos "
                    f"coincidentes con los de «{materia}» ({curso}). "
                    f"Se añadirán {len(solo_oficiales)} criterios oficiales que todavía no "
                    "tenías, sin duplicar nada.\n\n¿Continuar?"
                )
            respuesta = QMessageBox.question(self, "Comprobación antes de rellenar", mensaje)
            if respuesta != QMessageBox.StandardButton.Yes:
                return

        insertados = self.base_datos.agregar_criterios_evitando_duplicados(self.materia.id, codigos)
        self.refrescar()
        QMessageBox.information(
            self,
            "Criterios rellenados",
            f"Se han añadido {insertados} criterios oficiales de «{materia}» ({curso}). "
            "Puedes ajustar los pesos de cada uno en esta misma tabla.",
        )
