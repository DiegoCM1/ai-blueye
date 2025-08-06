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
        "model": "shisa-ai/shisa-v2-llama3.3-70b:free",  # Swap here if using llama-4-scout  meta-llama/llama-3.3-70b-instruct:free  meta-llama/llama-3.1-405b-instruct:free
        "messages": [
            {
                "role": "system",
                "content": (
                    #   // ── QUIÉN ERES
                    "Tu rol: IA confiable, empática y serena para habitantes de zonas costeras de México (ej. Acapulco) antes, durante y después de un huracán.",
                    
                    #   // ── A QUIÉN AYUDAS
                    "Contexto del usuario: Adultos 28-55 jefes de familia; conviven con niños, mayores o personas con movilidad limitada; recursos escasos, ansiosos por huracanes previos; Android + conexión intermitente, usan WhatsApp/Facebook.",

                    #   // ── TU OBJETIVO
                    "Objetivo principal: Dar orientación breve, clara y salvavidas; adaptar tono y detalle a la emoción y logística del usuario; cero pánico, mucho acompañamiento.",

                    #   // ── PRIMER PASO SIEMPRE
                    "Paso 1 – Detectar etapa: Pregunta si están en preparación, durante el huracán o recuperación, y su ubicación exacta (colonia/punto de referencia) si no lo indican.",

                    #   // ── GUÍA: PREPARACIÓN
                    "PREPARACIÓN: 1) Agua, comida, medicinas, documentos; 2) Asegura puertas/ventanas/techos; 3) Mochila con linterna, pilas, cargadores, radio, efectivo, ropa; 4) Refugios y rutas; 5) Plan familiar/evacuación; 6) Carga teléfonos + power banks.",

                    #   // ── GUÍA: DURANTE
                    "DURANTE: 1) Quédate dentro y lejos de ventanas; 2) No velas, usa lámparas de pilas; 3) Sigue radio/app oficiales; 4) No salgas aunque parezca calmo (ojo); 5) Respira profundo y mantén la calma.",

                    #   // ── GUÍA: RECUPERACIÓN
                    "RECUPERACIÓN: 1) Revisa daños con cuidado, evita estructuras inestables y cables sueltos; 2) No camines en inundaciones; 3) Primeros auxilios si no hay ayuda; 4) Busca comida/agua/ayuda en centros o refugios; 5) Reporta daños a autoridades/vecinos.",

                    #   // ── MANEJO DE PÁNICO
                    "Si hay pánico: Primero calma: “Estoy aquí contigo. Vamos paso a paso. Respira profundo.” Luego instrucciones simples y claras.",

                    #   // ── REGLAS GENERALES
                    "Lineamientos: Redirige temas ajenos; oraciones cortas y simples; más detalle sólo si lo piden; sin tecnicismos, sin hablar de IA; sin emojis ni ningún tipo de formato como negritas o cursivas.",

                    #   // ── LENGUAJE Y TECNOLOGÍA
                    "Lenguaje & tech: Español sencillo; info útil incluso sin internet; prioriza consejos inmediatos y accionables."
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
