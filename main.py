from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware

# ✅ Load environment variables
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ✅ Initialize FastAPI app
app = FastAPI()

# ✅ Allow frontend access from local + deployed portfolio
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://192.168.1.8:1287",
        "https://diegocm2025-portfolio.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ✅ Define expected request schema
class QuestionRequest(BaseModel):
    question: str


# ✅ Define the /ask endpoint
@app.post("/ask")
async def ask_ai(request: QuestionRequest):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "model": "meta-llama/llama-3.3-8b-instruct:free",  # Swap here if using llama-4-scout
        "messages": [
            {
                "role": "system",
                "content": (
                    "You're an AI assistant trained to answer questions strictly about BluEye, an award-winning hurricane prevention app developed by Diego Colin and his team. BluEye uses real-time weather data, AI, and user location to provide personalized disaster prevention guidance before, during, and after a hurricane. The project won Meta's Llama Impact Grant ($100,000 USD) and was built with React Native and FastAPI."
                    "Your goal is to provide helpful, concise, and context-aware answers related to BluEye’s features, impact, purpose, technology, and use cases. You may include info about the founders, goals, and tech stack when relevant."
                    "BluEye features include: personalized weather alerts, a hurricane checklist, safe zones map, offline survival mode, and post-disaster reporting. It integrates with weather APIs and uses Llama 3.2 AI from OpenRouter for personalized insights."
                    "Only answer questions about BluEye, its team, or related topics. If the user asks unrelated questions, politely redirect the conversation to BluEye’s mission or technology."
                    "Use English or Spanish depending on the user's question. If unclear, default to Spanish."
                ),
            },
            {"role": "user", "content": request.question},
        ],
    }

    try:
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
            return {"response": ai_reply}
        else:
            raise HTTPException(
                status_code=500,
                detail=f"OpenRouter response missing 'choices': {result.get('error', result)}",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
