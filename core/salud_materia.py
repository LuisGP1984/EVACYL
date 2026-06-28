"""
Detección de incidencias de configuración en una evaluación (1EVA,
2EVA, 3EVA o FINAL) de una materia, para mostrar un resumen ("panel de
salud") dentro de cada pestaña.

Importante: en EVACYL los criterios son una lista única y compartida
por toda la materia, pero NO todos tienen que usarse en todas las
evaluaciones — es perfectamente normal que un criterio se evalúe solo
en 1EVA y otro solo en 3EVA. Por eso aquí NUNCA se avisa de "los
criterios de la materia suman X%": esa suma global no es relevante por
evaluación. Lo que sí se revisa en cada evaluación parcial es el peso
de sus INSTRUMENTOS (deben sumar 100% entre ellos) y, dentro de cada
instrumento, el peso de sus PRUEBAS — pero solo cuando el instrumento es de tipo "media
ponderada", que es el único caso donde el docente asigna realmente un
peso a cada prueba. En "media aritmética" las pruebas pesan todas
igual por diseño y ese campo nunca se usa, así que comprobar su suma
ahí no tiene sentido y generaría un aviso falso.

El único aviso relacionado con "criterios sin usar" vive en FINAL, y
mira si un criterio se ha quedado sin ninguna nota en NINGUNA de las
tres evaluaciones para NINGÚN alumno — lo cual normalmente indica que
el docente se olvidó de asignarlo a algún instrumento en algún momento
del curso.

Todas las incidencias aquí son AVISOS, nunca ERRORES bloqueantes: el
motor de cálculo de EVACYL redistribuye dinámicamente sobre los pesos
presentes en cada caso, así que ninguna de estas situaciones impide
que se calcule una nota.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.database import BaseDatosCurso, Evaluacion, Materia, TIPO_MEDIA_PONDERADA

SEVERIDAD_AVISO = "aviso"
SEVERIDAD_ERROR = "error"


@dataclass
class IncidenciaSalud:
    severidad: str
    mensaje: str


def _umbral_ok(suma: float) -> bool:
    return abs(suma - 100.0) < 0.01


def revisar_salud_evaluacion(
    base_datos: BaseDatosCurso, materia: Materia, evaluacion: Evaluacion
) -> list[IncidenciaSalud]:
    """Incidencias de una evaluación concreta (1EVA, 2EVA o 3EVA): peso
    de los instrumentos de esa evaluación, instrumentos sin ningún
    criterio marcado, e instrumentos de media ponderada con varias
    pruebas cuyo peso no
    suma 100% entre ellas.
    """
    incidencias: list[IncidenciaSalud] = []

    instrumentos = base_datos.listar_instrumentos(evaluacion.id)
    if not instrumentos:
        incidencias.append(
            IncidenciaSalud(SEVERIDAD_AVISO, "Todavía no hay ningún instrumento de evaluación creado en esta evaluación.")
        )
        return incidencias

    suma_instrumentos = base_datos.suma_pesos_instrumentos(evaluacion.id)
    if not _umbral_ok(suma_instrumentos):
        incidencias.append(
            IncidenciaSalud(
                SEVERIDAD_AVISO,
                f"Los pesos de los instrumentos de esta evaluación suman {suma_instrumentos:g}% "
                "(deberían ser 100%).",
            )
        )

    for instrumento in instrumentos:
        if not base_datos.criterios_marcados_de_instrumento(instrumento.id):
            incidencias.append(
                IncidenciaSalud(
                    SEVERIDAD_AVISO,
                    f"El instrumento «{instrumento.nombre}» no evalúa ningún criterio todavía.",
                )
            )

        pruebas = base_datos.listar_pruebas(instrumento.id)
        if instrumento.tipo == TIPO_MEDIA_PONDERADA and len(pruebas) > 1:
            suma_pruebas = base_datos.suma_pesos_pruebas(instrumento.id)
            if not _umbral_ok(suma_pruebas):
                incidencias.append(
                    IncidenciaSalud(
                        SEVERIDAD_AVISO,
                        f"Las pruebas del instrumento «{instrumento.nombre}» suman {suma_pruebas:g}% "
                        "(deberían ser 100%).",
                    )
                )

    return incidencias


def revisar_salud_final(base_datos: BaseDatosCurso, materia: Materia) -> list[IncidenciaSalud]:
    """Incidencias de FINAL: evaluaciones (1EVA/2EVA/3EVA) sin ningún
    instrumento, y criterios que se han quedado sin ninguna nota en
    ninguna de las tres evaluaciones para ningún alumno (probablemente
    olvidados al configurar los instrumentos).
    """
    incidencias: list[IncidenciaSalud] = []

    evaluaciones = [ev for ev in base_datos.listar_evaluaciones(materia.id) if ev.nombre != "FINAL"]
    if not evaluaciones:
        incidencias.append(IncidenciaSalud(SEVERIDAD_AVISO, "Esta materia no tiene evaluaciones."))
    else:
        for evaluacion in evaluaciones:
            if not base_datos.listar_instrumentos(evaluacion.id):
                incidencias.append(
                    IncidenciaSalud(
                        SEVERIDAD_AVISO,
                        f"«{evaluacion.nombre}» todavía no tiene ningún instrumento de evaluación "
                        "creado, así que no aporta nada a la nota final.",
                    )
                )

    criterios = base_datos.listar_criterios(materia.id)
    alumnos = base_datos.listar_alumnos(materia.id)
    if criterios and alumnos:
        notas_criterios_final = base_datos.calcular_notas_criterios_final(materia.id)
        criterios_sin_calificar = [
            criterio
            for criterio in criterios
            if all(notas_criterios_final.get((criterio.id, alumno.id)) is None for alumno in alumnos)
        ]
        if criterios_sin_calificar:
            codigos = ", ".join(c.codigo for c in criterios_sin_calificar[:8])
            extra = f" y {len(criterios_sin_calificar) - 8} más" if len(criterios_sin_calificar) > 8 else ""
            incidencias.append(
                IncidenciaSalud(
                    SEVERIDAD_AVISO,
                    f"{len(criterios_sin_calificar)} criterio(s) sin ninguna nota en todo el curso "
                    f"(ningún alumno, en ninguna evaluación): {codigos}{extra}. Puede que se hayan "
                    "olvidado al configurar los instrumentos.",
                )
            )

    return incidencias
