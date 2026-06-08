"""
Paso 4: traducción del texto con la API de Gemini (temperature = 0).

Diseño orientado a REPRODUCIBILIDAD:
  - Se recolectan los textos ÚNICOS de los spans extraídos (output/extracted_text.json).
  - Se traduce cada texto con Gemini usando temperature = 0 (salida casi determinista).
  - El resultado se cachea en output/translations.json (mapa texto_exacto -> español).
  - En corridas siguientes solo se piden a la API las entradas que faltan en el caché,
    de modo que el PDF puede reconstruirse OFFLINE y de forma idéntica sin volver a
    llamar a la API. El caché versionado en el repo es la fuente de verdad reproducible.

Notas de fidelidad:
  - No se traducen spans vacíos ni los que son solo números/códigos/separadores
    (p. ej. "2.1", "CP_IFU_16-XX-XX...", "I 3 I"): se dejan literales.
  - El espacio en blanco inicial/final (incluidos tabuladores) se preserva exactamente
    re-aplicándolo en código, sin depender de que el modelo lo respete.
  - Marcas comerciales y números de parte (Bacillol, Clorox, 75-510-218...) se piden
    como "mantener sin cambios" en el prompt.

Uso:
    export GEMINI_API_KEY="..."          # o GOOGLE_API_KEY
    python scripts/04_translate_gemini.py            # solo traduce lo que falta en el caché
    python scripts/04_translate_gemini.py --refresh  # retraduce TODO vía Gemini

Si no hay API key, el script no falla: deja el caché como está (para que el resto del
pipeline siga funcionando con las traducciones ya cacheadas) e indica cómo configurarla.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
TEXT_JSON = OUT / "extracted_text.json"
CACHE = OUT / "translations.json"

MODEL = "gemini-2.5-flash"
TEMPERATURE = 0
BATCH_SIZE = 60
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

# Spans que NO se traducen (se dejan literales): vacíos o solo números/códigos/separadores.
SKIP_RE = re.compile(r"^[\d\.\-_ \t\|/IV]+$")

SYSTEM_INSTRUCTION = (
    "Eres un traductor técnico médico. Traduces del inglés al español de España neutro "
    "el texto de un instructivo de uso (IFU) de un equipo médico (Sistema "
    "Calentador-Enfriador 3T). Reglas estrictas:\n"
    "1. Devuelve SOLO la traducción de cada fragmento, sin explicaciones.\n"
    "2. Mantén sin cambios: números, unidades, códigos, números de parte, nombres de "
    "productos y marcas (p. ej. Bacillol, CaviWipe, Clorox, Puristeril, Peresal, "
    "Minncare, Aquasafe, Pall, SORIN, 75-510-218, CP_IFU_16-XX-XX...), fórmulas "
    "químicas (H2O2) y letras/numeración de secciones (A.1, C.2, D.10).\n"
    "3. Usa terminología médica coherente (p. ej. cardioplegia, peróxido de hidrógeno, "
    "circuitos de agua, cortocircuito, desinfección).\n"
    "4. No agregues ni quites puntuación ni mayúsculas que cambien el sentido.\n"
    "5. Conserva el registro de instrucción imperativa cuando el original lo use."
)


def need_translation(text: str) -> bool:
    core = text.strip()
    if not core:
        return False
    if SKIP_RE.match(text):
        return False
    return True


def collect_unique_cores(text_data):
    """Devuelve el conjunto de 'núcleos' (texto sin ws inicial/final) a traducir."""
    cores = {}
    for page in text_data:
        for block in page["blocks"]:
            for line in block["lines"]:
                for span in line["spans"]:
                    t = span["text"]
                    if need_translation(t):
                        cores.setdefault(t.strip(), None)
    return list(cores.keys())


def gemini_translate_batch(cores, api_key):
    """Traduce una lista de núcleos. Devuelve {core: traduccion}."""
    indexed = {str(i): c for i, c in enumerate(cores)}
    prompt = (
        "Traduce al español cada valor del siguiente objeto JSON. "
        "Devuelve EXCLUSIVAMENTE un objeto JSON con las MISMAS claves y, como valor, "
        "la traducción de cada texto. No incluyas nada fuera del JSON.\n\n"
        + json.dumps(indexed, ensure_ascii=False)
    )
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": TEMPERATURE,
            "responseMimeType": "application/json",
        },
    }
    url = ENDPOINT.format(model=MODEL, key=api_key)
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            out = json.loads(text)
            return {indexed[k]: v for k, v in out.items() if k in indexed}
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as e:
            last_err = e
            wait = 2 ** (attempt + 1)
            print(f"  ! intento {attempt+1} falló ({e}); reintento en {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Gemini falló tras 4 intentos: {last_err}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="retraduce TODO vía Gemini, ignorando el caché existente")
    args = ap.parse_args()

    text_data = json.loads(TEXT_JSON.read_text())
    cores = collect_unique_cores(text_data)

    cache = {"model": MODEL, "temperature": TEMPERATURE,
             "source_lang": "en", "target_lang": "es",
             "translations": {}, "size_specific": {}}
    if CACHE.exists():
        cache.update(json.loads(CACHE.read_text()))
    translations = cache.get("translations", {})

    # Reconstruir el mapa core -> traduccion a partir del caché por-span existente.
    core_cache = {}
    for src, tr in translations.items():
        core_cache[src.strip()] = tr.strip()

    if args.refresh:
        pending = list(cores)
    else:
        pending = [c for c in cores if c not in core_cache]

    print(f"Núcleos únicos a traducir: {len(cores)} | pendientes: {len(pending)}")

    if pending:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("\n[!] No hay GEMINI_API_KEY / GOOGLE_API_KEY en el entorno.")
            print("    Se conserva el caché actual (output/translations.json) sin cambios.")
            print("    Configura la clave y reejecuta para traducir vía Gemini:")
            print('        export GEMINI_API_KEY="tu_clave"')
            print("        python scripts/04_translate_gemini.py")
            return
        print(f"Llamando a Gemini ({MODEL}, temperature={TEMPERATURE})...")
        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending[i:i + BATCH_SIZE]
            print(f"  lote {i//BATCH_SIZE + 1}: {len(batch)} fragmentos")
            result = gemini_translate_batch(batch, api_key)
            for core in batch:
                if core in result:
                    core_cache[core] = result[core].strip()
                else:
                    print(f"  [SIN RESPUESTA] {core!r}")

    # Volcar el caché por-span exacto: clave = texto exacto del span (con ws),
    # valor = ws_izq + traduccion_del_nucleo + ws_der  (ws preservado en código).
    new_translations = {}
    for page in text_data:
        for block in page["blocks"]:
            for line in block["lines"]:
                for span in line["spans"]:
                    t = span["text"]
                    if not need_translation(t):
                        continue
                    core = t.strip()
                    tr = core_cache.get(core)
                    if tr is None:
                        continue
                    left = t[:len(t) - len(t.lstrip())]
                    right = t[len(t.rstrip()):]
                    new_translations[t] = f"{left}{tr}{right}"

    # Conservar entradas previas no recalculadas (p. ej. ws-only intencionales).
    translations.update(new_translations)
    cache["translations"] = translations
    cache["model"] = MODEL
    cache["temperature"] = TEMPERATURE
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
    print(f"\nCaché escrito: {CACHE}  ({len(translations)} entradas por-span)")


if __name__ == "__main__":
    main()
