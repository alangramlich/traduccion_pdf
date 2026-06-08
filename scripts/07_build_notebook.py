"""Construye el notebook de documentación (notebooks/proceso_traduccion.ipynb).

El notebook explica la metodología y muestra UNA página de cada PDF generado,
incluyendo los PDFs de control. Se ejecuta al final con nbconvert para que las
imágenes queden incrustadas.
"""
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
NB_DIR.mkdir(exist_ok=True)
NB_PATH = NB_DIR / "proceso_traduccion.ipynb"

nb = new_notebook()
cells = []

cells.append(new_markdown_cell(
    "# Traducción del IFU 3T (inglés → español) con fidelidad visual\n"
    "\n"
    "Este notebook documenta **la metodología y los pasos** seguidos para traducir al\n"
    "español el instructivo `3T-Quick-Start-for-cleaning-CP_IFU_16-XX-XX_Q_USA_001.pdf`\n"
    "(Sistema Calentador-Enfriador 3T) **manteniendo la fidelidad** del contenido y de\n"
    "la apariencia del original, y muestra **una página de cada PDF generado**, incluidos\n"
    "los PDFs de control.\n"
))

cells.append(new_markdown_cell(
    "## Cómo se hace la traducción\n"
    "\n"
    "- La traducción del texto se hace con una **llamada a la API de Gemini**\n"
    "  (`gemini-2.5-flash`) con **`temperature = 0`** para una salida casi determinista.\n"
    "- El resultado se **cachea** en `output/translations.json` (mapa *texto exacto del\n"
    "  span → español*). Las corridas siguientes solo piden a la API lo que falte en el\n"
    "  caché, de modo que el PDF se reconstruye **offline y de forma reproducible** sin\n"
    "  volver a llamar a la API. El caché versionado en el repo es la fuente de verdad.\n"
    "- Los números de paso, códigos, marcas y números de parte (`2.1`,\n"
    "  `CP_IFU_16-XX-XX...`, `75-510-218`, `Clorox`) se conservan **literales**, y el\n"
    "  espacio en blanco inicial/final de cada span se re-aplica en código para no\n"
    "  depender de que el modelo lo respete.\n"
    "\n"
    "> **Reproducibilidad:** `temperature = 0` reduce mucho la variabilidad, pero la API\n"
    "> no garantiza salidas idénticas bit a bit entre versiones del modelo. La garantía\n"
    "> fuerte la da el **caché** (modelo fijado + JSON versionado).\n"
    "\n"
    "## Principio rector de fidelidad\n"
    "\n"
    "> **No se rehace el documento: se reemplaza únicamente la capa de texto, dejando\n"
    "> intacto todo lo demás (fondo, imágenes, vectores, diagramas, flechas).**\n"
    "\n"
    "## Pipeline\n"
    "\n"
    "| Paso | Script | Salida principal |\n"
    "|---|---|---|\n"
    "| 1. Extracción fiel (texto + imágenes + fondo sin texto) | `01_extract.py` | `background_only.pdf`, `extracted_preview.pdf`, `extracted_text.json` |\n"
    "| 2. Volcado de texto legible | `02_text_dump.py` | `extracted_text.txt` |\n"
    "| 3. Control de la extracción (3 columnas) | `03_compare.py` | `comparacion_3col.pdf` |\n"
    "| 4. Traducción vía API de Gemini (temp 0) → caché | `04_translate_gemini.py` | `translations.json` |\n"
    "| 5. Armado del PDF final (lee el caché) | `05_build_translated_pdf.py` | `translated.pdf` |\n"
    "| 6. Control de la traducción (3 columnas) | `06_compare_translated.py` | `comparacion_traducido.pdf` |\n"
    "\n"
    "Mecanismos de fidelidad aplicados al reescribir el texto: misma posición (`origin`),\n"
    "mismo color/tamaño, negrita/cursiva y versalitas, rotación de la línea, y\n"
    "**auto-reducción del tamaño** si el español no entra, limitada por el siguiente\n"
    "span u obstáculos (flechas) para no pisar figuras ni celdas vecinas.\n"
))

# --- Código: helper de render ---
cells.append(new_code_cell(
    "import fitz  # PyMuPDF\n"
    "from pathlib import Path\n"
    "from IPython.display import Image, display, Markdown\n"
    "\n"
    "ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n"
    "OUT = ROOT / 'output'\n"
    "ORIG = ROOT / '3T-Quick-Start-for-cleaning-CP_IFU_16-XX-XX_Q_USA_001.pdf'\n"
    "\n"
    "def mostrar_pagina(pdf_path, page_index=0, dpi=110, titulo=None):\n"
    "    \"\"\"Renderiza una página de un PDF a PNG y la muestra incrustada.\"\"\"\n"
    "    pdf_path = Path(pdf_path)\n"
    "    if titulo:\n"
    "        display(Markdown(f'### {titulo}'))\n"
    "    display(Markdown(f'`{pdf_path.name}` — página {page_index + 1}'))\n"
    "    doc = fitz.open(pdf_path)\n"
    "    pix = doc[page_index].get_pixmap(dpi=dpi)\n"
    "    png = pix.tobytes('png')\n"
    "    doc.close()\n"
    "    display(Image(data=png))\n"
))

cells.append(new_markdown_cell(
    "## 0) Original (inglés)\n"
    "Punto de partida: el PDF tal cual fue recibido."
))
cells.append(new_code_cell("mostrar_pagina(ORIG, 0, titulo='Original')"))

cells.append(new_markdown_cell(
    "## 1) `background_only.pdf` — fondo sin texto\n"
    "Se eliminó **solo el texto** por redacción; imágenes, vectores y flechas quedan\n"
    "intactos. Es el lienzo sobre el que se escribe el español."
))
cells.append(new_code_cell("mostrar_pagina(OUT / 'background_only.pdf', 0, titulo='Fondo sin texto')"))

cells.append(new_markdown_cell(
    "## 2) `extracted_preview.pdf` — reconstrucción de control\n"
    "Vectores + imágenes + texto extraído recolocados sobre páginas en blanco, para\n"
    "verificar que la extracción capturó todo en su lugar **(PDF de control)**."
))
cells.append(new_code_cell("mostrar_pagina(OUT / 'extracted_preview.pdf', 0, titulo='Reconstrucción (control)')"))

cells.append(new_markdown_cell(
    "## 3) `comparacion_3col.pdf` — control de la extracción **(PDF de control)**\n"
    "Tres columnas: **Original | Sin texto | Reconstruido**. Confirma que el fondo quedó\n"
    "limpio y que la maquetación no se perdió antes de traducir."
))
cells.append(new_code_cell("mostrar_pagina(OUT / 'comparacion_3col.pdf', 0, titulo='Comparación de extracción (control)')"))

cells.append(new_markdown_cell(
    "## 4) `translated.pdf` — PDF final en español\n"
    "El texto en español escrito sobre el fondo, en la posición y estilo del original."
))
cells.append(new_code_cell("mostrar_pagina(OUT / 'translated.pdf', 0, titulo='Traducido (final)')"))

cells.append(new_markdown_cell(
    "## 5) `comparacion_traducido.pdf` — control de la traducción **(PDF de control)**\n"
    "Tres columnas: **Original (inglés) | Sin texto | Traducido (español)**. Verificación\n"
    "final de que cada elemento gráfico permanece en su sitio y el texto en español ocupa\n"
    "el lugar del inglés sin desbordes ni solapamientos."
))
cells.append(new_code_cell("mostrar_pagina(OUT / 'comparacion_traducido.pdf', 0, titulo='Comparación de traducción (control)')"))

cells.append(new_markdown_cell(
    "## Artefactos generados (`output/`)\n"
    "\n"
    "- `extracted_text.json` / `extracted_text.txt` — texto extraído con atributos / legible\n"
    "- `extracted_images.json` + `images/*.png` — imágenes extraídas con su posición\n"
    "- `background_only.pdf` — original sin texto (lienzo base)\n"
    "- `extracted_preview.pdf` — reconstrucción de control\n"
    "- `translated.pdf` — **PDF final en español**\n"
    "- `comparacion_3col.pdf` — control de la extracción\n"
    "- `comparacion_traducido.pdf` — control final\n"
))

nb["cells"] = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbf.write(nb, NB_PATH)
print(f"Notebook escrito en {NB_PATH}")
