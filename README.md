#  SmartBrowser

**AI-powered browser automation with multi-model intelligence.**

SmartBrowser is an intelligent browser agent that uses LLMs to autonomously navigate the web, perform research, and complete complex tasks — all through a sleek dark-themed Gradio interface.

---

##  Features

- **Multi-Model Support** — Seamlessly switch between **Groq** (Llama 3.3, Llama 4, Qwen 3), **OpenRouter** (Gemini Flash, DeepSeek R1), OpenAI, Anthropic, Google, DeepSeek, Ollama, and more
- **Browser Agent** — AI navigates real websites, fills forms, clicks buttons, and extracts data
- **Deep Research** — Multi-step autonomous research with planning, parallel browser searches, and report synthesis
- **Custom Browser** — Use your own Chrome profile (no re-login needed) with HD recording
- **Profile Presets** — Pick detected Chrome/Edge default profiles from a dropdown in Browser Settings
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
2. (Optional) Enable **Force Task Planning** to always run planning before execution
3. Go to **🌐 Browser Settings** and choose **Default Browser Profile** (`Chrome - Default` / `Edge - Default`) or keep custom manual paths
2. Go to **🤖 Run Agent** → Enter your task → Click **Run**
3. Watch the AI navigate in real-time

### File / PDF Guided Tasks
1. In **🤖 Run Agent**, click the upload `＋` button and attach an image, text file, or PDF
2. The agent receives grounded context from uploaded files and can use upload actions on target websites
3. For PDFs, SmartBrowser extracts a short local text context when possible to reduce hallucination

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

## How It Works

- `webui.py` launches the Gradio interface and tab wiring.
- `src/webui/components/agent_settings_tab.py` controls LLM/provider/planner configuration.
- `src/webui/components/browser_settings_tab.py` controls browser runtime settings, including profile presets.
- `src/webui/components/browser_use_agent_tab.py` runs interactive browser-use tasks and streaming UI updates.
- `src/agent/browser_use/browser_use_agent.py` extends browser-use with reliability backoff and fail-fast guards.
- `src/agent/deep_research/deep_research_agent.py` orchestrates multi-step planning, parallel browser tasks, and report synthesis.
- `src/controller/custom_controller.py` adds custom actions like assisted upload and MCP tool registration.
- `src/browser/custom_browser.py` and `src/browser/custom_context.py` wrap Playwright browser/context behavior.

---

## March 2026 Stability Update

- Added browser profile dropdown with Chrome/Edge preset detection.
- Added planner fallback so tasks can be planned even when no dedicated planner model is chosen.
- Added stronger navigation guardrails to reduce random URL retries and hallucinated domains.
- Removed expensive post-task site-description LLM call that consumed extra tokens.
- Added duplicate-query filtering in deep research parallel search tool.
- Improved uploaded file reliability by passing uploaded paths to agent actions and parsing PDF/text context.
- Fixed SmartBrowser header title visibility when gradient text rendering is unsupported.

---

##  License

This project is for personal and educational use.
