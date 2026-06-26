"""
Acceso al currículo oficial LOMLOE de Castilla y León: estructura
etapa -> curso -> materia -> lista de códigos de criterio de evaluación.

Los datos viven en datos_curriculares/curriculo_lomloe_cyl.json, generados
a partir de fuentes oficiales (BOCYL / Mapas de Relaciones Criteriales).

Disponibles: PRIMARIA (1º a 6º EP), SECUNDARIA (1º a 4º ESO) y
BACHILLERATO (1º y 2º BACH). En Bachillerato se usan únicamente las
hojas separadas por curso de la fuente original; la hoja agregada
("BACH") mezclaba criterios de 1º y 2º bajo el mismo nombre de materia
y no se utiliza para evitar duplicados.
"""

from __future__ import annotations

import json
from functools import lru_cache

from core.rutas_app import ruta_raiz_proyecto

RUTA_ARCHIVO_CURRICULO = ruta_raiz_proyecto() / "datos_curriculares" / "curriculo_lomloe_cyl.json"

# Etiquetas legibles para las etapas que YA están disponibles en los datos.
ETAPAS_DISPONIBLES = ["PRIMARIA", "SECUNDARIA", "BACHILLERATO", "ESPA"]

ETIQUETAS_ETAPA = {
    "PRIMARIA": "Educación Primaria",
    "SECUNDARIA": "Educación Secundaria Obligatoria (ESO)",
    "BACHILLERATO": "Bachillerato",
    "ESPA": "Educación Secundaria para Personas Adultas (ESPA)",
}

# Algunas etapas usan una jerarquía con otros nombres (ESPA se organiza
# en Ámbito -> Módulo, en vez de Curso -> Materia/Área). Esto solo
# afecta a las etiquetas que ve el docente en el asistente; los datos
# se guardan exactamente con la misma forma {etapa: {nivel1: {nivel2: [...]}}}.
ETIQUETAS_NIVELES = {
    "PRIMARIA": ("Curso", "Materia / Área"),
    "SECUNDARIA": ("Curso", "Materia / Área"),
    "BACHILLERATO": ("Curso", "Materia / Área"),
    "ESPA": ("Ámbito", "Módulo"),
}

# Referencia normativa oficial de la que se extrae el currículo de cada
# etapa, para que el docente sepa siempre cuál es la fuente legal.
REFERENCIA_NORMATIVA_ETAPA = {
    "PRIMARIA": (
        "Anexo III del Decreto 38/2022, de 29 de septiembre, por el que se establece "
        "la ordenación y el currículo de la Educación Primaria en la Comunidad de "
        "Castilla y León."
    ),
    "SECUNDARIA": (
        "Anexo III del Decreto 39/2022, de 29 de septiembre, por el que se establece "
        "la ordenación y el currículo de la Educación Secundaria Obligatoria en la "
        "Comunidad de Castilla y León."
    ),
    "BACHILLERATO": (
        "Anexo III del Decreto 40/2022, de 29 de septiembre, por el que se establece "
        "la ordenación y el currículo del Bachillerato en la Comunidad de Castilla y León."
    ),
    "ESPA": (
        "Decreto 10/2025, de 31 de julio, por el que se establecen la ordenación y el "
        "currículo de la enseñanza secundaria para personas adultas en la Comunidad de "
        "Castilla y León."
    ),
}


def referencia_normativa(etapa: str) -> str:
    """Devuelve el texto de referencia normativa de la etapa, o cadena
    vacía si la etapa no es una de las reconocidas.
    """
    return REFERENCIA_NORMATIVA_ETAPA.get(etapa, "")


def etiquetas_niveles(etapa: str) -> tuple[str, str]:
    """Devuelve (etiqueta_nivel1, etiqueta_nivel2) para los selectores
    del asistente: por ejemplo ("Curso", "Materia / Área") para LOMLOE,
    o ("Ámbito", "Módulo") para ESPA.
    """
    return ETIQUETAS_NIVELES.get(etapa, ("Curso", "Materia / Área"))


@lru_cache(maxsize=1)
def _cargar_datos() -> dict:
    if not RUTA_ARCHIVO_CURRICULO.exists():
        return {}
    with open(RUTA_ARCHIVO_CURRICULO, encoding="utf-8") as f:
        return json.load(f)


def etapas_disponibles() -> list[str]:
    """Etapas para las que SÍ hay datos curriculares cargados."""
    datos = _cargar_datos()
    return [etapa for etapa in ETAPAS_DISPONIBLES if etapa in datos]


def cursos_de_etapa(etapa: str) -> list[str]:
    datos = _cargar_datos()
    return list(datos.get(etapa, {}).keys())


def materias_de_curso(etapa: str, curso: str) -> list[str]:
    datos = _cargar_datos()
    return list(datos.get(etapa, {}).get(curso, {}).keys())


def criterios_de_materia(etapa: str, curso: str, materia: str) -> list[str]:
    """Devuelve la lista de códigos de criterio (ej. ["1.1", "1.2", ...])
    para una combinación etapa/curso/materia. Lista vacía si no existe.
    """
    datos = _cargar_datos()
    return list(datos.get(etapa, {}).get(curso, {}).get(materia, []))
