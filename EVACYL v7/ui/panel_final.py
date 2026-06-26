"""
Panel de la evaluación FINAL. A diferencia de 1EVA/2EVA/3EVA:

  - No tiene instrumentos propios: en su lugar, una sub-pestaña
    "Evaluaciones" donde se ajusta el peso de 1EVA/2EVA/3EVA (ver
    panel_evaluaciones_final.py).
  - Las calificaciones se calculan siempre a partir de las notas de
    criterio de 1EVA, 2EVA y 3EVA: no hace falta ningún botón, se
    recalculan solas cada vez que se entra en la pestaña.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.calificacion import calificacion_cualitativa
from core.database import BaseDatosCurso, Materia
from core.exportacion import exportar_final
from ui.dialogo_informes import DialogoGenerarInformes, generar_informe_final_individual
from ui.panel_evaluacion import (
    COLOR_FONDO_IDENTIDAD,
    _aplicar_cabeceras_por_bloque,
    _color_para_nota,
    _formatear_celda_nota,
    _formatear_numero,
)
from ui.panel_evaluaciones_final import PanelEvaluacionesFinal
from ui.panel_estadisticas import PanelEstadisticas
from ui.panel_trazabilidad import PanelTrazabilidadFinal
from ui.widgets_comunes import BotonAyuda

TEXTO_AYUDA_FINAL_CALIFICACIONES = (
    "Esta tabla es la nota final de curso para cada alumno/a: se calcula sola, "
    "combinando las notas de criterio de 1EVA, 2EVA y 3EVA según el peso que le "
    "hayas dado a cada evaluación en la sub-pestaña «⚖️ Evaluaciones».\n\n"
    "No introduces nada aquí directamente. Si a un alumno le falta nota de un "
    "criterio en alguna evaluación, las que sí tienen nota se reparten el 100% del "
    "peso para ese criterio (no se penaliza por tener menos evaluaciones)."
)


class TablaCalificacionesFinal(QWidget):
    """Igual que TablaCalificaciones de una evaluación normal, pero
    calculando a partir de calcular_notas_criterios_final /
    calcular_notas_materia_final, y sin atenuar a ningún alumno (en FINAL
    siempre se incluye a todo el alumnado, independientemente de cuándo
    se incorporara).
    """

    def __init__(self, base_datos: BaseDatosCurso, materia: Materia):
        super().__init__()
        self.base_datos = base_datos
        self.materia = materia

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        fila_titulo = QHBoxLayout()
        titulo = QLabel("🏁 Calificaciones — Evaluación Final del curso")
        titulo.setObjectName("subtitulo")
        fila_titulo.addWidget(titulo)
        fila_titulo.addStretch()
        fila_titulo.addWidget(BotonAyuda("Ayuda — Calificaciones FINAL", TEXTO_AYUDA_FINAL_CALIFICACIONES))
        layout.addLayout(fila_titulo)

        self.tabla = QTableWidget()
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabla)

        nota = QLabel(
            "Esta tabla se calcula automáticamente a partir de 1EVA, 2EVA y 3EVA, según el "
            "peso indicado en la sub-pestaña «Evaluaciones». No hace falta introducir nada "
            "aquí directamente."
        )
        nota.setWordWrap(True)
        nota.setStyleSheet("color: #5B6B82;")
        layout.addWidget(nota)

        fila_botones = QHBoxLayout()
        boton_exportar = QPushButton("📥 Exportar a Excel…")
        boton_exportar.clicked.connect(self.exportar_a_excel)
        fila_botones.addWidget(boton_exportar)

        boton_informe = QPushButton("📄 Generar informe de alumno…")
        boton_informe.setObjectName("botonSecundario")
        boton_informe.clicked.connect(self.abrir_dialogo_informes)
        fila_botones.addWidget(boton_informe)

        fila_botones.addStretch()
        layout.addLayout(fila_botones)

        self.refrescar()

    def exportar_a_excel(self):
        nombre_sugerido = f"{self.materia.nombre} - FINAL.xlsx"
        ruta_texto, _ = QFileDialog.getSaveFileName(
            self, "Exportar calificaciones finales a Excel", nombre_sugerido, filter="Excel (*.xlsx)"
        )
        if not ruta_texto:
            return
        ruta = Path(ruta_texto)
        if ruta.suffix.lower() != ".xlsx":
            ruta = ruta.with_suffix(".xlsx")
        try:
            exportar_final(self.base_datos, self.materia, ruta)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "No se pudo exportar", str(exc))
            return
        QMessageBox.information(self, "Exportación completada", f"Archivo guardado en:\n{ruta}")

    def abrir_dialogo_informes(self):
        alumnos = self.base_datos.listar_alumnos(self.materia.id)
        lista_alumnos = [(a.id, f"{a.apellidos}, {a.nombre}".strip(", ")) for a in alumnos]
        if not lista_alumnos:
            QMessageBox.information(self, "Sin alumnado", "Esta materia todavía no tiene alumnado.")
            return

        def generar_uno(alumno_id, formato, carpeta_destino):
            return generar_informe_final_individual(
                self.base_datos, self.materia, alumno_id, formato, carpeta_destino
            )

        dialogo = DialogoGenerarInformes("Generar informe — FINAL", lista_alumnos, generar_uno, self)
        dialogo.exec()

    def refrescar(self):
        criterios = self.base_datos.listar_criterios(self.materia.id)
        alumnos = self.base_datos.listar_alumnos(self.materia.id)

        encabezados = (
            ["Apellidos", "Nombre"]
            + [c.codigo for c in criterios]
            + ["NOTA FINAL DE CURSO", "CALIFICACIÓN"]
        )
        self.tabla.setColumnCount(len(encabezados))
        self.tabla.setRowCount(len(alumnos))

        col_final_numero = 2 + len(criterios)
        col_final_letra = col_final_numero + 1
        _aplicar_cabeceras_por_bloque(self.tabla, encabezados, col_final_numero)
        cabecera = self.tabla.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        cabecera.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in range(2, col_final_numero):
            cabecera.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.tabla.setColumnWidth(col, 70)
        cabecera.setSectionResizeMode(col_final_numero, QHeaderView.ResizeMode.Fixed)
        cabecera.setSectionResizeMode(col_final_letra, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(col_final_numero, 100)
        self.tabla.setColumnWidth(col_final_letra, 110)

        notas_criterio = self.base_datos.calcular_notas_criterios_final(self.materia.id)
        notas_materia = self.base_datos.calcular_notas_materia_final(self.materia.id)

        for fila, alumno in enumerate(alumnos):
            item_apellidos = QTableWidgetItem(alumno.apellidos)
            item_nombre = QTableWidgetItem(alumno.nombre)
            item_apellidos.setBackground(COLOR_FONDO_IDENTIDAD)
            item_nombre.setBackground(COLOR_FONDO_IDENTIDAD)
            self.tabla.setItem(fila, 0, item_apellidos)
            self.tabla.setItem(fila, 1, item_nombre)

            for indice_criterio, criterio in enumerate(criterios):
                valor = notas_criterio.get((criterio.id, alumno.id))
                texto, color = _formatear_celda_nota(valor)
                item = QTableWidgetItem(texto)
                if color is not None:
                    item.setBackground(color)
                self.tabla.setItem(fila, 2 + indice_criterio, item)

            valor_final = notas_materia.get(alumno.id)
            color_final = _color_para_nota(valor_final)

            item_numero_final = QTableWidgetItem(_formatear_numero(valor_final))
            item_letra_final = QTableWidgetItem(calificacion_cualitativa(valor_final))
            for item in (item_numero_final, item_letra_final):
                if color_final is not None:
                    item.setBackground(color_final)
                fuente = item.font()
                fuente.setBold(True)
                item.setFont(fuente)
            self.tabla.setItem(fila, col_final_numero, item_numero_final)
            self.tabla.setItem(fila, col_final_letra, item_letra_final)


class PanelFinal(QWidget):
    def __init__(self, base_datos: BaseDatosCurso, materia: Materia):
        super().__init__()
        self.base_datos = base_datos
        self.materia = materia

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.sub_pestanas = QTabWidget()
        layout.addWidget(self.sub_pestanas)

        self.tabla_calificaciones = TablaCalificacionesFinal(base_datos, materia)
        self.sub_pestanas.addTab(self.tabla_calificaciones, "📊 Calificaciones")

        self.panel_evaluaciones = PanelEvaluacionesFinal(base_datos, materia)
        self.sub_pestanas.addTab(self.panel_evaluaciones, "⚖️ Evaluaciones")

        self.panel_estadisticas = PanelEstadisticas(
            titulo="📈 Estadísticas — Evaluación Final",
            obtener_notas_finales=self._obtener_notas_finales_para_estadisticas,
            obtener_lista_alumnos=self._obtener_lista_alumnos,
            obtener_datos_grafico_alumno=self._obtener_datos_grafico_alumno,
            etiqueta_grafico="evaluación",
            obtener_datos_grafico_todos=self._obtener_datos_grafico_todos,
        )
        self.sub_pestanas.addTab(self.panel_estadisticas, "📈 Estadísticas")

        self.panel_trazabilidad = PanelTrazabilidadFinal(base_datos, materia)
        self.sub_pestanas.addTab(self.panel_trazabilidad, "🔗 Trazabilidad")

        self.sub_pestanas.currentChanged.connect(self._al_cambiar_sub_pestana)

    def _obtener_notas_finales_para_estadisticas(self) -> dict[int, float | None]:
        return self.base_datos.calcular_notas_materia_final(self.materia.id)

    def _obtener_lista_alumnos(self) -> list[tuple[int, str]]:
        alumnos = self.base_datos.listar_alumnos(self.materia.id)
        return [(a.id, f"{a.apellidos}, {a.nombre}".strip(", ")) for a in alumnos]

    def _obtener_datos_grafico_alumno(self, alumno_id: int) -> tuple[list[str], list[float | None]]:
        etiquetas = []
        valores = []
        for evaluacion in self.base_datos.listar_evaluaciones(self.materia.id):
            if evaluacion.nombre == "FINAL":
                continue
            notas_evaluacion = self.base_datos.calcular_notas_materia_evaluacion(
                evaluacion.id, self.materia.id
            )
            etiquetas.append(evaluacion.nombre)
            valores.append(notas_evaluacion.get(alumno_id))
        return etiquetas, valores

    def _obtener_datos_grafico_todos(self) -> tuple[list[str], list[str], list[list[float | None]]]:
        evaluaciones = [
            ev for ev in self.base_datos.listar_evaluaciones(self.materia.id) if ev.nombre != "FINAL"
        ]
        etiquetas = [ev.nombre for ev in evaluaciones]
        notas_por_evaluacion = {
            ev.id: self.base_datos.calcular_notas_materia_evaluacion(ev.id, self.materia.id)
            for ev in evaluaciones
        }
        alumnos = self._obtener_lista_alumnos()
        nombres_alumnos = [etiqueta for _alumno_id, etiqueta in alumnos]
        valores_por_alumno = [
            [notas_por_evaluacion[ev.id].get(alumno_id) for ev in evaluaciones]
            for alumno_id, _etiqueta in alumnos
        ]
        return etiquetas, nombres_alumnos, valores_por_alumno

    def _al_cambiar_sub_pestana(self, _indice: int):
        self.tabla_calificaciones.refrescar()
        if self.sub_pestanas.currentWidget() is self.panel_estadisticas:
            self.panel_estadisticas.refrescar()
        elif self.sub_pestanas.currentWidget() is self.panel_trazabilidad:
            self.panel_trazabilidad.refrescar()

    def refrescar(self):
        self.tabla_calificaciones.refrescar()
        self.panel_evaluaciones.refrescar()
        self.panel_estadisticas.refrescar()
        self.panel_trazabilidad.refrescar()
