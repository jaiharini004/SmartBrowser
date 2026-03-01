import gradio as gr

from src.webui.webui_manager import WebuiManager
from src.webui.components.agent_settings_tab import create_agent_settings_tab
from src.webui.components.browser_settings_tab import create_browser_settings_tab
from src.webui.components.browser_use_agent_tab import create_browser_use_agent_tab
from src.webui.components.deep_research_agent_tab import create_deep_research_agent_tab
from src.webui.components.load_save_config_tab import create_load_save_config_tab

theme_map = {
    "Default": gr.themes.Default(),
    "Soft": gr.themes.Soft(),
    "Monochrome": gr.themes.Monochrome(),
    "Glass": gr.themes.Glass(),
    "Origin": gr.themes.Origin(),
    "Citrus": gr.themes.Citrus(),
    "Ocean": gr.themes.Ocean(),
    "Base": gr.themes.Base()
}


def create_ui(theme_name="Default"):
    css = """
    /* ============================================
       SmartBrowser — Professional Dark Theme
       ============================================ */

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* --- Root Variables --- */
    :root {
        --sb-bg-primary: #0a0a0f;
        --sb-bg-secondary: #12121a;
        --sb-bg-card: #16161f;
        --sb-bg-card-hover: #1c1c28;
        --sb-bg-input: #1a1a26;
        --sb-border: #2a2a3a;
        --sb-border-hover: #3a3a50;
        --sb-accent: #6c5ce7;
        --sb-accent-hover: #7c6ef7;
        --sb-accent-glow: rgba(108, 92, 231, 0.25);
        --sb-text-primary: #e8e8f0;
        --sb-text-secondary: #9090a8;
        --sb-text-muted: #606078;
        --sb-success: #00d68f;
        --sb-warning: #ffaa00;
        --sb-danger: #ff4757;
        --sb-radius: 12px;
        --sb-transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* --- Global Reset --- */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    body, .gradio-container {
        background: var(--sb-bg-primary) !important;
        color: var(--sb-text-primary) !important;
    }

    .gradio-container {
        width: 75vw !important;
        max-width: 1400px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-top: 10px !important;
    }

    /* --- Header --- */
    .header-text {
        text-align: center;
        margin-bottom: 24px;
        padding: 32px 20px 24px 20px;
        background: linear-gradient(135deg, var(--sb-bg-secondary) 0%, var(--sb-bg-card) 100%);
        border: 1px solid var(--sb-border);
        border-radius: var(--sb-radius);
        position: relative;
        overflow: hidden;
    }
    .header-text::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--sb-accent), #a855f7, var(--sb-accent));
        background-size: 200% 100%;
        animation: shimmer 3s ease-in-out infinite;
    }
    @keyframes shimmer {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    .header-text h1 {
        font-size: 2rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
        background: linear-gradient(135deg, #e8e8f0 0%, #b8b8d0 50%, var(--sb-accent) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px !important;
    }
    .header-text h3 {
        font-weight: 400 !important;
        color: var(--sb-text-secondary) !important;
        -webkit-text-fill-color: var(--sb-text-secondary) !important;
        font-size: 0.95rem !important;
    }

    /* --- Tabs --- */
    .tabs {
        background: transparent !important;
    }
    .tab-nav {
        background: var(--sb-bg-secondary) !important;
        border: 1px solid var(--sb-border) !important;
        border-radius: var(--sb-radius) !important;
        padding: 6px !important;
        gap: 4px !important;
        margin-bottom: 16px !important;
    }
    .tab-nav button {
        background: transparent !important;
        color: var(--sb-text-secondary) !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        transition: var(--sb-transition) !important;
    }
    .tab-nav button:hover {
        background: var(--sb-bg-card) !important;
        color: var(--sb-text-primary) !important;
    }
    .tab-nav button.selected {
        background: var(--sb-accent) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 15px var(--sb-accent-glow) !important;
    }

    /* --- Groups / Cards --- */
    .gr-group, .block {
        background: var(--sb-bg-card) !important;
        border: 1px solid var(--sb-border) !important;
        border-radius: var(--sb-radius) !important;
        padding: 16px !important;
        margin-bottom: 12px !important;
        transition: var(--sb-transition) !important;
    }
    .gr-group:hover, .block:hover {
        border-color: var(--sb-border-hover) !important;
    }

    /* --- Inputs --- */
    input, textarea, select, .gr-input, .gr-text-input {
        background: var(--sb-bg-input) !important;
        border: 1px solid var(--sb-border) !important;
        border-radius: 8px !important;
        color: var(--sb-text-primary) !important;
        transition: var(--sb-transition) !important;
        font-size: 0.9rem !important;
    }
    input:focus, textarea:focus, select:focus {
        border-color: var(--sb-accent) !important;
        box-shadow: 0 0 0 3px var(--sb-accent-glow) !important;
        outline: none !important;
    }

    /* --- Dropdowns --- */
    .gr-dropdown {
        background: var(--sb-bg-input) !important;
        border: 1px solid var(--sb-border) !important;
        border-radius: 8px !important;
    }

    /* --- Buttons --- */
    .gr-button, button.primary, button.secondary {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        letter-spacing: 0.2px;
        transition: var(--sb-transition) !important;
        padding: 10px 24px !important;
    }
    button.primary, .gr-button-primary {
        background: linear-gradient(135deg, var(--sb-accent) 0%, #a855f7 100%) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 15px var(--sb-accent-glow) !important;
    }
    button.primary:hover, .gr-button-primary:hover {
        box-shadow: 0 6px 25px rgba(108, 92, 231, 0.4) !important;
        transform: translateY(-1px);
    }
    button.secondary, .gr-button-secondary {
        background: var(--sb-bg-card) !important;
        color: var(--sb-text-primary) !important;
        border: 1px solid var(--sb-border) !important;
    }
    button.secondary:hover, .gr-button-secondary:hover {
        border-color: var(--sb-accent) !important;
        background: var(--sb-bg-card-hover) !important;
    }
    button.stop, .gr-button-stop {
        background: linear-gradient(135deg, var(--sb-danger) 0%, #ff6b81 100%) !important;
        color: #ffffff !important;
        border: none !important;
    }

    /* --- Sliders --- */
    input[type="range"] {
        accent-color: var(--sb-accent) !important;
    }

    /* --- Checkboxes --- */
    input[type="checkbox"] {
        accent-color: var(--sb-accent) !important;
    }

    /* --- Labels --- */
    label, .gr-label {
        color: var(--sb-text-secondary) !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
    }

    /* --- Info text --- */
    .gr-info, .info {
        color: var(--sb-text-muted) !important;
        font-size: 0.8rem !important;
    }

    /* --- Chatbot --- */
    .chatbot {
        background: var(--sb-bg-secondary) !important;
        border: 1px solid var(--sb-border) !important;
        border-radius: var(--sb-radius) !important;
    }

    /* --- Scrollbar --- */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: var(--sb-bg-primary);
    }
    ::-webkit-scrollbar-thumb {
        background: var(--sb-border);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--sb-text-muted);
    }

    /* --- Animations --- */
    .tabitem {
        animation: fadeIn 0.35s ease-out;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* --- Tab Header --- */
    .tab-header-text {
        text-align: center;
    }
    .tab-header-text h3 {
        color: var(--sb-text-secondary) !important;
    }

    /* --- Footer --- */
    footer {
        display: none !important;
    }
    """

    # Force dark mode
    js_func = """
    function refresh() {
        const url = new URL(window.location);
        if (url.searchParams.get('__theme') !== 'dark') {
            url.searchParams.set('__theme', 'dark');
            window.location.href = url.href;
        }
    }
    """

    ui_manager = WebuiManager()

    with gr.Blocks(
            title="SmartBrowser", theme=theme_map[theme_name], css=css, js=js_func,
    ) as demo:
        with gr.Row():
            gr.Markdown(
                """
                #  SmartBrowser
                ### AI-powered browser automation with multi-model intelligence
                """,
                elem_classes=["header-text"],
            )

        with gr.Tabs() as tabs:
            with gr.TabItem(" Agent Settings"):
                create_agent_settings_tab(ui_manager)

            with gr.TabItem(" Browser Settings"):
                create_browser_settings_tab(ui_manager)

            with gr.TabItem(" Run Agent"):
                create_browser_use_agent_tab(ui_manager)

            with gr.TabItem(" Deep Research"):
                create_deep_research_agent_tab(ui_manager)

            with gr.TabItem(" Load & Save Config"):
                create_load_save_config_tab(ui_manager)

    return demo
