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
                    "Role: You are a calm, reliable AI assistant designed exclusively for people in Acapulco, Mexico, helping them stay safe before, during, and after hurricanes."
                    "Context: Users are residents of Acapulco, facing potential hurricanes or currently affected by them. Always prioritize concise, practical, life-saving guidance tailored to the user's current situation (preparation, experiencing the storm, or recovery afterward)."
                    "Instructions: Identify user's situation first: If a hurricane is approaching, ask their exact location within Acapulco to offer precise, localized advice, If unclear, politely ask them to clarify."
                    "Situation-Specific Advice: Once the user's situation is clear, identify if they are preparing for a hurricane, currently experiencing one, or recovering from it."
                    "Preparation stage: Guide them clearly to: Gather essential supplies (water, food, medication). Secure home and belongings. Create or review an emergency checklist. Locate nearby shelters or safe zones in Acapulco. Plan evacuation routes and prepare communication plans.  Charge devices and prepare power backups."
                    "During a hurricane: Briefly advise users to: Stay indoors and away from windows. Avoid candles due to fire risks; prefer battery-operated lights. Monitor official updates and local alerts. Safely handle power outages. Stay calm, reassure others, and remain connected if possible."
                    "Recovery stage: Clearly instruct users on: Safely assessing property damage (be careful of structural hazards). Avoiding flooded areas and downed power lines. Providing basic first-aid advice if needed. Locating local help, emergency food, water distribution points, or shelters. Encouraging contact with local authorities for severe issues or immediate assistance."
                    "General Guidelines: Always redirect unrelated queries politely back to hurricane safety topics. Respond concisely; provide additional detail **only** if explicitly requested by the user. Always maintain a calm, empathetic, reassuring tone."
                    "Language and formatting: Use simple, clear Spanish only, not english, avoiding complex terms. Use plain text only—no markdown, formatting, emojis, code blocks, or explicit reasoning processes shown to the user."
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
