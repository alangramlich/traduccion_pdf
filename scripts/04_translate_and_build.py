"""
Paso 2 + 3: traducción y armado del PDF final.

Estrategia:
  - Usamos background_only.pdf (que conserva imágenes y vectores tal cual estaban
    en el original) como base; no tocamos nada de las imágenes.
  - Por cada span de texto del JSON de extracción, escribimos arriba la traducción
    al español manteniendo posición (origin), color, tamaño, bold/italic, rotación.
  - Para spans cuya fuente original renderiza en mayúsculas (versalitas), aplicamos
    .upper() a la traducción para mantener la apariencia visual.
  - Si la traducción es más ancha que el bbox original, reducimos fuente
    progresivamente hasta que entre.
"""

import json
import math
import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
BG = OUT / "background_only.pdf"
DST = OUT / "translated.pdf"
TEXT_JSON = OUT / "extracted_text.json"

# ---------------------------------------------------------------------------
# Tabla de traducción
# Cada entrada mapea el texto EXACTO de un span (tal como aparece en el JSON,
# incluyendo tabuladores y espacios) a la traducción al español.
# ---------------------------------------------------------------------------
TRANSLATIONS = {
    # Página 1
    "QUICK START INSTRUCTIONS": "INSTRUCCIONES DE INICIO RÁPIDO",
    "Routine maintenance": "Mantenimiento de rutina",
    "Heater-Cooler System 3T": "Sistema Calentador-Enfriador 3T",
    "Timelines for disinfection and related tasks": "Cronograma de desinfección y tareas relacionadas",
    "A)\t prior to inital operation;": "A)\t previo a la operación;",
    "prior to storing": "antes de almacenar",
    "Surface disinfection and": "Desinfección de superficies y",
    "disinfection of water circuits": "desinfección de circuitos de agua",
    "page 2": "página 2",
    "B)\t after every operation": "B)\t tras cada operación",
    "Surface disinfection": "Desinfección de superficies",
    "C)\t every 7 days": "C)\t cada 7 días",
    "Water change;": "Cambio de agua;",
    "Add hydrogen-peroxide;": "Agregar peróxido de hidrógeno;",
    # Variantes con espacios/tabs finales (vienen del extractor exactos)
    "Surface disinfection and\t": "Desinfección de superficies y\t",
    "Surface disinfection\t": "Desinfección de superficies\t",
    "Water change; \t": "Cambio de agua; \t",
    "Add hydrogen-peroxide;\t": "Agregar peróxido de hidrógeno;\t",
    "Disinfection of overflow bottle\t": "Desinfección de la botella de rebose\t",
    "Disinfection of water circuits\t": "Desinfección de circuitos de agua\t",
    "Exchange the tubings\t": "Reemplazar las tuberías\t",
    "page 2 ": "página 2 ",
    "NOTE: These Quick Start Instructions are only an excerpt ": "NOTA: Estas Instrucciones de Inicio Rápido son solo un extracto ",
    "Bacillol \t": "Bacillol \t",
    "Bode\t": "Bode\t",
    "CaviWipe \t": "CaviWipe \t",
    "Super Sani Cloth \t": "Super Sani Cloth \t",
    "Meliseptol HBV \t": "Meliseptol HBV \t",
    "Mikrozid AF \t": "Mikrozid AF \t",
    "Be sure that the drain valves are closed ": "Asegúrese de que las válvulas de drenaje estén ",
    # H2O2 partido en sub-spans (subscript 2, O, 2, .)
    "Add 150ml hydrogen-peroxide (H": "Agregue 150 ml de peróxido (H",
    "O": "O",
    ").": ").",
    "and inlet of the patient 1 while disinfecting": "y la entrada del paciente 1 mientras desinfecta",
    " 450ml Peresal ": " 450 ml de Peresal ",
    " QUICK START INSTRUCTIONS": " INSTRUCCIONES DE INICIO RÁPIDO",
    "Include the tubings in the disinfection as described. ": "Incluya las tuberías en la desinfección como se describe. ",
    "Disinfect the drain ports (spray, wipe). ": "Desinfecte los puertos de drenaje (rocíe, limpie). ",
    "Only if disinfection has not been performed correctly, ": "Solo si la desinfección no se ha realizado correctamente, ",
    "water samples shall be taken and analyzed. ": "se deben tomar y analizar muestras de agua. ",
    "Disinfection of overflow bottle": "Desinfección de la botella de rebose",
    "page 3": "página 3",
    "page 4": "página 4",
    "D)\t every 14 days": "D)\t cada 14 días",
    "Disinfection of water circuits": "Desinfección de circuitos de agua",
    "page 5": "página 5",
    "E)\t once per year": "E)\t una vez por año",
    "Exchange the tubings": "Reemplazar las tuberías",
    "page 10": "página 10",
    "F)\t": "F)\t",
    " ": " ",
    "regularly\t": "regularmente\t",
    "Take water samples": "Tomar muestras de agua",
    "\t": "\t",
    "NOTE: These Quick Start Instructions are only an excerpt": "NOTA: Estas Instrucciones de Inicio Rápido son solo un extracto",
    "of the Operating Instructions (CP_IFU_16-XX-XX_USA_014) ": "de las Instrucciones de Operación (CP_IFU_16-XX-XX_USA_014) ",
    "regarding routine water maintenance and disinfection ": "sobre el mantenimiento y desinfección de rutina del agua ",
    "(chapter 5 and 6). They do not replace the Operating ": "(capítulos 5 y 6). No reemplazan las Instrucciones ",
    "Instructions. For complete set up, use of the machine and ": "de Operación. Para una configuración completa, uso de la máquina y ",
    "warnings and cautions, the comprehensive Heater Cooler ": "advertencias y precauciones, deben seguirse las Instrucciones de ",
    "System Operating Instructions must be followed.": "Operación completas del Sistema Calentador-Enfriador.",

    # Página 2
    "QUICK START INSTRUCTIONS  I  Heater-Cooler System 3T": "INSTRUCCIONES DE INICIO RÁPIDO  I  Sistema Calentador-Enfriador 3T",
    "  I  ": "  I  ",
    " ": " ",
    "I 2 I": "I 2 I",
    "A.1)\t Surface DIsinfection": "A.1)\t Desinfección de superficies",
    "Close the CAN-jack with the matching cover.": "Cierre el conector CAN con la tapa correspondiente.",
    "Use only pre-soaked, ready-to-use disinfectant": "Use solo paños desinfectantes pre-impregnados,",
    "tissues.": "listos para usar.",
    "1.1": "1.1",
    "1.2": "1.2",
    "1.3": "1.3",
    "1.4": "1.4",
    "Clean all accessible system surfaces.": "Limpie todas las superficies accesibles del sistema.",
    "Disinfect all accessible system surfaces.": "Desinfecte todas las superficies accesibles del sistema.",
    "Ensure that no liquids enter the housing.": "Asegúrese de que no entren líquidos en la carcasa.",
    "A) prior to inital operation; prior to storing   I   B) after every operation": "A) previo a la operación; antes de almacenar   I   B) tras cada operación",
    "A.2)\tDIsinfection of water circuits": "A.2)\tDesinfección de circuitos de agua",
    "see D) page 5 disinfection of water circuits every 14 days": "ver D) página 5 desinfección de circuitos de agua cada 14 días",
    "B.1)\t Surface DIsinfection": "B.1)\t Desinfección de superficies",
    "Required material ": "Material requerido ",
    "(ready-to-use disinfectant tissues)": "(paños desinfectantes listos para usar)",
    "Product name \t": "Nombre del producto \t",
    "Manufacturer": "Fabricante",
    "Bacillol": "Bacillol",
    "Bode": "Bode",
    "CaviWipe": "CaviWipe",
    "Metrex": "Metrex",
    "Super Sani Cloth": "Super Sani Cloth",
    "PDI": "PDI",
    "Meliseptol HBV": "Meliseptol HBV",
    "B. Braun": "B. Braun",
    "Mikrozid AF": "Mikrozid AF",
    "Schülke & Mayr": "Schülke & Mayr",
    "A) prior to inital operation; prior to storing": "A) previo a la operación; antes de almacenar",
    "B) after every operation": "B) tras cada operación",
    "CP_IFU_16-XX-XX_Q_USA_001": "CP_IFU_16-XX-XX_Q_USA_001",

    # Página 3
    "I 3 I": "I 3 I",
    "C.1) Drainage": "C.1) Drenaje",
    "Drain the water tanks.": "Drene los tanques de agua.",
    "Be sure that the drain valves are closed": "Asegúrese de que las válvulas de drenaje estén",
    "once the tanks are empty.": "cerradas una vez que los tanques estén vacíos.",
    "C.2) Fill and add hydrogene-peroxide": "C.2) Llenar y agregar peróxido de hidrógeno",
    "Open the filling.": "Abra el llenado.",
    "Fill the device with filtered tap water until": "Llene el dispositivo con agua del grifo filtrada",
    "the first orange bar is blinking.": "hasta que parpadee la primera barra naranja.",
    "2.1": "2.1",
    "Add 150ml hydrogen-peroxide (H2O2).": "Agregue 150 ml de peróxido de hidrógeno (H2O2).",
    "2.2": "2.2",
    "Fill the device with filtered tap water until ": "Llene el dispositivo con agua del grifo filtrada ",
    "2 bars are green.": "hasta que 2 barras estén verdes.",
    "Close tank filling.": "Cierre el llenado del tanque.",
    "2.3": "2.3",
    "Disconnect short circuit tubing patient 1.": "Desconecte la tubería de cortocircuito paciente 1.",
    "2.4": "2.4",
    "Create a short circuit between inlet of cardioplegia ": "Cree un cortocircuito entre la entrada de cardioplegia ",
    "and inlet of the patient 1 while disinfecting ": "y la entrada del paciente 1 mientras desinfecta ",
    "the tubing and device connector.": "la tubería y el conector del dispositivo.",
    "2.5": "2.5",
    "Start cold cardioplegia.": "Inicie cardioplegia fría.",
    "Circulate for 5min.": "Circule durante 5 min.",
    "2.6": "2.6",
    "Stop cold cardioplegia.": "Detenga la cardioplegia fría.",
    "2.7": "2.7",
    "Switch off the device.": "Apague el dispositivo.",
    "2.8": "2.8",
    "C) every 7 days": "C) cada 7 días",

    # Página 4
    "I  4  I": "I  4  I",
    "C.3) Disinfection of overflow bottle": "C.3) Desinfección de la botella de rebose",
    "Empty the overflow bottle.": "Vacíe la botella de rebose.",
    "3.1": "3.1",
    "Disinfect the overflow bottle with automatic ": "Desinfecte la botella de rebose con desinfección ",
    "chemical-thermal disinfection in a ": "químico-térmica automática en una ",
    "washer-disinfector.": "lavadora-desinfectadora.",
    "3.2": "3.2",

    # Página 5
    "I  5  I": "I  5  I",
    "D.1) Preparation": "D.1) Preparación",
    "Be sure to wear protective glasses and clothing.": "Asegúrese de usar gafas y ropa de protección.",
    "Disinfect your hands.": "Desinfecte sus manos.",
    "Use the Aquasafe water filter from Pall to fill ": "Use el filtro de agua Aquasafe de Pall para llenar ",
    "the device with filtered tap water.": "el dispositivo con agua del grifo filtrada.",
    "Be sure that the filter is not expired yet.": "Asegúrese de que el filtro no esté vencido.",
    "Switch on the device.": "Encienda el dispositivo.",
    "Mute the low level alarm.": "Silencie la alarma de nivel bajo.",
    "Open the filling. Disinfect the filling and the tubing ": "Abra el llenado. Desinfecte el llenado y la tubería ",
    "of the water filter. Fill the device with filtered tap ": "del filtro de agua. Llene el dispositivo con agua del ",
    "water until the first orange bar is blinking.": "grifo filtrada hasta que parpadee la primera barra naranja.",
    "D.2) add disinfectant": "D.2) agregar desinfectante",
    "Measure 450ml Puristeril 340 ": "Mida 450ml de Puristeril 340 ",
    "or": "o",
    " 450ml Peresal": " 450ml Peresal",
    " 450ml Peresal ": " 450ml Peresal ",
    " 450ml Minncare ": " 450ml Minncare ",
    " 180ml Clorox.": " 180ml Clorox.",
    "Fill the disinfectant into the device.": "Vierta el desinfectante en el dispositivo.",
    "Add filtered tap water until 2 bars are green.": "Agregue agua del grifo filtrada hasta que 2 barras estén verdes.",
    "Close the tank filling.": "Cierre el llenado del tanque.",
    "Make sure all circuits are closed.": "Asegúrese de que todos los circuitos estén cerrados.",
    "D) every 14 days": "D) cada 14 días",
    "Disinfect tubing connectors.": "Desinfecte los conectores de la tubería.",
    "Disinfect device connectors.": "Desinfecte los conectores del dispositivo.",
    "Create a short circuit between inlet of cardioplegia": "Cree un cortocircuito entre la entrada de cardioplegia",
    "and inlet of the patient 1.": "y la entrada del paciente 1.",
    "Make sure all circuits are closed.": "Asegúrese de que todos los circuitos estén cerrados.",

    # Página 6
    "I  6  I": "I  6  I",
    "Set cold cardioplegia to 10°C.": "Configure la cardioplegia fría a 10 °C.",
    "Set warm cardioplegia and patient ": "Configure la cardioplegia caliente y la ",
    "temperature to 20°C.": "temperatura del paciente a 20 °C.",
    "D.3) disinfect (5 min.)": "D.3) desinfectar (5 min.)",
    "Stop cold cardioplegia.": "Detenga la cardioplegia fría.",
    "3.3": "3.3",
    "Disinfect additional short circuit tubing.": "Desinfecte la tubería de cortocircuito adicional.",
    "Establish a short circuit tubing for patient 2.": "Establezca una tubería de cortocircuito para el paciente 2.",
    "3.4": "3.4",
    "Disconnect and disinfect established short circuit.": "Desconecte y desinfecte el cortocircuito establecido.",
    "Disinfect device connector.": "Desinfecte el conector del dispositivo.",
    "Establish short circuit tubing for cardioplegia.": "Establezca la tubería de cortocircuito para cardioplegia.",
    "Disinfect connectors of longer tubing and short ": "Desinfecte los conectores de la tubería más larga y ",
    "circuit adaptor. Connect both tubing ending with ": "el adaptador de cortocircuito. Conecte ambos extremos ",
    "short circuit adaptor.": "de la tubería con el adaptador de cortocircuito.",
    "3.5": "3.5",
    "Establish short circuit tubing for patient 1.": "Establezca la tubería de cortocircuito para el paciente 1.",
    "Open all valves.": "Abra todas las válvulas.",
    "3.6": "3.6",

    # Página 7
    " QUICK START INSTRUCTIONS  I  Heater-Cooler System 3T": " INSTRUCCIONES DE INICIO RÁPIDO  I  Sistema Calentador-Enfriador 3T",
    "I  7  I": "I  7  I",
    "D.4) disinfect (10 min.)": "D.4) desinfectar (10 min.)",
    "Start warm cardioplegia and patient 1 and 2.": "Inicie cardioplegia caliente y paciente 1 y 2.",
    "Circulate for 10min.": "Circule durante 10 min.",
    "4.1": "4.1",
    "Close all valves while circuits are running ": "Cierre todas las válvulas mientras los circuitos están ",
    "to empty the tubing.": "funcionando para vaciar la tubería.",
    "4.2": "4.2",
    "When tubing are empty stop all circuits.": "Cuando las tuberías estén vacías detenga todos los circuitos.",
    "4.3": "4.3",
    "D.5) drainage 1": "D.5) drenaje 1",
    "Disinfect drainage tubing and drains.": "Desinfecte las tuberías de drenaje y los drenajes.",
    "Connect both drainage tubing.": "Conecte ambas tuberías de drenaje.",
    "5.1": "5.1",
    "Open both drains.": "Abra ambos drenajes.",
    "Drain the device completely.": "Drene el dispositivo completamente.",
    "5.2": "5.2",
    "Close both drains.": "Cierre ambos drenajes.",
    "5.3": "5.3",

    # Página 8
    "I  8  I": "I  8  I",
    "D.6) Rinse 1": "D.6) Enjuague 1",
    "Open tank filling.": "Abra el llenado del tanque.",
    "Fill the device with filtered tap water until 2 bars ": "Llene el dispositivo con agua del grifo filtrada hasta ",
    "are green. Close tank filling.": "que 2 barras estén verdes. Cierre el llenado del tanque.",
    "6.1": "6.1",
    "Open all valves.": "Abra todas las válvulas.",
    "Circulate for 3min.": "Circule durante 3 min.",
    "6.2": "6.2",
    "6.3": "6.3",
    "6.4": "6.4",
    "D.7) Drainage 2": "D.7) Drenaje 2",
    "7.1": "7.1",
    "7.2": "7.2",
    "D.8) Rinse 2": "D.8) Enjuague 2",
    "8.1": "8.1",
    "8.2": "8.2",
    "8.3": "8.3",
    "8.4": "8.4",
    "D.9) Drainage 3": "D.9) Drenaje 3",
    "9.1": "9.1",
    "9.2": "9.2",

    # Página 9
    "I  9  I": "I  9  I",
    "D.10) Fill and add hydrogene-peroxide": "D.10) Llenar y agregar peróxido de hidrógeno",
    "10.1": "10.1",
    "10.2": "10.2",
    "10.3": "10.3",
    "10.4": "10.4",
    "10.5": "10.5",
    "10.6": "10.6",
    "10.7": "10.7",
    "10.8": "10.8",
    "NOTE: The overflow bottle must also ": "NOTA: La botella de rebose también debe ",
    "be disinfected regularly (see C.3) page 4).": "desinfectarse regularmente (ver C.3) página 4).",

    # Página 10
    "I  10  I": "I  10  I",
    "E.1) Exchange the tubings": "E.1) Reemplazar las tuberías",
    "Tubings that are used with the heater-cooler ": "Las tuberías que se usan con el calentador-enfriador ",
    "must be replaced once a year.": "deben reemplazarse una vez al año.",
    "Include the tubings in the disinfection as described.": "Incluya las tuberías en la desinfección como se describe.",
    "Connect the tubings during the disinfection cycle ": "Conecte las tuberías al calentador-enfriador durante ",
    "to the heater-cooler.": "el ciclo de desinfección.",
    "NOTE: Only use tubings that are certified ": "NOTA: Use solo tuberías certificadas para ",
    "for drinking water systems, such as SORIN ": "sistemas de agua potable, como el número ",
    "part number 75-510-218.": "de parte SORIN 75-510-218.",
    "F.1) Take water samples": "F.1) Tomar muestras de agua",
    "Disinfect the drain ports (spray, wipe).": "Desinfecte los puertos de drenaje (rocíe, limpie).",
    "Only if disinfection has not been performed correctly,": "Solo si la desinfección no se ha realizado correctamente,",
    "water samples shall be taken and analyzed.": "se deben tomar y analizar muestras de agua.",
    "Open the drain port. Let the water run for a while ": "Abra el puerto de drenaje. Deje correr el agua un ",
    "(5sec) and then take the water sample out of the ": "rato (5 seg) y luego tome la muestra de agua del ",
    "running water stream.": "chorro de agua que corre.",
    "E) once per year   I   F) regularly": "E) una vez por año   I   F) regularmente",
    "E) once per year": "E) una vez por año",
    "F) regularly": "F) regularmente",
}


_STRIPPED_TR = {k.strip(): v for k, v in TRANSLATIONS.items() if k.strip()}

# Variantes por tamaño: cuando un mismo texto aparece en distintos tamaños
# preferimos una traducción más corta en los headers chicos para no pisar el span vecino.
SIZE_SPECIFIC = {
    ("QUICK START INSTRUCTIONS", 8.0): "GUÍA RÁPIDA",
    (" QUICK START INSTRUCTIONS", 8.0): " GUÍA RÁPIDA",
    ("Heater-Cooler System 3T", 8.0): "Calentador-Enfriador 3T",
}


def translate_span(span) -> str:
    """Devuelve la traducción del texto del span, o el original si no hay traducción."""
    text = span["text"]
    size = round(span["size"], 1)
    key = (text, size)
    if key in SIZE_SPECIFIC:
        return SIZE_SPECIFIC[key]
    if text in TRANSLATIONS:
        return TRANSLATIONS[text]
    if not text.strip():
        return text
    if re.fullmatch(r"[\d\.\-_ \t\|/IV]+", text):
        return text
    stripped = text.strip()
    skey = (stripped, size)
    if skey in SIZE_SPECIFIC:
        left = text[:len(text) - len(text.lstrip())]
        right = text[len(text.rstrip()):]
        return f"{left}{SIZE_SPECIFIC[skey]}{right}"
    if stripped in _STRIPPED_TR:
        left = text[:len(text) - len(text.lstrip())]
        right = text[len(text.rstrip()):]
        return f"{left}{_STRIPPED_TR[stripped]}{right}"
    print(f"  [SIN TRADUCCIÓN] {text!r}")
    return text


def needs_uppercase(span):
    """Decide si un span se renderiza en mayúsculas en el original."""
    t = span["text"].strip()
    font = span["font"]
    # Subsecciones A.1), B.1), C.1), C.2), C.3), D.1)...D.10), E.1), F.1)
    if re.match(r"^[A-F]\.\d+\)", t):
        return True
    # "Required material" (mayúsculas en original)
    if t.startswith("Required material"):
        return True
    return False


def pick_fontname(flags, font):
    """Mapea flags PyMuPDF a una fuente Helvetica integrada (siempre disponible)."""
    bold = bool(flags & 16) or "Bold" in font
    italic = bool(flags & 2) or "Italic" in font
    if bold and italic:
        return "helv-bo"
    if bold:
        return "hebo"
    if italic:
        return "heit"
    return "helv"


def write_span(page, span, translated_text, debug_misfit, next_x_limit=None):
    """Escribe el texto traducido en la posición del span original.

    - mantiene origin (línea base) y color
    - intenta usar la misma altura de fuente
    - si la traducción no entra a lo ancho del bbox, reduce gradualmente
    - maneja rotación (90° si dir = (0, -1) o (0, 1))
    """
    if not translated_text:
        return
    bbox = fitz.Rect(span["bbox"])
    origin = span.get("origin", [bbox.x0, bbox.y1])
    size = span["size"]
    color = (0, 0, 0)
    if span["color_hex"]:
        c = int(span["color_hex"][1:], 16)
        color = ((c >> 16) & 0xFF) / 255, ((c >> 8) & 0xFF) / 255, (c & 0xFF) / 255

    fontname = pick_fontname(span["flags"], span["font"])
    helv_font = fitz.Font(fontname=fontname)

    # Detectar rotación a partir del vector dir de la línea
    rotate = 0
    line_dir = span.get("line_dir")
    if line_dir:
        dx, dy = line_dir
        if abs(dx) < 0.01 and dy < -0.5:
            rotate = 90  # texto leyendo de abajo hacia arriba
        elif abs(dx) < 0.01 and dy > 0.5:
            rotate = 270
        elif dx < -0.5 and abs(dy) < 0.01:
            rotate = 180

    # Ancho disponible según orientación. Si hay un siguiente span en la misma
    # línea, ese punto es el límite real (no el margen derecho).
    page_w = page.rect.width
    page_h = page.rect.height
    margin = 4
    if rotate == 0:
        limit = next_x_limit if next_x_limit is not None else (page_w - margin)
        avail_w = limit - origin[0] - 2  # 2px de gap entre spans
    elif rotate == 90:
        avail_w = origin[1] - margin
    elif rotate == 270:
        avail_w = page_h - origin[1] - margin
    else:  # 180
        avail_w = origin[0] - margin

    final_size = size
    text_w = helv_font.text_length(translated_text, fontsize=size)
    # No reducir tamaño de spans muy cortos (separadores "I", subíndices, etc.):
    # son posiciones fijas y el shrink no los acomoda mejor que dejarlos pisar.
    short_span = len(translated_text.strip()) <= 3
    if avail_w > 0 and text_w > avail_w * 1.0 and not short_span:
        for trial in (size * f for f in (0.95, 0.9, 0.85, 0.8, 0.75, 0.7)):
            if helv_font.text_length(translated_text, fontsize=trial) <= avail_w:
                final_size = trial
                break
        else:
            final_size = size * 0.7
            debug_misfit.append((page.number + 1, translated_text[:40], size, final_size, text_w, avail_w))

    try:
        page.insert_text(
            fitz.Point(origin[0], origin[1]),
            translated_text,
            fontsize=final_size,
            color=color,
            fontname=fontname,
            rotate=rotate,
            render_mode=0,
        )
    except Exception as e:
        print(f"  ! fallo insert_text: {e}  text={translated_text!r}")


def main():
    text_data = json.loads(TEXT_JSON.read_text())
    doc = fitz.open(BG)
    debug_misfit = []
    untranslated = []

    for pi, page_data in enumerate(text_data):
        page = doc[pi]
        # Obstáculos (flechas, dibujos pequeños con fill) que el texto no debe pisar
        obstacles = []
        for d in page.get_drawings():
            r = d.get("rect")
            if not r:
                continue
            if 0 < r.width < 50 and (d.get("fill") or d.get("color")):
                obstacles.append((r.x0, r.y0, r.y1))

        all_spans = []
        for block in page_data["blocks"]:
            for line in block["lines"]:
                for span in line["spans"]:
                    span["line_dir"] = line["dir"]
                    all_spans.append(span)

        # Excluir spans solo-whitespace (tabs sueltos) del cálculo de límites
        spans_h = [s for s in all_spans
                   if abs(s["line_dir"][0]) > 0.5 and s["text"].strip()]
        spans_h_sorted = sorted(spans_h, key=lambda s: (round(s["origin"][1], 1), s["origin"][0]))

        next_limit_map = {}  # id(span) -> next_x or None
        for s in spans_h_sorted:
            sx = s["origin"][0]
            y_top = s["bbox"][1]
            y_bot = s["bbox"][3]
            next_x = None
            # Otros spans cuya banda Y se superpone significativamente
            # (>= 30% de la altura del span más chico).
            s_height = y_bot - y_top
            for t in spans_h_sorted:
                if t is s:
                    continue
                t_top, t_bot = t["bbox"][1], t["bbox"][3]
                overlap = min(y_bot, t_bot) - max(y_top, t_top)
                t_height = t_bot - t_top
                min_h = min(s_height, t_height)
                if min_h <= 0 or overlap < min_h * 0.3:
                    continue
                if t["origin"][0] > sx + 0.1:
                    if next_x is None or t["origin"][0] < next_x:
                        next_x = t["origin"][0]
            # Obstáculos (flechas etc.)
            for ox, oy0, oy1 in obstacles:
                if ox <= sx + 0.1:
                    continue
                if oy1 < y_top - 1 or oy0 > y_bot + 1:
                    continue
                if next_x is None or ox < next_x:
                    next_x = ox
            next_limit_map[id(s)] = next_x

        for span in all_spans:
            raw = span["text"]
            translated = translate_span(span)
            if raw not in TRANSLATIONS and raw.strip() and not re.fullmatch(r"[\d\.\-_ \t\|/IV]+", raw):
                untranslated.append((pi + 1, raw))
            if needs_uppercase(span):
                translated = translated.upper()
            limit = next_limit_map.get(id(span))
            write_span(page, span, translated, debug_misfit, next_x_limit=limit)

    doc.save(DST, garbage=4, deflate=True)
    doc.close()

    print(f"\n=== Resumen traducción ===")
    print(f"PDF generado: {DST}")
    if untranslated:
        print(f"\n[!] {len(untranslated)} spans sin traducción (se dejaron en inglés):")
        for p, t in untranslated[:20]:
            print(f"  p{p}: {t!r}")
    if debug_misfit:
        print(f"\n[!] {len(debug_misfit)} spans que requieron reducción extrema (>30%):")
        for p, t, s0, s1, w, av in debug_misfit:
            print(f"  p{p} size {s0:.1f}->{s1:.1f}  w={w:.0f}>av={av:.0f}  {t!r}")


if __name__ == "__main__":
    main()
