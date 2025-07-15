<div align="center">

# 🌀 BluEye AI Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Meta Grant](https://img.shields.io/badge/Meta_Grant-$100K-blue?style=for-the-badge)](https://github.com/DiegoCM1/ai-blueye)

An award-winning AI-powered hurricane safety assistant built with **FastAPI** and **OpenRouter's LLMs** 

[Features](#-features) • [Setup](#%EF%B8%8F-setup) • [API Reference](#-api-reference) • [Deployment](#-deployment)

</div>

---

## 🎯 Features

- 🌪️ **Real-time Hurricane Guidance**
  - Preparation checklists
  - Shelter locations
  - Evacuation planning
- 🗣️ **Bilingual Support**
  - English and Spanish
  - Emergency-optimized responses
- 🤖 **Advanced AI Models**
  - LLaMA 3.3 8B Instruct
  - LLaMA 4 Scout

## 🛠️ Technologies

| Tool             | Purpose                              |
|-----------------|--------------------------------------|
| **FastAPI**     | API framework                        |
| **Uvicorn**     | ASGI server                         |
| **OpenRouter**  | LLM provider                        |
| **Pydantic**    | Data validation                     |
| **Railway**     | Deployment platform                 |

## ⚙️ Setup

```bash
# Clone repository
git clone https://github.com/DiegoCM1/ai-blueye.git
cd ai-blueye

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows
# source venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration

```env
# Copy .env.example to .env and add your key
OPENROUTER_API_KEY=your_openrouter_key_here
```

### Development Server

```bash
uvicorn main:app --reload
```
- Local API: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## 🏆 Achievements

- Meta Llama Impact Hackathon Winner
- $100K Grant Recipient
  
## 🧪 API Testing

```bash
curl -X POST https://your-backend-url/ask \
-H "Content-Type: application/json" \
-d "{\"question\": \"¿Qué hacer si hay alerta de huracán?\"}"
```

### Running Tests

```bash
pytest
```

---

<div align="center">

**[📝 Documentation](https://github.com/DiegoCM1/ai-blueye/wiki)** • 
**[🐛 Issues](https://github.com/DiegoCM1/ai-blueye/issues)** •
**[📫 Contact](mailto:your-email@domain.com)**

Released under the [MIT License](LICENSE).

</div>







