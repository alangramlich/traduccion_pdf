#!/usr/bin/env python3
"""
Paso 2 - Traduccion con Gemini.

Lee output/extracted_text.json y manda CADA texto extraido a la API de Gemini
para traducirlo. Guarda las traducciones en output/translated_text.json.

Es reanudable: si vuelve a ejecutarse, omite los segmentos ya traducidos
presentes en el archivo de salida (cache).

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


def translate_text(text):
    """Traduce un fragmento con Gemini. Reintenta ante errores transitorios."""
    prompt = (
        f"Translate the following text from {SOURCE_LANG} to {TARGET_LANG}. "
        "This is content from a medical device cleaning instructions (IFU) document. "
        "Preserve line breaks, numbers, units and product codes exactly. "
        "Return ONLY the translation, with no quotes, comments or extra text.\n\n"
        f"{text}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": API_KEY}

    delay = 2
    for attempt in range(5):
        try:
            r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                data = r.json()
                cand = data["candidates"][0]
                parts = cand["content"]["parts"]
                return "".join(p.get("text", "") for p in parts).strip()
            # 429 / 5xx -> reintentar
            if r.status_code in (429, 500, 502, 503, 504):
                print(f"  HTTP {r.status_code}, reintento en {delay}s...")
                time.sleep(delay)
                delay *= 2
                continue
            raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")
        except requests.RequestException as e:
            print(f"  Error de red: {e}; reintento en {delay}s...")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("No se pudo traducir tras varios reintentos")


def main():
    if not API_KEY:
        sys.exit("Falta GEMINI_API_KEY en el entorno.")
    if not os.path.exists(IN_JSON):
        sys.exit(f"No existe {IN_JSON}. Ejecuta primero 01_extract_text.py")

    with open(IN_JSON, encoding="utf-8") as f:
        data = json.load(f)
    segments = data["segments"]

    # Cache de traducciones previas (reanudable)
    translations = {}
    if os.path.exists(OUT_JSON):
        with open(OUT_JSON, encoding="utf-8") as f:
            prev = json.load(f)
        for seg in prev.get("segments", []):
            if seg.get("translated"):
                translations[seg["id"]] = seg["translated"]
        print(f"Cache: {len(translations)} traducciones ya existentes.")

    total = len(segments)
    for i, seg in enumerate(segments, 1):
        if seg["id"] in translations:
            continue
        preview = seg["text"][:50].replace("\n", " ")
        print(f"[{i}/{total}] traduciendo id={seg['id']}: {preview!r}")
        translations[seg["id"]] = translate_text(seg["text"])

        # Guardado incremental para no perder progreso
        out_segments = [dict(s, translated=translations.get(s["id"], "")) for s in segments]
        out = dict(data, target_lang=TARGET_LANG, model=MODEL, segments=out_segments)
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Listo. Traducciones guardadas en {OUT_JSON}")


if __name__ == "__main__":
    main()
