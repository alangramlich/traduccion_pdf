# Traducción del IFU 3T (inglés → español) con fidelidad visual

Pipeline para traducir al español el instructivo
`3T-Quick-Start-for-cleaning-CP_IFU_16-XX-XX_Q_USA_001.pdf` **manteniendo la
apariencia del original**: solo se reemplaza la capa de texto; imágenes,
diagramas, flechas y vectores quedan intactos.

La traducción del texto se hace con la **API de Gemini** (`temperature = 0`) y
se **cachea** en `output/translations.json` para que el PDF se reconstruya de
forma **reproducible y offline**. Ver `METODOLOGIA.md` para el detalle.

## Requisitos

```bash
pip install -r requirements.txt
```

## Configurar la API key (no se sube a git)

```bash
cp .env.example .env
# editá .env y poné tu GEMINI_API_KEY (se obtiene en https://aistudio.google.com/apikey)
```

> `.env` está en `.gitignore`: tu clave **nunca** se sube a git. Solo se versiona
> `.env.example` como plantilla. El script `04_translate_gemini.py` carga el
> `.env` automáticamente.

## Correr el pipeline

```bash
python scripts/01_extract.py                 # extrae texto, imágenes y fondo sin texto
python scripts/02_text_dump.py               # vuelca texto legible (control)
python scripts/03_compare.py                 # PDF de control de la extracción
python scripts/04_translate_gemini.py --refresh   # traduce con Gemini -> output/translations.json
python scripts/05_build_translated_pdf.py    # arma output/translated.pdf desde el caché
python scripts/06_compare_translated.py      # PDF de control de la traducción
python scripts/07_build_notebook.py          # genera el notebook de documentación
jupyter nbconvert --to notebook --execute --inplace notebooks/proceso_traduccion.ipynb
```

- `04_translate_gemini.py` (sin `--refresh`) solo pide a la API lo que falte en
  el caché. Con `--refresh` retraduce **todo** vía Gemini.
- Si no hay `GEMINI_API_KEY`, el paso 4 no falla: usa el caché ya versionado, de
  modo que los pasos 5–7 funcionan igual.

## Resultado y artefactos (`output/`)

- `translated.pdf` — **PDF final en español**
- `translations.json` — caché de traducciones (Gemini, `temperature = 0`)
- `background_only.pdf` — original sin texto (lienzo base)
- `comparacion_3col.pdf` — control de la extracción
- `comparacion_traducido.pdf` — control de la traducción
- `notebooks/proceso_traduccion.ipynb` — documentación con una página de cada PDF

## Volver a subir a git

```bash
git add output/translations.json output/translated.pdf output/comparacion_traducido.pdf \
        notebooks/proceso_traduccion.ipynb
git commit -m "Traducciones regeneradas con Gemini"
git push origin claude/wizardly-planck-ep0l6b
```

> Trabajamos en la rama `claude/wizardly-planck-ep0l6b` (PR #1). El `.env` con la
> key queda fuera del commit por el `.gitignore`.
