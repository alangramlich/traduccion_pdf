#!/usr/bin/env python3
"""
Paso 2 - Traduccion con Gemini (una sola llamada).

Lee output/extracted_text.json y manda TODOS los textos extraidos a la API de
Gemini en UNA UNICA llamada. Gemini devuelve un arreglo JSON con la traduccion
de cada segmento, alineadas por su "id". Guarda el resultado en
output/translated_text.json.

Variables de entorno:
  GEMINI_API_KEY   (obligatoria)  clave de la API de Gemini
  GEMINI_MODEL     (opcional)     modelo a usar (default: gemini-2.5-flash)
  TARGET_LANG      (opcional)     idioma destino (default: Spanish)
  SOURCE_LANG      (opcional)     idioma origen (default: English)
"""
import json
import os
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "output")
IN_JSON = os.path.join(OUT_DIR, "extracted_text.json")
OUT_JSON = os.path.join(OUT_DIR, "translated_text.json")

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
TARGET_LANG = os.environ.get("TARGET_LANG", "Spanish")
SOURCE_LANG = os.environ.get("SOURCE_LANG", "English")

ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
)


def translate_all(segments):
    """Traduce TODOS los segmentos en una sola llamada a Gemini.

    Devuelve un dict {id: traduccion}. Reintenta ante errores transitorios.
    """
    items = [{"id": s["id"], "text": s["text"]} for s in segments]
    prompt = (
        f"Translate each item from {SOURCE_LANG} to {TARGET_LANG}. "
        "The content is from a medical device cleaning instructions (IFU) document. "
        "Preserve line breaks (\\n), numbers, units and product codes exactly. "
        "You receive a JSON array of objects with fields 'id' and 'text'. "
        "Return ONLY a JSON array of objects with fields 'id' and 'translation', "
        "one per input item, keeping the same 'id' values. Do not add any extra "
        "text outside the JSON.\n\n"
        "INPUT:\n"
        f"{json.dumps(items, ensure_ascii=False)}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": API_KEY}

    delay = 2
    last_err = None
    for attempt in range(5):
        try:
            r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=300)
            if r.status_code == 200:
                data = r.json()
                cand = data["candidates"][0]
                parts = cand["content"]["parts"]
                raw = "".join(p.get("text", "") for p in parts).strip()
                arr = json.loads(raw)
                return {int(o["id"]): o["translation"] for o in arr}
            if r.status_code in (429, 500, 502, 503, 504):
                print(f"  HTTP {r.status_code}, reintento en {delay}s...")
                time.sleep(delay)
                delay *= 2
                continue
            raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")
        except (requests.RequestException, ValueError, KeyError) as e:
            last_err = e
            print(f"  Error ({e}); reintento en {delay}s...")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"No se pudo traducir tras varios reintentos: {last_err}")


def main():
    if not API_KEY:
        sys.exit("Falta GEMINI_API_KEY en el entorno.")
    if not os.path.exists(IN_JSON):
        sys.exit(f"No existe {IN_JSON}. Ejecuta primero 01_extract_text.py")

    with open(IN_JSON, encoding="utf-8") as f:
        data = json.load(f)
    segments = data["segments"]

    print(f"Enviando {len(segments)} segmentos a Gemini en una sola llamada...")
    translations = translate_all(segments)

    # Avisar si falto alguna traduccion
    faltantes = [s["id"] for s in segments if s["id"] not in translations]
    if faltantes:
        print(f"ADVERTENCIA: {len(faltantes)} segmentos sin traduccion: {faltantes}")

    out_segments = [
        dict(s, translated=translations.get(s["id"], "")) for s in segments
    ]
    out = dict(data, target_lang=TARGET_LANG, model=MODEL, segments=out_segments)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    traducidos = sum(1 for s in out_segments if s["translated"])
    print(f"Listo. {traducidos}/{len(segments)} traducidos -> {OUT_JSON}")


if __name__ == "__main__":
    main()
