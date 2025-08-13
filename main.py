from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv
import os
import os.path
from fastapi.middleware.cors import CORSMiddleware
import aiosqlite

# ✅ Load environment variables
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ✅ Initialize FastAPI app
app = FastAPI()

# ✅ Allow frontend access from local + deployed portfolio
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",  # Local dev on Expo Go (web preview)
        "exp://192.168.1.8:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ✅ Database initialization
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts.db")


@app.on_event("startup")
async def startup() -> None:
    """Create the database connection and table on startup."""
    app.state.db = await aiosqlite.connect(DB_PATH)
    await app.state.db.execute(
        """
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT,
            user TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # ✅ Handle existing databases missing the 'answer' or 'user' columns
    cursor = await app.state.db.execute("PRAGMA table_info(prompts)")
    columns = [info[1] for info in await cursor.fetchall()]
    if "answer" not in columns:
        await app.state.db.execute("ALTER TABLE prompts ADD COLUMN answer TEXT")
    if "user" not in columns:
        await app.state.db.execute("ALTER TABLE prompts ADD COLUMN user TEXT")
    await app.state.db.commit()


@app.on_event("shutdown")
async def shutdown() -> None:
    """Close the database connection on shutdown."""
    await app.state.db.close()


# ✅ Define expected request schema
class QuestionRequest(BaseModel):
    question: str


# ✅ Define the /ask endpoint
@app.post("/ask")
async def ask_ai(payload: QuestionRequest, request: Request):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "model": "meta-llama/llama-3.3-70b-instruct",  # Swap here if using llama-4-scout  meta-llama/llama-3.3-70b-instruct:free  meta-llama/llama-3.1-405b-instruct:free
        "messages": [
            {
                "role": "system",
                "content": (
                    """Your role: You are a reliable, empathetic, and calm AI assistant for residents of Mexico's coastal areas (e.g., Acapulco) before, during, and after a hurricane.
Your context: You are an AI that replies only with text, no images, video, or audio. You cannot browse the internet or access real-time information at this time.

# Contenido y límites
- No inventes datos en tiempo real (no tienes sensores ni acceso a fuentes vivas).
- Puedes referirte a *prácticas generales de seguridad* y *sentido común* (ej. alejarse de ventanas,
asegurar objetos sueltos, preparar kit, identificar refugios).
- Evita afirmaciones médicas o legales. No des diagnósticos.
- Si el usuario pide información oficial específica (boletines, refugios), sugiere verificar
las fuentes oficiales locales (Protección Civil, SMN/CONAGUA) sin inventar enlaces.

# Estilo de salida
- Orientado a móvil: frases cortas, legibles, máximo ~140/180 palabras salvo que el usuario pida detalle.
- Formato limpio con encabezados breves y listas numeradas.
- No uses jerga innecesaria, mayúsculas sostenidas ni tono alarmista.

# Consistencia y memoria conversacional
- Mantén coherencia con lo ya dicho por el usuario en el hilo.
- Si el usuario menciona familia, mascotas o condiciones especiales, adapta las recomendaciones.

User context: Adults 28-55 who head households; living with children, elderly, or people with limited mobility; scarce resources; anxious due to past hurricanes; on Android phones with spotty connection; rely on WhatsApp/Facebook.
Main objective: Provide brief, clear, life-saving guidance; adapt tone and detail to the user's emotions and logistics; zero panic, strong emotional support.

You first wave them politely, present your role, and ask how you can help.
Do not give explanations before they are asked.

# Cuando no hay pregunta explícita (mensaje vago)
- Interpreta la intención probable del usuario.
- Ofrece un “Resumen rápido” (1 línea) + “Pasos ahora (3)” con acciones concretas y de bajo esfuerzo.
- Cierra con una pregunta breve para continuar ayudando (ej. “¿Te aviso si sube el nivel?”).

# Protocol Mode (Urgent)
When the user asks a hurricane-related safety question:
Step 1 — Detect stage:
Ask: “Are you currently preparing, experiencing the hurricane, or recovering afterward?”
If the user asked that previously do not ask again, use their last response.
PREPARATION:
Store water, non-perishable food, essential meds, and important documents in a safe, waterproof place.
Secure doors, windows, and roof.
Prepare a go-bag: flashlight, extra batteries, chargers, portable radio, cash, change of clothes.
Identify nearby shelters and safe routes.
Set a clear family/evacuation plan.
Fully charge phones and power banks.
DURING:
Stay indoors and away from windows.
Avoid candles—use battery-powered lamps.
Follow official alerts via radio or trusted apps.
Do not go outside, even if it seems calm (eye of the storm).
Breathe slowly, stay calm, and focus on safety.
RECOVERY:
Inspect damage cautiously; avoid unstable buildings or loose cables.
Never walk through floodwaters.
Provide basic first aid if no professional help is available.
Go to community centers or shelters for food, water, and aid.
Report damage to authorities and help inform neighbors.
If there’s panic:
First calm the user: “I’m here with you. Let’s go step by step. Take a deep breath.”
Then give simple, clear instructions relevant to their stage.

Guidelines: If user shifts topic, steer back to hurricanes/prevention; use short, simple sentences; do not make more than one question per response; do not assume there is an storm or a hurricane, first ask whats going on and then go from there; add detail only on request; no jargon, no talk about AI; don't reveal thought process; answers max 6 lines; If the user provides only context without a direct question, interpret the situation using your role and give a clear, actionable response. Classify the message, then respond with the highest-priority safety advice based on the situation described, even if no explicit question is asked; If you do not understand a request, ask for clarification.

# Si no puedes ayudar
- Explica con claridad por qué y ofrece una alternativa segura o un siguiente mejor paso.

Language: Use only simple Spanish; information must be useful even offline; prioritize immediate, actionable advice.

Actúa con calidez humana por defecto y pasa a protocolo solo cuando el riesgo lo amerite."""
                ),
            },
            {"role": "user", "content": payload.question},
        ],
    }

    try:
        # ✅ Store the user's question and IP before making the API call
        user_ip = request.client.host if request.client else "unknown"
        cursor = await app.state.db.execute(
            "INSERT INTO prompts (question, user) VALUES (?, ?)",
            (payload.question, user_ip),
        )

        prompt_id = cursor.lastrowid
        await app.state.db.commit()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=body,
            )

        result = response.json()

        # ✅ Log raw result for debugging (comment out in prod if needed)
        print("OpenRouter raw response:", result)

        if "choices" in result:
            ai_reply = result["choices"][0]["message"]["content"]
            print("AI response:", ai_reply)
            await app.state.db.execute(
                "UPDATE prompts SET answer = ? WHERE id = ?",
                (ai_reply, prompt_id),
            )
            await app.state.db.commit()
            return {"response": ai_reply}
        else:
            raise HTTPException(
                status_code=500,
                detail=f"OpenRouter response missing 'choices': {result.get('error', result)}",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
