"""Comparativo lado-a-lado: original | sin texto | traducido al español."""
import fitz
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

orig = fitz.open(ROOT / "3T-Quick-Start-for-cleaning-CP_IFU_16-XX-XX_Q_USA_001.pdf")
bg = fitz.open(OUT / "background_only.pdf")
tr = fitz.open(OUT / "translated.pdf")

out = fitz.open()
DPI = 130
gap = 10
label_h = 18
labels = ["ORIGINAL (inglés)", "SIN TEXTO (background)", "TRADUCIDO (español)"]

for i in range(orig.page_count):
    pix_o = orig[i].get_pixmap(dpi=DPI)
    pix_b = bg[i].get_pixmap(dpi=DPI)
    pix_t = tr[i].get_pixmap(dpi=DPI)
    w, h = pix_o.width, pix_o.height
    total_w = w * 3 + gap * 2
    page = out.new_page(width=total_w, height=h + label_h * 2)
    for col, lbl in enumerate(labels):
        x = col * (w + gap)
        page.insert_textbox(fitz.Rect(x, 0, x + w, label_h), lbl, fontsize=11, fontname="hebo", align=1)
    for col, pix in enumerate([pix_o, pix_b, pix_t]):
        x = col * (w + gap)
        rect = fitz.Rect(x, label_h, x + w, label_h + h)
        page.insert_image(rect, pixmap=pix)

out.save(OUT / "comparacion_traducido.pdf", garbage=4, deflate=True)
out.close()
orig.close(); bg.close(); tr.close()
print("output/comparacion_traducido.pdf generado")
