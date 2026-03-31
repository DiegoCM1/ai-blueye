# BluEye — Offline Hurricane Survival AI: Training Roadmap

## Project Context

BluEye is an offline hurricane survival assistant for residents of Mexico. It runs natively on mobile devices (phones) with no internet connection during emergencies. The goal is to fine-tune two small language models — **Llama 3.2 1B Instruct** and **Llama 3.2 3B Instruct** (both fp16) — so they can provide concise, accurate, life-saving advice in simple Spanish when a user is in the middle of a hurricane with limited battery and no connectivity.

There is also a separate **online model** (Llama 4 Maverick cloud-based, more powerful) that will have internet access and tool-calling capabilities. Some of the training data generated for the offline models will be reused for the online model with a different system prompt.

## Why Synthetic Data

We are generating a synthetic dataset because:
- The source material is raw PDF documents (official hurricane preparedness guides). These are not in a Q&A format suitable for training.
- A strong "teacher" model (Gemini 3.1 Pro) will convert the PDF content into high-quality question-answer pairs that mimic real user interactions during a hurricane.
- Synthetic data generation from authoritative sources is standard industry practice (used by Meta, Microsoft, Google for training smaller models).
- The operator (the person building this) is **not a domain expert** in hurricane preparedness. This means every generated answer must be strictly traceable to the source PDF text — no hallucinated facts, no invented procedures.

## Key Technical Decisions

### Dataset
- **Format:** JSONL (JSON Lines) — one JSON object per line
- **Size:** 200 pairs (sufficient for a narrow-domain fine-tune on 1B/3B models for a demo; can scale to 500 later)
- **System prompt:** Included in every row (training must mirror inference structure)
- **Labels/metadata:** Extra fields (id, category, use, tool_usage) added to each row for filtering. These do NOT affect training — training libraries only read the `messages` field.

### JSONL Row Structure
```json
{
  "id": "001",
  "category": "evacuation",
  "use": "both",
  "tool_usage": false,
  "messages": [
    {"role": "system", "content": "[BluEye offline system prompt]"},
    {"role": "user", "content": "[Panicked user question in Spanish]"},
    {"role": "assistant", "content": "[Short, actionable survival response in Spanish]"}
  ]
}
```

### Label Definitions (FIXED — must use only these values)

**Categories** (adjust based on actual PDF content — this is a starter list):
```python
VALID_CATEGORIES = [
    "pre_storm_preparation",
    "evacuation",
    "shelter_in_place",
    "during_storm_safety",
    "water_and_food",
    "medical_emergency",
    "post_storm_assessment",
    "infrastructure_damage",
    "communication",
    "landslide_risk",
    "flooding",
    "electrical_safety",
    "general_knowledge"
]
```

**Category Creation**
If a chunk overlaps two categories, the teacher model will generate confused pairs that don't cleanly
  belong to either. When you check dataset balance later, a chunk tagged flooding +                 
during_storm_safety won't count cleanly toward either bucket.

When content genuinely overlaps, apply this rule: assign the most specific category. Flooding during
a storm → flooding, not during_storm_safety. Electrical hazard after the storm → electrical_safety,
not post_storm_assessment.

**Use** (which dataset this pair belongs to):
```python
VALID_USE = ["offline", "online", "both"]
```

**Tool usage** (for future augmentation with tool-calling examples):
```python
VALID_TOOL_USAGE = [False, True]
```

### System Prompt (Offline Models)
The system prompt for the 1B/3B models must be short (60–150 words, 4–6 clear rules). Small models have limited instruction-following capacity and we need to reserve context window space for conversation. The actual hurricane knowledge comes from fine-tuning, not from the system prompt. The system prompt only defines behavior: language, tone, format, and hard boundaries.

Three candidate prompts were drafted for A/B testing. The winning prompt should be selected by testing all three against a strong model with the same set of panicked user questions, then evaluating: correct language (Spanish), conciseness (under 80–100 words), refusal to fabricate live data, and practical usefulness.

**Candidate Prompt A — "The Minimalist":**
```
You are BluEye, an offline emergency assistant for hurricane situations in Mexico.

RULES:
1. Respond ONLY in simple, clear Spanish.
2. Keep every response under 80 words. Use short sentences.
3. You have no internet access. Never invent weather data, forecasts, or real-time information.
4. When the user is in immediate danger, give 3 actionable steps. Nothing else.
```

**Candidate Prompt B — "The Medic":**
```
You are BluEye, an offline hurricane survival assistant serving residents of Mexico.


RULES:
1. Always respond in simple Spanish. No English.
2. Be calm and reassuring but never minimize real danger.
3. Keep responses under 100 words. Prefer bullet points for action steps.
4. You are fully offline. Do not reference websites, phone numbers, or live data. If asked for real-time information, tell the user to check local radio or authorities.
5. Prioritize immediate safety first, then practical next steps.
```

**Candidate Prompt C — "The Structured Operator":**
```
You are BluEye, a calm and direct offline hurricane assistant for Mexico.

LANGUAGE: Respond only in simple, everyday Spanish.
FORMAT: Maximum 80 words. Short sentences. Bullet points for steps.

BEHAVIOR:
- If the user describes immediate danger: give 2-3 survival actions. No explanations unless asked.
- If the user asks a general preparedness question: give a concise, practical answer.
- Never invent real-time data. You are offline. If asked about current weather or alerts, say: "No tengo acceso a datos en tiempo real. Consulta tu radio local o autoridades."
```

**Candidate Prompt D — "The Medic in a hurry":**  Winning Prompt 🏆
```
You are BluEye, an offline hurricane survival assistant serving residents of Mexico.
FORMAT: Maximum 80 words. Short sentences. Bullet points for steps.

RULES:
1. Always respond in simple Spanish. No English.
2. Be calm and reassuring but never minimize real danger.
3. You are fully offline. Do not reference websites, phone numbers or live data. Never assume outcomes about people, locations, or safety status. If asked for real-time information, tell the user to check local radio or authorities.
4. Prioritize immediate safety first, then practical next steps.
```

### Teacher Model & Generation
- **Model:** Gemini 3.1 Pro Preview via OpenRouter API
- **Cost:** ~$2/M input tokens, ~$12/M output tokens (+ thinking tokens). Estimated total: $1–2 USD for 200 pairs.
- **Budget:** 100 MXN (~$5.50 USD) on OpenRouter — more than sufficient.

---

## Step-by-Step Pipeline

### Phase 1: Preparation

**Step 1 — Select the system prompt** ✅
- Test all three candidate prompts against a strong model (Gemini 3.1 Pro in AI Studio for free, or Claude/ChatGPT)
- Use the same 5–6 test questions for each, including at least one trap question asking for live weather data
- Pick the winner based on: correct Spanish, conciseness, no hallucinated data, practical tone
- Lock it in as a constant in the generation script

**Step 2 — Define final categories**
- Skim all PDFs (table of contents, section headers), remove PDFs that are not related to hurricanes.
  - Final List
    1. FASCCULO INUNDACIONES
    2. FASCICULO CICLONES TROPICALES
    3. FASCCULO TSUNAMIS (x2)
    4. FASCICULO INESTABILIDAD DE LADERAS
    5. FASCICULO TORMENTAS SEVERAS
    6. ELCLIMAENLAINESTABILIDADDELADERAS
    7. MANUAL SIAT CT 2019
- From remaining PDFs, Map every distinct topic to one of the fixed categories
- Adjust the VALID_CATEGORIES list based on what the PDFs actually cover
- Rule: one category per chunk. If a section covers two topics, split it.

**Step 3 — Extract and chunk PDFs**
- Use Python (PyMuPDF) to extract text from each PDF
- Split by section (using headers), NOT by arbitrary page/token count
- Each chunk should be a complete, coherent topic
- Assign one category to each chunk

### Phase 2: Dataset Generation

**Step 4 — Build the generation script**
- Python script that:
  - Reads each chunk + its assigned category
  - Constructs a generation prompt with: the winning system prompt, the PDF chunk, the category, strict instructions to only use information from the provided text
  - Calls Gemini 3.1 Pro via OpenRouter API
  - Parses the response into JSONL rows
  - Validates each row: correct JSON structure, category is in VALID_CATEGORIES, use is in VALID_USE, messages array has system/user/assistant roles
  - Writes validated rows to the output JSONL file

**Step 5 — Generation prompt (the instructions to the teacher model)**
- This is critical. Must include:
  - The BluEye system prompt (so the teacher follows it)
  - The PDF chunk as the only source of truth
  - Explicit instruction: "Only use information present in the provided text. Do not add, infer, or extrapolate any facts not explicitly stated."
  - The exact output JSON structure expected
  - The assigned category for this chunk
  - Request for 10–15 pairs per chunk

**Step 6 — Run generation**
- Execute the script across all chunks
- Target: 200 pairs total (~15–20 API calls)

### Phase 3: Review

**Step 7 — Review the dataset**
- Since the operator is NOT a domain expert, review by matching output to source:
  - Can every claim in the assistant response be found in the PDF chunk that was fed?
  - If a fact cannot be traced back to the source text, discard or rewrite that pair
- Also check for:
  - Language: Is it in simple Spanish?
  - Format: Is it under the word limit?
  - Tone: Does it sound calm and actionable?
  - Trap: Does it ever fabricate live weather data?
- Spot-check method: review 3–5 pairs per batch carefully, skim the rest for obvious issues

**Step 8 — Validate the final JSONL file**
- Run a validation script:
  - Every line is valid JSON
  - Every line has all three roles (system, user, assistant)
  - System prompt is identical across all 200 rows
  - All categories are in VALID_CATEGORIES
  - All use values are in VALID_USE
  - No duplicate IDs

### Phase 4: Training

**Step 9 — Train the models using LoRA**
- Fine-tune Llama 3.2 3B Instruct and Llama 3.2 1B Instruct using the validated JSONL dataset
- Recommended tools: Unsloth (2x faster for Llama on Mac/consumer GPUs) or Hugging Face TRL
- Hyperparameters to watch: learning rate, number of epochs, LoRA rank (if using LoRA/QLoRA)
- Establish a baseline first: test the raw base model with the system prompt before training to measure improvement after

**Step 10 — Merge adapters (if using LoRA)**
- Merge the LoRA adapter weights back into the base model

**Step 11 — Quantize for mobile deployment**
- Quantize the merged model (e.g., Q4_K_M via llama.cpp) for on-device inference
- Test the quantized model to ensure quality didn't degrade significantly

### Future Phase: Augmentation

**Step 12 — Tool usage dataset**
- Generate additional pairs that include tool-calling examples (weather API, emergency contacts)
- These will have `"tool_usage": true` in the metadata
- Used to train the online model

**Step 13 — Online model dataset**
- Filter existing pairs where `"use"` is `"online"` or `"both"`
- Swap the system prompt to the online version (longer, includes tool schemas and internet capabilities)
- Combine with tool-usage pairs
- Train the online model separately

---

## Important Warnings

1. **Catastrophic forgetting** is caused by learning rate, epoch count, and data diversity — not just dataset size. Monitor training loss carefully.
2. **KV-cache** means the system prompt is only fully processed on the first message, not every message. But keeping it short is still important for instruction-following capacity on small models.
3. **The generation prompt quality is as important as the system prompt quality.** If the generation instructions are vague, the teacher model will hallucinate.
4. **Since the operator is not a domain expert, the source-traceability constraint is non-negotiable.** Every assistant response must be verifiable against the source PDF chunk.