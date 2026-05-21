"""
Paso 1: Extracción del PDF original.

Genera:
  - output/extracted_text.json  -> Todo el texto con posición, fuente, tamaño, color, rotación.
  - output/images/*.png         -> Cada imagen rasterizada con su nombre p{pag}_i{idx}.png
  - output/extracted_images.json -> Listado de imágenes con su bbox por página.
  - output/background_only.pdf  -> El PDF original al que se le borró el texto (queda fondo + imágenes + vectores).
  - output/extracted_preview.pdf -> PDF en blanco con el texto e imágenes extraídos colocados en su posición original (para verificación visual).
"""

import json
import os
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = ROOT / "3T-Quick-Start-for-cleaning-CP_IFU_16-XX-XX_Q_USA_001.pdf"
OUT = ROOT / "output"
IMG_DIR = OUT / "images"
OUT.mkdir(exist_ok=True)
IMG_DIR.mkdir(exist_ok=True)


def color_int_to_hex(c):
    if c is None:
        return None
    try:
        c = int(c)
    except Exception:
        return None
    return f"#{c & 0xFFFFFF:06x}"


def extract_text(doc):
    """Extrae todo el texto preservando posición, fuente, tamaño y color."""
    pages_data = []
    for page_index, page in enumerate(doc):
        page_dict = page.get_text("dict")
        page_info = {
            "page": page_index + 1,
            "width": page.rect.width,
            "height": page.rect.height,
            "rotation": page.rotation,
            "blocks": [],
        }
        for block in page_dict["blocks"]:
            if block["type"] != 0:
                continue  # imágenes las tratamos aparte
            block_info = {
                "bbox": list(block["bbox"]),
                "lines": [],
            }
            for line in block["lines"]:
                line_info = {
                    "bbox": list(line["bbox"]),
                    "dir": list(line["dir"]),  # dirección (cos, sin)
                    "wmode": line.get("wmode", 0),
                    "spans": [],
                }
                for span in line["spans"]:
                    span_info = {
                        "text": span["text"],
                        "bbox": list(span["bbox"]),
                        "origin": list(span.get("origin", [span["bbox"][0], span["bbox"][3]])),
                        "font": span["font"],
                        "size": span["size"],
                        "flags": span["flags"],
                        "color_hex": color_int_to_hex(span.get("color")),
                        "ascender": span.get("ascender"),
                        "descender": span.get("descender"),
                    }
                    line_info["spans"].append(span_info)
                block_info["lines"].append(line_info)
            page_info["blocks"].append(block_info)
        pages_data.append(page_info)
    return pages_data


def extract_images(doc):
    """Extrae cada imagen como PNG y guarda su bbox/transformación."""
    images_data = []
    for page_index, page in enumerate(doc):
        page_entry = {"page": page_index + 1, "images": []}
        infos = page.get_image_info(xrefs=True)
        for img_index, info in enumerate(infos):
            xref = info.get("xref", 0)
            bbox = info.get("bbox")
            transform = info.get("transform")
            if xref:
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n - pix.alpha >= 4:  # CMYK -> RGB
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    name = f"p{page_index+1:02d}_i{img_index+1:02d}.png"
                    pix.save(str(IMG_DIR / name))
                    pix = None
                except Exception as e:
                    name = None
                    print(f"  ! no se pudo guardar imagen p{page_index+1} #{img_index+1}: {e}")
            else:
                name = None
            page_entry["images"].append({
                "index": img_index,
                "xref": xref,
                "file": name,
                "bbox": list(bbox) if bbox else None,
                "transform": list(transform) if transform else None,
                "width": info.get("width"),
                "height": info.get("height"),
                "colorspace": info.get("colorspace"),
                "bpc": info.get("bpc"),
            })
        images_data.append(page_entry)
    return images_data


def build_background_pdf(src_pdf, dst_pdf):
    """Genera un PDF basado en el original con todo el texto borrado (queda fondo + imágenes + vectores)."""
    doc = fitz.open(src_pdf)
    for page in doc:
        # add_redact_annot + apply_redactions elimina texto preservando todo lo demás
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    rect = fitz.Rect(span["bbox"])
                    if rect.is_empty:
                        continue
                    ann = page.add_redact_annot(rect)
                    ann.set_colors(fill=None)
                    ann.update()
        # images=0 -> ignora imágenes; graphics=0 -> ignora gráficos; text=0 -> elimina texto en el área
        page.apply_redactions(images=0, graphics=0, text=0)
    doc.save(dst_pdf, garbage=4, deflate=True)
    doc.close()


def _pick_font(flags):
    """Mapea los flags PyMuPDF a una de las fuentes Helvetica integradas."""
    bold = bool(flags & 16)
    italic = bool(flags & 2)
    if bold and italic:
        return "helv-bo"
    if bold:
        return "hebo"
    if italic:
        return "heit"
    return "helv"


def _draw_vector(page, d):
    """Re-dibuja un drawing extraído del original sobre una página nueva."""
    shape = page.new_shape()
    for item in d["items"]:
        op = item[0]
        if op == "l":
            shape.draw_line(item[1], item[2])
        elif op == "re":
            shape.draw_rect(item[1])
        elif op == "qu":
            shape.draw_quad(item[1])
        elif op == "c":
            shape.draw_bezier(item[1], item[2], item[3], item[4])
        elif op == "n":  # close path
            pass
    fill = d.get("fill")
    stroke = d.get("color")
    width = d.get("width") or 1
    even_odd = d.get("even_odd", False)
    closePath = d.get("closePath", True)
    try:
        shape.finish(color=stroke, fill=fill, width=width, even_odd=even_odd, closePath=closePath)
    except Exception:
        shape.finish(color=stroke, fill=fill, width=width)
    shape.commit()


def build_preview_pdf(src_pdf_path, text_data, images_data, dst_pdf, page_sizes):
    """Genera un PDF en blanco con los vectores, imágenes y texto extraídos en su posición original."""
    src = fitz.open(src_pdf_path)
    out = fitz.open()
    for page_idx, ps in enumerate(page_sizes):
        page = out.new_page(width=ps[0], height=ps[1])
        # 1) Dibujos vectoriales (cajas, líneas, etc.)
        for d in src[page_idx].get_drawings():
            try:
                _draw_vector(page, d)
            except Exception as e:
                pass
        # 2) Imágenes
        for img in images_data[page_idx]["images"]:
            if not img["file"] or not img["bbox"]:
                continue
            rect = fitz.Rect(img["bbox"])
            try:
                page.insert_image(rect, filename=str(IMG_DIR / img["file"]))
            except Exception as e:
                print(f"  ! no pude insertar imagen {img['file']}: {e}")
        # 3) Texto span por span en su posición exacta
        for block in text_data[page_idx]["blocks"]:
            for line in block["lines"]:
                for span in line["spans"]:
                    if not span["text"].strip():
                        continue
                    bbox = fitz.Rect(span["bbox"])
                    color = (0, 0, 0)
                    if span["color_hex"]:
                        c = int(span["color_hex"][1:], 16)
                        color = ((c >> 16) & 0xFF) / 255, ((c >> 8) & 0xFF) / 255, (c & 0xFF) / 255
                    origin = span["origin"]
                    fontname = _pick_font(span["flags"])
                    try:
                        page.insert_text(
                            fitz.Point(origin[0], origin[1]),
                            span["text"],
                            fontsize=span["size"],
                            color=color,
                            fontname=fontname,
                            render_mode=0,
                        )
                    except Exception:
                        page.insert_textbox(bbox, span["text"], fontsize=span["size"], color=color, fontname=fontname)
    src.close()
    out.save(dst_pdf, garbage=4, deflate=True)
    out.close()


def main():
    print(f"Abriendo: {PDF_PATH.name}")
    doc = fitz.open(PDF_PATH)
    page_sizes = [(p.rect.width, p.rect.height) for p in doc]

    print("Extrayendo texto...")
    text_data = extract_text(doc)
    (OUT / "extracted_text.json").write_text(json.dumps(text_data, indent=2, ensure_ascii=False))

    print("Extrayendo imágenes...")
    images_data = extract_images(doc)
    (OUT / "extracted_images.json").write_text(json.dumps(images_data, indent=2, ensure_ascii=False))

    doc.close()

    print("Construyendo background_only.pdf (sin texto)...")
    build_background_pdf(str(PDF_PATH), str(OUT / "background_only.pdf"))

    print("Construyendo extracted_preview.pdf (texto + imágenes sobre blanco)...")
    build_preview_pdf(str(PDF_PATH), text_data, images_data, str(OUT / "extracted_preview.pdf"), page_sizes)

    # Resumen
    n_text_spans = sum(
        len(s["spans"]) for p in text_data for b in p["blocks"] for s in b["lines"]
    )
    n_images = sum(len(p["images"]) for p in images_data)
    print()
    print("=== Resumen extracción ===")
    print(f"Páginas: {len(page_sizes)}")
    print(f"Spans de texto: {n_text_spans}")
    print(f"Imágenes: {n_images}")
    print(f"Salida en: {OUT}")


if __name__ == "__main__":
    main()
