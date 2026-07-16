"""
Exportación e importación de una materia completa entre instalaciones
distintas de EVACYL, a través de un archivo .evacyl (JSON comprimido
con gzip).

El archivo incluye TODO: estructura (criterios, pesos, modo de cálculo
final), instrumentos de evaluación con sus pruebas y criterios
vinculados, alumnado, y todas las notas registradas. Los IDs internos
de la base de datos origen se descartan al importar — se generan IDs
nuevos en la base de datos destino, evitando cualquier conflicto.

Flujo:
  Exportar: exportar_materia(base_datos, materia) → ruta .evacyl
  Importar: importar_materia(base_datos_destino, ruta) → Materia nueva
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from core.database import BaseDatosCurso, Materia

EXTENSION = ".evacyl"
VERSION_FORMATO = 1


# ---------------------------------------------------------------------------
# EXPORTACIÓN
# ---------------------------------------------------------------------------

def exportar_materia(
    base_datos: BaseDatosCurso, materia: Materia, ruta_destino: Path,
    solo_estructura: bool = False
) -> Path:
    """Serializa la materia (completa o solo estructura) a un archivo .evacyl."""
    datos = _serializar_materia(base_datos, materia, solo_estructura)
    contenido = json.dumps(datos, ensure_ascii=False, indent=None).encode("utf-8")
    with gzip.open(ruta_destino, "wb") as f:
        f.write(contenido)
    return ruta_destino


def _serializar_materia(
    base_datos: BaseDatosCurso, materia: Materia, solo_estructura: bool = False
) -> dict:
    db = base_datos.conexion

    # -- materia --
    datos: dict = {
        "version": VERSION_FORMATO,
        "solo_estructura": solo_estructura,
        "materia": {
            "nombre": materia.nombre,
            "modo_calculo_final": base_datos.obtener_modo_calculo_final(materia.id),
        },
        "evaluaciones": [],
        "alumnos": [],
        "criterios": [],
    }

    # -- evaluaciones (1EVA, 2EVA, 3EVA, FINAL) --
    cur = db.execute("SELECT id, nombre FROM evaluacion WHERE materia_id = ? ORDER BY id;", (materia.id,))
    evaluaciones_raw = cur.fetchall()
    evaluaciones_por_id = {r[0]: r[1] for r in evaluaciones_raw}

    # -- pesos de evaluación final --
    cur = db.execute("SELECT nombre_evaluacion, peso FROM peso_evaluacion_final WHERE materia_id = ?;", (materia.id,))
    pesos_final = {r[0]: r[1] for r in cur.fetchall()}
    datos["pesos_evaluacion_final"] = pesos_final

    # -- criterios --
    cur = db.execute(
        "SELECT id, codigo, peso, orden, modo_calculo_final FROM criterio WHERE materia_id = ? ORDER BY orden;",
        (materia.id,)
    )
    criterios_raw = cur.fetchall()
    criterios_por_id = {}
    for r in criterios_raw:
        criterio_data = {"codigo": r[1], "peso": r[2], "orden": r[3], "modo_calculo_final": r[4]}
        datos["criterios"].append(criterio_data)
        criterios_por_id[r[0]] = criterio_data

    # -- alumnos (solo en exportación completa) --
    alumnos_por_id = {}
    if not solo_estructura:
        cur = db.execute(
            "SELECT id, apellidos, nombre, orden, orden_alta FROM alumno WHERE materia_id = ? ORDER BY orden;",
            (materia.id,)
        )
        alumnos_raw = cur.fetchall()
        for r in alumnos_raw:
            alumno_data = {"apellidos": r[1], "nombre": r[2], "orden": r[3], "orden_alta": r[4]}
            datos["alumnos"].append(alumno_data)
            alumnos_por_id[r[0]] = alumno_data

    # -- evaluaciones con sus instrumentos, pruebas y notas --
    for eval_id, eval_nombre in evaluaciones_por_id.items():
        eval_data: dict = {"nombre": eval_nombre, "instrumentos": []}

        if not solo_estructura:
            cur = db.execute(
                "SELECT id, nombre, tipo, peso, nota_maxima FROM instrumento_evaluacion WHERE evaluacion_id = ? ORDER BY id;",
                (eval_id,)
            )
            for ie_row in cur.fetchall():
                ie_id = ie_row[0]
                ie_data: dict = {
                    "nombre": ie_row[1], "tipo": ie_row[2], "peso": ie_row[3], "nota_maxima": ie_row[4],
                    "criterios_vinculados": [], "pruebas": [],
                    "notas_instrumento": [], "notas_criterio": [],
                }

                cur2 = db.execute(
                    """SELECT c.codigo, ic.peso, ic.peso_manual
                       FROM instrumento_criterio ic JOIN criterio c ON c.id = ic.criterio_id
                       WHERE ic.instrumento_id = ?;""", (ie_id,)
                )
                ie_data["criterios_vinculados"] = [
                    {"codigo": r[0], "peso": r[1], "peso_manual": r[2]} for r in cur2.fetchall()
                ]

                cur2 = db.execute(
                    "SELECT nombre, peso, orden FROM prueba_instrumento WHERE instrumento_id = ? ORDER BY orden;",
                    (ie_id,)
                )
                ie_data["pruebas"] = [{"nombre": r[0], "peso": r[1], "orden": r[2]} for r in cur2.fetchall()]

                cur2 = db.execute(
                    """SELECT a.apellidos, a.nombre, n.valor
                       FROM nota_instrumento_alumno n JOIN alumno a ON a.id = n.alumno_id
                       WHERE n.instrumento_id = ?;""", (ie_id,)
                )
                ie_data["notas_instrumento"] = [
                    {"apellidos": r[0], "nombre": r[1], "nota": r[2]} for r in cur2.fetchall()
                ]

                cur2 = db.execute(
                    """SELECT a.apellidos, a.nombre, c.codigo, n.valor, n.es_manual
                       FROM nota_criterio_instrumento_alumno n
                       JOIN alumno a ON a.id = n.alumno_id
                       JOIN criterio c ON c.id = n.criterio_id
                       WHERE n.instrumento_id = ?;""", (ie_id,)
                )
                ie_data["notas_criterio"] = [
                    {"apellidos": r[0], "nombre": r[1], "codigo_criterio": r[2], "nota": r[3], "es_manual": r[4]}
                    for r in cur2.fetchall()
                ]

                cur2 = db.execute(
                    """SELECT a.apellidos, a.nombre, pi.nombre as prueba_nombre, n.valor
                       FROM nota_prueba n
                       JOIN alumno a ON a.id = n.alumno_id
                       JOIN prueba_instrumento pi ON pi.id = n.prueba_id
                       WHERE pi.instrumento_id = ?;""", (ie_id,)
                )
                notas_prueba = cur2.fetchall()
                if notas_prueba:
                    ie_data["notas_prueba"] = [
                        {"apellidos": r[0], "nombre": r[1], "prueba_nombre": r[2], "nota": r[3]}
                        for r in notas_prueba
                    ]

                eval_data["instrumentos"].append(ie_data)

        datos["evaluaciones"].append(eval_data)

    return datos


# ---------------------------------------------------------------------------
# IMPORTACIÓN
# ---------------------------------------------------------------------------

def leer_metadatos_archivo(ruta: Path) -> dict:
    """Lee solo los metadatos básicos (nombre de materia, versión) sin
    importar nada — útil para mostrar información antes de confirmar.
    """
    datos = _leer_archivo(ruta)
    return {
        "nombre": datos["materia"]["nombre"],
        "version": datos.get("version", 1),
        "solo_estructura": datos.get("solo_estructura", False),
        "num_criterios": len(datos.get("criterios", [])),
        "num_alumnos": len(datos.get("alumnos", [])),
    }


def importar_materia(
    base_datos: BaseDatosCurso,
    ruta: Path,
    nombre_override: str | None = None,
) -> Materia:
    """Importa una materia desde un archivo .evacyl en la base de datos
    dada. Si nombre_override no es None, usa ese nombre en vez del
    original del archivo (para resolver conflictos de nombre).
    """
    datos = _leer_archivo(ruta)
    return _deserializar_materia(base_datos, datos, nombre_override)


def _leer_archivo(ruta: Path) -> dict:
    with gzip.open(ruta, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def _deserializar_materia(
    base_datos: BaseDatosCurso, datos: dict, nombre_override: str | None
) -> Materia:
    nombre = nombre_override or datos["materia"]["nombre"]
    modo = datos["materia"].get("modo_calculo_final", "CONTINUA")

    # Crear la materia nueva
    materia = base_datos.crear_materia(nombre)
    if modo != "CONTINUA":
        base_datos.actualizar_modo_calculo_final(materia.id, modo)

    # Releer el objeto para que refleje el modo actualizado en la BD
    materia = next(m for m in base_datos.listar_materias() if m.id == materia.id)

    db = base_datos.conexion

    # -- pesos de evaluación final --
    pesos_final = datos.get("pesos_evaluacion_final", {})
    for nombre_eval, peso in pesos_final.items():
        base_datos.actualizar_peso_evaluacion_final(materia.id, nombre_eval, peso)

    # -- criterios: mapa codigo → nuevo id --
    criterios_por_codigo: dict[str, int] = {}
    for c in datos.get("criterios", []):
        criterio = base_datos.agregar_criterio(materia.id, c["codigo"], c["peso"])
        modo_c = c.get("modo_calculo_final", "HEREDADO")
        if modo_c != "HEREDADO":
            base_datos.actualizar_modo_calculo_criterio(criterio.id, modo_c)
        criterios_por_codigo[c["codigo"]] = criterio.id

    # -- alumnos: mapa (apellidos, nombre) → nuevo id --
    alumnos_por_clave: dict[tuple[str, str], int] = {}
    for a in datos.get("alumnos", []):
        alumno = base_datos.agregar_alumno(
            materia.id, a["apellidos"], a["nombre"],
            orden_alta=a.get("orden_alta", 1)
        )
        alumnos_por_clave[(a["apellidos"], a["nombre"])] = alumno.id

    # -- evaluaciones, instrumentos, notas --
    evaluaciones_por_nombre = {
        ev.nombre: ev for ev in base_datos.listar_evaluaciones(materia.id)
    }

    for eval_data in datos.get("evaluaciones", []):
        eval_nombre = eval_data["nombre"]
        evaluacion = evaluaciones_por_nombre.get(eval_nombre)
        if evaluacion is None:
            continue  # FINAL no tiene instrumentos propios

        for ie_data in eval_data.get("instrumentos", []):
            # Crear el instrumento
            ie = base_datos.crear_instrumento(
                evaluacion.id, ie_data["nombre"], ie_data["tipo"],
                nota_maxima=ie_data.get("nota_maxima", 10)
            )
            base_datos.actualizar_instrumento(
                ie.id, ie_data["nombre"], ie_data["peso"],
                ie_data.get("nota_maxima", 10)
            )

            # Pruebas
            for p in ie_data.get("pruebas", []):
                prueba = base_datos.agregar_prueba(ie.id, p["nombre"])
                if p.get("peso", 0) > 0:
                    base_datos.actualizar_prueba(prueba.id, p["nombre"], p["peso"])

            # Criterios vinculados
            for cv in ie_data.get("criterios_vinculados", []):
                criterio_id = criterios_por_codigo.get(cv["codigo"])
                if criterio_id is None:
                    continue
                db.execute(
                    """INSERT OR IGNORE INTO instrumento_criterio
                       (instrumento_id, criterio_id, peso, peso_manual)
                       VALUES (?, ?, ?, ?);""",
                    (ie.id, criterio_id, cv["peso"], cv.get("peso_manual", 0))
                )
            db.commit()

            # Notas de instrumento
            pruebas_por_nombre = {
                p.nombre: p for p in base_datos.listar_pruebas(ie.id)
            }
            for n in ie_data.get("notas_instrumento", []):
                alumno_id = alumnos_por_clave.get((n["apellidos"], n["nombre"]))
                if alumno_id is None or n["nota"] is None:
                    continue
                db.execute(
                    """INSERT OR IGNORE INTO nota_instrumento_alumno
                       (instrumento_id, alumno_id, valor) VALUES (?, ?, ?);""",
                    (ie.id, alumno_id, n["nota"])
                )
            db.commit()

            # Notas de criterio por instrumento
            for n in ie_data.get("notas_criterio", []):
                alumno_id = alumnos_por_clave.get((n["apellidos"], n["nombre"]))
                criterio_id = criterios_por_codigo.get(n["codigo_criterio"])
                if alumno_id is None or criterio_id is None or n["nota"] is None:
                    continue
                db.execute(
                    """INSERT OR IGNORE INTO nota_criterio_instrumento_alumno
                       (instrumento_id, criterio_id, alumno_id, valor, es_manual)
                       VALUES (?, ?, ?, ?, ?);""",
                    (ie.id, criterio_id, alumno_id, n["nota"], n.get("es_manual", 0))
                )
            db.commit()

            # Notas de prueba
            for n in ie_data.get("notas_prueba", []):
                alumno_id = alumnos_por_clave.get((n["apellidos"], n["nombre"]))
                prueba = pruebas_por_nombre.get(n["prueba_nombre"])
                if alumno_id is None or prueba is None or n["nota"] is None:
                    continue
                db.execute(
                    """INSERT OR IGNORE INTO nota_prueba
                       (prueba_id, alumno_id, valor) VALUES (?, ?, ?);""",
                    (prueba.id, alumno_id, n["nota"])
                )
            db.commit()

    return materia
