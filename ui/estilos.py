"""
Estilos visuales de la aplicación: una paleta de verdes aplicada de forma
centralizada con una hoja de estilos Qt (QSS, parecido a CSS).

Además de la paleta general, se definen colores específicos para cada
pestaña fija de una materia (Alumnos, Criterios, 1EVA, 2EVA, 3EVA, FINAL)
y para las distintas "clases" de columna dentro de las tablas de notas
(identidad del alumno, instrumentos, resultado final), de forma que el
conjunto se perciba ordenado y armonioso sin recurrir a colores ajenos
a la gama verde.
"""

"""
Estilos visuales de la aplicación EVACYL: una paleta azul-verde (la
identidad visual del proyecto) aplicada de forma centralizada con una
hoja de estilos Qt (QSS, parecido a CSS).

Las claves de PALETA mantienen los nombres "verde_*" por compatibilidad
con el resto del código (que las referencia por ese nombre), aunque
ahora representan tonos de la gama azul-verde de EVACYL en vez de verde
puro — así no hace falta tocar ningún otro archivo al cambiar de paleta.

Además de la paleta general, se definen colores específicos para cada
pestaña fija de una materia (Alumnos, Criterios, 1EVA, 2EVA, 3EVA, FINAL)
y para las distintas "clases" de columna dentro de las tablas de notas
(identidad del alumno, instrumentos, resultado final), de forma que el
conjunto se perciba ordenado y armonioso.
"""

PALETA = {
    "verde_muy_oscuro": "#071A33",   # azul marino muy oscuro (fondo general)
    "verde_oscuro": "#0D3D6B",       # azul oscuro
    "verde_medio": "#0F6FB9",        # azul vivo (color principal, extraído del logo)
    "verde": "#1591A8",              # azul-turquesa de transición
    "verde_claro": "#9FD9D0",        # turquesa claro
    "verde_muy_claro": "#EAF6F4",    # casi blanco con tinte turquesa
    "blanco": "#FFFFFF",
    "gris_texto_atenuado": "#7E96A8",
    # Toques de color de acento (no azul/verde), usados con moderación en
    # detalles puntuales: la pantalla de bienvenida y algún resalte.
    "acento_calido": "#E8A33D",   # mostaza suave, para detalles decorativos
    "acento_calido_claro": "#FBE9CC",
}

# Un color distinto para cada una de las 6 pestañas fijas de una materia,
# en el mismo orden en que aparecen siempre. Recorren la gama azul -> verde
# de la identidad EVACYL (como el degradado del logo), con suficiente
# variación de matiz para que cada pestaña se distinga a simple vista.
COLORES_PESTANAS_MATERIA = {
    "Alumnos": "#1859A8",     # azul
    "Criterios": "#1271AE",   # azul-medio
    "1EVA": "#0F6FB9",        # azul vivo
    "2EVA": "#138FA0",        # azul-turquesa
    "3EVA": "#159B8E",        # turquesa-verde
    "FINAL": "#0DAB6C",       # verde vivo (el verde del logo, como punto de llegada)
}

# Colores suaves para diferenciar "clases" de columna dentro de una tabla
# de notas: identidad del alumno, columnas de instrumento/criterio, y
# resultado final — todos dentro de la misma gama azul-verde, con distinta
# intensidad para que el ojo separe los bloques sin que choquen entre sí.
COLOR_COLUMNA_IDENTIDAD = "#DCEEF6"   # Apellidos, Nombre
COLOR_COLUMNA_DATOS = "#FFFFFF"        # IE / criterios / pruebas (neutra, ya llevan su propio degradado de nota)
COLOR_COLUMNA_RESULTADO = "#C9EAE0"    # Nota final / calificación

# Colores de FONDO DE CABECERA (más saturados, con texto blanco) para
# distinguir visualmente, en la propia fila de títulos de columna, el
# bloque al que pertenece cada una: identidad del alumno, datos (criterios
# o instrumentos/pruebas) y resultado final.
COLOR_CABECERA_IDENTIDAD = "#0F6FB9"   # azul vivo — Apellidos, Nombre
COLOR_CABECERA_DATOS = "#159B8E"        # turquesa — criterios, pruebas, instrumentos
COLOR_CABECERA_RESULTADO = "#0D3D6B"    # azul oscuro — nota final, calificación

# Colores específicos para la tabla de notas DENTRO de un instrumento
# (Apellidos/Nombre, pruebas o nota cruda del examen, y resultado por
# criterio): tres bloques con tonos bien diferenciados entre sí —
# gris para identidad, azul para los datos de entrada (pruebas/examen),
# verde para el resultado por criterio.
COLOR_CABECERA_IDENTIDAD_GRIS = "#6B7B8C"
COLOR_CABECERA_DATOS_AZUL = "#0F6FB9"
COLOR_CABECERA_CRITERIO_VERDE = "#0DAB6C"
COLOR_CELDA_IDENTIDAD_GRIS_CLARO = "#E6EAEE"  # fondo de Apellidos/Nombre a juego con la cabecera gris

HOJA_ESTILOS = f"""
QMainWindow {{
    background-color: {PALETA['verde_muy_claro']};
}}

QWidget {{
    background-color: {PALETA['verde_muy_claro']};
    color: {PALETA['verde_muy_oscuro']};
    font-size: 13px;
}}

QWidget#fondoTransparente {{
    background-color: transparent;
}}

QWidget#panelSobreFondo {{
    background-color: rgba(255, 255, 255, 235);
    border-radius: 10px;
}}

QWidget#barraSuperior {{
    background-color: {PALETA['verde_muy_claro']};
    border-bottom: 2px solid {PALETA['verde_claro']};
}}

QLabel#titulo {{
    font-size: 18px;
    font-weight: bold;
    color: {PALETA['verde_oscuro']};
}}

QLabel#subtitulo {{
    font-size: 15px;
    font-weight: bold;
    color: {PALETA['verde_medio']};
}}

QPushButton {{
    background-color: {PALETA['verde_medio']};
    color: {PALETA['blanco']};
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {PALETA['verde_oscuro']};
}}

QPushButton:pressed {{
    background-color: {PALETA['verde_muy_oscuro']};
}}

QPushButton#botonSecundario {{
    background-color: {PALETA['blanco']};
    color: {PALETA['verde_medio']};
    border: 1px solid {PALETA['verde_medio']};
}}

QPushButton#botonSecundario:hover {{
    background-color: {PALETA['verde_claro']};
}}

QPushButton#botonPeligro {{
    background-color: {PALETA['blanco']};
    color: #B23B3B;
    border: 1px solid #B23B3B;
}}

QPushButton#botonPeligro:hover {{
    background-color: #FBEAEA;
}}

QPushButton#botonAyuda {{
    background-color: {PALETA['acento_calido_claro']};
    color: #8A5A1D;
    border: 1px solid {PALETA['acento_calido']};
    border-radius: 14px;
    padding: 4px 12px;
    font-weight: 600;
}}

QPushButton#botonAyuda:hover {{
    background-color: {PALETA['acento_calido']};
    color: {PALETA['blanco']};
}}

QPushButton#botonSeccionPlegable {{
    background-color: {PALETA['verde_muy_claro']};
    color: {PALETA['verde_muy_oscuro']};
    border: 1px solid {PALETA['verde_claro']};
    border-radius: 6px;
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
}}

QPushButton#botonSeccionPlegable:hover {{
    background-color: {PALETA['verde_claro']};
}}

QTableWidget {{
    background-color: {PALETA['blanco']};
    alternate-background-color: {PALETA['verde_muy_claro']};
    gridline-color: {PALETA['verde_claro']};
    border: 1px solid {PALETA['verde_claro']};
    border-radius: 4px;
}}

QHeaderView::section {{
    background-color: {PALETA['verde_medio']};
    color: {PALETA['blanco']};
    padding: 6px;
    border: none;
    font-weight: bold;
}}

QTabWidget::pane {{
    border: 1px solid {PALETA['verde_claro']};
    border-radius: 4px;
    background-color: {PALETA['verde_muy_claro']};
}}

QTabBar::tab {{
    background-color: {PALETA['verde_claro']};
    color: {PALETA['verde_muy_oscuro']};
    padding: 8px 18px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {PALETA['verde_medio']};
    color: {PALETA['blanco']};
    font-weight: bold;
}}

QListWidget {{
    background-color: {PALETA['blanco']};
    border: 1px solid {PALETA['verde_claro']};
    border-radius: 4px;
}}

QListWidget::item:selected {{
    background-color: {PALETA['verde_medio']};
    color: {PALETA['blanco']};
}}

QLineEdit, QInputDialog QLineEdit {{
    background-color: {PALETA['blanco']};
    border: 1px solid {PALETA['verde_claro']};
    border-radius: 4px;
    padding: 4px;
}}
"""


def hoja_estilos_pestanas_materia() -> str:
    """Genera el QSS para colorear cada una de las 6 pestañas fijas de una
    materia (Alumnos, Criterios, 1EVA, 2EVA, 3EVA, FINAL) con un tono de
    verde distinto, en el orden en que siempre se añaden. Se aplica sobre
    el propio QTabWidget de la ventana de materia (no de forma global),
    para no afectar a otros QTabWidget de la aplicación (como las
    sub-pestañas de Calificaciones / Instrumentos dentro de cada evaluación).
    """
    nombres = list(COLORES_PESTANAS_MATERIA.keys())
    reglas = []
    for indice, nombre in enumerate(nombres):
        color = COLORES_PESTANAS_MATERIA[nombre]
        reglas.append(
            f"QTabBar::tab:nth-child({indice + 1}) {{ background-color: {color}; "
            f"color: {PALETA['blanco']}; }}"
        )
    return "\n".join(reglas)
