import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional
from urllib.parse import urlparse

import gradio as gr

# from browser_use.agent.service import Agent
from browser_use.agent.views import (
    AgentHistoryList,
    AgentOutput,
)
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.browser.views import BrowserState
from gradio.components import Component
from langchain_core.language_models.chat_models import BaseChatModel

from src.agent.browser_use.browser_use_agent import BrowserUseAgent
from src.browser.custom_browser import CustomBrowser
from src.browser.profile_utils import resolve_profile_selection
from src.controller.custom_controller import CustomController
from src.utils import llm_provider
from src.utils.memory_manager import MemoryManager
from src.webui.webui_manager import WebuiManager

logger = logging.getLogger(__name__)

_SITE_DESCRIPTION_OVERRIDES: Dict[str, str] = {
    "pinterest.com": "Pinterest is a visual discovery platform used to explore and save ideas through image pins, boards, and curated collections.",
    "www.pinterest.com": "Pinterest is a visual discovery platform used to explore and save ideas through image pins, boards, and curated collections.",
}


def _extract_uploaded_file_context(file_path: Optional[str]) -> str:
    """Extract concise context from a supported uploaded file to ground execution."""
    if not file_path:
        return ""

    try:
        path_obj = Path(file_path)
        if not path_obj.exists() or not path_obj.is_file():
            return ""

        suffix = path_obj.suffix.lower()
        if suffix in {".txt", ".md", ".csv", ".json", ".log"}:
            content = path_obj.read_text(encoding="utf-8", errors="ignore")
            excerpt = content[:3000].strip()
            if excerpt:
                return f"\n\nUploaded file context ({path_obj.name}):\n{excerpt}"

        if suffix == ".docx":
            try:
                import docx

                doc = docx.Document(str(path_obj))
                text_parts = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text and paragraph.text.strip()]
                excerpt = "\n".join(text_parts)[:4000].strip()
                if excerpt:
                    return f"\n\nUploaded DOCX context ({path_obj.name}):\n{excerpt}"
            except Exception as docx_exc:
                logger.warning(f"Could not parse uploaded DOCX '{file_path}': {docx_exc}")

        if suffix == ".doc":
            return (
                f"\n\nUploaded DOC file ({path_obj.name}) is attached. "
                "Legacy .doc local parsing is limited; use browser upload actions for source-grounded handling."
            )

        if suffix == ".pdf":
            try:
                from pypdf import PdfReader

                reader = PdfReader(str(path_obj))
                text_parts = []
                max_pages = min(len(reader.pages), 12)
                for page in reader.pages[:max_pages]:
                    raw_text = (page.extract_text() or "").replace("\u00ad", "")
                    compact = " ".join(raw_text.split())
                    if compact:
                        text_parts.append(compact)
                excerpt = "\n\n".join(text_parts)[:4500].strip()
                if excerpt:
                    return f"\n\nUploaded PDF context ({path_obj.name}):\n{excerpt}"
                return (
                    f"\n\nUploaded file ({path_obj.name}) is a PDF. "
                    "If needed, use upload actions to submit it to websites and rely on page rendering for details."
                )
            except Exception as pdf_exc:
                logger.warning(f"Could not parse uploaded PDF '{file_path}': {pdf_exc}")
                return (
                    f"\n\nUploaded file ({path_obj.name}) is a PDF. "
                    "Local extraction failed; continue using browser actions and available file upload tools."
                )
    except Exception as exc:
        logger.warning(f"Failed to extract uploaded file context: {exc}")

    return ""


def _build_task_with_guardrails(task: str, uploaded_context: str) -> str:
    guidance = (
        "Execution policy:\n"
        "1. Plan briefly before acting: identify the target site and the minimal steps needed.\n"
        "2. If a URL is uncertain, do not invent domains. Use a search engine first and open a verified result.\n"
        "3. Prefer official domains and stable sources.\n"
        "4. Avoid repeating the same failed URL more than once; switch strategy to search and verify.\n"
        "5. Keep actions token-efficient and finish the task with a clear final result."
    )
    return f"{task}\n\n{guidance}{uploaded_context}"


# --- Helper Functions --- (Defined at module level)


async def _initialize_llm(
        provider: Optional[str],
        model_name: Optional[str],
        temperature: float,
        base_url: Optional[str],
        api_key: Optional[str],
        num_ctx: Optional[int] = None,
) -> Optional[BaseChatModel]:
    """Initializes the LLM based on settings. Returns None if provider/model is missing."""
    if not provider or not model_name:
        logger.info("LLM Provider or Model Name not specified, LLM will be None.")
        return None
    try:
        # Use your actual LLM provider logic here
        logger.info(
            f"Initializing LLM: Provider={provider}, Model={model_name}, Temp={temperature}"
        )
        # Example using a placeholder function
        llm = llm_provider.get_llm_model(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            base_url=base_url or None,
            api_key=api_key or None,
            # Add other relevant params like num_ctx for ollama
            num_ctx=num_ctx if provider == "ollama" else None,
        )
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}", exc_info=True)
        gr.Warning(
            f"Failed to initialize LLM '{model_name}' for provider '{provider}'. Please check settings. Error: {e}"
        )
        return None


async def _initialize_llm_with_fallback(
        provider: Optional[str],
        model_name: Optional[str],
        temperature: float,
        base_url: Optional[str],
        api_key: Optional[str],
        num_ctx: Optional[int] = None,
) -> Optional[BaseChatModel]:
    """Initialize an LLM and try provider-specific fallback model names when needed."""
    if not provider:
        return None

    normalized_provider = provider.strip().lower()
    candidate_models: list[str] = []

    if model_name:
        candidate_models.append(model_name)

    if normalized_provider == "groq":
        groq_fallbacks = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-8b-8192",
            "mixtral-8x7b-32768"
        ]
        for fallback_model in groq_fallbacks:
            if fallback_model not in candidate_models:
                candidate_models.append(fallback_model)

    if not candidate_models:
        return None

    last_error_model = candidate_models[-1]
    for candidate_model in candidate_models:
        llm = await _initialize_llm(
            provider=provider,
            model_name=candidate_model,
            temperature=temperature,
            base_url=base_url,
            api_key=api_key,
            num_ctx=num_ctx,
        )
        if llm is not None:
            if candidate_model != model_name:
                logger.warning(
                    f"LLM model fallback activated for provider '{provider}': '{model_name}' -> '{candidate_model}'"
                )
            return llm
        last_error_model = candidate_model

    logger.error(
        f"All fallback models failed for provider '{provider}'. Last attempted model: '{last_error_model}'"
    )
    return None


def _get_config_value(
        webui_manager: WebuiManager,
        comp_dict: Dict[gr.components.Component, Any],
        comp_id_suffix: str,
        default: Any = None,
) -> Any:
    """Safely get value from component dictionary using its ID suffix relative to the tab."""
    # Assumes component ID format is "tab_name.comp_name"
    tab_name = "browser_use_agent"  # Hardcode or derive if needed
    comp_id = f"{tab_name}.{comp_id_suffix}"
    # Need to find the component object first using the ID from the manager
    try:
        comp = webui_manager.get_component_by_id(comp_id)
        return comp_dict.get(comp, default)
    except KeyError:
        # Try accessing settings tabs as well
        for prefix in ["agent_settings", "browser_settings"]:
            try:
                comp_id = f"{prefix}.{comp_id_suffix}"
                comp = webui_manager.get_component_by_id(comp_id)
                return comp_dict.get(comp, default)
            except KeyError:
                continue
        logger.warning(
            f"Component with suffix '{comp_id_suffix}' not found in manager for value lookup."
        )
        return default


def _format_agent_output(model_output: AgentOutput) -> str:
    """Formats AgentOutput for display in the chatbot using JSON."""
    content = ""
    if model_output:
        try:
            # Directly use model_dump if actions and current_state are Pydantic models
            action_dump = [
                action.model_dump(exclude_none=True) for action in model_output.action
            ]

            state_dump = model_output.current_state.model_dump(exclude_none=True)
            model_output_dump = {
                "current_state": state_dump,
                "action": action_dump,
            }
            # Dump to JSON string with indentation
            json_string = json.dumps(model_output_dump, indent=4, ensure_ascii=False)
            # Wrap in <pre><code> for proper display in HTML
            content = f"<pre><code class='language-json'>{json_string}</code></pre>"

        except AttributeError as ae:
            logger.error(
                f"AttributeError during model dump: {ae}. Check if 'action' or 'current_state' or their items support 'model_dump'."
            )
            content = f"<pre><code>Error: Could not format agent output (AttributeError: {ae}).\nRaw output: {str(model_output)}</code></pre>"
        except Exception as e:
            logger.error(f"Error formatting agent output: {e}", exc_info=True)
            # Fallback to simple string representation on error
            content = f"<pre><code>Error formatting agent output.\nRaw output:\n{str(model_output)}</code></pre>"

    return content.strip()


def _extract_last_public_page(history: AgentHistoryList) -> tuple[Optional[str], Optional[str]]:
    """Return the last non-internal page URL/title from agent history."""
    try:
        history_items = getattr(history, "history", None) or []
        for entry in reversed(history_items):
            state = getattr(entry, "state", None)
            if state is None:
                continue
            page_url = (getattr(state, "url", "") or "").strip()
            page_title = (getattr(state, "title", "") or "").strip()
            if not page_url:
                continue
            if page_url.startswith("about:") or page_url.startswith("chrome:") or page_url.startswith("edge:"):
                continue
            return page_url, page_title
    except Exception as exc:
        logger.debug(f"Could not extract last public page from history: {exc}")
    return None, None


def _build_site_description(page_url: Optional[str], page_title: Optional[str], task: Optional[str]) -> str:
    """Build a concise site/topic description for what was opened or searched."""
    if not page_url:
        if task:
            return f"I could not detect a final public page URL, but your request was: {task[:180]}"
        return "I could not detect a final public page URL to describe."

    parsed = urlparse(page_url)
    host = (parsed.netloc or "").lower()
    normalized_host = host[4:] if host.startswith("www.") else host
    display_name = normalized_host.split(".")[0].capitalize() if normalized_host else "Website"

    if host in _SITE_DESCRIPTION_OVERRIDES:
        summary = _SITE_DESCRIPTION_OVERRIDES[host]
    elif normalized_host in _SITE_DESCRIPTION_OVERRIDES:
        summary = _SITE_DESCRIPTION_OVERRIDES[normalized_host]
    else:
        if page_title:
            summary = f"{display_name} appears to be related to: {page_title}."
        else:
            summary = f"{display_name} is the website opened for your request."

    title_part = f"Title: {page_title}\n" if page_title else ""
    return f"**Site Description**\n- URL: {page_url}\n- {title_part}- Summary: {summary}"


# --- Updated Callback Implementation ---


async def _handle_new_step(
        webui_manager: WebuiManager, state: BrowserState, output: AgentOutput, step_num: int
):
    """Callback for each step taken by the agent, including screenshot display."""

    # Use the correct chat history attribute name from the user's code
    if not hasattr(webui_manager, "bu_chat_history"):
        logger.error(
            "Attribute 'bu_chat_history' not found in webui_manager! Cannot add chat message."
        )
        # Initialize it maybe? Or raise an error? For now, log and potentially skip chat update.
        webui_manager.bu_chat_history = []  # Initialize if missing (consider if this is the right place)
        # return # Or stop if this is critical
    step_num -= 1
    logger.info(f"Step {step_num} completed.")

    # --- Screenshot Handling ---
    screenshot_html = ""
    # Ensure state.screenshot exists and is not empty before proceeding
    # Use getattr for safer access
    screenshot_data = getattr(state, "screenshot", None)
    if screenshot_data:
        try:
            # Basic validation: check if it looks like base64
            if (
                    isinstance(screenshot_data, str) and len(screenshot_data) > 100
            ):  # Arbitrary length check
                # *** UPDATED STYLE: Removed centering, adjusted width ***
                img_tag = f'<img src="data:image/jpeg;base64,{screenshot_data}" alt="Step {step_num} Screenshot" style="max-width: 800px; max-height: 600px; object-fit:contain;" />'
                screenshot_html = (
                        img_tag + "<br/>"
                )  # Use <br/> for line break after inline-block image
            else:
                logger.warning(
                    f"Screenshot for step {step_num} seems invalid (type: {type(screenshot_data)}, len: {len(screenshot_data) if isinstance(screenshot_data, str) else 'N/A'})."
                )
                screenshot_html = "**[Invalid screenshot data]**<br/>"

        except Exception as e:
            logger.error(
                f"Error processing or formatting screenshot for step {step_num}: {e}",
                exc_info=True,
            )
            screenshot_html = "**[Error displaying screenshot]**<br/>"
    else:
        logger.debug(f"No screenshot available for step {step_num}.")

    # --- Format Agent Output ---
    formatted_output = _format_agent_output(output)  # Use the updated function

    # --- Combine and Append to Chat ---
    step_header = f"--- **Step {step_num}** ---"
    # Combine header, image (with line break), and JSON block
    final_content = step_header + "<br/>" + screenshot_html + formatted_output

    chat_message = {
        "role": "assistant",
        "content": final_content.strip(),  # Remove leading/trailing whitespace
    }

    # Append to the correct chat history list
    webui_manager.bu_chat_history.append(chat_message)

    await asyncio.sleep(0.05)


def _handle_done(webui_manager: WebuiManager, history: AgentHistoryList, task: Optional[str] = None):
    """Callback when the agent finishes the task (success or failure)."""
    logger.info(
        f"Agent task finished. Duration: {history.total_duration_seconds():.2f}s, Tokens: {history.total_input_tokens()}"
    )
    final_summary = "**Task Completed**\n"
    final_summary += f"- Duration: {history.total_duration_seconds():.2f} seconds\n"
    final_summary += f"- Total Input Tokens: {history.total_input_tokens()}\n"  # Or total tokens if available

    final_result = history.final_result()
    if final_result:
        final_summary += f"- Final Result: {final_result}\n"

    errors = history.errors()
    if errors and any(errors):
        final_summary += f"- **Errors:**\n```\n{errors}\n```\n"
    else:
        final_summary += "- Status: Success\n"

    webui_manager.bu_chat_history.append(
        {"role": "assistant", "content": final_summary}
    )

    page_url, page_title = _extract_last_public_page(history)
    description_message = _build_site_description(page_url, page_title, task)
    webui_manager.bu_chat_history.append(
        {"role": "assistant", "content": description_message}
    )


async def _ask_assistant_callback(
        webui_manager: WebuiManager, query: str, browser_context: BrowserContext
) -> Dict[str, Any]:
    """Callback triggered by the agent's ask_for_assistant action."""
    logger.info("Agent requires assistance. Waiting for user input.")

    if not hasattr(webui_manager, "_chat_history"):
        logger.error("Chat history not found in webui_manager during ask_assistant!")
        return {"response": "Internal Error: Cannot display help request."}

    webui_manager.bu_chat_history.append(
        {
            "role": "assistant",
            "content": f"**Need Help:** {query}\nPlease provide information or perform the required action in the browser, then type your response/confirmation below and click 'Submit Response'.",
        }
    )

    # Use state stored in webui_manager
    webui_manager.bu_response_event = asyncio.Event()
    webui_manager.bu_user_help_response = None  # Reset previous response

    try:
        logger.info("Waiting for user response event...")
        await asyncio.wait_for(
            webui_manager.bu_response_event.wait(), timeout=3600.0
        )  # Long timeout
        logger.info("User response event received.")
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for user assistance.")
        webui_manager.bu_chat_history.append(
            {
                "role": "assistant",
                "content": "**Timeout:** No response received. Trying to proceed.",
            }
        )
        webui_manager.bu_response_event = None  # Clear the event
        return {"response": "Timeout: User did not respond."}  # Inform the agent

    response = webui_manager.bu_user_help_response
    webui_manager.bu_chat_history.append(
        {"role": "user", "content": response}
    )  # Show user response in chat
    webui_manager.bu_response_event = (
        None  # Clear the event for the next potential request
    )
    return {"response": response}


# --- Core Agent Execution Logic --- (Needs access to webui_manager)


async def run_agent_task(
        webui_manager: WebuiManager, components: Dict[gr.components.Component, Any]
) -> AsyncGenerator[Dict[gr.components.Component, Any], None]:
    """Handles the entire lifecycle of initializing and running the agent."""

    # --- Get Components ---
    # Need handles to specific UI components to update them
    user_input_comp = webui_manager.get_component_by_id("browser_use_agent.user_input")
    run_button_comp = webui_manager.get_component_by_id("browser_use_agent.run_button")
    stop_button_comp = webui_manager.get_component_by_id(
        "browser_use_agent.stop_button"
    )
    pause_resume_button_comp = webui_manager.get_component_by_id(
        "browser_use_agent.pause_resume_button"
    )
    clear_button_comp = webui_manager.get_component_by_id(
        "browser_use_agent.clear_button"
    )
    chatbot_comp = webui_manager.get_component_by_id("browser_use_agent.chatbot")
    history_file_comp = webui_manager.get_component_by_id(
        "browser_use_agent.agent_history_file"
    )
    gif_comp = webui_manager.get_component_by_id("browser_use_agent.recording_gif")
    browser_view_comp = webui_manager.get_component_by_id(
        "browser_use_agent.browser_view"
    )

    # --- 1. Get Task and Initial UI Update ---
    task = components.get(user_input_comp, "").strip()
    upload_state_comp = webui_manager.get_component_by_id("browser_use_agent.uploaded_file_path_state")
    uploaded_file_path = components.get(upload_state_comp)
    uploaded_context = _extract_uploaded_file_context(uploaded_file_path)
    task_for_agent = _build_task_with_guardrails(task, uploaded_context)

    if not task:
        gr.Warning("Please enter a task.")
        yield {run_button_comp: gr.update(interactive=True)}
        return

    # Set running state indirectly via _current_task
    webui_manager.bu_chat_history.append({"role": "user", "content": task})

    yield {
        user_input_comp: gr.Textbox(
            value="", interactive=False, placeholder="Agent is running..."
        ),
        run_button_comp: gr.Button(value="⏳ Running...", interactive=False),
        stop_button_comp: gr.Button(interactive=True),
        pause_resume_button_comp: gr.Button(value="⏸️ Pause", interactive=True),
        clear_button_comp: gr.Button(interactive=False),
        chatbot_comp: gr.update(value=webui_manager.bu_chat_history),
        history_file_comp: gr.update(value=None),
        gif_comp: gr.update(value=None),
    }

    # --- Agent Settings ---
    # Access settings values via components dict, getting IDs from webui_manager
    def get_setting(key, default=None):
        comp = webui_manager.id_to_component.get(f"agent_settings.{key}")
        return components.get(comp, default) if comp else default

    # Memory injection
    memory_manager = MemoryManager()
    memory_context = memory_manager.get_memory_context()


    override_system_prompt = get_setting("override_system_prompt") or None
    extend_system_prompt = get_setting("extend_system_prompt") or ""
    llm_provider_name = get_setting(
        "llm_provider", None
    )  # Default to None if not found
    llm_model_name = get_setting("llm_model_name", None)
    llm_temperature = get_setting("llm_temperature", 0.6)
    use_vision = get_setting("use_vision", True)

    # Providers that use ChatOpenAI wrapper but don't support multimodal/vision
    _NO_VISION_PROVIDERS = {"groq", "openrouter", "grok"}
    # Providers that use ChatOpenAI wrapper (mem0 defaults to OpenAI embeddings which requires OPENAI_API_KEY)
    _NO_MEMORY_PROVIDERS = {"groq", "openrouter", "grok"}
    _LOW_TPM_PROVIDERS = {"groq"}
    _PROVIDER_MAX_INPUT_TOKEN_CAP = {
        "groq": 3500,
    }

    # Avoid injecting large rolling memory context for strict low-TPM providers.
    if memory_context:
        if llm_provider_name in _LOW_TPM_PROVIDERS:
            logger.info(f"Skipping rolling memory prompt injection for {llm_provider_name} to avoid oversized requests.")
        else:
            extend_system_prompt += "\n" + memory_context
    extend_system_prompt = extend_system_prompt if extend_system_prompt else None

    # Auto-disable vision for providers that don't support multimodal messages
    if llm_provider_name in _NO_VISION_PROVIDERS and use_vision:
        logger.info(f"⚠️ Auto-disabling vision for {llm_provider_name} (multimodal not supported)")
        use_vision = False

    # Skip the OPENAI_API_KEY verification for non-OpenAI providers using ChatOpenAI
    if llm_provider_name in _NO_VISION_PROVIDERS:
        os.environ["SKIP_LLM_API_KEY_VERIFICATION"] = "true"
    ollama_num_ctx = get_setting("ollama_num_ctx", 16000)
    llm_base_url = get_setting("llm_base_url") or None
    llm_api_key = get_setting("llm_api_key") or None
    max_steps = get_setting("max_steps", 100)
    max_actions = get_setting("max_actions", 10)
    max_input_tokens = int(get_setting("max_input_tokens", 128000))
    tool_calling_str = get_setting("tool_calling_method", "auto")
    tool_calling_method = tool_calling_str if tool_calling_str != "None" else None
    mcp_server_config_comp = webui_manager.id_to_component.get(
        "agent_settings.mcp_server_config"
    )
    mcp_server_config_str = (
        components.get(mcp_server_config_comp) if mcp_server_config_comp else None
    )
    mcp_server_config = (
        json.loads(mcp_server_config_str) if mcp_server_config_str else None
    )

    # Planner LLM Settings (Optional)
    planner_llm_provider_name = get_setting("planner_llm_provider") or None
    force_task_planning = bool(get_setting("force_task_planning", True))
    planner_interval = 1

    if llm_provider_name in _LOW_TPM_PROVIDERS:
        provider_cap = _PROVIDER_MAX_INPUT_TOKEN_CAP[llm_provider_name]
        if max_input_tokens > provider_cap:
            logger.warning(
                f"Capping max_input_tokens for {llm_provider_name}: {max_input_tokens} -> {provider_cap} "
                "to stay under provider TPM limits."
            )
            max_input_tokens = provider_cap

        # Running planner each step with full history is expensive for strict TPM providers.
        planner_interval = 4
        if force_task_planning and not planner_llm_provider_name:
            force_task_planning = False
            logger.warning(
                f"Auto-disabling planner fallback for {llm_provider_name} because it can exceed TPM limits. "
                "Set Planner LLM explicitly to re-enable planning."
            )

    planner_llm = None
    planner_use_vision = False
    if planner_llm_provider_name:
        planner_llm_model_name = get_setting("planner_llm_model_name")
        planner_llm_temperature = get_setting("planner_llm_temperature", 0.6)
        planner_ollama_num_ctx = get_setting("planner_ollama_num_ctx", 16000)
        planner_llm_base_url = get_setting("planner_llm_base_url") or None
        planner_llm_api_key = get_setting("planner_llm_api_key") or None
        planner_use_vision = get_setting("planner_use_vision", False)

        planner_llm = await _initialize_llm(
            planner_llm_provider_name,
            planner_llm_model_name,
            planner_llm_temperature,
            planner_llm_base_url,
            planner_llm_api_key,
            planner_ollama_num_ctx if planner_llm_provider_name == "ollama" else None,
        )

    # --- Browser Settings ---
    def get_browser_setting(key, default=None):
        comp = webui_manager.id_to_component.get(f"browser_settings.{key}")
        return components.get(comp, default) if comp else default

    browser_binary_path = get_browser_setting("browser_binary_path") or None
    browser_user_data_dir = get_browser_setting("browser_user_data_dir") or None
    browser_profile = get_browser_setting("browser_profile") or "Custom (manual path)"
    use_own_browser = get_browser_setting(
        "use_own_browser", False
    )  # Logic handled by CDP/WSS presence
    keep_browser_open = get_browser_setting("keep_browser_open", False)
    headless = get_browser_setting("headless", False)
    disable_security = get_browser_setting("disable_security", False)
    window_w = int(get_browser_setting("window_w", 1280))
    window_h = int(get_browser_setting("window_h", 1100))
    cdp_url = get_browser_setting("cdp_url") or None
    wss_url = get_browser_setting("wss_url") or None
    save_recording_path = get_browser_setting("save_recording_path") or None
    save_trace_path = get_browser_setting("save_trace_path") or None
    save_agent_history_path = get_browser_setting(
        "save_agent_history_path", "./tmp/agent_history"
    )
    save_download_path = get_browser_setting("save_download_path", "./tmp/downloads")

    resolved_profile = resolve_profile_selection(
        profile_label=browser_profile,
        manual_user_data_dir=browser_user_data_dir,
        manual_binary_path=browser_binary_path,
    )
    browser_user_data_dir = resolved_profile["user_data_dir"]
    browser_profile_directory = resolved_profile.get("profile_directory")
    browser_binary_path = resolved_profile["binary_path"]

    # In own-browser mode we launch a local browser/profile; stale remote endpoints should not override that path.
    if use_own_browser and (cdp_url or wss_url):
        logger.warning(
            "Use Own Browser is enabled; ignoring configured CDP/WSS endpoint to launch local browser profile."
        )
        cdp_url = None
        wss_url = None

    stream_vw = 70
    stream_vh = int(70 * window_h // window_w)

    os.makedirs(save_agent_history_path, exist_ok=True)
    if save_recording_path:
        os.makedirs(save_recording_path, exist_ok=True)
    if save_trace_path:
        os.makedirs(save_trace_path, exist_ok=True)
    if save_download_path:
        os.makedirs(save_download_path, exist_ok=True)

    # --- 2. Initialize LLM ---
    main_llm = await _initialize_llm_with_fallback(
        llm_provider_name,
        llm_model_name,
        llm_temperature,
        llm_base_url,
        llm_api_key,
        ollama_num_ctx if llm_provider_name == "ollama" else None,
    )
    if main_llm is None:
        gr.Error("Failed to initialize LLM with all fallback models. Please verify provider, model name, and API key.")
        yield {
            user_input_comp: gr.update(interactive=True, placeholder="LLM initialization failed. Update settings and retry."),
            run_button_comp: gr.update(value="▶️ Submit Task", interactive=True),
            stop_button_comp: gr.update(value="⏹️ Stop", interactive=False),
            pause_resume_button_comp: gr.update(value="⏸️ Pause", interactive=False),
            clear_button_comp: gr.update(interactive=True),
            chatbot_comp: gr.update(value=webui_manager.bu_chat_history),
        }
        return

    if force_task_planning and planner_llm is None:
        planner_llm = main_llm
        planner_use_vision = False
        logger.info("Planner fallback enabled: using main LLM as planner.")

    # Pass the webui_manager instance to the callback when wrapping it
    async def ask_callback_wrapper(
            query: str, browser_context: BrowserContext
    ) -> Dict[str, Any]:
        return await _ask_assistant_callback(webui_manager, query, browser_context)

    if not webui_manager.bu_controller:
        webui_manager.bu_controller = CustomController(
            ask_assistant_callback=ask_callback_wrapper
        )
        await webui_manager.bu_controller.setup_mcp_client(mcp_server_config)

    # --- 4. Initialize Browser and Context ---
    should_close_browser_on_finish = not keep_browser_open

    try:
        # Close existing resources if not keeping open
        if not keep_browser_open:
            if webui_manager.bu_browser_context:
                logger.info("Closing previous browser context.")
                await webui_manager.bu_browser_context.close()
                webui_manager.bu_browser_context = None
            if webui_manager.bu_browser:
                logger.info("Closing previous browser.")
                await webui_manager.bu_browser.close()
                webui_manager.bu_browser = None

        # Create Browser if needed
        if not webui_manager.bu_browser:
            logger.info("Launching new browser instance.")
            extra_args = []
            if use_own_browser:
                browser_binary_path = browser_binary_path or os.getenv("BROWSER_PATH", None)
                if browser_binary_path == "":
                    browser_binary_path = None
                browser_user_data = browser_user_data_dir or os.getenv("BROWSER_USER_DATA", None)
                if browser_user_data:
                    extra_args += [f"--user-data-dir={browser_user_data}"]
                if browser_profile_directory:
                    extra_args += [f"--profile-directory={browser_profile_directory}"]
            else:
                browser_binary_path = None

            webui_manager.bu_browser = CustomBrowser(
                config=BrowserConfig(
                    headless=headless,
                    disable_security=disable_security,
                    browser_binary_path=browser_binary_path,
                    extra_browser_args=extra_args,
                    wss_url=wss_url,
                    cdp_url=cdp_url,
                    new_context_config=BrowserContextConfig(
                        window_width=window_w,
                        window_height=window_h,
                    )
                )
            )

        # Create Context if needed
        if not webui_manager.bu_browser_context:
            logger.info("Creating new browser context.")
            context_config = BrowserContextConfig(
                trace_path=save_trace_path if save_trace_path else None,
                save_recording_path=save_recording_path
                if save_recording_path
                else None,
                save_downloads_path=save_download_path if save_download_path else None,
                window_height=window_h,
                window_width=window_w,
            )
            if not webui_manager.bu_browser:
                raise ValueError("Browser not initialized, cannot create context.")
            webui_manager.bu_browser_context = (
                await webui_manager.bu_browser.new_context(config=context_config)
            )

            # Force browser bootstrap now so profile/CDP errors fail during setup, not inside the task loop.
            try:
                startup_page = await asyncio.wait_for(
                    webui_manager.bu_browser_context.get_current_page(),
                    timeout=12,
                )
            except Exception as startup_bootstrap_err:
                raise RuntimeError(
                    "Browser startup failed before task execution. "
                    "If you are using your own profile, close all Edge/Chrome background processes and retry."
                ) from startup_bootstrap_err

            # Own-profile launches often start on a blank/new-tab page. Open a practical default entry page.
            if use_own_browser:
                try:
                    page = startup_page
                    current_url = (page.url or "").strip().lower()
                    if current_url in {"", "about:blank", "chrome://newtab/", "edge://newtab/"}:
                        await page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=20000)
                except Exception as startup_err:
                    logger.info(f"Startup page warmup skipped: {startup_err}")

        # --- 5. Initialize or Update Agent ---
        webui_manager.bu_agent_task_id = str(uuid.uuid4())  # New ID for this task run
        os.makedirs(
            os.path.join(save_agent_history_path, webui_manager.bu_agent_task_id),
            exist_ok=True,
        )
        history_file = os.path.join(
            save_agent_history_path,
            webui_manager.bu_agent_task_id,
            f"{webui_manager.bu_agent_task_id}.json",
        )
        gif_path = os.path.join(
            save_agent_history_path,
            webui_manager.bu_agent_task_id,
            f"{webui_manager.bu_agent_task_id}.gif",
        )

        # Pass the webui_manager to callbacks when wrapping them
        async def step_callback_wrapper(
                state: BrowserState, output: AgentOutput, step_num: int
        ):
            await _handle_new_step(webui_manager, state, output, step_num)

        def done_callback_wrapper(history: AgentHistoryList):
            _handle_done(webui_manager, history, task)
            # Add to persistent memory database once agent finishes
            memory_manager.add_memory(task, str(history.final_result()))

        if not webui_manager.bu_agent:
            logger.info(f"Initializing new agent for task: {task}")
            if not webui_manager.bu_browser or not webui_manager.bu_browser_context:
                raise ValueError(
                    "Browser or Context not initialized, cannot create agent."
                )
            webui_manager.bu_agent = BrowserUseAgent(
                task=task_for_agent,
                llm=main_llm,
                browser=webui_manager.bu_browser,
                browser_context=webui_manager.bu_browser_context,
                controller=webui_manager.bu_controller,
                register_new_step_callback=step_callback_wrapper,
                register_done_callback=done_callback_wrapper,
                use_vision=use_vision,
                override_system_message=override_system_prompt,
                extend_system_message=extend_system_prompt,
                max_input_tokens=max_input_tokens,
                max_actions_per_step=max_actions,
                tool_calling_method=tool_calling_method,
                planner_llm=planner_llm,
                planner_interval=planner_interval,
                use_vision_for_planner=planner_use_vision if planner_llm else False,
                enable_memory=llm_provider_name not in _NO_MEMORY_PROVIDERS,
                source="webui",
            )
            webui_manager.bu_agent.state.agent_id = webui_manager.bu_agent_task_id
            webui_manager.bu_agent.settings.generate_gif = gif_path
        else:
            webui_manager.bu_agent.state.agent_id = webui_manager.bu_agent_task_id
            webui_manager.bu_agent.add_new_task(task_for_agent)
            webui_manager.bu_agent.settings.generate_gif = gif_path
            webui_manager.bu_agent.browser = webui_manager.bu_browser
            webui_manager.bu_agent.browser_context = webui_manager.bu_browser_context
            webui_manager.bu_agent.controller = webui_manager.bu_controller

        # --- 6. Run Agent Task and Stream Updates ---
        agent_run_coro = webui_manager.bu_agent.run(max_steps=max_steps)
        agent_task = asyncio.create_task(agent_run_coro)
        webui_manager.bu_current_task = agent_task  # Store the task

        last_chat_len = len(webui_manager.bu_chat_history)
        while not agent_task.done():
            is_paused = webui_manager.bu_agent.state.paused
            is_stopped = webui_manager.bu_agent.state.stopped

            # Check for pause state
            if is_paused:
                yield {
                    pause_resume_button_comp: gr.update(
                        value="▶️ Resume", interactive=True
                    ),
                    stop_button_comp: gr.update(interactive=True),
                }
                # Wait until pause is released or task is stopped/done
                while is_paused and not agent_task.done():
                    # Re-check agent state in loop
                    is_paused = webui_manager.bu_agent.state.paused
                    is_stopped = webui_manager.bu_agent.state.stopped
                    if is_stopped:  # Stop signal received while paused
                        break
                    await asyncio.sleep(0.2)

                if (
                        agent_task.done() or is_stopped
                ):  # If stopped or task finished while paused
                    break

                # If resumed, yield UI update
                yield {
                    pause_resume_button_comp: gr.update(
                        value="⏸️ Pause", interactive=True
                    ),
                    run_button_comp: gr.update(
                        value="⏳ Running...", interactive=False
                    ),
                }

            # Check if agent stopped itself or stop button was pressed (which sets agent.state.stopped)
            if is_stopped:
                logger.info("Agent has stopped (internally or via stop button).")
                if not agent_task.done():
                    # Ensure the task coroutine finishes if agent just set flag
                    try:
                        await asyncio.wait_for(
                            agent_task, timeout=1.0
                        )  # Give it a moment to exit run()
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Agent task did not finish quickly after stop signal, cancelling."
                        )
                        agent_task.cancel()
                    except Exception:  # Catch task exceptions if it errors on stop
                        pass
                break  # Exit the streaming loop

            # Check if agent is asking for help (via response_event)
            update_dict = {}
            if webui_manager.bu_response_event is not None:
                update_dict = {
                    user_input_comp: gr.update(
                        placeholder="Agent needs help. Enter response and submit.",
                        interactive=True,
                    ),
                    run_button_comp: gr.update(
                        value="✔️ Submit Response", interactive=True
                    ),
                    pause_resume_button_comp: gr.update(interactive=False),
                    stop_button_comp: gr.update(interactive=False),
                    chatbot_comp: gr.update(value=webui_manager.bu_chat_history),
                }
                last_chat_len = len(webui_manager.bu_chat_history)
                yield update_dict
                # Wait until response is submitted or task finishes
                await webui_manager.bu_response_event.wait()

                # Restore UI after response submitted or if task ended unexpectedly
                if not agent_task.done():
                    yield {
                        user_input_comp: gr.update(
                            placeholder="Agent is running...", interactive=False
                        ),
                        run_button_comp: gr.update(
                            value="⏳ Running...", interactive=False
                        ),
                        pause_resume_button_comp: gr.update(interactive=True),
                        stop_button_comp: gr.update(interactive=True),
                    }
                else:
                    break  # Task finished while waiting for response

            # Update Chatbot if new messages arrived via callbacks
            if len(webui_manager.bu_chat_history) > last_chat_len:
                update_dict[chatbot_comp] = gr.update(
                    value=webui_manager.bu_chat_history
                )
                last_chat_len = len(webui_manager.bu_chat_history)

            # Update Browser View
            if headless and webui_manager.bu_browser_context:
                try:
                    screenshot_b64 = (
                        await webui_manager.bu_browser_context.take_screenshot()
                    )
                    if screenshot_b64:
                        html_content = f'<img src="data:image/jpeg;base64,{screenshot_b64}" style="width:{stream_vw}vw; height:{stream_vh}vh ; border:1px solid #ccc;">'
                        update_dict[browser_view_comp] = gr.update(
                            value=html_content, visible=True
                        )
                    else:
                        html_content = f"<h1 style='width:{stream_vw}vw; height:{stream_vh}vh'>Waiting for browser session...</h1>"
                        update_dict[browser_view_comp] = gr.update(
                            value=html_content, visible=True
                        )
                except Exception as e:
                    logger.debug(f"Failed to capture screenshot: {e}")
                    update_dict[browser_view_comp] = gr.update(
                        value="<div style='...'>Error loading view...</div>",
                        visible=True,
                    )
            else:
                update_dict[browser_view_comp] = gr.update(visible=False)

            # Yield accumulated updates
            if update_dict:
                yield update_dict

            await asyncio.sleep(0.1)  # Polling interval

        # --- 7. Task Finalization ---
        webui_manager.bu_agent.state.paused = False
        webui_manager.bu_agent.state.stopped = False
        final_update = {}
        try:
            logger.info("Agent task completing...")
            # Await the task ensure completion and catch exceptions if not already caught
            if not agent_task.done():
                await agent_task  # Retrieve result/exception
            elif agent_task.exception():  # Check if task finished with exception
                agent_task.result()  # Raise the exception to be caught below
            logger.info("Agent task completed processing.")
            logger.info("Skipping extra post-task LLM description generation to preserve token budget.")

            logger.info(f"Explicitly saving agent history to: {history_file}")
            webui_manager.bu_agent.save_history(history_file)

            if os.path.exists(history_file):
                final_update[history_file_comp] = gr.File(value=history_file)

            if gif_path and os.path.exists(gif_path):
                logger.info(f"GIF found at: {gif_path}")
                final_update[gif_comp] = gr.Image(value=gif_path)

        except asyncio.CancelledError:
            logger.info("Agent task was cancelled.")
            if not any(
                    "Cancelled" in msg.get("content", "")
                    for msg in webui_manager.bu_chat_history
                    if msg.get("role") == "assistant"
            ):
                webui_manager.bu_chat_history.append(
                    {"role": "assistant", "content": "**Task Cancelled**."}
                )
            final_update[chatbot_comp] = gr.update(value=webui_manager.bu_chat_history)
        except Exception as e:
            logger.error(f"Error during agent execution: {e}", exc_info=True)
            error_message = (
                f"**Agent Execution Error:**\n```\n{type(e).__name__}: {e}\n```"
            )
            if not any(
                    error_message in msg.get("content", "")
                    for msg in webui_manager.bu_chat_history
                    if msg.get("role") == "assistant"
            ):
                webui_manager.bu_chat_history.append(
                    {"role": "assistant", "content": error_message}
                )
            final_update[chatbot_comp] = gr.update(value=webui_manager.bu_chat_history)
            gr.Error(f"Agent execution failed: {e}")

        finally:
            webui_manager.bu_current_task = None  # Clear the task reference

            # Close browser/context if requested
            if should_close_browser_on_finish:
                if webui_manager.bu_browser_context:
                    logger.info("Closing browser context after task.")
                    await webui_manager.bu_browser_context.close()
                    webui_manager.bu_browser_context = None
                if webui_manager.bu_browser:
                    logger.info("Closing browser after task.")
                    await webui_manager.bu_browser.close()
                    webui_manager.bu_browser = None

            # --- 8. Final UI Update ---
            final_update.update(
                {
                    user_input_comp: gr.update(
                        value="",
                        interactive=True,
                        placeholder="Enter your next task...",
                    ),
                    run_button_comp: gr.update(value="▶️ Submit Task", interactive=True),
                    stop_button_comp: gr.update(value="⏹️ Stop", interactive=False),
                    pause_resume_button_comp: gr.update(
                        value="⏸️ Pause", interactive=False
                    ),
                    clear_button_comp: gr.update(interactive=True),
                    # Ensure final chat history is shown
                    chatbot_comp: gr.update(value=webui_manager.bu_chat_history),
                }
            )
            yield final_update

    except Exception as e:
        # Catch errors during setup (before agent run starts)
        logger.error(f"Error setting up agent task: {e}", exc_info=True)
        webui_manager.bu_current_task = None  # Ensure state is reset
        yield {
            user_input_comp: gr.update(
                interactive=True, placeholder="Error during setup. Enter task..."
            ),
            run_button_comp: gr.update(value="▶️ Submit Task", interactive=True),
            stop_button_comp: gr.update(value="⏹️ Stop", interactive=False),
            pause_resume_button_comp: gr.update(value="⏸️ Pause", interactive=False),
            clear_button_comp: gr.update(interactive=True),
            chatbot_comp: gr.update(
                value=webui_manager.bu_chat_history
                      + [{"role": "assistant", "content": f"**Setup Error:** {e}"}]
            ),
        }


# --- Button Click Handlers --- (Need access to webui_manager)


async def handle_submit(
        webui_manager: WebuiManager, components: Dict[gr.components.Component, Any]
):
    """Handles clicks on the main 'Submit' button."""
    user_input_comp = webui_manager.get_component_by_id("browser_use_agent.user_input")
    user_input_value = components.get(user_input_comp, "").strip()

    # Check if waiting for user assistance
    if webui_manager.bu_response_event and not webui_manager.bu_response_event.is_set():
        logger.info(f"User submitted assistance: {user_input_value}")
        webui_manager.bu_user_help_response = (
            user_input_value if user_input_value else "User provided no text response."
        )
        webui_manager.bu_response_event.set()
        # UI updates handled by the main loop reacting to the event being set
        yield {
            user_input_comp: gr.update(
                value="",
                interactive=False,
                placeholder="Waiting for agent to continue...",
            ),
            webui_manager.get_component_by_id(
                "browser_use_agent.run_button"
            ): gr.update(value="⏳ Running...", interactive=False),
        }
    # Check if a task is currently running (using _current_task)
    elif webui_manager.bu_current_task and not webui_manager.bu_current_task.done():
        logger.warning(
            "Submit button clicked while agent is already running and not asking for help."
        )
        gr.Info("Agent is currently running. Please wait or use Stop/Pause.")
        yield {}  # No change
    else:
        # Handle submission for a new task
        logger.info("Submit button clicked for new task.")
        # Use async generator to stream updates from run_agent_task
        async for update in run_agent_task(webui_manager, components):
            yield update


async def handle_stop(webui_manager: WebuiManager):
    """Handles clicks on the 'Stop' button."""
    logger.info("Stop button clicked.")
    agent = webui_manager.bu_agent
    task = webui_manager.bu_current_task

    if agent and task and not task.done():
        # Signal the agent to stop by setting its internal flag
        agent.state.stopped = True
        agent.state.paused = False  # Ensure not paused if stopped
        return {
            webui_manager.get_component_by_id(
                "browser_use_agent.stop_button"
            ): gr.update(interactive=False, value="⏹️ Stopping..."),
            webui_manager.get_component_by_id(
                "browser_use_agent.pause_resume_button"
            ): gr.update(interactive=False),
            webui_manager.get_component_by_id(
                "browser_use_agent.run_button"
            ): gr.update(interactive=False),
        }
    else:
        logger.warning("Stop clicked but agent is not running or task is already done.")
        # Reset UI just in case it's stuck
        return {
            webui_manager.get_component_by_id(
                "browser_use_agent.run_button"
            ): gr.update(interactive=True),
            webui_manager.get_component_by_id(
                "browser_use_agent.stop_button"
            ): gr.update(interactive=False),
            webui_manager.get_component_by_id(
                "browser_use_agent.pause_resume_button"
            ): gr.update(interactive=False),
            webui_manager.get_component_by_id(
                "browser_use_agent.clear_button"
            ): gr.update(interactive=True),
        }


async def handle_pause_resume(webui_manager: WebuiManager):
    """Handles clicks on the 'Pause/Resume' button."""
    agent = webui_manager.bu_agent
    task = webui_manager.bu_current_task

    if agent and task and not task.done():
        if agent.state.paused:
            logger.info("Resume button clicked.")
            agent.resume()
            # UI update happens in main loop
            return {
                webui_manager.get_component_by_id(
                    "browser_use_agent.pause_resume_button"
                ): gr.update(value="⏸️ Pause", interactive=True)
            }  # Optimistic update
        else:
            logger.info("Pause button clicked.")
            agent.pause()
            return {
                webui_manager.get_component_by_id(
                    "browser_use_agent.pause_resume_button"
                ): gr.update(value="▶️ Resume", interactive=True)
            }  # Optimistic update
    else:
        logger.warning(
            "Pause/Resume clicked but agent is not running or doesn't support state."
        )
        return {}  # No change


async def handle_clear(webui_manager: WebuiManager):
    """Handles clicks on the 'Clear' button."""
    logger.info("Clear button clicked.")

    # Stop any running task first
    task = webui_manager.bu_current_task
    if task and not task.done():
        logger.info("Clearing requires stopping the current task.")
        if webui_manager.bu_agent:
            webui_manager.bu_agent.stop()
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=2.0)  # Wait briefly
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        except Exception as e:
            logger.warning(f"Error stopping task on clear: {e}")
    webui_manager.bu_current_task = None

    if webui_manager.bu_controller:
        await webui_manager.bu_controller.close_mcp_client()
        webui_manager.bu_controller = None
    webui_manager.bu_agent = None

    # Reset state stored in manager
    webui_manager.bu_chat_history = []
    webui_manager.bu_response_event = None
    webui_manager.bu_user_help_response = None
    webui_manager.bu_agent_task_id = None

    logger.info("Agent state and browser resources cleared.")

    # Reset UI components
    return {
        webui_manager.get_component_by_id("browser_use_agent.chatbot"): gr.update(
            value=[]
        ),
        webui_manager.get_component_by_id("browser_use_agent.user_input"): gr.update(
            value="", placeholder="Enter your task here..."
        ),
        webui_manager.get_component_by_id(
            "browser_use_agent.agent_history_file"
        ): gr.update(value=None),
        webui_manager.get_component_by_id("browser_use_agent.recording_gif"): gr.update(
            value=None
        ),
        webui_manager.get_component_by_id("browser_use_agent.image_preview"): gr.update(
            value=None, visible=False
        ),
        webui_manager.get_component_by_id("browser_use_agent.uploaded_file_path_state"): None,
        webui_manager.get_component_by_id("browser_use_agent.image_data_state"): None,
        webui_manager.get_component_by_id("browser_use_agent.uploaded_file_row"): gr.update(
            visible=False
        ),
        webui_manager.get_component_by_id("browser_use_agent.uploaded_file_label"): gr.update(
            value=""
        ),
        webui_manager.get_component_by_id("browser_use_agent.browser_view"): gr.update(
            value="<div style='...'>Browser Cleared</div>"
        ),
        webui_manager.get_component_by_id("browser_use_agent.run_button"): gr.update(
            value="▶️ Submit Task", interactive=True
        ),
        webui_manager.get_component_by_id("browser_use_agent.stop_button"): gr.update(
            interactive=False
        ),
        webui_manager.get_component_by_id(
            "browser_use_agent.pause_resume_button"
        ): gr.update(value="⏸️ Pause", interactive=False),
        webui_manager.get_component_by_id("browser_use_agent.clear_button"): gr.update(
            interactive=True
        ),
    }



def create_browser_use_agent_tab(webui_manager: WebuiManager):
    """
    Create the run agent tab, defining UI, state, and handlers.
    Features a ChatGPT-style input pill with multimodal support.
    """
    webui_manager.init_browser_use_agent()

    # --- Define UI Components ---
    tab_components = {}
    with gr.Column():
        chatbot = gr.Chatbot(
            lambda: webui_manager.bu_chat_history,  # Load history dynamically
            elem_id="browser_use_chatbot",
            label="Agent Interaction",
            type="messages",
            height=600,
            show_copy_button=True,
        )

        # Image preview (shown when user uploads an image)
        image_preview = gr.Image(
            label="Uploaded Image",
            elem_id="image-preview-box",
            visible=False,
            interactive=False,
            type="filepath",
            height=60,
        )

        # Hidden state to carry image data for VLM
        image_data_state = gr.State(value=None)
        uploaded_file_path_state = gr.State(value=None)

        with gr.Row(visible=False) as uploaded_file_row:
            uploaded_file_label = gr.Textbox(
                label="Attached file",
                value="",
                interactive=False,
            )
            remove_uploaded_file_btn = gr.Button("Remove file", variant="secondary")

        # ======== ChatGPT-Style Input Pill ========
        with gr.Row(elem_id="chatgpt-input-pill"):
            # The '+' Upload Button (opens native file picker)
            multimodal_upload = gr.UploadButton(
                "＋",
                file_types=["image", ".pdf", ".txt", ".md", ".doc", ".docx"],
                file_count="single",
                elem_id="chat-plus-btn",
            )

            # The main borderless text input
            user_input = gr.Textbox(
                show_label=False,
                placeholder="Ask anything",
                lines=1,
                interactive=True,
                elem_id="chat-text-box",
                container=False,
            )

            # The Voice Mic Button (just a styled button)
            mic_button = gr.Button("🎤", elem_id="chat-mic-btn")

            # The White Circular Submit Button
            run_button = gr.Button("➤", elem_id="chat-send-btn")

        # ======== Hidden Audio Recorder (toggled by mic button) ========
        voice_input = gr.Audio(
            sources=["microphone"],
            type="filepath",
            show_label=False,
            elem_id="voice-recorder",
            visible=False,
        )

        # ======== Control Buttons Below the Pill ========
        with gr.Row(elem_id="agent-control-row"):
            stop_button = gr.Button(
                "⏹️ Stop", interactive=False, variant="stop", scale=2
            )
            pause_resume_button = gr.Button(
                "⏸️ Pause", interactive=False, variant="secondary", scale=2, visible=True
            )
            clear_button = gr.Button(
                "🗑️ Clear", interactive=True, variant="secondary", scale=2
            )

        browser_view = gr.HTML(
            value="<div style='width:100%; height:50vh; display:flex; justify-content:center; align-items:center; border:1px solid #ccc; background-color:#f0f0f0;'><p>Browser View (Requires Headless=True)</p></div>",
            label="Browser Live View",
            elem_id="browser_view",
            visible=False,
        )
        with gr.Column():
            gr.Markdown("### Task Outputs")
            agent_history_file = gr.File(label="Agent History JSON", interactive=False)
            recording_gif = gr.Image(
                label="Task Recording GIF",
                format="gif",
                interactive=False,
                type="filepath",
            )

    # --- Store Components in Manager ---
    tab_components.update(
        dict(
            chatbot=chatbot,
            user_input=user_input,
            clear_button=clear_button,
            run_button=run_button,
            stop_button=stop_button,
            pause_resume_button=pause_resume_button,
            agent_history_file=agent_history_file,
            recording_gif=recording_gif,
            browser_view=browser_view,
            multimodal_upload=multimodal_upload,
            mic_button=mic_button,
            voice_input=voice_input,
            image_preview=image_preview,
            image_data_state=image_data_state,
            uploaded_file_path_state=uploaded_file_path_state,
            uploaded_file_row=uploaded_file_row,
            uploaded_file_label=uploaded_file_label,
            remove_uploaded_file_btn=remove_uploaded_file_btn,
        )
    )
    webui_manager.add_components(
        "browser_use_agent", tab_components
    )  # Use "browser_use_agent" as tab_name prefix

    all_managed_components = [
        comp for comp in webui_manager.get_components() if comp.__class__.__name__ != "Row"
    ]
    run_tab_outputs = [comp for comp in tab_components.values() if comp.__class__.__name__ != "Row"]

    # --- Multimodal Handlers ---

    def handle_mic_click():
        """Toggle the hidden audio recorder visible so user can record."""
        return gr.update(visible=True)

    async def handle_voice_input(audio_filepath):
        """Transcribe voice audio using Groq Whisper STT, fill textbox, hide recorder."""
        if not audio_filepath:
            return gr.update(), gr.update(visible=False)  # Hide recorder, no text change

        logger.info(f"🎤 Voice input received: {audio_filepath}")
        try:
            groq_key = os.environ.get("GROQ_API_KEY", "")
            if groq_key:
                import httpx
                async with httpx.AsyncClient(timeout=30.0) as client:
                    with open(audio_filepath, "rb") as f:
                        resp = await client.post(
                            "https://api.groq.com/openai/v1/audio/transcriptions",
                            headers={"Authorization": f"Bearer {groq_key}"},
                            files={"file": ("audio.wav", f, "audio/wav")},
                            data={"model": "whisper-large-v3-turbo", "language": "en"},
                        )
                    if resp.status_code == 200:
                        transcribed = resp.json().get("text", "")
                        logger.info(f"🎤 Transcribed: {transcribed}")
                        return gr.update(value=transcribed), gr.update(visible=False)
                    else:
                        logger.warning(f"🎤 Groq Whisper returned {resp.status_code}: {resp.text}")
            else:
                logger.warning("🎤 GROQ_API_KEY not set, cannot transcribe voice input.")

        except Exception as e:
            logger.error(f"🎤 Voice transcription failed: {e}")

        gr.Warning("Voice transcription failed. Please type your task instead.")
        return gr.update(), gr.update(visible=False)

    def handle_file_upload(file):
        """Handle uploaded file — store image data for VLM and show preview."""
        if file is None:
            return (
                gr.update(visible=False),
                None,
                None,
                gr.update(visible=False),
                gr.update(value=""),
            )

        file_path = file.name if hasattr(file, 'name') else str(file)
        logger.info(f"📎 File uploaded: {file_path}")
        file_name = os.path.basename(file_path)

        # Check if it's an image
        img_exts = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
        if file_path.lower().endswith(img_exts):
            import base64
            try:
                with open(file_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")
                # Determine MIME type
                ext = os.path.splitext(file_path)[1].lower()
                mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                            ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp"}
                mime = mime_map.get(ext, "image/png")
                image_data_url = f"data:{mime};base64,{image_b64}"

                logger.info(f"📎 Image encoded ({len(image_b64)} chars), stored for VLM.")
                return (
                    gr.update(value=file_path, visible=True),
                    image_data_url,
                    file_path,
                    gr.update(visible=True),
                    gr.update(value=file_name),
                )
            except Exception as e:
                logger.error(f"📎 Image encoding failed: {e}")
                return (
                    gr.update(visible=False),
                    None,
                    file_path,
                    gr.update(visible=True),
                    gr.update(value=file_name),
                )
        else:
            binary_supported = {".pdf", ".docx"}
            if os.path.splitext(file_path)[1].lower() in binary_supported:
                gr.Info(f"File loaded: {os.path.basename(file_path)}")
                return (
                    gr.update(visible=False),
                    None,
                    file_path,
                    gr.update(visible=True),
                    gr.update(value=file_name),
                )

            # Non-image file: read text content and prepend to task
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(5000)  # First 5000 chars
                logger.info(f"📎 Text file read ({len(content)} chars)")
                gr.Info(f"File loaded: {os.path.basename(file_path)}")
                return (
                    gr.update(visible=False),
                    None,
                    file_path,
                    gr.update(visible=True),
                    gr.update(value=file_name),
                )
            except Exception as e:
                logger.error(f"📎 File read failed: {e}")
                return (
                    gr.update(visible=False),
                    None,
                    file_path,
                    gr.update(visible=True),
                    gr.update(value=file_name),
                )

    def clear_uploaded_file():
        return (
            gr.update(visible=False),
            None,
            None,
            gr.update(visible=False),
            gr.update(value=""),
        )

    # --- Wrappers ---
    async def submit_wrapper(
            *component_values,
    ) -> AsyncGenerator[Dict[Component, Any], None]:
        """Wrapper for handle_submit that yields its results."""
        components_dict: Dict[Component, Any] = {
            comp: value for comp, value in zip(all_managed_components, component_values)
        }
        async for update in handle_submit(webui_manager, components_dict):
            yield update

    async def stop_wrapper() -> AsyncGenerator[Dict[Component, Any], None]:
        """Wrapper for handle_stop."""
        update_dict = await handle_stop(webui_manager)
        yield update_dict

    async def pause_resume_wrapper() -> AsyncGenerator[Dict[Component, Any], None]:
        """Wrapper for handle_pause_resume."""
        update_dict = await handle_pause_resume(webui_manager)
        yield update_dict

    async def clear_wrapper() -> AsyncGenerator[Dict[Component, Any], None]:
        """Wrapper for handle_clear."""
        update_dict = await handle_clear(webui_manager)
        yield update_dict

    # --- Connect Event Handlers ---

    # Submit on button click or Enter key
    run_button.click(
        fn=submit_wrapper, inputs=all_managed_components, outputs=run_tab_outputs, trigger_mode="multiple"
    )
    user_input.submit(
        fn=submit_wrapper, inputs=all_managed_components, outputs=run_tab_outputs
    )

    # Agent control buttons
    stop_button.click(fn=stop_wrapper, inputs=None, outputs=run_tab_outputs)
    pause_resume_button.click(
        fn=pause_resume_wrapper, inputs=None, outputs=run_tab_outputs
    )
    clear_button.click(fn=clear_wrapper, inputs=None, outputs=run_tab_outputs)

    # Mic button: toggle the hidden audio recorder
    mic_button.click(
        fn=handle_mic_click,
        inputs=None,
        outputs=[voice_input],
    )

    # Voice STT: when recording is done, transcribe, fill textbox, hide recorder
    voice_input.change(
        fn=handle_voice_input,
        inputs=[voice_input],
        outputs=[user_input, voice_input],
    )

    # Vision VLM: on file upload, encode image and show preview
    multimodal_upload.upload(
        fn=handle_file_upload,
        inputs=[multimodal_upload],
        outputs=[image_preview, image_data_state, uploaded_file_path_state, uploaded_file_row, uploaded_file_label],
    )

    remove_uploaded_file_btn.click(
        fn=clear_uploaded_file,
        inputs=None,
        outputs=[image_preview, image_data_state, uploaded_file_path_state, uploaded_file_row, uploaded_file_label],
    )
