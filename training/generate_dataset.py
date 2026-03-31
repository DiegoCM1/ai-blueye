import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────
API_KEY        = os.getenv("OPENROUTER_API_KEY")
MODEL          = "deepseek/deepseek-v3.2"   # swap this one line to change models
CHUNKS_DIR     = Path("training/chunks/gemini")
OUTPUT_FILE    = Path("training/dataset.jsonl")
TARGET_PAIRS   = 200
PAIRS_PER_CHUNK = "entre 1 y 3 según la riqueza del contenido"   # model decides based on content depth
# ─────────────────────────────────────────────────────────────────────────────

# BluEye system prompt — this goes into every training example so the model
# learns to answer *as BluEye*, not as a generic assistant
BLUEYE_SYSTEM_PROMPT = """Eres BluEye, un asistente de supervivencia offline para huracanes que sirve a residentes de México.
FORMATO: Máximo 80 palabras. Oraciones cortas. Puntos o listas para pasos.

REGLAS:
1. Responde siempre en español sencillo. Sin inglés.
2. Mantén la calma y tranquiliza, pero nunca minimices el peligro real.
3. Estás completamente offline. No menciones sitios web, números de teléfono ni datos en tiempo real. Nunca asumas resultados sobre personas, lugares o estado de seguridad. Si te preguntan por información en tiempo real, indica al usuario que consulte la radio local o las autoridades.
4. Prioriza la seguridad inmediata primero, luego los siguientes pasos prácticos."""

# Generation prompt — instructs the teacher model how to create Q&A pairs
# from each chunk. The teacher never sees BluEye's system prompt; it just
# produces raw question/answer content that we then wrap in the chat format.
GENERATION_SYSTEM_PROMPT = """Eres un experto en generación de datasets de entrenamiento para modelos de lenguaje.
Tu tarea es leer fragmentos de documentos oficiales mexicanos sobre preparación ante desastres y generar preguntas y respuestas realistas.

REGLAS:
1. Las preguntas deben sonar como mensajes reales que mandaría una persona en México durante una emergencia — alguien asustado, con familia, en una zona costera o de inundaciones. Usa situaciones concretas: "el río se está desbordando", "mi mamá no puede caminar", "ya se fue la luz", "estamos en el techo". No preguntas académicas.
2. Las respuestas deben basarse ÚNICAMENTE en el texto del fragmento. No inventes información.
3. Las respuestas deben sonar como un vecino preparado que ayuda en crisis — directo y claro, pero humano. En situaciones de riesgo activo, reconoce brevemente la situación antes de dar instrucciones ("Mantén la calma, esto es lo que debes hacer:"). Nunca frío ni robótico.
4. Las respuestas deben tener máximo 80 palabras, en español sencillo, con listas o puntos cuando corresponda.
5. No menciones el nombre del documento fuente en las respuestas.
6. Devuelve SOLO un JSON válido, sin texto adicional, sin markdown, sin explicaciones.

FORMATO DE SALIDA — devuelve exactamente esto:
[
  {"question": "...", "answer": "..."},
  {"question": "...", "answer": "..."}
]"""


def load_all_chunks(chunks_dir: Path) -> list[dict]:
    """Load and flatten all chunks from every JSON file in the folder."""
    all_chunks = []
    for filepath in chunks_dir.iterdir():
        if filepath.suffix.lower() == ".json":
            data = json.loads(filepath.read_text())
            for chunk in data:
                # attach the source filename so we can trace pairs back to their chunk
                chunk["_source_file"] = filepath.name
            all_chunks.extend(data)
    print(f"Loaded {len(all_chunks)} chunks from {chunks_dir}")
    return all_chunks


def generate_pairs(chunk: dict) -> list[dict]:
    """
    Send one chunk to the teacher model and get back Q&A pairs.
    Returns a list of dicts with 'question' and 'answer' keys.
    """
    user_message = f"""Genera {PAIRS_PER_CHUNK} pares de pregunta-respuesta basándote en este fragmento:

CATEGORÍA: {chunk['category']}
RESUMEN: {chunk['summary']}

TEXTO:
{chunk['text']}"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            "temperature": 0.7,   # some creativity in question phrasing, not too wild
        },
        timeout=60,
    )
    response.raise_for_status()

    raw = response.json()["choices"][0]["message"]["content"].strip()

    # Strip markdown code fences if the model wraps the JSON in them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw)


def format_as_training_example(question: str, answer: str) -> dict:
    """
    Wrap a Q&A pair in the Llama 3.2 chat template format.
    Every example includes the BluEye system prompt so the model learns
    to answer *as BluEye* in context, not just answer generically.
    """
    return {
        "messages": [
            {"role": "system",    "content": BLUEYE_SYSTEM_PROMPT},
            {"role": "user",      "content": question},
            {"role": "assistant", "content": answer},
        ]
    }


def main():
    chunks = load_all_chunks(CHUNKS_DIR)
    pairs  = []

    for i, chunk in enumerate(chunks):
        if len(pairs) >= TARGET_PAIRS:
            break

        print(f"[{i+1}/{len(chunks)}] Generating pairs for chunk {chunk['chunk_id']} "
              f"({chunk['category']}) — {len(pairs)}/{TARGET_PAIRS} pairs so far")

        try:
            raw_pairs = generate_pairs(chunk)

            for pair in raw_pairs:
                if len(pairs) >= TARGET_PAIRS:
                    break
                pairs.append(format_as_training_example(pair["question"], pair["answer"]))

        except Exception as e:
            # Don't crash the whole run on one bad chunk — log and keep going
            print(f"  ⚠ Skipped chunk {chunk['chunk_id']}: {e}")

        # Polite delay to avoid rate limit errors
        time.sleep(0.5)

    # Append to existing file — never overwrite previous batches
    # Each run adds new lines; the full file is the cumulative dataset
    with OUTPUT_FILE.open("a", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
    print(f"\nDone. {len(pairs)} new pairs appended to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
