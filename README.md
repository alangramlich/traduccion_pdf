# Traducción del PDF (IFU)

Tres scripts encadenados para traducir el PDF original conservando su diseño.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
# 1) Extraer todo el texto del PDF -> output/extracted_text.json
python3 scripts/01_extract_text.py

# 2) Traducir cada segmento con Gemini -> output/translated_text.json
export GEMINI_API_KEY="tu_clave"
python3 scripts/02_translate.py

# 3) Recolocar el texto traducido en su posición original -> output/translated.pdf
python3 scripts/03_rebuild_pdf.py
```

## Detalle de cada paso

1. **`01_extract_text.py`** — Recorre el PDF con PyMuPDF y extrae el texto a
   nivel de bloque, guardando posición (`bbox`), página y estilo (tamaño,
   color, fuente) de cada segmento.
2. **`02_translate.py`** — Envía **todos** los textos extraídos a la API de Gemini
   en **una sola llamada** (como arreglo JSON) y guarda las traducciones alineadas
   por `id`.
3. **`03_rebuild_pdf.py`** — Tapa el texto original y escribe la traducción en
   la misma posición, ajustando el tamaño de fuente para que entre en el espacio.

## Variables de entorno

| Variable          | Default                | Descripción                       |
|-------------------|------------------------|-----------------------------------|
| `GEMINI_API_KEY`  | —                      | Clave de la API de Gemini (req.)  |
| `GEMINI_MODEL`    | `gemini-2.5-flash`     | Modelo de Gemini a usar           |
| `TARGET_LANG`     | `Spanish`              | Idioma destino                    |
| `SOURCE_LANG`     | `English`              | Idioma origen                     |
| `SRC_PDF`         | PDF del repo           | Ruta del PDF de entrada           |
