"""
Paso 5: armado del PDF final en español.

Estrategia:
  - Las traducciones se leen del caché output/translations.json, generado por
    scripts/04_translate_gemini.py (Gemini, temperature = 0). Mantener el caché
    separado del armado hace que esta etapa sea 100% offline y reproducible.
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
CACHE = OUT / "translations.json"

# ---------------------------------------------------------------------------
# Tabla de traducción: se carga del caché generado por Gemini (paso 4).
# Cada entrada mapea el texto EXACTO de un span (incluyendo tabuladores y
# espacios) a su traducción al español.
# ---------------------------------------------------------------------------
_cache = json.loads(CACHE.read_text())
TRANSLATIONS = _cache.get("translations", {})
# size_specific: claves "texto␟tamaño" -> traducción más corta para headers chicos.
SIZE_SPECIFIC = {}
for k, v in _cache.get("size_specific", {}).items():
    txt, _, sz = k.rpartition("␟")
    SIZE_SPECIFIC[(txt, float(sz))] = v

_STRIPPED_TR = {k.strip(): v for k, v in TRANSLATIONS.items() if k.strip()}



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
