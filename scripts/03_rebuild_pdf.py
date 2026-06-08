#!/usr/bin/env python3
"""
Paso 3 - Reconstruccion del PDF.

Toma el PDF original y output/translated_text.json y coloca cada texto
traducido en la posicion (bbox) original, tapando el texto en el idioma
de origen. Conserva imagenes y graficos del documento.

Salida: output/translated.pdf

Variables de entorno:
  SRC_PDF   (opcional)  ruta del PDF original
"""
import json
import os
import sys

import fitz  # PyMuPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_PDF = os.environ.get(
    "SRC_PDF",
    os.path.join(ROOT, "3T-Quick-Start-for-cleaning-CP_IFU_16-XX-XX_Q_USA_001.pdf"),
)
OUT_DIR = os.path.join(ROOT, "output")
IN_JSON = os.path.join(OUT_DIR, "translated_text.json")
OUT_PDF = os.path.join(OUT_DIR, "translated.pdf")


def int_to_rgb(color_int):
    """Convierte un color entero de PyMuPDF (0xRRGGBB) a tupla 0..1."""
    r = ((color_int >> 16) & 255) / 255.0
    g = ((color_int >> 8) & 255) / 255.0
    b = (color_int & 255) / 255.0
    return (r, g, b)


def fit_fontsize(text, rect, base_size):
    """Reduce el tamano de fuente hasta que el texto entre en el rectangulo."""
    size = base_size
    while size > 4:
        # estimacion: ancho medio de glifo ~0.5*size; alto de linea ~1.2*size
        max_chars_line = max(1, int(rect.width / (size * 0.5)))
        lines = 0
        for paragraph in text.split("\n"):
            lines += max(1, -(-len(paragraph) // max_chars_line))  # ceil
        if lines * size * 1.2 <= rect.height:
            return size
        size -= 0.5
    return size


def main():
    if not os.path.exists(SRC_PDF):
        sys.exit(f"No se encuentra el PDF original: {SRC_PDF}")
    if not os.path.exists(IN_JSON):
        sys.exit(f"No existe {IN_JSON}. Ejecuta primero 02_translate.py")

    with open(IN_JSON, encoding="utf-8") as f:
        data = json.load(f)
    segments = data["segments"]

    doc = fitz.open(SRC_PDF)

    # 1) Tapar el texto original: redaccion por bbox (elimina el texto fuente)
    by_page = {}
    for seg in segments:
        by_page.setdefault(seg["page"], []).append(seg)

    for pno, segs in by_page.items():
        page = doc[pno]
        for seg in segs:
            if not seg.get("translated"):
                continue
            rect = fitz.Rect(seg["bbox"])
            page.add_redact_annot(rect, fill=(1, 1, 1))  # tapar con blanco
        page.apply_redactions()

    # 2) Insertar el texto traducido en cada posicion original
    for pno, segs in by_page.items():
        page = doc[pno]
        for seg in segs:
            translated = seg.get("translated")
            if not translated:
                continue
            rect = fitz.Rect(seg["bbox"])
            color = int_to_rgb(seg.get("color", 0))
            base_size = seg.get("size", 10.0)
            size = fit_fontsize(translated, rect, base_size)
            # Un pequeno margen evita que el texto toque los bordes
            page.insert_textbox(
                rect,
                translated,
                fontsize=size,
                fontname="helv",
                color=color,
                align=fitz.TEXT_ALIGN_LEFT,
            )

    doc.save(OUT_PDF, garbage=4, deflate=True)
    doc.close()
    print(f"PDF traducido generado -> {OUT_PDF}")


if __name__ == "__main__":
    main()
