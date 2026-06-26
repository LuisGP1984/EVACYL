"""
Recopilación de datos para el informe individual de un alumno: pensado
para que el alumno (o su familia) entienda exactamente de dónde sale
cada nota, de cara a posibles reclamaciones. No genera ningún archivo —
eso lo hacen informe_pdf.py e informe_docx.py a partir de estas
estructuras, para no duplicar la lógica de cálculo en dos sitios.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.calificacion import calificacion_cualitativa
from core.database import BaseDatosCurso, Evaluacion, Materia


@dataclass
class FilaCriterioInstrumento:
    codigo_criterio: str
    peso_en_instrumento: float
    valor: float | None
    calificacion: str  # IN/SU/BI/NT/SB, o "" si no hay nota


@dataclass
class BloqueInstrumento:
    nombre_instrumento: str
    tipo_instrumento: str
    peso_global: float  # peso del instrumento dentro de la evaluación
    criterios: list[FilaCriterioInstrumento]


@dataclass
class FilaCriterioFinal:
    codigo_criterio: str
    valor: float | None
    calificacion: str
    valor_1eva: float | None
    valor_2eva: float | None
    valor_3eva: float | None


@dataclass
class InformeAlumno:
    """Todo lo necesario para construir el informe de un alumno en una
    evaluación normal (1EVA/2EVA/3EVA). Para FINAL, ver InformeAlumnoFinal.
    """

    nombre_materia: str
    nombre_evaluacion: str
    apellidos_alumno: str
    nombre_alumno: str
    filas_criterios: list[FilaCriterioInstrumento] = field(default_factory=list)
    nota_final_numerica: float | None = None
    calificacion_final: str = ""
    bloques_instrumentos: list[BloqueInstrumento] = field(default_factory=list)


@dataclass
class InformeAlumnoFinal:
    """Todo lo necesario para construir el informe de un alumno en FINAL."""

    nombre_materia: str
    apellidos_alumno: str
    nombre_alumno: str
    filas_criterios: list[FilaCriterioFinal] = field(default_factory=list)
    nota_final_numerica: float | None = None
    calificacion_final: str = ""
    pesos_evaluaciones: dict[str, float] = field(default_factory=dict)


def recopilar_informe_evaluacion(
    base_datos: BaseDatosCurso, materia: Materia, evaluacion: Evaluacion, alumno_id: int
) -> InformeAlumno | None:
    """Recopila los datos del informe de un alumno en una evaluación
    normal (1EVA/2EVA/3EVA). Devuelve None si el alumno no existe o no es
    evaluable en esta evaluación (se incorporó más adelante).
    """
    vista_alumnos = base_datos.listar_alumnos_para_evaluacion(materia.id, evaluacion.nombre)
    alumno_encontrado = None
    evaluable = False
    for alumno, es_evaluable in vista_alumnos:
        if alumno.id == alumno_id:
            alumno_encontrado = alumno
            evaluable = es_evaluable
            break
    if alumno_encontrado is None or not evaluable:
        return None

    criterios = base_datos.listar_criterios(materia.id)
    notas_criterio = base_datos.calcular_notas_criterios_evaluacion(evaluacion.id, materia.id)
    notas_materia = base_datos.calcular_notas_materia_evaluacion(evaluacion.id, materia.id)

    filas_criterios = []
    for criterio in criterios:
        valor = notas_criterio.get((criterio.id, alumno_id))
        filas_criterios.append(
            FilaCriterioInstrumento(
                codigo_criterio=criterio.codigo,
                peso_en_instrumento=criterio.peso,
                valor=valor,
                calificacion=calificacion_cualitativa(valor),
            )
        )

    nota_final = notas_materia.get(alumno_id)

    instrumentos = base_datos.listar_instrumentos(evaluacion.id)
    bloques = []
    for instrumento in instrumentos:
        criterios_marcados_ids = base_datos.criterios_marcados_de_instrumento(instrumento.id)
        if not criterios_marcados_ids:
            continue
        relaciones = {
            ic.criterio_id: ic for ic in base_datos.listar_criterios_de_instrumento(instrumento.id)
        }
        notas_criterio_instrumento = base_datos.obtener_notas_criterio_instrumento(instrumento.id)

        filas_bloque = []
        for criterio in criterios:
            if criterio.id not in criterios_marcados_ids:
                continue
            relacion = relaciones.get(criterio.id)
            valor, _es_manual = notas_criterio_instrumento.get((criterio.id, alumno_id), (None, False))
            filas_bloque.append(
                FilaCriterioInstrumento(
                    codigo_criterio=criterio.codigo,
                    peso_en_instrumento=relacion.peso if relacion is not None else 0.0,
                    valor=valor,
                    calificacion=calificacion_cualitativa(valor),
                )
            )
        bloques.append(
            BloqueInstrumento(
                nombre_instrumento=instrumento.nombre,
                tipo_instrumento=instrumento.tipo,
                peso_global=instrumento.peso,
                criterios=filas_bloque,
            )
        )

    return InformeAlumno(
        nombre_materia=materia.nombre,
        nombre_evaluacion=evaluacion.nombre,
        apellidos_alumno=alumno_encontrado.apellidos,
        nombre_alumno=alumno_encontrado.nombre,
        filas_criterios=filas_criterios,
        nota_final_numerica=nota_final,
        calificacion_final=calificacion_cualitativa(nota_final),
        bloques_instrumentos=bloques,
    )


def recopilar_informe_final(
    base_datos: BaseDatosCurso, materia: Materia, alumno_id: int
) -> InformeAlumnoFinal | None:
    """Recopila los datos del informe de un alumno en FINAL: nota de cada
    criterio en FINAL, y su desglose por 1EVA/2EVA/3EVA. Devuelve None si
    el alumno no existe en la materia.
    """
    alumnos = base_datos.listar_alumnos(materia.id)
    alumno_encontrado = next((a for a in alumnos if a.id == alumno_id), None)
    if alumno_encontrado is None:
        return None

    criterios = base_datos.listar_criterios(materia.id)
    notas_final = base_datos.calcular_notas_criterios_final(materia.id)
    nota_materia_final = base_datos.calcular_notas_materia_final(materia.id)

    evaluaciones = [
        ev for ev in base_datos.listar_evaluaciones(materia.id) if ev.nombre != "FINAL"
    ]
    notas_por_evaluacion = {
        ev.nombre: base_datos.calcular_notas_criterios_evaluacion(ev.id, materia.id)
        for ev in evaluaciones
    }

    filas = []
    for criterio in criterios:
        valor_final = notas_final.get((criterio.id, alumno_id))
        valor_1 = notas_por_evaluacion.get("1EVA", {}).get((criterio.id, alumno_id))
        valor_2 = notas_por_evaluacion.get("2EVA", {}).get((criterio.id, alumno_id))
        valor_3 = notas_por_evaluacion.get("3EVA", {}).get((criterio.id, alumno_id))
        filas.append(
            FilaCriterioFinal(
                codigo_criterio=criterio.codigo,
                valor=valor_final,
                calificacion=calificacion_cualitativa(valor_final),
                valor_1eva=valor_1,
                valor_2eva=valor_2,
                valor_3eva=valor_3,
            )
        )

    nota_final_materia = nota_materia_final.get(alumno_id)
    pesos_evaluaciones = base_datos.obtener_pesos_evaluaciones_final(materia.id)

    return InformeAlumnoFinal(
        nombre_materia=materia.nombre,
        apellidos_alumno=alumno_encontrado.apellidos,
        nombre_alumno=alumno_encontrado.nombre,
        filas_criterios=filas,
        nota_final_numerica=nota_final_materia,
        calificacion_final=calificacion_cualitativa(nota_final_materia),
        pesos_evaluaciones=pesos_evaluaciones,
    )
