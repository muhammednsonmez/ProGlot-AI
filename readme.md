# ProGlot AI: Adaptive Polyglot Tutor

**ProGlot AI** is a stateful, adaptive language learning assistant powered by Google's **Gemini 1.5 Flash**. 

Unlike generic chatbots, ProGlot utilizes a **Pure LLM Architecture** with **Role-Playing Prompt Engineering** to deliver a personalized pedagogical experience. It features persistent memory, context optimization, and robust error handling.

## Key Features

* **Dynamic Persona Injection:** The System Prompt is dynamically reconstructed based on the selected target language (Italian, German, Japanese, etc.), preventing "prompt drift."
* **Persistent State Management:** User sessions are serialized and stored in isolated JSON files (`history_It.json`, etc.), ensuring continuity across sessions.
* **Token Optimization (Sliding Window):** Implements a sliding window algorithm to manage the context window efficiently, processing only the most relevant recent interactions (`N=20`) to minimize latency and API costs.
* **Robust Error Handling:** Features "Graceful Degradation" for API outages and quota limits, including a manual export feature to Gemini Web.

## Tech Stack

* **Core:** Python 3.10+
* **LLM Engine:** Google Gemini 1.5 Flash (via `google-generativeai`)
* **Frontend:** Streamlit
* **State Persistence:** JSON-based local storage
* **Configuration:** Python-dotenv

## Installation & Setup

### 1. Clone the Repository
Clone or download this repository.

### 2. Set Up Virtual Environment
```bash
python -m venv .venv
```
```bash
# Windows:
.\.venv\Scripts\Activate
# Mac/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Rename test.env to .env and add your API key:

GEMINI_API_KEY=your_actual_api_key_here\
GEMINI_MODEL=gemini-1.5-flash

### 5. Run the Application
```bash
streamlit run app.py
```

### 🧩 Architectural Insights
The project follows a Stateful-Frontend pattern:
Initialization: The app checks for existing language-specific history files.
Prompt Engineering: Pedagogical rules are injected via f-strings into the System Instruction.
Inference Loop: User input is combined with the optimized context window and sent to the inference engine.
Atomic Persistence: Responses are immediately committed to disk to prevent data loss.