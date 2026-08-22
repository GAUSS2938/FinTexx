# FinTex — AI Financial Companion & Autonomous Inbuilt Mentor

A full-stack, production-ready AI Financial Companion for college students and young adults (aligned with **UN SDG 8.10 - Financial Inclusion & Literacy** and **SDG 4.4 - Skills for Decent Work**).

FinTex combines **Phone SMS Auto-Sync** (reading transaction notifications without manual typing), an **unbreakable 5-page SPA** (*Overview*, *Expenses*, *Budget*, *Goals*, *Mentor*), and an **Inbuilt AI Financial Mentor** capable of executing website tasks upon conversational prompts.

---

## 🌟 Key Capabilities

1. **🔐 Login & Phone SMS Permission Consent**:
   - Phone sign-in (+91) with explicit permission consent for background SMS transaction sync.
2. **📱 Background Phone SMS Auto-Sync**:
   - Continuously ingests incoming UPI / bank SMS transaction alerts (Swiggy, Uber, Blinkit, Amazon, Spotify, etc.) and categorizes spending automatically without manual entry.
3. **📊 5 Dedicated SPA Pages (Zero Breaking Views)**:
   - **Overview**: Financial health metric strip, primary goal progress ring, latest auto-synced transactions, proactive AI insights, action checklist.
   - **Expenses**: Live transaction ledger with instant category filter pills (`Food`, `Travel`, `Shopping`, `Subscriptions`, `Education`, `Other`) and real-time search.
   - **Budget**: **50/30/20 Rule Visualizer** + Category Budget Caps with real-time caution and danger threshold meters.
   - **Goals**: Multi-goal cards with circular SVG progress rings and an **Interactive Math Pacing Simulator**.
   - **Mentor**: Full-screen Inbuilt AI Financial Mentor chatbot console.
4. **🤖 Autonomous Inbuilt AI Mentor**:
   - Answers open-ended financial literacy questions (compounding, credit building, emergency buffers, affordability analysis).
   - Executes live website mutations on prompt:
     - *"Add task: Review Swiggy budget by Sunday"* ➔ Inserts task to live checklist.
     - *"Set food budget cap to 4200"* ➔ Updates category cap and re-renders progress bars.
     - *"Update my monthly income to 20000"* ➔ Recalculates flexible room and updates all metric cards.
     - *"Update laptop goal to 48000 in 6 months"* ➔ Re-evaluates mathematical pacing.

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10+
- Dependencies: `fastapi`, `uvicorn`, `pydantic`, `httpx`

### 2. Installation
```bash
pip install -r requirements.txt
```

### 3. Running the Server
```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```
- **Web App UI**: [http://localhost:8000/](http://localhost:8000/)
- **Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Running Automated Tests
```bash
python test_backend.py
python test_openai_mentor.py
```

---

## 🏗️ Architecture & Technology Stack

- **Backend**: FastAPI, SQLite3, Pydantic v2, Python 3.12
- **Frontend**: Vanilla JavaScript SPA, HTML5, CSS3 (Replit Dark Slate & Sea Blue Design System)
- **AI Engine**: Multi-Layered Natural Language Understanding (NLU) with OpenAI Tool/Function Calling compatibility
- **Compliance**: Aligned with UN Sustainable Development Goals (SDG 8.10 & 4.4)
