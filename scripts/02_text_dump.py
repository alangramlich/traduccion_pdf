"""Vuelca el texto extraído a un .txt legible para verificación rápida."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "output/extracted_text.json").read_text())

lines_out = []
for page in data:
    lines_out.append(f"\n{'='*70}\nPÁGINA {page['page']}  ({page['width']:.0f} x {page['height']:.0f})\n{'='*70}")
    for block in page["blocks"]:
        bx, by = block["bbox"][0], block["bbox"][1]
        lines_out.append(f"\n--- bloque @({bx:.0f},{by:.0f}) ---")
        for line in block["lines"]:
            parts = []
            for span in line["spans"]:
                t = span["text"]
                if span["flags"] & 16:
                    t = f"**{t}**"
                if span["flags"] & 2:
                    t = f"_{t}_"
                parts.append(t)
            joined = "".join(parts).strip()
            if joined:
                lines_out.append(joined)
(ROOT / "output/extracted_text.txt").write_text("\n".join(lines_out))
print("output/extracted_text.txt generado")
