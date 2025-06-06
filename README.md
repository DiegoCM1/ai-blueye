# 🧠 Portfolio AI Assistant – Backend

This is the backend of an AI-powered assistant built with **FastAPI** and integrated with **OpenRouter's free-tier LLMs** like Mistral 7B, LLaMA 3.3, and LLaMA 4 Scout.  
It serves as a personalized assistant that can answer questions about Luis’s skills, projects, and career.

---

## 🚀 Technologies Used

| Tool / Library       | Purpose                                                                 |
|----------------------|-------------------------------------------------------------------------|
| **Python**           | Main backend language                                                   |
| **FastAPI**          | API framework                                                           |
| **Uvicorn**          | ASGI server to run the FastAPI app                                      |
| **httpx**            | HTTP client for calling external APIs (like OpenRouter)                 |
| **pydantic**         | Data validation and request parsing                                     |
| **python-dotenv**    | Load secret API keys from `.env` files                                  |
| **OpenRouter API**   | Used to connect to LLMs like Mistral, LLaMA 3.3, and LLaMA 4 Scout      |

---

## 🛠️ Project Setup (Development)

### 🔧 Initial Setup

 1. Clone the repo
git clone https://github.com/DiegoCM1/portfolio-ai-assistant.git
cd portfolio-ai-assistant

 2. Create and activate virtual environment
python -m venv venv
source venv/Scripts/activate   Linux/macOS: source venv/bin/activate

 3. Install dependencies
pip install fastapi uvicorn httpx python-dotenv

### ⚙️ Daily Usage

- Activate virtual environment
source venv/Scripts/activate

- Run the FastAPI backend
uvicorn main:app --reload
🧪 Test endpoint: http://127.0.0.1:8000/

📘 Swagger UI: http://127.0.0.1:8000/docs

📕 ReDoc UI: http://127.0.0.1:8000/redoc


## 🤖 AI Models Supported
These are the free-tier LLMs integrated into the backend:

### 🧠 Mistral 7B Instruct (Free)
https://openrouter.ai/mistralai/mistral-7b-instruct:free
→ Fast, reliable for general-purpose Q&A

### 🦙 LLaMA 3.3 8B Instruct (Free)
https://openrouter.ai/meta-llama/llama-3.3-8b-instruct:free
→ Better for longer context, multilingual-friendly


### 🚀 LLaMA 4 Scout (Free)
https://openrouter.ai/meta-llama/llama-4-scout:free
→ Supports multimodal input, Mixture-of-Experts, powerful next-gen model


## 🔐 .env File
Create a .env file in the root directory with your OpenRouter API key:
 OPENROUTER_API_KEY=your_openrouter_key_here
Don’t forget to add .env to your .gitignore to keep it safe.


## 🧪 Example curl Test
curl -X POST http://127.0.0.1:8000/ask \
-H "Content-Type: application/json" \
-d "{\"question\": \"¿Quién es Luis?\"}"


## 📦 Deployment (Coming Soon)
This backend can be deployed for free using platforms like:

- Render
- Railway
- Fly.io


## Next steps include Docker setup, frontend integration (Next.js), and production deployment.

## 💡 About the Creator
This project was built by Luis, a bilingual full-stack developer and AI builder.
He co-founded Verskod and COMS, won Meta's Llama Impact Grant ($100K) for his BluEye project,
and regularly participates in hackathons, conferences, and social-impact innovation.


## 📌 TODOs (Project Roadmap)
 Add error handling for bad API responses

 Add logging (file or database)

 Add authentication for the AI endpoint

 Integrate with Next.js frontend

 Deploy on Render or Railway
