"""
Capa de acceso a datos.

Toda la información de un curso académico vive en UN SOLO archivo SQLite
(curso.db). No hay ninguna conexión a internet ni a servidores: es un
archivo local que el docente guarda donde quiera.

Estructura general (a partir de esta versión):

    Curso
      └─ Materia (ej. "Tecnología y Digitalización 1ºESO")
           ├─ Alumno            (UNA sola lista para toda la materia)
           ├─ Criterio          (UNA sola lista para toda la materia: código + peso)
           └─ Evaluacion (1EVA, 2EVA, 3EVA, FINAL) -> exactamente 4 por materia

El alumnado y los criterios ya NO pertenecen a cada evaluación por
separado: se introducen una vez por materia y las 4 evaluaciones los
comparten. Cada alumno guarda en qué evaluación se dio de alta
(orden_alta, 1=1EVA, 2=2EVA, 3=3EVA); en las evaluaciones anteriores a su
alta se considerará "no evaluado" (la interfaz lo mostrará atenuado).

En entregas futuras se añadirán: InstrumentoEvaluacion, relación
Instrumento-Criterio (con peso propio) y Nota.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

# Nombres fijos de las 4 evaluaciones que se crean siempre al crear una materia.
NOMBRES_EVALUACIONES = ["1EVA", "2EVA", "3EVA", "FINAL"]

# orden_alta de cada evaluación, usado para decidir si un alumno "ya existía"
# en una evaluación dada. FINAL siempre incluye a todo el alumnado (de ahí el 3:
# cualquier orden_alta de 1, 2 o 3 es <= 3, así que nadie queda fuera).
ORDEN_ALTA_POR_EVALUACION = {"1EVA": 1, "2EVA": 2, "3EVA": 3, "FINAL": 3}


# ---------------------------------------------------------------------------
# Modelos simples (dataclasses) para pasar datos entre la BD y la interfaz
# ---------------------------------------------------------------------------

@dataclass
class Materia:
    id: int
    nombre: str


@dataclass
class Evaluacion:
    id: int
    materia_id: int
    nombre: str  # "1EVA", "2EVA", "3EVA" o "FINAL"


@dataclass
class Alumno:
    id: int
    materia_id: int
    apellidos: str
    nombre: str
    orden: int
    orden_alta: int  # 1, 2 o 3: evaluación en la que se incorporó


@dataclass
class Criterio:
    id: int
    materia_id: int
    codigo: str  # ej. "1.1"
    peso: float
    orden: int


# Tipos posibles de un instrumento de evaluación.
TIPO_MANUAL = "MANUAL"
TIPO_MEDIA_ARITMETICA = "MEDIA_ARITMETICA"
TIPO_MEDIA_PONDERADA = "MEDIA_PONDERADA"
TIPO_EXAMEN = "EXAMEN"
TIPOS_INSTRUMENTO = [TIPO_MANUAL, TIPO_MEDIA_ARITMETICA, TIPO_MEDIA_PONDERADA, TIPO_EXAMEN]


@dataclass
class InstrumentoEvaluacion:
    id: int
    evaluacion_id: int
    nombre: str
    tipo: str
    peso: float
    nota_maxima: float  # solo relevante para tipo EXAMEN; 10 por defecto
    orden: int


@dataclass
class PruebaInstrumento:
    id: int
    instrumento_id: int
    nombre: str
    peso: float  # solo se usa si el instrumento es MEDIA_PONDERADA
    orden: int


@dataclass
class InstrumentoCriterio:
    id: int
    instrumento_id: int
    criterio_id: int
    peso: float  # peso de ESTE instrumento para ESTE criterio en particular
    peso_manual: bool = False  # True si el docente fijó este peso a mano,
    # independiente del peso global del instrumento (que ya no lo sincroniza)


@dataclass
class NotaPrueba:
    prueba_id: int
    alumno_id: int
    valor: float | None  # None = no presentado


@dataclass
class NotaInstrumentoAlumno:
    instrumento_id: int
    alumno_id: int
    valor: float | None  # nota 0-10 ya calculada/introducida; None = no presentado


@dataclass
class NotaCriterioInstrumentoAlumno:
    instrumento_id: int
    criterio_id: int
    alumno_id: int
    valor: float | None
    es_manual: bool  # True si el docente ha editado este valor a mano


# ---------------------------------------------------------------------------
# Gestión de la base de datos
# ---------------------------------------------------------------------------

class BaseDatosCurso:
    """Envuelve la conexión SQLite de un curso.db y expone operaciones
    de alto nivel. Se usa con un 'with' o llamando a cerrar() al terminar.
    """

    def __init__(self, ruta_archivo: str | Path):
        self.ruta_archivo = Path(ruta_archivo)
        self.conexion = sqlite3.connect(self.ruta_archivo)
        self.conexion.execute("PRAGMA foreign_keys = ON;")
        self._crear_esquema_si_falta()

    def cerrar(self):
        self.conexion.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cerrar()

    # -- creación de esquema ------------------------------------------------

    def _crear_esquema_si_falta(self):
        cur = self.conexion.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS materia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS evaluacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                materia_id INTEGER NOT NULL REFERENCES materia(id) ON DELETE CASCADE,
                nombre TEXT NOT NULL,
                UNIQUE(materia_id, nombre)
            );

            CREATE TABLE IF NOT EXISTS alumno (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                materia_id INTEGER NOT NULL REFERENCES materia(id) ON DELETE CASCADE,
                apellidos TEXT NOT NULL DEFAULT '',
                nombre TEXT NOT NULL DEFAULT '',
                orden INTEGER NOT NULL,
                orden_alta INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS criterio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                materia_id INTEGER NOT NULL REFERENCES materia(id) ON DELETE CASCADE,
                codigo TEXT NOT NULL,
                peso REAL NOT NULL DEFAULT 1,
                orden INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS instrumento_evaluacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluacion_id INTEGER NOT NULL REFERENCES evaluacion(id) ON DELETE CASCADE,
                nombre TEXT NOT NULL,
                tipo TEXT NOT NULL,
                peso REAL NOT NULL DEFAULT 0,
                nota_maxima REAL NOT NULL DEFAULT 10,
                orden INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS prueba_instrumento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrumento_id INTEGER NOT NULL REFERENCES instrumento_evaluacion(id) ON DELETE CASCADE,
                nombre TEXT NOT NULL,
                peso REAL NOT NULL DEFAULT 0,
                orden INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS instrumento_criterio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrumento_id INTEGER NOT NULL REFERENCES instrumento_evaluacion(id) ON DELETE CASCADE,
                criterio_id INTEGER NOT NULL REFERENCES criterio(id) ON DELETE CASCADE,
                peso REAL NOT NULL DEFAULT 100,
                peso_manual INTEGER NOT NULL DEFAULT 0,
                UNIQUE(instrumento_id, criterio_id)
            );

            CREATE TABLE IF NOT EXISTS nota_prueba (
                prueba_id INTEGER NOT NULL REFERENCES prueba_instrumento(id) ON DELETE CASCADE,
                alumno_id INTEGER NOT NULL REFERENCES alumno(id) ON DELETE CASCADE,
                valor REAL,
                PRIMARY KEY (prueba_id, alumno_id)
            );

            CREATE TABLE IF NOT EXISTS nota_instrumento_alumno (
                instrumento_id INTEGER NOT NULL REFERENCES instrumento_evaluacion(id) ON DELETE CASCADE,
                alumno_id INTEGER NOT NULL REFERENCES alumno(id) ON DELETE CASCADE,
                valor REAL,
                PRIMARY KEY (instrumento_id, alumno_id)
            );

            CREATE TABLE IF NOT EXISTS nota_criterio_instrumento_alumno (
                instrumento_id INTEGER NOT NULL REFERENCES instrumento_evaluacion(id) ON DELETE CASCADE,
                criterio_id INTEGER NOT NULL REFERENCES criterio(id) ON DELETE CASCADE,
                alumno_id INTEGER NOT NULL REFERENCES alumno(id) ON DELETE CASCADE,
                valor REAL,
                es_manual INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (instrumento_id, criterio_id, alumno_id)
            );

            CREATE TABLE IF NOT EXISTS peso_evaluacion_final (
                materia_id INTEGER NOT NULL REFERENCES materia(id) ON DELETE CASCADE,
                nombre_evaluacion TEXT NOT NULL,
                peso REAL NOT NULL DEFAULT 1,
                PRIMARY KEY (materia_id, nombre_evaluacion)
            );
            """
        )
        self.conexion.commit()
        self._migrar_columnas_si_faltan()

    def _migrar_columnas_si_faltan(self):
        """Añade columnas nuevas a tablas de cursos creados con una versión
        anterior de la aplicación, sin tocar los datos que ya tuvieran.
        SQLite no soporta "ADD COLUMN IF NOT EXISTS", así que se comprueba
        primero si la columna ya existe antes de intentar añadirla.
        """
        cur = self.conexion.execute("PRAGMA table_info(instrumento_criterio);")
        columnas_existentes = {fila[1] for fila in cur.fetchall()}
        if "peso_manual" not in columnas_existentes:
            self.conexion.execute(
                "ALTER TABLE instrumento_criterio ADD COLUMN peso_manual INTEGER NOT NULL DEFAULT 0;"
            )
            self.conexion.commit()

    # -- materias -------------------------------------------------------

    def listar_materias(self) -> list[Materia]:
        cur = self.conexion.execute("SELECT id, nombre FROM materia ORDER BY nombre;")
        return [Materia(id=r[0], nombre=r[1]) for r in cur.fetchall()]

    def crear_materia(self, nombre: str) -> Materia:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre de la materia no puede estar vacío.")
        cur = self.conexion.execute(
            "INSERT INTO materia (nombre) VALUES (?);", (nombre,)
        )
        materia_id = cur.lastrowid
        # Al crear la materia, se crean automáticamente sus 4 evaluaciones.
        for nombre_eval in NOMBRES_EVALUACIONES:
            self.conexion.execute(
                "INSERT INTO evaluacion (materia_id, nombre) VALUES (?, ?);",
                (materia_id, nombre_eval),
            )
        self.conexion.commit()
        return Materia(id=materia_id, nombre=nombre)

    def eliminar_materia(self, materia_id: int):
        self.conexion.execute("DELETE FROM materia WHERE id = ?;", (materia_id,))
        self.conexion.commit()

    def renombrar_materia(self, materia_id: int, nuevo_nombre: str):
        nuevo_nombre = nuevo_nombre.strip()
        if not nuevo_nombre:
            raise ValueError("El nombre de la materia no puede estar vacío.")
        self.conexion.execute(
            "UPDATE materia SET nombre = ? WHERE id = ?;", (nuevo_nombre, materia_id)
        )
        self.conexion.commit()

    # -- evaluaciones -----------------------------------------------------

    def listar_evaluaciones(self, materia_id: int) -> list[Evaluacion]:
        cur = self.conexion.execute(
            "SELECT id, materia_id, nombre FROM evaluacion WHERE materia_id = ?;",
            (materia_id,),
        )
        filas = cur.fetchall()
        # Se devuelven siempre en el orden fijo 1EVA, 2EVA, 3EVA, FINAL
        por_nombre = {nombre: None for nombre in NOMBRES_EVALUACIONES}
        for r in filas:
            por_nombre[r[2]] = Evaluacion(id=r[0], materia_id=r[1], nombre=r[2])
        return [por_nombre[n] for n in NOMBRES_EVALUACIONES if por_nombre[n] is not None]

    # -- alumnos (a nivel de MATERIA) --------------------------------------

    def listar_alumnos(self, materia_id: int) -> list[Alumno]:
        """Lista TODO el alumnado de la materia (independiente de evaluación)."""
        cur = self.conexion.execute(
            """SELECT id, materia_id, apellidos, nombre, orden, orden_alta
               FROM alumno WHERE materia_id = ? ORDER BY orden;""",
            (materia_id,),
        )
        return [
            Alumno(id=r[0], materia_id=r[1], apellidos=r[2], nombre=r[3], orden=r[4], orden_alta=r[5])
            for r in cur.fetchall()
        ]

    def listar_alumnos_para_evaluacion(
        self, materia_id: int, nombre_evaluacion: str
    ) -> list[tuple[Alumno, bool]]:
        """Devuelve todos los alumnos de la materia junto con un booleano
        'evaluable_aqui': True si el alumno ya estaba dado de alta para esta
        evaluación, False si se incorporó más tarde (no se le evalúa aquí,
        se mostrará atenuado en la interfaz).
        """
        orden_evaluacion = ORDEN_ALTA_POR_EVALUACION[nombre_evaluacion]
        alumnos = self.listar_alumnos(materia_id)
        resultado = []
        for alumno in alumnos:
            evaluable_aqui = alumno.orden_alta <= orden_evaluacion
            resultado.append((alumno, evaluable_aqui))
        return resultado

    def agregar_alumno(
        self, materia_id: int, apellidos: str = "", nombre: str = "", orden_alta: int = 1
    ) -> Alumno:
        cur = self.conexion.execute(
            "SELECT COALESCE(MAX(orden), 0) + 1 FROM alumno WHERE materia_id = ?;",
            (materia_id,),
        )
        siguiente_orden = cur.fetchone()[0]
        cur = self.conexion.execute(
            """INSERT INTO alumno (materia_id, apellidos, nombre, orden, orden_alta)
               VALUES (?, ?, ?, ?, ?);""",
            (materia_id, apellidos, nombre, siguiente_orden, orden_alta),
        )
        self.conexion.commit()
        return Alumno(
            id=cur.lastrowid,
            materia_id=materia_id,
            apellidos=apellidos,
            nombre=nombre,
            orden=siguiente_orden,
            orden_alta=orden_alta,
        )

    def agregar_alumnos_en_lote(self, materia_id: int, filas: list[tuple[str, str]]) -> int:
        """Inserta varios alumnos de golpe (uso: importar/pegar desde Excel).
        'filas' es una lista de tuplas (apellidos, nombre).
        Devuelve cuántos alumnos se insertaron.
        """
        cur = self.conexion.execute(
            "SELECT COALESCE(MAX(orden), 0) FROM alumno WHERE materia_id = ?;",
            (materia_id,),
        )
        orden_actual = cur.fetchone()[0]
        insertados = 0
        for apellidos, nombre in filas:
            apellidos = (apellidos or "").strip()
            nombre = (nombre or "").strip()
            if not apellidos and not nombre:
                continue  # saltamos filas totalmente vacías al pegar/importar
            orden_actual += 1
            self.conexion.execute(
                """INSERT INTO alumno (materia_id, apellidos, nombre, orden, orden_alta)
                   VALUES (?, ?, ?, ?, 1);""",
                (materia_id, apellidos, nombre, orden_actual),
            )
            insertados += 1
        self.conexion.commit()
        return insertados

    def actualizar_alumno(self, alumno_id: int, apellidos: str, nombre: str):
        self.conexion.execute(
            "UPDATE alumno SET apellidos = ?, nombre = ? WHERE id = ?;",
            (apellidos, nombre, alumno_id),
        )
        self.conexion.commit()

    def actualizar_orden_alta_alumno(self, alumno_id: int, orden_alta: int):
        if orden_alta not in (1, 2, 3):
            raise ValueError("La evaluación de alta debe ser 1 (1EVA), 2 (2EVA) o 3 (3EVA).")
        self.conexion.execute(
            "UPDATE alumno SET orden_alta = ? WHERE id = ?;", (orden_alta, alumno_id)
        )
        self.conexion.commit()

    # -- "deshacer" de eliminaciones -----------------------------------------
    #
    # Antes de borrar un alumno, criterio o instrumento, se captura ese
    # registro y TODO lo que depende de él en cascada (notas, relaciones
    # instrumento-criterio, pruebas...) en un diccionario plano. Si el
    # docente pulsa "deshacer", se reinserta todo exactamente como estaba,
    # con sus mismos ids (SQLite lo permite mientras no haya colisión, y
    # como se restaura justo después de borrar, no la hay).
    #
    # Solo se conserva el último elemento borrado (no un historial
    # completo): es deliberadamente simple, pensado para el caso de "me
    # he equivocado al borrar esto", no como un deshacer genérico de toda
    # la aplicación.

    # Mapa de qué tablas dependen de cada tipo de entidad, y por qué columna.
    _TABLAS_DEPENDIENTES = {
        "alumno": [
            ("nota_prueba", "alumno_id"),
            ("nota_instrumento_alumno", "alumno_id"),
            ("nota_criterio_instrumento_alumno", "alumno_id"),
        ],
        "criterio": [
            ("instrumento_criterio", "criterio_id"),
            ("nota_criterio_instrumento_alumno", "criterio_id"),
        ],
        "instrumento_evaluacion": [
            ("prueba_instrumento", "instrumento_id"),
            ("instrumento_criterio", "instrumento_id"),
            ("nota_prueba", "prueba_id"),  # se filtra de forma especial, ver más abajo
            ("nota_instrumento_alumno", "instrumento_id"),
            ("nota_criterio_instrumento_alumno", "instrumento_id"),
        ],
    }

    def _capturar_subarbol(self, tabla_principal: str, id_principal: int) -> dict | None:
        """Lee la fila principal y sus filas dependientes en cascada, como
        diccionarios planos {nombre_columna: valor}. Devuelve None si la
        fila principal ya no existe.
        """
        cur = self.conexion.execute(f"SELECT * FROM {tabla_principal} WHERE id = ?;", (id_principal,))
        columnas = [d[0] for d in cur.description]
        fila = cur.fetchone()
        if fila is None:
            return None
        captura = {"tabla_principal": tabla_principal, "fila_principal": dict(zip(columnas, fila)), "dependientes": []}

        if tabla_principal == "instrumento_evaluacion":
            # Las pruebas dependen del instrumento; las notas de prueba
            # dependen, a su vez, de cada prueba (no directamente del
            # instrumento), así que se capturan en dos pasos.
            cur_pruebas = self.conexion.execute(
                "SELECT * FROM prueba_instrumento WHERE instrumento_id = ?;", (id_principal,)
            )
            columnas_p = [d[0] for d in cur_pruebas.description]
            filas_pruebas = [dict(zip(columnas_p, f)) for f in cur_pruebas.fetchall()]
            captura["dependientes"].append(("prueba_instrumento", filas_pruebas))

            for fila_prueba in filas_pruebas:
                cur_np = self.conexion.execute(
                    "SELECT * FROM nota_prueba WHERE prueba_id = ?;", (fila_prueba["id"],)
                )
                columnas_np = [d[0] for d in cur_np.description]
                filas_np = [dict(zip(columnas_np, f)) for f in cur_np.fetchall()]
                captura["dependientes"].append(("nota_prueba", filas_np))

            for tabla_dep, columna_fk in [
                ("instrumento_criterio", "instrumento_id"),
                ("nota_instrumento_alumno", "instrumento_id"),
                ("nota_criterio_instrumento_alumno", "instrumento_id"),
            ]:
                cur_dep = self.conexion.execute(
                    f"SELECT * FROM {tabla_dep} WHERE {columna_fk} = ?;", (id_principal,)
                )
                columnas_dep = [d[0] for d in cur_dep.description]
                filas_dep = [dict(zip(columnas_dep, f)) for f in cur_dep.fetchall()]
                captura["dependientes"].append((tabla_dep, filas_dep))
        else:
            for tabla_dep, columna_fk in self._TABLAS_DEPENDIENTES.get(tabla_principal, []):
                cur_dep = self.conexion.execute(
                    f"SELECT * FROM {tabla_dep} WHERE {columna_fk} = ?;", (id_principal,)
                )
                columnas_dep = [d[0] for d in cur_dep.description]
                filas_dep = [dict(zip(columnas_dep, f)) for f in cur_dep.fetchall()]
                captura["dependientes"].append((tabla_dep, filas_dep))

        return captura

    def _restaurar_subarbol(self, captura: dict):
        """Reinserta exactamente las filas capturadas por _capturar_subarbol,
        en el orden correcto (la fila principal primero, para que las
        claves foráneas de las dependientes encuentren a quién apuntar).
        """
        tabla_principal = captura["tabla_principal"]
        fila_principal = captura["fila_principal"]
        columnas = list(fila_principal.keys())
        marcadores = ", ".join("?" for _ in columnas)
        nombres_columnas = ", ".join(columnas)
        self.conexion.execute(
            f"INSERT INTO {tabla_principal} ({nombres_columnas}) VALUES ({marcadores});",
            [fila_principal[c] for c in columnas],
        )

        # Para "instrumento_evaluacion", prueba_instrumento debe reinsertarse
        # ANTES que nota_prueba (que depende de prueba_instrumento.id).
        # El orden de captura ya garantiza esto si se reinserta en el mismo
        # orden en que se guardó.
        for tabla_dep, filas_dep in captura["dependientes"]:
            for fila_dep in filas_dep:
                columnas_dep = list(fila_dep.keys())
                marcadores_dep = ", ".join("?" for _ in columnas_dep)
                nombres_columnas_dep = ", ".join(columnas_dep)
                self.conexion.execute(
                    f"INSERT INTO {tabla_dep} ({nombres_columnas_dep}) VALUES ({marcadores_dep});",
                    [fila_dep[c] for c in columnas_dep],
                )
        self.conexion.commit()

    def eliminar_alumno_con_deshacer(self, alumno_id: int) -> dict | None:
        """Igual que eliminar_alumno, pero devuelve la captura necesaria
        para poder deshacerlo luego con restaurar_eliminacion().
        """
        captura = self._capturar_subarbol("alumno", alumno_id)
        self.eliminar_alumno(alumno_id)
        return captura

    def eliminar_criterio_con_deshacer(self, criterio_id: int) -> dict | None:
        captura = self._capturar_subarbol("criterio", criterio_id)
        self.eliminar_criterio(criterio_id)
        return captura

    def eliminar_instrumento_con_deshacer(self, instrumento_id: int) -> dict | None:
        captura = self._capturar_subarbol("instrumento_evaluacion", instrumento_id)
        self.eliminar_instrumento(instrumento_id)
        return captura

    def restaurar_eliminacion(self, captura: dict):
        """Deshace una eliminación previamente capturada con
        eliminar_*_con_deshacer(). No comprueba si algo ha cambiado desde
        entonces (por ejemplo, si se han añadido nuevos criterios con el
        mismo código); simplemente reinserta lo capturado.
        """
        self._restaurar_subarbol(captura)

    def eliminar_alumno(self, alumno_id: int):
        self.conexion.execute("DELETE FROM alumno WHERE id = ?;", (alumno_id,))
        self.conexion.commit()

    # -- criterios (a nivel de MATERIA) ------------------------------------

    def listar_criterios(self, materia_id: int) -> list[Criterio]:
        cur = self.conexion.execute(
            """SELECT id, materia_id, codigo, peso, orden
               FROM criterio WHERE materia_id = ? ORDER BY orden;""",
            (materia_id,),
        )
        return [
            Criterio(id=r[0], materia_id=r[1], codigo=r[2], peso=r[3], orden=r[4])
            for r in cur.fetchall()
        ]

    def agregar_criterio(self, materia_id: int, codigo: str, peso: float = 1.0) -> Criterio:
        codigo = codigo.strip()
        if not codigo:
            raise ValueError("El código del criterio no puede estar vacío.")
        cur = self.conexion.execute(
            "SELECT COALESCE(MAX(orden), 0) + 1 FROM criterio WHERE materia_id = ?;",
            (materia_id,),
        )
        siguiente_orden = cur.fetchone()[0]
        cur = self.conexion.execute(
            """INSERT INTO criterio (materia_id, codigo, peso, orden)
               VALUES (?, ?, ?, ?);""",
            (materia_id, codigo, peso, siguiente_orden),
        )
        self.conexion.commit()
        return Criterio(
            id=cur.lastrowid,
            materia_id=materia_id,
            codigo=codigo,
            peso=peso,
            orden=siguiente_orden,
        )

    def agregar_criterios_en_lote(self, materia_id: int, filas: list[tuple[str, float]]) -> int:
        """Inserta varios criterios de golpe (uso: importar/pegar desde Excel).
        'filas' es una lista de tuplas (codigo, peso).
        Devuelve cuántos criterios se insertaron.
        """
        cur = self.conexion.execute(
            "SELECT COALESCE(MAX(orden), 0) FROM criterio WHERE materia_id = ?;",
            (materia_id,),
        )
        orden_actual = cur.fetchone()[0]
        insertados = 0
        for codigo, peso in filas:
            codigo = (codigo or "").strip()
            if not codigo:
                continue
            orden_actual += 1
            self.conexion.execute(
                """INSERT INTO criterio (materia_id, codigo, peso, orden)
                   VALUES (?, ?, ?, ?);""",
                (materia_id, codigo, peso, orden_actual),
            )
            insertados += 1
        self.conexion.commit()
        return insertados

    def agregar_criterios_evitando_duplicados(
        self, materia_id: int, codigos: list[str], peso_por_defecto: float = 1.0
    ) -> int:
        """Inserta los códigos de criterio indicados, EXCEPTO los que ya
        existan en esa materia (comparando por código exacto). Pensado para
        el asistente de currículo oficial: si se repite por error, no
        duplica filas. Devuelve cuántos criterios nuevos se insertaron.
        """
        existentes = {c.codigo for c in self.listar_criterios(materia_id)}
        codigos_nuevos = [codigo for codigo in codigos if codigo not in existentes]
        filas = [(codigo, peso_por_defecto) for codigo in codigos_nuevos]
        return self.agregar_criterios_en_lote(materia_id, filas)
        return insertados

    def actualizar_criterio(self, criterio_id: int, codigo: str, peso: float):
        codigo = codigo.strip()
        if not codigo:
            raise ValueError("El código del criterio no puede estar vacío.")
        self.conexion.execute(
            "UPDATE criterio SET codigo = ?, peso = ? WHERE id = ?;",
            (codigo, peso, criterio_id),
        )
        self.conexion.commit()

    def eliminar_criterio(self, criterio_id: int):
        # Antes de borrar, identificamos qué instrumentos tenían este
        # criterio marcado: tras el borrado (que se propaga en cascada a
        # instrumento_criterio), los demás criterios que sigan marcados
        # en esos instrumentos deben recalcular su peso, ya que el total
        # entre los que queden ha cambiado.
        cur = self.conexion.execute(
            "SELECT instrumento_id FROM instrumento_criterio WHERE criterio_id = ?;", (criterio_id,)
        )
        instrumentos_afectados = [r[0] for r in cur.fetchall()]
        self.conexion.execute("DELETE FROM criterio WHERE id = ?;", (criterio_id,))
        self.conexion.commit()
        for instrumento_id in instrumentos_afectados:
            self.recalcular_pesos_criterios_de_instrumento(instrumento_id)

    # -- instrumentos de evaluación -----------------------------------------

    def listar_instrumentos(self, evaluacion_id: int) -> list[InstrumentoEvaluacion]:
        cur = self.conexion.execute(
            """SELECT id, evaluacion_id, nombre, tipo, peso, nota_maxima, orden
               FROM instrumento_evaluacion WHERE evaluacion_id = ? ORDER BY orden;""",
            (evaluacion_id,),
        )
        return [
            InstrumentoEvaluacion(
                id=r[0], evaluacion_id=r[1], nombre=r[2], tipo=r[3], peso=r[4],
                nota_maxima=r[5], orden=r[6],
            )
            for r in cur.fetchall()
        ]

    def obtener_instrumento(self, instrumento_id: int) -> InstrumentoEvaluacion | None:
        """Relee un instrumento por su id directamente de la base de
        datos (no de ningún objeto en memoria que pudiera estar
        desactualizado). Devuelve None si ya no existe.
        """
        cur = self.conexion.execute(
            """SELECT id, evaluacion_id, nombre, tipo, peso, nota_maxima, orden
               FROM instrumento_evaluacion WHERE id = ?;""",
            (instrumento_id,),
        )
        r = cur.fetchone()
        if r is None:
            return None
        return InstrumentoEvaluacion(
            id=r[0], evaluacion_id=r[1], nombre=r[2], tipo=r[3], peso=r[4],
            nota_maxima=r[5], orden=r[6],
        )

    def suma_pesos_instrumentos(self, evaluacion_id: int) -> float:
        cur = self.conexion.execute(
            "SELECT COALESCE(SUM(peso), 0) FROM instrumento_evaluacion WHERE evaluacion_id = ?;",
            (evaluacion_id,),
        )
        return cur.fetchone()[0]

    def crear_instrumento(
        self, evaluacion_id: int, nombre: str, tipo: str, nota_maxima: float = 10.0
    ) -> InstrumentoEvaluacion:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre del instrumento no puede estar vacío.")
        if tipo not in TIPOS_INSTRUMENTO:
            raise ValueError(f"Tipo de instrumento no reconocido: {tipo}")

        cur = self.conexion.execute(
            "SELECT COALESCE(MAX(orden), 0) + 1 FROM instrumento_evaluacion WHERE evaluacion_id = ?;",
            (evaluacion_id,),
        )
        siguiente_orden = cur.fetchone()[0]

        # Si es el primer instrumento de la evaluación, se le asigna 100% automáticamente.
        instrumentos_existentes = self.listar_instrumentos(evaluacion_id)
        peso_inicial = 100.0 if not instrumentos_existentes else 0.0

        cur = self.conexion.execute(
            """INSERT INTO instrumento_evaluacion
               (evaluacion_id, nombre, tipo, peso, nota_maxima, orden)
               VALUES (?, ?, ?, ?, ?, ?);""",
            (evaluacion_id, nombre, tipo, peso_inicial, nota_maxima, siguiente_orden),
        )
        self.conexion.commit()
        return InstrumentoEvaluacion(
            id=cur.lastrowid, evaluacion_id=evaluacion_id, nombre=nombre, tipo=tipo,
            peso=peso_inicial, nota_maxima=nota_maxima, orden=siguiente_orden,
        )

    def actualizar_instrumento(
        self, instrumento_id: int, nombre: str, peso: float, nota_maxima: float
    ):
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre del instrumento no puede estar vacío.")
        if nota_maxima <= 0:
            raise ValueError("La nota máxima debe ser mayor que 0.")
        self.conexion.execute(
            "UPDATE instrumento_evaluacion SET nombre = ?, peso = ?, nota_maxima = ? WHERE id = ?;",
            (nombre, peso, nota_maxima, instrumento_id),
        )
        self.conexion.commit()
        # Nota: el peso GLOBAL del instrumento ya no afecta al peso de
        # cada criterio dentro de él (eso ahora depende solo del peso
        # del criterio en la materia, ver
        # recalcular_pesos_criterios_de_instrumento). El peso global se
        # usa únicamente para repartir entre varios instrumentos que
        # evalúen el mismo criterio.

    def eliminar_instrumento(self, instrumento_id: int):
        self.conexion.execute(
            "DELETE FROM instrumento_evaluacion WHERE id = ?;", (instrumento_id,)
        )
        self.conexion.commit()

    # -- pruebas de un instrumento (para MEDIA_ARITMETICA / MEDIA_PONDERADA) --

    def listar_pruebas(self, instrumento_id: int) -> list[PruebaInstrumento]:
        cur = self.conexion.execute(
            """SELECT id, instrumento_id, nombre, peso, orden
               FROM prueba_instrumento WHERE instrumento_id = ? ORDER BY orden;""",
            (instrumento_id,),
        )
        return [
            PruebaInstrumento(id=r[0], instrumento_id=r[1], nombre=r[2], peso=r[3], orden=r[4])
            for r in cur.fetchall()
        ]

    def suma_pesos_pruebas(self, instrumento_id: int) -> float:
        cur = self.conexion.execute(
            "SELECT COALESCE(SUM(peso), 0) FROM prueba_instrumento WHERE instrumento_id = ?;",
            (instrumento_id,),
        )
        return cur.fetchone()[0]

    def agregar_prueba(self, instrumento_id: int, nombre: str | None = None) -> PruebaInstrumento:
        cur = self.conexion.execute(
            "SELECT COALESCE(MAX(orden), 0) + 1 FROM prueba_instrumento WHERE instrumento_id = ?;",
            (instrumento_id,),
        )
        siguiente_orden = cur.fetchone()[0]
        nombre = (nombre or f"Prueba {siguiente_orden}").strip()

        pruebas_existentes = self.listar_pruebas(instrumento_id)
        peso_inicial = 100.0 if not pruebas_existentes else 0.0

        cur = self.conexion.execute(
            """INSERT INTO prueba_instrumento (instrumento_id, nombre, peso, orden)
               VALUES (?, ?, ?, ?);""",
            (instrumento_id, nombre, peso_inicial, siguiente_orden),
        )
        self.conexion.commit()
        return PruebaInstrumento(
            id=cur.lastrowid, instrumento_id=instrumento_id, nombre=nombre,
            peso=peso_inicial, orden=siguiente_orden,
        )

    def actualizar_prueba(self, prueba_id: int, nombre: str, peso: float):
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre de la prueba no puede estar vacío.")
        self.conexion.execute(
            "UPDATE prueba_instrumento SET nombre = ?, peso = ? WHERE id = ?;",
            (nombre, peso, prueba_id),
        )
        self.conexion.commit()

    def eliminar_prueba(self, prueba_id: int):
        self.conexion.execute("DELETE FROM prueba_instrumento WHERE id = ?;", (prueba_id,))
        self.conexion.commit()

    # -- relación instrumento <-> criterio (con peso propio, "modelo b") -----

    def listar_criterios_de_instrumento(self, instrumento_id: int) -> list[InstrumentoCriterio]:
        cur = self.conexion.execute(
            """SELECT id, instrumento_id, criterio_id, peso, peso_manual
               FROM instrumento_criterio WHERE instrumento_id = ?;""",
            (instrumento_id,),
        )
        return [
            InstrumentoCriterio(
                id=r[0], instrumento_id=r[1], criterio_id=r[2], peso=r[3], peso_manual=bool(r[4])
            )
            for r in cur.fetchall()
        ]

    def criterios_marcados_de_instrumento(self, instrumento_id: int) -> set[int]:
        """Devuelve el conjunto de ids de criterio que este instrumento evalúa."""
        return {ic.criterio_id for ic in self.listar_criterios_de_instrumento(instrumento_id)}

    def marcar_criterio_en_instrumento(self, instrumento_id: int, criterio_id: int, peso: float = 100.0):
        """Marca que este instrumento evalúa este criterio. El peso que
        se pasa aquí es solo un valor de partida (se recalcula
        inmediatamente después con recalcular_pesos_criterios_de_instrumento,
        así que en la práctica da igual lo que se indique).
        """
        self.conexion.execute(
            """INSERT INTO instrumento_criterio (instrumento_id, criterio_id, peso, peso_manual)
               VALUES (?, ?, ?, 0)
               ON CONFLICT(instrumento_id, criterio_id)
               DO UPDATE SET peso = excluded.peso, peso_manual = 0;""",
            (instrumento_id, criterio_id, peso),
        )
        self.conexion.commit()
        self.recalcular_pesos_criterios_de_instrumento(instrumento_id)

    def desmarcar_criterio_en_instrumento(self, instrumento_id: int, criterio_id: int):
        self.conexion.execute(
            "DELETE FROM instrumento_criterio WHERE instrumento_id = ? AND criterio_id = ?;",
            (instrumento_id, criterio_id),
        )
        # Al desmarcar, también se eliminan notas de criterio ya calculadas para ese cruce.
        self.conexion.execute(
            "DELETE FROM nota_criterio_instrumento_alumno WHERE instrumento_id = ? AND criterio_id = ?;",
            (instrumento_id, criterio_id),
        )
        self.conexion.commit()
        self.recalcular_pesos_criterios_de_instrumento(instrumento_id)

    def recalcular_pesos_criterios_de_instrumento(self, instrumento_id: int):
        """Recalcula el peso de cada criterio marcado en este
        instrumento, a partir del peso ORIGINAL de cada criterio en la
        materia (pestaña "Criterios"), redistribuido entre los
        criterios marcados en este mismo instrumento para que sumen
        100% entre ellos.

        Ejemplo: una materia con criterios de peso 30/30/40 (sobre 100
        en total). Si el instrumento solo marca los dos primeros, sus
        pesos originales (30 y 30) se reescalan sobre su nueva suma (60)
        para que ese instrumento les dé 50% y 50% entre sí.

        El docente nunca edita esto a mano: se recalcula solo cada vez
        que se marca o desmarca un criterio en el instrumento.
        """
        relaciones = self.listar_criterios_de_instrumento(instrumento_id)
        if not relaciones:
            return
        ids_marcados = {r.criterio_id for r in relaciones}

        cur = self.conexion.execute(
            f"SELECT id, peso FROM criterio WHERE id IN ({','.join('?' for _ in ids_marcados)});",
            tuple(ids_marcados),
        )
        peso_original_por_criterio = {r[0]: r[1] for r in cur.fetchall()}
        suma_total = sum(peso_original_por_criterio.values())

        for criterio_id in ids_marcados:
            peso_original = peso_original_por_criterio.get(criterio_id, 0.0)
            peso_recalculado = (peso_original * 100.0 / suma_total) if suma_total > 0 else 0.0
            self.conexion.execute(
                "UPDATE instrumento_criterio SET peso = ? WHERE instrumento_id = ? AND criterio_id = ?;",
                (round(peso_recalculado, 4), instrumento_id, criterio_id),
            )
        self.conexion.commit()

    # -- notas de pruebas (ARITMETICA / PONDERADA) ---------------------------

    def obtener_notas_pruebas(self, instrumento_id: int) -> dict[tuple[int, int], float | None]:
        """Devuelve {(prueba_id, alumno_id): valor} para todas las pruebas del instrumento."""
        cur = self.conexion.execute(
            """SELECT np.prueba_id, np.alumno_id, np.valor
               FROM nota_prueba np
               JOIN prueba_instrumento pi ON pi.id = np.prueba_id
               WHERE pi.instrumento_id = ?;""",
            (instrumento_id,),
        )
        return {(r[0], r[1]): r[2] for r in cur.fetchall()}

    def guardar_nota_prueba(self, prueba_id: int, alumno_id: int, valor: float | None):
        self.conexion.execute(
            """INSERT INTO nota_prueba (prueba_id, alumno_id, valor) VALUES (?, ?, ?)
               ON CONFLICT(prueba_id, alumno_id) DO UPDATE SET valor = excluded.valor;""",
            (prueba_id, alumno_id, valor),
        )
        self.conexion.commit()

    # -- nota general del instrumento por alumno -----------------------------

    def obtener_notas_instrumento(self, instrumento_id: int) -> dict[int, float | None]:
        """Devuelve {alumno_id: valor} para un instrumento."""
        cur = self.conexion.execute(
            "SELECT alumno_id, valor FROM nota_instrumento_alumno WHERE instrumento_id = ?;",
            (instrumento_id,),
        )
        return {r[0]: r[1] for r in cur.fetchall()}

    def guardar_nota_instrumento(self, instrumento_id: int, alumno_id: int, valor: float | None):
        self.conexion.execute(
            """INSERT INTO nota_instrumento_alumno (instrumento_id, alumno_id, valor)
               VALUES (?, ?, ?)
               ON CONFLICT(instrumento_id, alumno_id) DO UPDATE SET valor = excluded.valor;""",
            (instrumento_id, alumno_id, valor),
        )
        self.conexion.commit()

    # -- nota que el instrumento aporta a cada criterio, por alumno ----------

    def obtener_notas_criterio_instrumento(
        self, instrumento_id: int
    ) -> dict[tuple[int, int], tuple[float | None, bool]]:
        """Devuelve {(criterio_id, alumno_id): (valor, es_manual)} para un instrumento."""
        cur = self.conexion.execute(
            """SELECT criterio_id, alumno_id, valor, es_manual
               FROM nota_criterio_instrumento_alumno WHERE instrumento_id = ?;""",
            (instrumento_id,),
        )
        return {(r[0], r[1]): (r[2], bool(r[3])) for r in cur.fetchall()}

    def guardar_nota_criterio_instrumento(
        self, instrumento_id: int, criterio_id: int, alumno_id: int,
        valor: float | None, es_manual: bool,
    ):
        self.conexion.execute(
            """INSERT INTO nota_criterio_instrumento_alumno
               (instrumento_id, criterio_id, alumno_id, valor, es_manual)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(instrumento_id, criterio_id, alumno_id)
               DO UPDATE SET valor = excluded.valor, es_manual = excluded.es_manual;""",
            (instrumento_id, criterio_id, alumno_id, valor, 1 if es_manual else 0),
        )
        self.conexion.commit()

    # -- cálculo de la nota general del instrumento --------------------------

    def calcular_nota_instrumento_para_alumno(
        self, instrumento: InstrumentoEvaluacion, alumno_id: int
    ) -> float | None:
        """Calcula la nota 0-10 'general' del instrumento para un alumno, según
        su tipo. Devuelve None si el alumno no se ha presentado (sin datos).
        No incluye el caso MANUAL (esa nota no se calcula, se introduce
        directamente sobre cada criterio).
        """
        if instrumento.tipo == TIPO_EXAMEN:
            notas = self.obtener_notas_instrumento(instrumento.id)
            valor_crudo = notas.get(alumno_id)
            if valor_crudo is None:
                return None
            return round(valor_crudo * 10.0 / instrumento.nota_maxima, 2)

        if instrumento.tipo == TIPO_MEDIA_ARITMETICA:
            pruebas = self.listar_pruebas(instrumento.id)
            notas = self.obtener_notas_pruebas(instrumento.id)
            valores = [
                notas.get((p.id, alumno_id))
                for p in pruebas
                if notas.get((p.id, alumno_id)) is not None
            ]
            if not valores:
                return None
            return round(sum(valores) / len(valores), 2)

        if instrumento.tipo == TIPO_MEDIA_PONDERADA:
            pruebas = self.listar_pruebas(instrumento.id)
            notas = self.obtener_notas_pruebas(instrumento.id)
            suma_pesos = 0.0
            suma_ponderada = 0.0
            for p in pruebas:
                valor = notas.get((p.id, alumno_id))
                if valor is None:
                    continue
                suma_pesos += p.peso
                suma_ponderada += valor * p.peso
            if suma_pesos == 0:
                return None
            return round(suma_ponderada / suma_pesos, 2)

        return None  # MANUAL no se calcula aquí

    def nota_representativa_instrumento_para_alumno(
        self, instrumento: InstrumentoEvaluacion, alumno_id: int
    ) -> float | None:
        """Igual que calcular_nota_instrumento_para_alumno, pero SÍ cubre
        el caso MANUAL: para ese tipo, la nota representativa es la media
        de las notas de criterio que el alumno tiene en ese instrumento
        (puede haber varias si el instrumento evalúa varios criterios).
        Pensada para mostrar "la nota de este alumno en este IE" de forma
        homogénea entre los 4 tipos, por ejemplo en un gráfico.
        """
        if instrumento.tipo != TIPO_MANUAL:
            return self.calcular_nota_instrumento_para_alumno(instrumento, alumno_id)

        notas_criterio = self.obtener_notas_criterio_instrumento(instrumento.id)
        valores = [
            valor
            for (criterio_id, a_id), (valor, _es_manual) in notas_criterio.items()
            if a_id == alumno_id and valor is not None
        ]
        if not valores:
            return None
        return round(sum(valores) / len(valores), 2)

    def recalcular_notas_criterio_para_instrumento(self, instrumento: InstrumentoEvaluacion):
        """Tras cambiar una nota general (examen/aritmética/ponderada), vuelve
        a copiar el valor calculado a todos los criterios marcados de este
        instrumento, PERO solo para las celdas que el docente no haya editado
        a mano (es_manual=False). Las editadas a mano quedan intactas.
        """
        if instrumento.tipo == TIPO_MANUAL:
            return  # en MANUAL no hay nota "general" que propagar

        criterios_ids = self.criterios_marcados_de_instrumento(instrumento.id)
        if not criterios_ids:
            return

        # Alumnos relevantes: cualquiera con nota registrada en este
        # instrumento (el origen depende del tipo: nota_instrumento_alumno
        # para EXAMEN, nota_prueba para ARITMETICA/PONDERADA), o ya con una
        # fila de criterio guardada (para poder limpiarla si ya no aplica).
        alumno_ids = set(self.obtener_notas_instrumento(instrumento.id).keys())
        if instrumento.tipo in (TIPO_MEDIA_ARITMETICA, TIPO_MEDIA_PONDERADA):
            alumno_ids |= {a_id for (_p_id, a_id) in self.obtener_notas_pruebas(instrumento.id).keys()}
        existentes = self.obtener_notas_criterio_instrumento(instrumento.id)
        alumno_ids |= {a_id for (_c_id, a_id) in existentes.keys()}

        for alumno_id in alumno_ids:
            valor_calculado = self.calcular_nota_instrumento_para_alumno(instrumento, alumno_id)
            for criterio_id in criterios_ids:
                _valor_previo, es_manual = existentes.get((criterio_id, alumno_id), (None, False))
                if es_manual:
                    continue  # no tocar lo editado a mano por el docente
                self.guardar_nota_criterio_instrumento(
                    instrumento.id, criterio_id, alumno_id, valor_calculado, es_manual=False
                )

    # -- cálculo agregado: nota de cada criterio en una evaluación -----------
    #
    # Cuando varios instrumentos evalúan el mismo criterio, la nota de ese
    # criterio para un alumno es la media ponderada de las notas que le
    # dan los instrumentos que SÍ tienen nota para él en ese criterio,
    # usando como peso el peso IE↔criterio (instrumento_criterio.peso),
    # redistribuido entre los instrumentos presentes (igual que el
    # "Reparto MODIF" del Excel: si un instrumento no tiene nota para ese
    # alumno en ese criterio, no participa y los demás se reparten el 100%).

    def calcular_notas_criterios_evaluacion(
        self, evaluacion_id: int, materia_id: int
    ) -> dict[tuple[int, int], float | None]:
        """Devuelve {(criterio_id, alumno_id): nota_0_10 o None} para todos
        los criterios de la materia y todos los alumnos, considerando los
        instrumentos de esta evaluación.
        """
        criterios = self.listar_criterios(materia_id)
        instrumentos = self.listar_instrumentos(evaluacion_id)
        alumnos = self.listar_alumnos(materia_id)

        # Precargar: para cada instrumento, sus notas de criterio y su peso por criterio.
        notas_por_instrumento = {
            inst.id: self.obtener_notas_criterio_instrumento(inst.id) for inst in instrumentos
        }
        pesos_por_instrumento = {
            inst.id: {ic.criterio_id: ic.peso for ic in self.listar_criterios_de_instrumento(inst.id)}
            for inst in instrumentos
        }

        resultado: dict[tuple[int, int], float | None] = {}
        for criterio in criterios:
            for alumno in alumnos:
                suma_pesos = 0.0
                suma_ponderada = 0.0
                for inst in instrumentos:
                    peso_ie_criterio = pesos_por_instrumento[inst.id].get(criterio.id)
                    if peso_ie_criterio is None:
                        continue  # este instrumento no evalúa este criterio
                    valor, _es_manual = notas_por_instrumento[inst.id].get(
                        (criterio.id, alumno.id), (None, False)
                    )
                    if valor is None:
                        continue  # el alumno no tiene nota de este instrumento en este criterio
                    suma_pesos += peso_ie_criterio
                    suma_ponderada += valor * peso_ie_criterio
                if suma_pesos == 0:
                    resultado[(criterio.id, alumno.id)] = None
                else:
                    resultado[(criterio.id, alumno.id)] = round(suma_ponderada / suma_pesos, 2)
        return resultado

    # -- cálculo agregado: nota final de la materia en una evaluación --------
    #
    # La nota final es la media ponderada de las notas de criterio del
    # alumno, usando como peso el peso del criterio (definido en la
    # pestaña Criterios de la materia), redistribuido entre los criterios
    # que el alumno SÍ tiene calificados (de nuevo, igual que el Excel:
    # columna CW = SUMPRODUCT(notas_criterio, pesos_modificados) / 100).

    def calcular_notas_materia_evaluacion(
        self, evaluacion_id: int, materia_id: int
    ) -> dict[int, float | None]:
        """Devuelve {alumno_id: nota_0_10 o None} con la nota final de la
        materia para cada alumno, en una evaluación concreta.
        """
        criterios = self.listar_criterios(materia_id)
        alumnos = self.listar_alumnos(materia_id)
        notas_criterio = self.calcular_notas_criterios_evaluacion(evaluacion_id, materia_id)

        resultado: dict[int, float | None] = {}
        for alumno in alumnos:
            suma_pesos = 0.0
            suma_ponderada = 0.0
            for criterio in criterios:
                valor = notas_criterio.get((criterio.id, alumno.id))
                if valor is None:
                    continue
                suma_pesos += criterio.peso
                suma_ponderada += valor * criterio.peso
            resultado[alumno.id] = None if suma_pesos == 0 else round(suma_ponderada / suma_pesos, 2)
        return resultado

    # -- pesos de 1EVA/2EVA/3EVA usados por FINAL ----------------------------

    NOMBRES_EVALUACIONES_PARA_FINAL = ["1EVA", "2EVA", "3EVA"]

    def obtener_pesos_evaluaciones_final(self, materia_id: int) -> dict[str, float]:
        """Devuelve {"1EVA": peso, "2EVA": peso, "3EVA": peso}. Si todavía no
        se han guardado, se inicializan con 1/1/1 (peso igual por defecto).
        """
        cur = self.conexion.execute(
            "SELECT nombre_evaluacion, peso FROM peso_evaluacion_final WHERE materia_id = ?;",
            (materia_id,),
        )
        guardados = {r[0]: r[1] for r in cur.fetchall()}
        return {
            nombre: guardados.get(nombre, 1.0)
            for nombre in self.NOMBRES_EVALUACIONES_PARA_FINAL
        }

    def actualizar_peso_evaluacion_final(self, materia_id: int, nombre_evaluacion: str, peso: float):
        if nombre_evaluacion not in self.NOMBRES_EVALUACIONES_PARA_FINAL:
            raise ValueError(f"Evaluación no reconocida para FINAL: {nombre_evaluacion}")
        self.conexion.execute(
            """INSERT INTO peso_evaluacion_final (materia_id, nombre_evaluacion, peso)
               VALUES (?, ?, ?)
               ON CONFLICT(materia_id, nombre_evaluacion) DO UPDATE SET peso = excluded.peso;""",
            (materia_id, nombre_evaluacion, peso),
        )
        self.conexion.commit()

    # -- cálculo de FINAL: igual mecánica, pero agregando 1EVA/2EVA/3EVA -----
    #
    # FINAL no tiene instrumentos propios: trata a 1EVA, 2EVA y 3EVA como si
    # fueran "instrumentos", usando su peso (por defecto 1/1/1, editable) y
    # redistribuyendo dinámicamente entre las evaluaciones que sí tienen nota
    # para ese alumno en ese criterio (igual mecánica que el Excel FINAL, que
    # usaba pesos 1/1000/1000000 para dar prioridad a la evaluación más
    # reciente; aquí el docente decide la proporción).

    def calcular_notas_criterios_final(self, materia_id: int) -> dict[tuple[int, int], float | None]:
        """Devuelve {(criterio_id, alumno_id): nota_0_10 o None} para FINAL,
        agregando las notas de criterio de 1EVA, 2EVA y 3EVA.
        """
        criterios = self.listar_criterios(materia_id)
        alumnos = self.listar_alumnos(materia_id)
        pesos_evaluaciones = self.obtener_pesos_evaluaciones_final(materia_id)

        evaluaciones_por_nombre = {
            ev.nombre: ev for ev in self.listar_evaluaciones(materia_id)
            if ev.nombre in self.NOMBRES_EVALUACIONES_PARA_FINAL
        }
        notas_por_evaluacion = {
            nombre: self.calcular_notas_criterios_evaluacion(ev.id, materia_id)
            for nombre, ev in evaluaciones_por_nombre.items()
        }

        resultado: dict[tuple[int, int], float | None] = {}
        for criterio in criterios:
            for alumno in alumnos:
                suma_pesos = 0.0
                suma_ponderada = 0.0
                for nombre_eval, notas_criterio_eval in notas_por_evaluacion.items():
                    valor = notas_criterio_eval.get((criterio.id, alumno.id))
                    if valor is None:
                        continue
                    peso = pesos_evaluaciones[nombre_eval]
                    suma_pesos += peso
                    suma_ponderada += valor * peso
                if suma_pesos == 0:
                    resultado[(criterio.id, alumno.id)] = None
                else:
                    resultado[(criterio.id, alumno.id)] = round(suma_ponderada / suma_pesos, 2)
        return resultado

    def calcular_notas_materia_final(self, materia_id: int) -> dict[int, float | None]:
        """Devuelve {alumno_id: nota_0_10 o None} con la nota final de curso
        de la materia, agregando las notas de criterio de FINAL (que a su
        vez agregan 1EVA/2EVA/3EVA) con el peso de cada criterio.
        """
        criterios = self.listar_criterios(materia_id)
        alumnos = self.listar_alumnos(materia_id)
        notas_criterio = self.calcular_notas_criterios_final(materia_id)

        resultado: dict[int, float | None] = {}
        for alumno in alumnos:
            suma_pesos = 0.0
            suma_ponderada = 0.0
            for criterio in criterios:
                valor = notas_criterio.get((criterio.id, alumno.id))
                if valor is None:
                    continue
                suma_pesos += criterio.peso
                suma_ponderada += valor * criterio.peso
            resultado[alumno.id] = None if suma_pesos == 0 else round(suma_ponderada / suma_pesos, 2)
        return resultado

    # -- trazabilidad: qué IE evalúa cada criterio / en qué evaluación se evaluó --

    def trazabilidad_criterios_instrumentos(
        self, evaluacion_id: int, materia_id: int
    ) -> tuple[list[Criterio], list[InstrumentoEvaluacion], dict[tuple[int, int], float | None]]:
        """Para una evaluación (1EVA/2EVA/3EVA): devuelve (criterios,
        instrumentos, pesos), donde pesos[(criterio_id, instrumento_id)]
        es el peso de ese instrumento para ese criterio, o None si ese
        instrumento no evalúa ese criterio. Reutilizado tanto por la
        exportación a Excel como por la pestaña de Trazabilidad en pantalla.
        """
        criterios = self.listar_criterios(materia_id)
        instrumentos = self.listar_instrumentos(evaluacion_id)
        pesos_por_instrumento = {
            instrumento.id: {
                ic.criterio_id: ic.peso for ic in self.listar_criterios_de_instrumento(instrumento.id)
            }
            for instrumento in instrumentos
        }
        pesos: dict[tuple[int, int], float | None] = {}
        for criterio in criterios:
            for instrumento in instrumentos:
                pesos[(criterio.id, instrumento.id)] = pesos_por_instrumento.get(instrumento.id, {}).get(
                    criterio.id
                )
        return criterios, instrumentos, pesos

    def trazabilidad_criterios_instrumentos_con_manual(
        self, evaluacion_id: int, materia_id: int
    ) -> tuple[
        list[Criterio],
        list[InstrumentoEvaluacion],
        dict[tuple[int, int], float | None],
        dict[tuple[int, int], bool],
    ]:
        """Igual que trazabilidad_criterios_instrumentos, pero además
        devuelve es_manual[(criterio_id, instrumento_id)]: True si ese
        peso fue editado a mano por el docente para ese criterio en
        particular (y por tanto ya no sigue al peso global del
        instrumento si este cambia).
        """
        criterios = self.listar_criterios(materia_id)
        instrumentos = self.listar_instrumentos(evaluacion_id)
        relaciones_por_instrumento = {
            instrumento.id: {
                ic.criterio_id: ic for ic in self.listar_criterios_de_instrumento(instrumento.id)
            }
            for instrumento in instrumentos
        }
        pesos: dict[tuple[int, int], float | None] = {}
        es_manual: dict[tuple[int, int], bool] = {}
        for criterio in criterios:
            for instrumento in instrumentos:
                relacion = relaciones_por_instrumento.get(instrumento.id, {}).get(criterio.id)
                pesos[(criterio.id, instrumento.id)] = relacion.peso if relacion is not None else None
                es_manual[(criterio.id, instrumento.id)] = (
                    relacion.peso_manual if relacion is not None else False
                )
        return criterios, instrumentos, pesos, es_manual

    def trazabilidad_criterios_evaluaciones(
        self, materia_id: int
    ) -> tuple[list[Criterio], list[Evaluacion], dict[tuple[int, int], bool]]:
        """Para FINAL: devuelve (criterios, evaluaciones [1EVA/2EVA/3EVA],
        evaluado), donde evaluado[(criterio_id, evaluacion_id)] es True si
        ese criterio tuvo al menos una nota calculada en esa evaluación
        (para algún alumno), False si no.
        """
        criterios = self.listar_criterios(materia_id)
        evaluaciones = [ev for ev in self.listar_evaluaciones(materia_id) if ev.nombre != "FINAL"]

        criterios_evaluados_por_evaluacion = {}
        for evaluacion in evaluaciones:
            notas_criterio = self.calcular_notas_criterios_evaluacion(evaluacion.id, materia_id)
            criterios_con_nota = {
                criterio_id
                for (criterio_id, _alumno_id), valor in notas_criterio.items()
                if valor is not None
            }
            criterios_evaluados_por_evaluacion[evaluacion.id] = criterios_con_nota

        evaluado: dict[tuple[int, int], bool] = {}
        for criterio in criterios:
            for evaluacion in evaluaciones:
                evaluado[(criterio.id, evaluacion.id)] = (
                    criterio.id in criterios_evaluados_por_evaluacion[evaluacion.id]
                )
        return criterios, evaluaciones, evaluado

    # -- copiar estructura de una materia a otra (misma BD u otro curso) ----
    #
    # Pensado para cuando un docente imparte la misma materia en varios
    # grupos, o repite estructura curso tras curso: en vez de montar
    # criterios e instrumentos desde cero cada vez, copia la estructura ya
    # hecha de una materia existente a una materia nueva (vacía de
    # alumnado y notas). base_datos_origen y self pueden ser la misma
    # instancia (copiar dentro del mismo curso.db) o instancias distintas
    # abiertas sobre dos archivos .db diferentes (copiar entre cursos
    # académicos distintos).

    def copiar_criterios_desde(self, base_datos_origen: "BaseDatosCurso", materia_origen_id: int, materia_destino_id: int):
        """Copia los criterios (código + peso) de una materia a otra,
        sin tocar alumnado ni notas. Devuelve un mapa {criterio_id_origen: criterio_id_destino},
        útil para copiar_instrumentos_desde si se llama justo después.
        """
        criterios_origen = base_datos_origen.listar_criterios(materia_origen_id)
        mapa_criterios: dict[int, int] = {}
        for criterio in criterios_origen:
            nuevo_criterio = self.agregar_criterio(materia_destino_id, criterio.codigo, criterio.peso)
            mapa_criterios[criterio.id] = nuevo_criterio.id
        return mapa_criterios

    def copiar_instrumentos_desde(
        self,
        base_datos_origen: "BaseDatosCurso",
        materia_origen_id: int,
        materia_destino_id: int,
        mapa_criterios: dict[int, int],
    ):
        """Copia los instrumentos de evaluación (de 1EVA, 2EVA y 3EVA —
        FINAL no tiene instrumentos propios) de una materia a otra: su
        nombre, tipo, peso y nota máxima; sus pruebas con su peso (para
        media aritmética/ponderada); y qué criterios marca cada uno, con
        el peso de esa relación. No copia ninguna nota de alumnado.

        mapa_criterios debe ser el devuelto por copiar_criterios_desde,
        para traducir los ids de criterio de la materia origen a los
        ids de la materia destino (son distintos aunque el código sea
        el mismo).
        """
        evaluaciones_origen = {ev.nombre: ev for ev in base_datos_origen.listar_evaluaciones(materia_origen_id)}
        evaluaciones_destino = {ev.nombre: ev for ev in self.listar_evaluaciones(materia_destino_id)}

        for nombre_evaluacion in ("1EVA", "2EVA", "3EVA"):
            evaluacion_origen = evaluaciones_origen.get(nombre_evaluacion)
            evaluacion_destino = evaluaciones_destino.get(nombre_evaluacion)
            if evaluacion_origen is None or evaluacion_destino is None:
                continue

            for instrumento_origen in base_datos_origen.listar_instrumentos(evaluacion_origen.id):
                instrumento_destino = self.crear_instrumento(
                    evaluacion_destino.id,
                    instrumento_origen.nombre,
                    instrumento_origen.tipo,
                    instrumento_origen.nota_maxima,
                )
                # crear_instrumento ya fija el peso a 100 si es el primero
                # de la evaluación, o a 0 si no; lo sobrescribimos para
                # que coincida exactamente con el de origen.
                self.actualizar_instrumento(
                    instrumento_destino.id,
                    instrumento_origen.nombre,
                    instrumento_origen.peso,
                    instrumento_origen.nota_maxima,
                )

                for prueba_origen in base_datos_origen.listar_pruebas(instrumento_origen.id):
                    prueba_destino = self.agregar_prueba(instrumento_destino.id, prueba_origen.nombre)
                    self.actualizar_prueba(prueba_destino.id, prueba_origen.nombre, prueba_origen.peso)

                for relacion_origen in base_datos_origen.listar_criterios_de_instrumento(instrumento_origen.id):
                    criterio_destino_id = mapa_criterios.get(relacion_origen.criterio_id)
                    if criterio_destino_id is None:
                        continue  # por seguridad: no debería ocurrir si se llamó antes a copiar_criterios_desde
                    self.marcar_criterio_en_instrumento(
                        instrumento_destino.id, criterio_destino_id, peso=relacion_origen.peso
                    )
