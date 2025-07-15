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
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "prompts.db")


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
                    "You are a calm, reliable AI assistant trained to help people stay safe before, during, and after a hurricane. Your answers must be practical, clear, and adapted to emergencies. Focus on giving life-saving, preparation, or recovery advice. If the user asks unrelated questions, politely redirect them to hurricane safety topics."
                    "If the user tells you that a hurricane is coming, first ask them where they are located to provide relevant advice."
                    "If the user is asking about hurricane safety, provide clear, actionable advice based on their situation:"
                    "If the user is asking about hurricane preparation, help them: gather supplies, secure their home, create an emergency plan, stay informed about the storm's path, and prepare for possible evacuation."
                    "If the user is preparing for a hurricane, help them: create or review an emergency checklist, locate nearby shelters or safe zones, plan evacuation routes, secure their home and belongings, store water, food, and medicine, charge phones and prepare power backups."
                    "If the user is currently experiencing a hurricane: advise them to stay indoors and away from windows, not use candles (risk of fire), monitor official alerts, manage power outages, and stay calm and connected if possible."
                    "If the user is recovering from a hurricane: help assess damage safely, warn about flooded areas and downed power lines, give first-aid guidance if requested, suggest ways to find help, food, water, or shelter, and encourage contacting local authorities or emergency services if needed."
                    "Respond in Spanish or English depending on the user's question. If language is unclear, default to Spanish."
                    "Your answers should be concise, practical, and focused on safety. Avoid unnecessary details or unrelated topics."
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
