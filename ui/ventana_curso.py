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
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.database import BaseDatosCurso, Materia
from core.respaldo import listar_copias_seguridad, restaurar_copia_seguridad
from ui.dialogo_nueva_materia import (
    NIVEL_CRITERIOS_E_INSTRUMENTOS,
    NOMBRE_ARCHIVO_BD,
    DialogoNuevaMateria,
    _cursos_disponibles,
)
from ui.ventana_materia import VentanaMateria
from ui.widgets_comunes import BotonAyuda, VentanaConFondo

TEXTO_AYUDA_CURSO = (
    "Una <b>materia</b> agrupa todo lo necesario para evaluar una asignatura concreta de "
    "un grupo (por ejemplo, «Tecnología 1ºESO A»): su alumnado, sus criterios de "
    "evaluación, y las 4 evaluaciones (1EVA, 2EVA, 3EVA y FINAL) con sus notas.\n\n"
    "Si impartes la misma asignatura en dos grupos distintos (1ºESO A y 1ºESO B), o repites "
    "estructura curso tras curso, al pulsar «➕ Crear nueva materia» puedes copiar los "
    "criterios (y, si quieres, también los instrumentos de evaluación con sus pesos y "
    "pruebas) de una materia que ya tengas hecha — de este curso académico o de cualquier "
    "otro. La materia nueva siempre empieza sin alumnado ni notas.\n\n"
    "También puedes usar «📥 Importar materia…» para cargar una materia exportada por otro "
    "docente (o por ti mismo desde otro curso). Al exportar puedes elegir entre exportar "
    "solo la estructura (criterios y pesos, sin alumnado ni notas) o la materia completa.\n\n"
    "El campo de búsqueda filtra la lista al momento mientras escribes. Si la materia existe "
    "también en otros cursos académicos, los resultados aparecen debajo — haz doble clic "
    "para abrirla directamente.\n\n"
    "Haz doble clic en una materia de la lista para entrar en ella."
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
        self.carpeta_docente = ruta_bd.parent.parent
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

        self.campo_busqueda = QLineEdit()
        self.campo_busqueda.setPlaceholderText("🔎 Buscar materia por nombre… (también busca en otros cursos académicos)")
        self.campo_busqueda.setMinimumHeight(32)
        self.campo_busqueda.textChanged.connect(self._al_cambiar_busqueda)
        layout.addWidget(self.campo_busqueda)

        self.lista_materias = QListWidget()
        self.lista_materias.itemDoubleClicked.connect(self.entrar_en_materia_seleccionada)
        layout.addWidget(self.lista_materias)

        self.etiqueta_otros_cursos = QLabel("")
        self.etiqueta_otros_cursos.setStyleSheet("color: #8A7A6E; font-size: 12px;")
        self.etiqueta_otros_cursos.setVisible(False)
        layout.addWidget(self.etiqueta_otros_cursos)

        self.lista_otros_cursos = QListWidget()
        self.lista_otros_cursos.setMaximumHeight(120)
        self.lista_otros_cursos.itemDoubleClicked.connect(self._abrir_resultado_de_otro_curso)
        self.lista_otros_cursos.setVisible(False)
        layout.addWidget(self.lista_otros_cursos)

        fila_botones = QWidget()
        layout_botones = QVBoxLayout(fila_botones)
        layout_botones.setContentsMargins(0, 0, 0, 0)

        boton_crear = QPushButton("➕ Crear nueva materia")
        boton_crear.clicked.connect(self.crear_materia)
        layout_botones.addWidget(boton_crear)

        boton_importar = QPushButton("📥 Importar materia…")
        boton_importar.setObjectName("botonSecundario")
        boton_importar.clicked.connect(self.importar_materia)
        layout_botones.addWidget(boton_importar)

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
            item.setData(2, materia.nombre)  # texto puro para comparar en la búsqueda
            self.lista_materias.addItem(item)

    def _al_cambiar_busqueda(self, texto: str):
        texto_normalizado = texto.strip().lower()

        # Filtra la lista de materias de ESTE curso en tiempo real, sin
        # tocar la base de datos: solo oculta/muestra filas ya cargadas.
        for fila in range(self.lista_materias.count()):
            item = self.lista_materias.item(fila)
            nombre_materia = (item.data(2) or "").lower()
            item.setHidden(bool(texto_normalizado) and texto_normalizado not in nombre_materia)

        if not texto_normalizado:
            self.lista_otros_cursos.clear()
            self.lista_otros_cursos.setVisible(False)
            self.etiqueta_otros_cursos.setVisible(False)
            return

        # Buscar también en los demás cursos académicos (abre cada
        # curso.db solo para consultar, sin mantenerlo abierto).
        self.lista_otros_cursos.clear()
        encontrados = []
        for carpeta_curso in _cursos_disponibles(self.carpeta_docente):
            ruta_bd_otro_curso = carpeta_curso / NOMBRE_ARCHIVO_BD
            if ruta_bd_otro_curso == self.ruta_bd:
                continue  # el curso actual ya se busca arriba, en la lista principal
            try:
                base_datos_otro_curso = BaseDatosCurso(ruta_bd_otro_curso)
                for materia in base_datos_otro_curso.listar_materias():
                    if texto_normalizado in materia.nombre.lower():
                        encontrados.append((carpeta_curso.name, ruta_bd_otro_curso, materia.nombre))
                base_datos_otro_curso.cerrar()
            except Exception:  # noqa: BLE001
                continue  # un curso.db dañado o ilegible no debe romper la búsqueda del resto

        if encontrados:
            self.etiqueta_otros_cursos.setText("📂 Encontrado también en otros cursos académicos (doble clic para abrir):")
            self.etiqueta_otros_cursos.setVisible(True)
            self.lista_otros_cursos.setVisible(True)
            for nombre_curso, ruta_bd_otro_curso, nombre_materia in encontrados:
                item = QListWidgetItem(f"{nombre_materia}  —  curso {nombre_curso}")
                item.setData(1, str(ruta_bd_otro_curso))
                item.setData(2, nombre_materia)
                self.lista_otros_cursos.addItem(item)
        else:
            self.etiqueta_otros_cursos.setVisible(False)
            self.lista_otros_cursos.setVisible(False)

    def _abrir_resultado_de_otro_curso(self, item: QListWidgetItem):
        ruta_bd_otro_curso = Path(item.data(1))
        try:
            base_datos_otro_curso = BaseDatosCurso(ruta_bd_otro_curso)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "No se pudo abrir ese curso", str(exc))
            return
        ventana_otro_curso = VentanaCurso(base_datos_otro_curso, ruta_bd_otro_curso)
        ventana_otro_curso.conectar_ir_a_inicio(self._accion_ir_a_inicio)
        ventana_otro_curso.showMaximized()
        ventana_otro_curso.campo_busqueda.setText(item.data(2))
        self._ventana_otro_curso_abierta = ventana_otro_curso  # evita que el GC la cierre

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
        dialogo = DialogoNuevaMateria(self.ruta_bd, self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            materia_nueva = self.base_datos.crear_materia(dialogo.nombre_materia)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "No se pudo crear la materia", str(exc))
            return

        if dialogo.copiar_desde is not None:
            ruta_bd_origen, nombre_materia_origen = dialogo.copiar_desde
            try:
                self._copiar_estructura_materia(
                    ruta_bd_origen, nombre_materia_origen, materia_nueva.id, dialogo.nivel_copia
                )
            except Exception as exc:  # noqa: BLE001
                QMessageBox.warning(
                    self,
                    "Materia creada, pero la copia no se completó",
                    f"La materia «{dialogo.nombre_materia}» se ha creado, pero no se pudo "
                    f"copiar la estructura solicitada:\n{exc}",
                )

        self.refrescar_lista_materias()

    def importar_materia(self):
        """Importa una materia desde un archivo .evacyl. El docente
        elige el archivo y el curso destino donde crearla.
        """
        from PySide6.QtWidgets import QFileDialog
        from core.exportacion_materia import importar_materia, leer_metadatos_archivo

        # 1. Elegir el archivo .evacyl
        ruta_texto, _ = QFileDialog.getOpenFileName(
            self, "Importar materia", "",
            "Materia EVACYL (*.evacyl)"
        )
        if not ruta_texto:
            return
        ruta = Path(ruta_texto)

        # 2. Leer metadatos para mostrar información antes de confirmar
        try:
            meta = leer_metadatos_archivo(ruta)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Archivo no válido", f"No se pudo leer el archivo:\n{exc}")
            return

        nombre_original = meta["nombre"]

        # 3. Elegir curso destino (por defecto el curso actual)
        cursos = _cursos_disponibles(self.carpeta_docente)
        nombres_cursos = [c.name for c in cursos]
        nombre_curso_actual = self.ruta_bd.parent.name
        indice_actual = nombres_cursos.index(nombre_curso_actual) if nombre_curso_actual in nombres_cursos else 0

        nombre_curso_elegido, ok = QInputDialog.getItem(
            self,
            "Seleccionar curso destino",
            f"Importar «{nombre_original}» ({meta['num_criterios']} criterios, "
            f"{meta['num_alumnos']} alumnos) en el curso:",
            nombres_cursos, indice_actual, False
        )
        if not ok:
            return

        ruta_bd_destino = cursos[nombres_cursos.index(nombre_curso_elegido)] / NOMBRE_ARCHIVO_BD
        misma_bd = ruta_bd_destino == self.ruta_bd
        base_datos_destino = self.base_datos if misma_bd else BaseDatosCurso(ruta_bd_destino)

        try:
            # 4. Comprobar si ya existe una materia con ese nombre
            nombre_a_usar = nombre_original
            materias_existentes = [m.nombre for m in base_datos_destino.listar_materias()]
            if nombre_original in materias_existentes:
                respuesta = QMessageBox.question(
                    self,
                    "Nombre ya existe",
                    f"Ya existe una materia llamada «{nombre_original}» en el curso «{nombre_curso_elegido}».\n\n"
                    "¿Quieres crear una copia con un nombre distinto?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                )
                if respuesta != QMessageBox.StandardButton.Yes:
                    return
                nombre_a_usar, ok = QInputDialog.getText(
                    self, "Nombre para la copia",
                    "Introduce un nombre para la materia importada:",
                    text=f"{nombre_original} (importada)"
                )
                if not ok or not nombre_a_usar.strip():
                    return
                nombre_a_usar = nombre_a_usar.strip()
                if nombre_a_usar in materias_existentes:
                    QMessageBox.warning(
                        self, "Nombre ya existe",
                        f"«{nombre_a_usar}» también existe ya. Importación cancelada."
                    )
                    return

            # 5. Importar
            importar_materia(base_datos_destino, ruta, nombre_override=nombre_a_usar)

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error al importar", str(exc))
            return
        finally:
            if not misma_bd:
                base_datos_destino.cerrar()

        self.refrescar_lista_materias()
        QMessageBox.information(
            self, "Importación completada",
            f"Materia «{nombre_a_usar}» importada correctamente en el curso «{nombre_curso_elegido}»."
        )

    def _copiar_estructura_materia(
        self, ruta_bd_origen: Path, nombre_materia_origen: str, materia_destino_id: int, nivel_copia: str
    ):
        """Copia criterios (y, si corresponde, instrumentos) de la
        materia indicada en ruta_bd_origen hacia la materia ya creada
        materia_destino_id en self.base_datos. Si ruta_bd_origen es el
        mismo curso actual, reutiliza self.base_datos en vez de abrir
        una segunda conexión sobre el mismo archivo.
        """
        mismo_curso = ruta_bd_origen == self.ruta_bd
        base_datos_origen = self.base_datos if mismo_curso else BaseDatosCurso(ruta_bd_origen)
        try:
            materia_origen = next(
                (m for m in base_datos_origen.listar_materias() if m.nombre == nombre_materia_origen), None
            )
            if materia_origen is None:
                raise ValueError(f"No se ha encontrado la materia «{nombre_materia_origen}» en el curso origen.")

            mapa_criterios = self.base_datos.copiar_criterios_desde(
                base_datos_origen, materia_origen.id, materia_destino_id
            )
            if nivel_copia == NIVEL_CRITERIOS_E_INSTRUMENTOS:
                self.base_datos.copiar_instrumentos_desde(
                    base_datos_origen, materia_origen.id, materia_destino_id, mapa_criterios
                )
        finally:
            if not mismo_curso:
                base_datos_origen.cerrar()

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
