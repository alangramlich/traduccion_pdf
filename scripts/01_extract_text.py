#!/usr/bin/env python3
"""
Paso 1 - Extraccion de texto.

Recorre el PDF original y extrae todo el texto a nivel de bloque, guardando
para cada segmento su posicion (bbox), pagina, y atributos de estilo
(tamano de fuente, color, fuente) necesarios para volver a colocarlo despues.

Salida: output/extracted_text.json
"""
import json
import os
import sys

import fitz  # PyMuPDF

# Rutas (relativas a la raiz del repo)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_PDF = os.environ.get(
    "SRC_PDF",
    os.path.join(ROOT, "3T-Quick-Start-for-cleaning-CP_IFU_16-XX-XX_Q_USA_001.pdf"),
)
OUT_DIR = os.path.join(ROOT, "output")
OUT_JSON = os.path.join(OUT_DIR, "extracted_text.json")


def block_text(block):
    """Reconstruye el texto de un bloque respetando saltos de linea."""
    lines = []
    for line in block.get("lines", []):
        spans = [s["text"] for s in line.get("spans", [])]
        lines.append("".join(spans))
    return "\n".join(lines)


def representative_span(block):
    """Devuelve el span 'mas representativo' (el mas largo) del bloque para
    tomar de el el tamano de fuente, color y fuente."""
    best = None
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            if best is None or len(span["text"]) > len(best["text"]):
                best = span
    return best


def main():
    if not os.path.exists(SRC_PDF):
        sys.exit(f"No se encuentra el PDF original: {SRC_PDF}")

    os.makedirs(OUT_DIR, exist_ok=True)
    doc = fitz.open(SRC_PDF)

    segments = []
    seg_id = 0
    for pno in range(doc.page_count):
        page = doc[pno]
        data = page.get_text("dict")
        for block in data["blocks"]:
            if block.get("type", 0) != 0:  # solo bloques de texto
                continue
            text = block_text(block).strip()
            if not text:
                continue
            span = representative_span(block)
            segments.append(
                {
                    "id": seg_id,
                    "page": pno,
                    "bbox": [round(c, 2) for c in block["bbox"]],
                    "text": text,
                    "size": round(span["size"], 2) if span else 10.0,
                    "color": span["color"] if span else 0,
                    "font": span["font"] if span else "",
                }
            )
            seg_id += 1

    out = {
        "source_pdf": os.path.basename(SRC_PDF),
        "page_count": doc.page_count,
        "segments": segments,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    doc.close()
    print(f"Extraidos {len(segments)} segmentos de texto -> {OUT_JSON}")


if __name__ == "__main__":
    main()
