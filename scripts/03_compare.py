"""Genera un PDF de comparación 3-columnas: original | sin texto | preview reconstruido."""
import fitz
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

orig = fitz.open(ROOT / "3T-Quick-Start-for-cleaning-CP_IFU_16-XX-XX_Q_USA_001.pdf")
bg = fitz.open(OUT / "background_only.pdf")
pv = fitz.open(OUT / "extracted_preview.pdf")

out = fitz.open()
DPI = 130
gap = 10
label_h = 18
labels = ["ORIGINAL", "SIN TEXTO (background_only)", "RECONSTRUIDO (extracted_preview)"]

for i in range(orig.page_count):
    pix_o = orig[i].get_pixmap(dpi=DPI)
    pix_b = bg[i].get_pixmap(dpi=DPI)
    pix_p = pv[i].get_pixmap(dpi=DPI)
    w, h = pix_o.width, pix_o.height
    total_w = w * 3 + gap * 2
    page = out.new_page(width=total_w, height=h + label_h * 2)
    # etiquetas
    for col, lbl in enumerate(labels):
        x = col * (w + gap)
        page.insert_textbox(fitz.Rect(x, 0, x + w, label_h), lbl, fontsize=11, fontname="hebo", align=1)
    # imágenes
    for col, pix in enumerate([pix_o, pix_b, pix_p]):
        x = col * (w + gap)
        rect = fitz.Rect(x, label_h, x + w, label_h + h)
        page.insert_image(rect, pixmap=pix)

out.save(OUT / "comparacion_3col.pdf", garbage=4, deflate=True)
out.close()
orig.close(); bg.close(); pv.close()
print("output/comparacion_3col.pdf generado")
