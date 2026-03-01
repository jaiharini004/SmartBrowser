#  SmartBrowser

**AI-powered browser automation with multi-model intelligence.**

SmartBrowser is an intelligent browser agent that uses LLMs to autonomously navigate the web, perform research, and complete complex tasks — all through a sleek dark-themed Gradio interface.

---

##  Features

- **Multi-Model Support** — Seamlessly switch between **Groq** (Llama 3.3, Llama 4, Qwen 3), **OpenRouter** (Gemini Flash, DeepSeek R1), OpenAI, Anthropic, Google, DeepSeek, Ollama, and more
- **Browser Agent** — AI navigates real websites, fills forms, clicks buttons, and extracts data
- **Deep Research** — Multi-step autonomous research with planning, parallel browser searches, and report synthesis
- **Custom Browser** — Use your own Chrome profile (no re-login needed) with HD recording
- **Persistent Sessions** — Keep the browser open between tasks for continuous workflow
- **Professional Dark UI** — Clean, modern dark theme with smooth animations

---

##  Quick Start

### 1. Clone & Setup
```bash
git clone <your-repo-url>
cd SmartBrowser
python -m venv .venv
```

**Activate the virtual environment:**
```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure API Keys
```bash
copy .env.example .env
```

Edit `.env` and add your API keys:
```ini
# Get a free key at https://console.groq.com
GROQ_API_KEY=gsk_your_key_here

# Get a free key at https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-v1-your_key_here
```

### 4. Launch
```bash
python webui.py
```

Open **http://127.0.0.1:7788** in your browser.

---

##  Usage Guide

### Browser Agent
1. Go to **⚙️ Agent Settings** → Select **Groq** as provider → Choose a model (e.g. `llama-3.3-70b-versatile`)
2. Go to **🤖 Run Agent** → Enter your task → Click **Run**
3. Watch the AI navigate in real-time

### Deep Research
1. Go to **🔬 Deep Research** → Enter a research topic
2. The agent creates a research plan, opens multiple browser tabs, and synthesizes a report
3. Download the final markdown report when complete

---

##  Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `DEFAULT_LLM` | Default LLM provider | `groq` |
| `GROQ_ENDPOINT` | Groq API endpoint | `https://api.groq.com/openai/v1` |
| `OPENROUTER_ENDPOINT` | OpenRouter API endpoint | `https://openrouter.ai/api/v1` |
| `KEEP_BROWSER_OPEN` | Keep browser open between tasks | `true` |
| `BROWSER_USE_LOGGING_LEVEL` | Log verbosity (`result`, `info`, `debug`) | `info` |

---

## Project Structure

```
SmartBrowser/
├── webui.py                          # Entry point
├── src/
│   ├── agent/
│   │   ├── browser_use/              # Browser automation agent
│   │   └── deep_research/            # Deep research agent with LangGraph
│   ├── utils/
│   │   ├── config.py                 # Provider & model configuration
│   │   └── llm_provider.py           # LLM provider factory
│   └── webui/
│       ├── interface.py              # UI layout & dark theme
│       └── components/               # Gradio tab components
├── .env.example                      # Environment template
└── requirements.txt                  # Python dependencies
```

---

##  License

This project is for personal and educational use.
