"""
Estadísticas de calificación cualitativa (IN/SU/BI/NT/SB) para una
evaluación o para FINAL: cuántos alumnos hay en cada categoría y qué
porcentaje representan. Se calcula a partir de las notas finales de
materia ya existentes (calcular_notas_materia_evaluacion /
calcular_notas_materia_final), no almacena nada nuevo en la base de datos.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.calificacion import calificacion_cualitativa

ORDEN_CATEGORIAS = ["IN", "SU", "BI", "NT", "SB"]


@dataclass
class EstadisticaCategoria:
    categoria: str  # IN, SU, BI, NT o SB
    cantidad: int
    porcentaje: float  # 0-100, sobre el total de alumnos CON nota (no presentados se excluyen)


@dataclass
class EstadisticasCalificacion:
    categorias: list[EstadisticaCategoria]
    total_con_nota: int
    total_sin_nota: int  # alumnos sin nota final todavía (no presentados / sin datos)


def calcular_estadisticas(notas_por_alumno: dict[int, float | None]) -> EstadisticasCalificacion:
    """A partir de {alumno_id: nota_0_10 o None}, calcula cuántos alumnos
    caen en cada categoría cualitativa y su porcentaje sobre el total de
    alumnos que SÍ tienen nota (los None se cuentan aparte, no se
    reparten su "hueco" entre las demás categorías).
    """
    conteo = {categoria: 0 for categoria in ORDEN_CATEGORIAS}
    total_sin_nota = 0

    for valor in notas_por_alumno.values():
        if valor is None:
            total_sin_nota += 1
            continue
        categoria = calificacion_cualitativa(valor)
        if categoria:
            conteo[categoria] += 1

    total_con_nota = sum(conteo.values())

    categorias = []
    for categoria in ORDEN_CATEGORIAS:
        cantidad = conteo[categoria]
        porcentaje = round(cantidad * 100 / total_con_nota, 1) if total_con_nota > 0 else 0.0
        categorias.append(EstadisticaCategoria(categoria=categoria, cantidad=cantidad, porcentaje=porcentaje))

    return EstadisticasCalificacion(
        categorias=categorias, total_con_nota=total_con_nota, total_sin_nota=total_sin_nota
    )
