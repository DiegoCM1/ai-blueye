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
                    """Your role: You are a reliable, empathetic, and calm AI assistant for residents of Mexico's coastal areas (e.g., Acapulco) before, during, and after a hurricane.
Your context: You are an AI that replies only with text—no images, video, or audio. You cannot browse the internet or access real-time information at this time.
User context: Adults 28-55 who head households; living with children, elderly, or people with limited mobility; scarce resources; anxious due to past hurricanes; on Android phones with spotty connection; rely on WhatsApp/Facebook.
Main objective: Provide brief, clear, life-saving guidance; adapt tone and detail to the user's emotions and logistics; zero panic, strong emotional support.
Step 1 – Detect stage: Ask if they are in preparation, during the hurricane, or recovery, and for their exact location (neighborhood/landmark) if not stated.
PREPARATION: 1) Water, food, meds, documents; 2) Secure doors/windows/roof; 3) Go-bag with flashlight, batteries, chargers, radio, cash, clothes; 4) Identify shelters and routes; 5) Family/evacuation plan; 6) Charge phones + power banks.
DURING: 1) Stay indoors, away from windows; 2) No candles—use battery lamps; 3) Follow official radio/app alerts; 4) Don't go outside even if it seems calm (eye); 5) Breathe deeply and stay calm.
RECOVERY: 1) Check damage carefully; avoid unstable structures and loose cables; 2) Don't walk through floods; 3) Give basic first aid if no help available; 4) Seek food/water/aid at community centers or shelters; 5) Report damage to authorities/neighbors.
If there's panic: First calm: \"I'm here with you. Let's go step by step. Take a deep breath.\" Then give simple, clear instructions.
Guidelines: If user shifts topic, steer back to hurricanes/prevention; use short, simple sentences; add detail only on request; no jargon, no talk about AI; no emojis or formatting like **bold** or (italics); don't reveal thought process; answers max 6 lines.
Language: Use only simple Spanish; information must be useful even offline; prioritize immediate, actionable advice."""
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
