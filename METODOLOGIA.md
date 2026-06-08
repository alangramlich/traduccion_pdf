# Metodología de traducción con fidelidad visual y de contenido

Documento que describe la metodología y los pasos seguidos para traducir al
español el documento original
`3T-Quick-Start-for-cleaning-CP_IFU_16-XX-XX_Q_USA_001.pdf` (instrucciones de
inicio rápido del Sistema Calentador-Enfriador 3T) **manteniendo la fidelidad**
tanto del contenido como de la apariencia del PDF original.

El documento es un instructivo médico/técnico (IFU), por lo que la fidelidad no
es opcional: cada paso, número, advertencia (NOTA) y referencia de página debe
conservarse exactamente, y la disposición visual (imágenes, diagramas, flechas,
numeración de pasos) debe quedar intacta para no romper la correspondencia
entre texto e ilustración.

---

## Principio rector

> **No se "rehace" el documento: se reemplaza únicamente la capa de texto,
> dejando intacto todo lo demás (fondo, imágenes, vectores, diagramas).**

Esto garantiza que la traducción sea un *calco* del original: el lector ve la
misma página, con las mismas figuras en el mismo lugar, pero el texto en
español.

---

## Pipeline de 6 pasos

Los scripts están en `scripts/` y se ejecutan en orden. Cada uno produce
artefactos verificables en `output/`.

### Paso 1 — Extracción fiel del original (`01_extract.py`)

Se usa **PyMuPDF (fitz)** para descomponer el PDF en sus capas:

- **Texto con todos sus atributos** → `extracted_text.json`
  Por cada *span* de texto se guarda: el texto exacto (incluidos tabuladores y
  espacios), la posición (`bbox` y `origin`/línea base), la fuente, el tamaño,
  el color (hex), los *flags* (negrita/cursiva), la rotación de la línea
  (vector `dir`) y los `ascender`/`descender`. Esta granularidad es la que
  permite recolocar la traducción **en el mismo punto y con el mismo estilo**.

- **Imágenes** → `output/images/*.png` + `extracted_images.json`
  Cada imagen se rasteriza y se guarda con su `bbox` y su matriz de
  transformación. Las imágenes **no se traducen ni se alteran**.

- **Fondo sin texto** → `background_only.pdf`
  Se parte del PDF original y se eliminan **solo los spans de texto** mediante
  *redacciones* (`add_redact_annot` + `apply_redactions` con
  `images=0, graphics=0`). El resultado conserva el fondo, las imágenes, las
  flechas y todos los vectores **exactamente como estaban**. Este archivo es el
  lienzo sobre el que luego se escribe el español.

- **Vista de verificación** → `extracted_preview.pdf`
  Reconstrucción del original (vectores + imágenes + texto extraído) sobre
  páginas en blanco, para confirmar que la extracción capturó todo en su lugar.

### Paso 2 — Volcado de texto legible (`02_text_dump.py`)

Genera `extracted_text.txt`, una versión plana y legible del texto extraído
(marcando **negrita** y _cursiva_), usada para revisar el contenido a traducir
y detectar partido de palabras, subíndices, etc.

### Paso 3 — Comparación de la extracción (`03_compare.py`)

Genera `comparacion_3col.pdf`: tres columnas lado a lado
**Original | Sin texto | Reconstruido**, página por página. Permite verificar
visualmente que el fondo quedó limpio y que nada de la maquetación se perdió
antes de traducir.

### Paso 4 — Traducción vía API de Gemini (`04_translate_gemini.py`)

La traducción del texto se hace con una **llamada a la API de Gemini**
(`gemini-2.5-flash`) configurada con **`temperature = 0`** para obtener una
salida casi determinista. El resultado se **cachea** en
`output/translations.json` (mapa *texto exacto del span → español*).

- **Reproducibilidad.** Las corridas siguientes solo piden a la API las
  entradas que faltan en el caché; el PDF se reconstruye **offline e idéntico**
  sin volver a llamar a la API. El caché versionado en el repo es la fuente de
  verdad. `temperature = 0` reduce mucho la variabilidad, pero la API no
  garantiza salidas idénticas bit a bit entre versiones del modelo: la garantía
  fuerte la da el caché (modelo fijado + JSON versionado). Con `--refresh` se
  retraduce todo vía Gemini.
- **Qué no se traduce.** Spans vacíos y los que son solo números/códigos/
  separadores (`2.1`, `CP_IFU_16-XX-XX...`, `I 3 I`) se dejan **literales**. Las
  marcas y números de parte (Bacillol, Clorox, `75-510-218`...) se piden al
  modelo como "mantener sin cambios" mediante la *system instruction*.
- **Espacio en blanco.** El espacio inicial/final (incluidos tabuladores) de
  cada span se **re-aplica en código**, sin depender de que el modelo lo
  respete, para no romper la alineación.
- **Sin clave configurada** (`GEMINI_API_KEY` / `GOOGLE_API_KEY`), el script no
  falla: conserva el caché existente para que el resto del pipeline siga
  funcionando.

Salida: `output/translations.json`.

### Paso 5 — Armado del PDF final (`05_build_translated_pdf.py`)

Es el corazón del armado. Lee el caché `translations.json` y, sobre
`background_only.pdf`, escribe cada traducción respetando estas reglas de
fidelidad:

1. **Posición idéntica.** Cada traducción se inserta en el `origin` (línea
   base) del span original, no en un flujo nuevo: el texto queda donde estaba.

2. **Estilo idéntico.** Se conserva el color y se mapean negrita/cursiva a la
   variante correspondiente de la fuente (Helvetica integrada, siempre
   disponible). Los spans que en el original se renderizan en versalitas/
   mayúsculas (subsecciones `A.1)`, `B.1)`… y "Required material") se pasan a
   mayúsculas con `.upper()` para mantener la apariencia.

3. **Rotación respetada.** Si la línea original estaba rotada (vector `dir`
   vertical), la traducción se escribe con la misma rotación (90°/270°/180°),
   por ejemplo los encabezados laterales.

4. **Ajuste para no desbordar ni pisar.** El español suele ser más largo que el
   inglés. Si la traducción no entra en el ancho disponible, se **reduce el
   tamaño de fuente progresivamente** (95 %, 90 %… hasta 70 %) hasta que entre.
   El "ancho disponible" no es el margen de página sino el **inicio del
   siguiente span de la misma línea** o el borde de un **obstáculo** (flechas,
   pequeños dibujos con relleno), calculado por solapamiento vertical. Así la
   traducción no invade celdas vecinas ni se monta sobre diagramas.

5. **Trazabilidad.** El script reporta los spans **sin traducción** (que se
   dejan en inglés en vez de inventar) y los que requirieron **reducción
   extrema** (>30 %), para revisión manual.

Salida: `translated.pdf`.

### Paso 6 — Comparación final (`06_compare_translated.py`)

Genera `comparacion_traducido.pdf`: tres columnas
**Original (inglés) | Sin texto | Traducido (español)**, página por página.
Es la verificación visual final de que cada elemento gráfico permanece en su
sitio y de que el texto en español ocupa el lugar del inglés sin desbordes ni
solapamientos.

---

## Resumen de los mecanismos de fidelidad

| Aspecto | Cómo se preserva |
|---|---|
| **Imágenes / diagramas / flechas** | Nunca se tocan: se reutiliza `background_only.pdf`, que solo borró texto |
| **Maquetación / posición del texto** | Cada traducción se escribe en el `origin` exacto del span original |
| **Tipografía (negrita, cursiva, mayúsculas)** | Mapeo de *flags* a fuentes; `.upper()` para versalitas |
| **Color y tamaño** | Se copian del span original; el tamaño solo baja si es necesario para que entre |
| **Rotación** | Se reaplica la rotación de la línea original |
| **Contenido técnico (números, códigos, partes)** | Se conservan literales; no se traducen (regex de descarte + instrucción al modelo) |
| **Terminología médica** | Traducción vía API de Gemini (`temperature = 0`) con *system instruction* de IFU; cacheada en `translations.json` |
| **Reproducibilidad** | `temperature = 0` + caché versionado (`translations.json`): el PDF se reconstruye offline e idéntico sin re-llamar a la API |
| **No invadir vecinos / figuras** | Ancho disponible limitado por el siguiente span u obstáculos detectados |
| **Verificación** | PDFs comparativos de 3 columnas (extracción y traducción) + reporte de spans sin traducir o muy reducidos |

---

## Artefactos generados (`output/`)

- `extracted_text.json` / `extracted_text.txt` — texto extraído con atributos / legible
- `extracted_images.json` + `images/*.png` — imágenes extraídas con su posición
- `background_only.pdf` — original sin texto (lienzo base)
- `extracted_preview.pdf` — reconstrucción de control
- `translations.json` — **caché de traducciones** (Gemini, `temperature = 0`)
- `translated.pdf` — **PDF final en español**
- `comparacion_3col.pdf` — control de la extracción (orig | sin texto | reconstruido)
- `comparacion_traducido.pdf` — control final (orig | sin texto | traducido)

## Cómo reproducir

```bash
pip install pymupdf
export GEMINI_API_KEY="tu_clave"   # opcional: si falta, se usa el caché versionado

python scripts/01_extract.py
python scripts/02_text_dump.py
python scripts/03_compare.py
python scripts/04_translate_gemini.py        # Gemini temp 0 -> output/translations.json
python scripts/05_build_translated_pdf.py    # arma translated.pdf desde el caché
python scripts/06_compare_translated.py
python scripts/07_build_notebook.py          # opcional: regenera el notebook de control
```

> El caché `output/translations.json` ya está versionado, por lo que los pasos
> 5–7 funcionan **sin clave de API**. Para regenerar las traducciones desde
> cero con Gemini, configurá `GEMINI_API_KEY` y ejecutá
> `python scripts/04_translate_gemini.py --refresh`.
