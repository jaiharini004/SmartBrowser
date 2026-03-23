# MASTER PROJECT DOCUMENT

## 1. Executive Meta-Summary (For PPT and Quick AI Context)

### Project Name and Core Purpose

SmartBrowser is an AI-first browser automation and deep research platform built as a Python monolithic application with a Gradio user interface. Its core goal is to let users express web tasks in natural language and have an autonomous browser agent execute those tasks on real websites, including navigation, extraction, and interaction. In parallel, it offers a deep-research mode that decomposes a topic into a structured plan, executes multiple browser-backed sub-queries, and synthesizes a consolidated markdown report.

The product exists to close the gap between conversational AI and practical web execution. Instead of only generating text from static model memory, SmartBrowser connects model reasoning to live browsing, files, and tools. It can ground tasks with uploaded documents, leverage multiple LLM providers, and maintain operation state across sessions. This makes it useful for automation-heavy workflows where users want both convenience and transparency via step-by-step execution traces.

### Primary Target Audience and Use Case

Primary audiences:
- Developers and technical operators building browser-driven automation workflows.
- Researchers and analysts who need structured, tool-assisted evidence gathering from the web.
- Product and growth teams running repetitive browser tasks (data collection, monitoring, form operations).
- AI workflow experimenters comparing model providers in a consistent execution shell.

Primary use cases:
- Prompt-to-browser execution for tasks like searching, extraction, and interaction.
- Multi-step research orchestration with planning, parallel searching, and synthesized reporting.
- Profile-aware browser sessions where authenticated state is reused through existing Chrome or Edge profiles.
- File-grounded tasks that use PDF, DOCX, and text content as context.

### Tech Stack Snapshot

Languages:
- Python 3.11 (application and orchestration).
- CSS and minimal JavaScript embedded in Gradio UI definitions.

Frameworks and runtime libraries:
- Gradio for UI construction and event wiring.
- browser-use for autonomous browser action loops.
- Playwright (through browser-use and direct wrappers) for browser control.
- LangChain ecosystem for model adapters and tools.
- LangGraph for stateful deep research orchestration.

Key libraries from requirements and imports:
- browser-use==0.1.48
- gradio==5.27.0
- langgraph==0.3.34
- langchain_mcp_adapters==0.0.9
- langchain-mistralai==0.2.4
- langchain-ibm==0.3.10
- langchain-community
- pypdf>=4.2.0
- python-docx>=1.1.2
- MainContentExtractor==0.0.4
- pyperclip==1.9.0
- json-repair

LLM provider integration layer includes:
- OpenAI and Azure OpenAI.
- Anthropic.
- Google.
- Groq.
- OpenRouter.
- DeepSeek.
- Ollama.
- Mistral.
- Alibaba.
- Moonshot.
- IBM.
- Grok.
- SiliconFlow.
- ModelScope.

Data storage model:
- No relational or document database is implemented in this repository.
- Persistent state is file-based (JSON and markdown artifacts in tmp directories).

Deployment:
- Docker and Docker Compose.
- Supervisor-managed multi-process container runtime.

---

## 2. System Architecture and Design (For Project Report and PPT)

### High-Level Architecture

Architectural style:
- Single-application, modular monolith.
- UI and orchestration run in one Python process during local mode.
- Browser execution and model calls are async event-driven flows.
- Deep research uses graph-style state transitions via LangGraph.

Core architectural layers:
- Presentation layer: Gradio tabs and interaction handlers.
- Orchestration layer: agent tabs invoking BrowserUseAgent or DeepResearchAgent flows.
- Agent execution layer: browser-use based runtime loops and callbacks.
- Browser abstraction layer: custom wrappers around browser and context creation.
- Tools layer: built-in actions plus MCP tool registration.
- Provider layer: multi-vendor LLM adapter/factory.
- Persistence layer: file-based config snapshots, memory JSON, task artifacts.

### Component Interaction

User interface to orchestration:
- User actions in Gradio components trigger async handlers in tab modules.
- Tab handlers read cross-tab values through WebuiManager component registry.
- WebuiManager tracks current browser, controller, and active task references.

Orchestration to execution:
- Browser Use tab creates or reuses browser, context, and controller.
- BrowserUseAgent executes step loop with callback hooks for UI streaming.
- Deep Research tab builds a graph run that loops planning, execution, synthesis.

Execution to external services:
- LLM calls are routed through provider factory with API key and endpoint resolution.
- Browser automation uses Playwright through browser-use abstractions.
- Optional MCP tools are loaded from user-provided JSON server configs.

Execution to persistence:
- Agent histories are saved into task-specific JSON files under tmp paths.
- Research plans and reports are written into markdown and JSON files.
- Memory manager stores recent task-result pairs in tmp/memory.json.
- UI save/load tab serializes managed component values to JSON snapshots.

Container topology:
- One container service exposes:
  - Gradio web interface.
  - VNC server for remote visual browser access.
  - noVNC proxy for browser access through web.
  - Optional CDP remote debug port.
- Supervisord coordinates Xvfb, x11vnc, noVNC, and webui process startup.

### File Structure Overview

Root files:
- webui.py: application entry point and CLI argument parsing.
- Dockerfile: container build with system dependencies and Playwright setup.
- docker-compose.yml: runtime environment mapping and service ports.
- supervisord.conf: process supervisor configuration.
- requirements.txt: dependency set.
- README.md: user-focused project overview.
- SECURITY.md: vulnerability disclosure process.
- docs/update-2026-03-22.md: release update notes.

Primary source directories:
- src/agent/browser_use: custom BrowserUseAgent implementation.
- src/agent/deep_research: graph-based deep research runtime.
- src/browser: browser and profile handling wrappers.
- src/controller: custom actions and MCP tool registration.
- src/utils: providers, config maps, memory, MCP schema helpers.
- src/webui: interface assembly, manager, and tab components.

Supporting directories:
- tests: script-like test files for agents, controller, providers, and Playwright checks.
- tmp: runtime artifacts such as memory file, task histories, downloads, and saved settings.

---

## 3. Module-Level Deep Dive (Crucial for the 60-page Report Expansion)

This section documents each major file and module with responsibility, key logic, and behavior.

### Root Runtime and Deployment Files

#### Module Name and Path
- webui.py

Primary responsibility:
- Loads environment variables and starts the Gradio UI server.

Key variables, classes, and functions:
- main()
  - Inputs: CLI args ip, port, theme.
  - Output: launches Gradio app.
  - Side effects: binds server address and port.

Business logic breakdown:
- Reads CLI options.
- Calls create_ui(theme_name).
- Launches with queue enabled.

#### Module Name and Path
- requirements.txt

Primary responsibility:
- Declares Python dependencies required to run the project.

Business logic breakdown:
- Not executable code, but effectively defines available provider adapters, research graph runtime, UI library, and file parsing support.

#### Module Name and Path
- docker-compose.yml

Primary responsibility:
- Defines containerized runtime settings and host-to-container port mapping.

Key runtime design details:
- Maps ports for web UI, noVNC, VNC, and CDP debug.
- Loads broad provider endpoint and key env vars.
- Includes browser and display settings.
- Healthcheck uses VNC port readiness.

Business logic breakdown:
- Acts as deployment-time configuration orchestration, not application logic.

#### Module Name and Path
- Dockerfile

Primary responsibility:
- Builds runtime image with browser, Playwright, VNC/noVNC, and application code.

Key details:
- Base image python:3.11-slim-bookworm.
- Installs OS libs needed by Chromium and UI stack.
- Installs Node.js used by MCP and tooling components.
- Installs Python requirements.
- Installs Chromium via Playwright installer.
- Starts supervisord.

#### Module Name and Path
- supervisord.conf

Primary responsibility:
- Coordinates startup of X virtual display, VNC services, noVNC proxy, and web UI process.

Business logic breakdown:
- Ensures browser-visible operations can run in headless containerized environments with remote access.

### Browser Layer

#### Module Name and Path
- src/browser/custom_browser.py

Primary responsibility:
- Extends browser-use Browser behavior for custom context creation and anti-detection launch flags.

Key functions and classes:
- class CustomBrowser(Browser)
- async new_context(config)
  - Input: BrowserContextConfig.
  - Output: CustomBrowserContext.
  - Side effect: merges browser and context settings.
- async _setup_builtin_browser(playwright)
  - Computes launch args from headless, security, rendering, and display settings.
  - Removes remote debugging port argument if port is already occupied.

Important state and variables:
- screen size computation from context config or current display.
- dynamic args sets for chromium/firefox/webkit.

Business logic breakdown:
- A configuration merge strategy allows context config to override base browser config.
- Applies defensive runtime behavior for debugging port collisions.

#### Module Name and Path
- src/browser/custom_context.py

Primary responsibility:
- Minimal subclass of BrowserContext used by CustomBrowser.

Key classes:
- class CustomBrowserContext(BrowserContext)

Business logic breakdown:
- Currently delegates almost entirely to parent class while preserving extension point for future context-specific features.

#### Module Name and Path
- src/browser/profile_utils.py

Primary responsibility:
- Discovers Chrome and Edge profiles and resolves selected profile with manual overrides.

Key functions:
- _first_existing(paths)
- _profile_dirs(base_user_data_dir)
- _read_profile_name_map(base_user_data_dir)
- _normalize_manual_profile_path(manual_user_data_dir)
- discover_browser_profiles()
- resolve_profile_selection(profile_label, manual_user_data_dir, manual_binary_path)

Business logic breakdown:
- Scans local app data for Chromium profile directories.
- Parses Local State profile info_cache for user-friendly profile names.
- Maintains manual override precedence: manual paths override dropdown presets.

Algorithmic intent:
- Improve usability and reduce setup friction by auto-suggesting launchable profile presets.

### Controller and Tooling Layer

#### Module Name and Path
- src/controller/custom_controller.py

Primary responsibility:
- Extends controller behavior with custom actions and MCP tool integration.

Key classes and functions:
- class CustomController(Controller)
- __init__(exclude_actions, output_model, ask_assistant_callback)
- _register_custom_actions()
  - Registers ask_for_assistant action.
  - Registers upload_file action with path whitelist checks.
- async act(action, browser_context, page_extraction_llm, sensitive_data, available_file_paths, context)
  - Executes either MCP-prefixed tools or registry actions.
- async setup_mcp_client(mcp_server_config)
- register_mcp_tools()
- async close_mcp_client()

Important side effects:
- Dynamic tool registration into controller registry.
- Upload action can set files into DOM file inputs via Playwright.

Business logic breakdown:
- Standardizes action execution path for built-in and MCP tools.
- Converts mixed return types into ActionResult for consistent agent processing.

### Utilities Layer

#### Module Name and Path
- src/utils/config.py

Primary responsibility:
- Declares provider display names and model lists for UI dropdowns.

Key variables:
- PROVIDER_DISPLAY_NAMES dictionary.
- model_names dictionary with curated model options by provider.

Business logic breakdown:
- Serves as static provider/model configuration map for UI and defaults.

#### Module Name and Path
- src/utils/llm_provider.py

Primary responsibility:
- Provides factory for creating provider-specific chat model objects and wraps DeepSeek reasoning variants.

Key classes:
- DeepSeekR1ChatOpenAI(ChatOpenAI)
  - Extracts reasoning_content from DeepSeek reasoner responses.
- DeepSeekR1ChatOllama(ChatOllama)
  - Parses think tags and reasoning output from local DeepSeek-R1 formats.

Key function:
- get_llm_model(provider, **kwargs)
  - Inputs: provider, model_name, temperature, base_url, api_key, context settings.
  - Output: provider-appropriate chat model instance.
  - Side effects: validates required keys for non-local providers and raises informative errors.

Business logic breakdown:
- Resolves API keys from kwargs or environment variables.
- Selects default base URLs per provider when not manually supplied.
- Normalizes many providers to a ChatOpenAI-compatible interface where possible.

Security and reliability implications:
- Hard fail when API key is missing for remote providers.
- Allows custom endpoint override, useful for enterprise proxies but increases misconfiguration risk.

#### Module Name and Path
- src/utils/mcp_client.py

Primary responsibility:
- Initializes MultiServerMCPClient and converts tool schemas into controller-compatible param models.

Key functions:
- async setup_mcp_client_and_tools(mcp_server_config)
- create_tool_param_model(tool)
- resolve_type(prop_details, prefix)

Business logic breakdown:
- Supports both explicit and nested mcpServers config formats.
- Converts JSON schema tool definitions into Pydantic models with constraints.
- Handles enum, union, nested object, and formatted-string schema patterns.

Algorithmic details:
- Recursive JSON schema to Python type mapping with constraint propagation.

#### Module Name and Path
- src/utils/memory_manager.py

Primary responsibility:
- Maintains short rolling memory of recent user tasks and outcomes.

Key class and methods:
- class MemoryManager
- add_memory(task, result)
- get_memory_context()
- clear_memory()

Business logic breakdown:
- Appends task-result records into tmp/memory.json.
- Caps memory size to last 10 entries for token economy.
- Formats memory as a text preamble injected into future prompts.

#### Module Name and Path
- src/utils/utils.py

Primary responsibility:
- Misc helper functions for image encoding and artifact retrieval.

Key functions:
- encode_image(img_path)
- get_latest_files(directory, file_types)

Business logic breakdown:
- Encodes binary image data to base64 for multimodal model messages.
- Finds latest completed artifact files older than one second to avoid partial reads.

### Browser Use Agent Layer

#### Module Name and Path
- src/agent/browser_use/browser_use_agent.py

Primary responsibility:
- Extends core browser-use Agent with additional reliability controls and signal handling.

Key class:
- class BrowserUseAgent(Agent)

Key methods:
- _set_tool_calling_method()
  - Chooses calling mode based on provider/model family characteristics.
- async run(max_steps, on_step_start, on_step_end)
  - Main agent loop with control flags, backoff, fail-fast logic, and callback lifecycle.

Key execution behaviors:
- Installs Ctrl+C signal handler for pause/resume behavior.
- Uses consecutive failure backoff: min(10 * failures, 30) seconds.
- Tracks repeated failures on same URL and stops early when threshold reached.
- Checks likely anti-bot pages by title and inserts wait/reload healing steps.
- Persists generated playwright scripts when configured.
- Generates execution GIF artifacts when enabled.

Business logic breakdown:
- This module enforces runtime robustness around the base agent step executor.
- It prioritizes avoiding infinite loops and reducing repeated model and browser failures.

### Deep Research Agent Layer

#### Module Name and Path
- src/agent/deep_research/deep_research_agent.py

Primary responsibility:
- Implements graph-driven multi-step research with task planning, parallel browsing, and synthesis.

Key models and types:
- BrowserSearchInput(BaseModel)
- ResearchTaskItem(TypedDict)
- ResearchCategoryItem(TypedDict)
- DeepResearchState(TypedDict)

Key orchestration functions:
- run_single_browser_task(...)
- _run_browser_search_tool(...)
- create_browser_search_tool(...)
- planning_node(state)
- research_execution_node(state)
- synthesis_node(state)
- should_continue(state)

Persistence helpers:
- _load_previous_state(task_id, output_dir)
- _save_plan_to_md(plan, output_dir)
- _save_search_results_to_json(results, output_dir)
- _save_report_to_md(report, output_dir)

Key class:
- class DeepResearchAgent
  - _setup_tools(task_id, stop_event, max_parallel_browsers)
  - _compile_graph()
  - async run(topic, task_id, save_dir, max_parallel_browsers)
  - async stop()
  - async _stop_lingering_browsers(task_id)

Business logic breakdown:
- Planning stage asks LLM to return JSON categories and tasks.
- Execution stage binds tools, asks LLM to choose tool calls for current task, executes tool calls, then updates task state.
- Search tool path can execute multiple browser subqueries concurrently with semaphore-limited parallelism.
- Synthesis stage compiles gathered findings into a markdown report.
- Resume support loads prior plan and search file artifacts and continues from first pending task.

Important side effects:
- Creates per-task directories in tmp/deep_research.
- Spawns browser agents for each query execution.
- Writes progress and final report artifacts.

### Web UI Core Layer

#### Module Name and Path
- src/webui/interface.py

Primary responsibility:
- Builds overall Gradio app, theming, and tab composition.

Key function:
- create_ui(theme_name)

Business logic breakdown:
- Defines substantial CSS-based visual theme and layout.
- Defines JS snippet to enforce dark theme query parameter.
- Initializes WebuiManager and mounts five tab creators:
  - agent settings
  - browser settings
  - run agent
  - deep research
  - load and save config

#### Module Name and Path
- src/webui/webui_manager.py

Primary responsibility:
- Stores UI component registry and mutable runtime state for both agents.

Key class:
- class WebuiManager

Key state fields:
- component maps: id_to_component and component_to_id.
- browser-use state: bu_agent, bu_browser, bu_browser_context, bu_controller, bu_chat_history, task ids.
- deep-research state: dr_agent, dr_current_task, dr_agent_task_id, dr_save_dir.

Key methods:
- init_browser_use_agent()
- init_deep_research_agent()
- add_components(tab_name, components_dict)
- get_component_by_id(comp_id)
- save_config(components)
- load_config(config_path)

Business logic breakdown:
- Provides cross-tab value access and event interoperability.
- Enables consistent load and save behavior for interactive component values.

### Web UI Tab Modules

#### Module Name and Path
- src/webui/components/agent_settings_tab.py

Primary responsibility:
- Renders and wires settings controls for main LLM and planner LLM, plus MCP config.

Key functions:
- update_model_dropdown(llm_provider)
- async update_mcp_server(mcp_file, webui_manager)
- create_agent_settings_tab(webui_manager)

Key controls exposed:
- provider/model selection.
- temperature and vision toggles.
- ollama context settings.
- base URL and API key overrides.
- force task planning toggle.
- tool calling method dropdown.

Business logic breakdown:
- Dynamically updates model dropdown options based on selected provider.
- Closes/reloads MCP connection when MCP JSON changes.

#### Module Name and Path
- src/webui/components/browser_settings_tab.py

Primary responsibility:
- Renders browser runtime settings and profile discovery controls.

Key functions:
- async close_browser(webui_manager)
- create_browser_settings_tab(webui_manager)

Key controls:
- detected profile dropdown and refresh.
- manual binary path and user data path.
- own browser, keep open, headless, disable security.
- window dimensions and CDP/WSS endpoints.
- output path settings for recordings, traces, history, downloads.

Business logic breakdown:
- On config changes, closes current browser/context to avoid inconsistent reused state.
- Resolves profile selection using helper utility and updates relevant controls.

#### Module Name and Path
- src/webui/components/browser_use_agent_tab.py

Primary responsibility:
- Implements interactive BrowserUseAgent task execution loop and UI streaming.

Key helper functions:
- _extract_uploaded_file_context(file_path)
- _build_task_with_guardrails(task, uploaded_context)
- _initialize_llm(...)
- _initialize_llm_with_fallback(...)
- _format_agent_output(model_output)
- _extract_last_public_page(history)
- _build_site_description(page_url, page_title, task)

Key lifecycle handlers:
- _handle_new_step(...)
- _handle_done(...)
- _ask_assistant_callback(...)
- run_agent_task(...)
- handle_submit(...)
- handle_stop(...)
- handle_pause_resume(...)
- handle_clear(...)
- create_browser_use_agent_tab(...)

Business logic breakdown:
- Combines user task with execution guardrails and uploaded file context.
- Initializes main and planner LLMs, including fallback behavior.
- Auto-disables unsupported vision for certain providers.
- Creates browser/context/controller and reuses them depending on keep-open setting.
- Streams step screenshots and tool outputs into chat UI.
- Handles user-assist pauses and response continuation.
- Saves JSON history and optional GIF artifacts per task id.
- Supports file upload states and voice transcription from Groq endpoint.

#### Module Name and Path
- src/webui/components/deep_research_agent_tab.py

Primary responsibility:
- Connects DeepResearchAgent lifecycle to Gradio controls and live markdown updates.

Key functions:
- _initialize_llm(...)
- _read_file_safe(file_path)
- run_deep_research(webui_manager, components)
- stop_deep_research(webui_manager)
- update_mcp_server(mcp_file, webui_manager)
- create_deep_research_agent_tab(webui_manager)

Business logic breakdown:
- Reads settings from other tabs and constructs llm and browser config for deep research agent.
- Validates safe save directory root under tmp/deep_research.
- Starts graph run and monitors research_plan.md and report.md for progressive UI updates.
- Exposes stop behavior that signals agent stop and attempts to preserve report output when available.

#### Module Name and Path
- src/webui/components/load_save_config_tab.py

Primary responsibility:
- UI for exporting and importing current tab settings.

Key function:
- create_load_save_config_tab(webui_manager)

Business logic breakdown:
- Save button serializes interactive values to timestamped JSON.
- Load button hydrates components from uploaded JSON via manager mapping.

### Tests and Quality Layer

#### Module Name and Path
- tests/test_agents.py

Primary responsibility:
- Manual/interactive-style async scripts for browser agent and deep research behavior.

Observed characteristics:
- Contains executable task examples and environment-dependent runs.
- Includes MCP server examples and local browser profile usage.
- Not written as strict unit tests with assertions throughout.

#### Module Name and Path
- tests/test_controller.py

Primary responsibility:
- Manual scripts for MCP client and controller action invocation.

Observed characteristics:
- Contains debugger breakpoints and runtime loops.
- Uses concrete external tools (desktop-commander) and may require local runtime dependencies.

#### Module Name and Path
- tests/test_llm_api.py

Primary responsibility:
- Provider smoke checks for model initialization and prompt execution.

Observed characteristics:
- Multiple provider test functions.
- Optional image inputs for multimodal checks.
- Mostly manual execution style.

#### Module Name and Path
- tests/test_playwright.py

Primary responsibility:
- Playwright persistent-context connectivity check.

Observed characteristics:
- Uses interactive input prompt to close browser.
- More diagnostic script than CI-friendly unit test.

---

## 4. Data Flow and State Management (For Project Report)

### Data Lifecycle

Primary lifecycle example: Browser Use task from user input to persisted outputs.

Step-by-step flow:
1. User enters task in Run Agent tab input and optionally uploads a file.
2. browser_use_agent_tab handler reads task and uploaded file path state.
3. Uploaded file context is extracted for supported types.
4. Guardrail policy text is appended to user task.
5. Agent settings are read from manager component registry.
6. Browser settings are read and profile resolution is applied.
7. Main LLM and optional planner LLM are initialized.
8. Controller is initialized and MCP tools registered if configured.
9. Browser and browser context are created or reused.
10. BrowserUseAgent is created or updated with new task.
11. Agent run loop executes up to max steps.
12. Each step produces callback updates with screenshot and model output.
13. Final summary and page description are posted to chat.
14. Task history is persisted to tmp/agent_history/task_id/task_id.json.
15. Optional GIF artifact is generated and exposed in UI.
16. Task and result summary are appended to tmp/memory.json.
17. UI components are reset to ready state.

Deep research lifecycle example:
1. User enters research topic and optional resume task id.
2. Tab handler builds LLM and browser config from shared settings.
3. DeepResearchAgent initializes tools including browser search and optional MCP tools.
4. Graph planning node generates category-task plan.
5. Plan file is written to research_plan.md.
6. Execution node iterates task-by-task and invokes tool-calling LLM.
7. Browser search tool deduplicates and runs query tasks in parallel.
8. Search results are appended and saved to search_info.json.
9. Graph transitions repeat until tasks complete or stop requested.
10. Synthesis node generates final markdown report.
11. Report file is written to report.md and linked in UI.

### State Management

State mechanism summary:
- No Redux-like frontend state manager is used.
- State is held in Python objects and Gradio component values.
- WebuiManager is the central runtime state holder.
- Agents maintain their own internal state objects and histories.
- Persistence is file-based JSON/markdown in tmp directories.

State domains:
- UI component state
  - Stored in Gradio components and manager maps.
- Browser Use runtime state
  - Agent object, browser/context refs, chat history, running task handle.
- Deep Research runtime state
  - Current run task id, stop event, plan and result files, runner task.
- Provider and config state
  - Pulled from environment variables and interactive fields.
- Memory state
  - Last 10 task-result records in tmp/memory.json.

Concurrency and mutability:
- Async tasks for agent runs and periodic UI update loops.
- Stop/pause flags are mutable and polled in run loops.
- Deep research uses threading.Event for stop signaling across asynchronous execution.

### Database Schema and Models

Database status:
- No SQL or NoSQL database schema exists in this codebase.

Equivalent data models in file and in-memory form:

Deep research typed models:
- ResearchTaskItem
  - task_description
  - status
  - queries
  - result_summary
- ResearchCategoryItem
  - category_name
  - tasks
- DeepResearchState
  - task_id
  - topic
  - research_plan
  - search_results
  - llm
  - tools
  - output_dir
  - browser_config
  - final_report
  - current_category_index
  - current_task_index_in_category
  - stop_requested
  - error_message
  - messages

MCP tool schema model:
- create_tool_param_model dynamically generates Pydantic param models from tool schemas.

Memory model:
- tmp/memory.json entries
  - task
  - result

Agent history model:
- browser-use AgentHistoryList serialization per task id.

Relationships:
- One deep research task id has one plan file, one search result file, one report file.
- One browser-use task id has one history JSON and optional GIF artifact.
- Memory file keeps many task-result pairs with capped length.

---

## 5. Algorithmic Innovations and Methodology (For Research Paper)

### Core Algorithms

1. Consecutive-failure backoff algorithm
- Location: BrowserUseAgent.run
- Formula: min(10 * consecutive_failures, 30)
- Intent: reduce repeated provider throttling and transient failures.

2. Same-URL repeated failure fail-fast guard
- Location: BrowserUseAgent.run
- Logic:
  - track last failed URL.
  - increment repeated_failures_same_url when identical.
  - early stop when repeated failures and consecutive failure thresholds are met.
- Intent: avoid infinite loops and hallucinated URL retries.

3. Query normalization and deduplication for deep research
- Location: _run_browser_search_tool
- Logic:
  - strip whitespace.
  - lowercase canonical key.
  - remove duplicates.
  - cap list size to configured parallel limit.
- Intent: reduce redundant web tasks and token spend.

4. Hierarchical plan generation and stateful execution
- Location: planning_node plus research_execution_node plus should_continue
- Logic:
  - produce category-task plan.
  - execute tasks sequentially while each task may run parallel subqueries.
  - transition until synthesis state.
- Intent: structure research into explainable and resumable phases.

5. JSON schema to Pydantic model conversion
- Location: resolve_type and create_tool_param_model
- Logic:
  - recursively resolve primitive, enum, arrays, objects, union/allOf and constraints.
- Intent: safe runtime binding of external MCP tools with validated inputs.

6. Profile discovery and resolution heuristic
- Location: profile_utils module.
- Logic:
  - discover local Chrome and Edge user data directories.
  - parse Local State profile names.
  - present friendly labels while preserving manual override precedence.
- Intent: simplify authenticated browser reuse with minimal setup friction.

7. Uploaded file context grounding heuristic
- Location: _extract_uploaded_file_context
- Logic:
  - parse supported file types into bounded excerpts.
  - append excerpt to task guardrails for grounding.
- Intent: reduce hallucinations and improve task specificity.

### Performance Optimizations

Implemented optimizations:
- Backoff strategy to avoid aggressive retry loops.
- Query deduplication before launching parallel browser tasks.
- Memory capped at last 10 records to limit prompt bloat.
- File artifact retrieval checks for write completion using timestamp threshold.
- Optional keep-browser-open mode to avoid browser restart overhead.
- Removed extra post-task LLM completion in Browser Use tab finalization path.

Optimization opportunities not yet implemented:
- Provider-side token caching and response caching.
- Circuit breaker around failing providers.
- Structured retry policy based on error class and endpoint response codes.
- More efficient screenshot cadence and adaptive capture.

### Novelty and Research Value

Potential contributions to applied AI systems literature:
- Practical coupling of LLM planning with real browser execution in a user-facing, multi-provider architecture.
- Hierarchical deep-research workflow that combines graph state management with browser tool-grounded evidence collection.
- Human-in-the-loop fallback action integrated into autonomous execution loops.
- Dynamic MCP tool schema adaptation from JSON schema to strongly typed invocation models.

Research angles:
- Reliability tradeoffs in autonomous browser agents under anti-bot pressure.
- Cost and quality effects of guardrail prompts plus planner fallback strategies.
- Comparative provider behavior in tool-calling and multimodal browsing tasks.

---

## 6. Security, Limitations, and Future Scope (For Research Paper and Report)

### Security Implementations

Implemented controls visible in code:
- Environment-variable-first credential pattern for provider API keys.
- Upload action whitelist check that verifies path is part of available_file_paths.
- Basic safe root check for deep-research output directory normalization.
- Signal-based pause and stop controls to interrupt unsafe or runaway actions.
- Browser-use sensitive-data-aware script-saving hooks available when configured.

Security relevant operational files:
- SECURITY.md provides disclosure workflow via GitHub security advisory process.

### Current Limitations and Bottlenecks

Critical technical limitations:
- No database; all persistence is file-based and local, limiting multi-user scale.
- Tests are primarily script-style and environment-dependent, not robust CI-quality unit/integration suites.
- MCP tool trust model is permissive; external command-based servers can execute powerful actions.
- Minimal explicit request timeout governance in top-level provider factory wrappers.
- Limited explicit sanitization for uploaded file text before prompt injection.
- Potential race conditions around shared browser/profile resources in highly parallel scenarios.
- Deep research state persistence depends on local files and may be brittle if files are externally altered.

Operational limitations:
- Requires careful environment setup and API key management.
- Behavior quality strongly depends on selected model and provider stability.
- Browser anti-bot pages still require manual intervention in many cases.
- No built-in authentication or multi-tenant access control in UI server.

Documentation and process limitations:
- Current test scripts include debugger hooks and interactive prompts, reducing automation readiness.
- Some utility modules contain unused imports and technical debt patterns that may affect maintainability.

### Future Roadmap

Architecture and scalability roadmap:
- Add service boundaries for execution workers and queue-backed scheduling.
- Introduce persistent database for run metadata, reports, and memory indexing.
- Add optional multi-user auth layer and workspace separation.

Reliability and performance roadmap:
- Add robust timeout, retry, and circuit-breaker policies by provider and tool class.
- Add adaptive screenshot and observation strategies to reduce latency and token usage.
- Add deterministic replay artifacts and trace viewer.

Security roadmap:
- Implement MCP server allowlist and sandbox constraints.
- Add upload file scanning and stricter content filtering.
- Encrypt local memory and task artifacts when handling sensitive tasks.

Research-method roadmap:
- Add benchmark harness for provider comparison on browser and deep research tasks.
- Add reproducible experiments and metrics collection (latency, cost, completion quality).
- Add formal evaluation datasets for browsing and synthesis quality.

Quality engineering roadmap:
- Convert script-style tests into deterministic pytest suites.
- Add integration tests for full Browser Use and Deep Research workflows.
- Add CI for lint, type checks, and smoke execution with mocked providers.

---

## Appendix A: End-to-End Trace Narratives

### A.1 Browser Use Trace

Narrative:
- User opens Run Agent tab.
- User writes objective and optionally uploads supporting file.
- System builds enriched prompt from task plus policy plus file context excerpt.
- LLM and optional planner LLM are prepared using provider factory.
- Browser and context are created with settings including profile selection.
- Agent loop executes actions with observation cycles.
- UI receives streamed screenshots and action JSON dumps.
- Upon completion, summary and site description are posted.
- JSON history and optional GIF are saved and exposed.
- Task-result is written into memory file for next-run context.

### A.2 Deep Research Trace

Narrative:
- User opens Deep Research tab and submits a topic.
- Agent creates or resumes task folder.
- Planning node generates category-task plan and saves markdown plan.
- Execution node iterates each task and triggers tool calls.
- Browser search tool executes distinct queries in parallel lanes.
- Results are incrementally written to JSON.
- Synthesis node composes final report and saves markdown.
- UI monitors files and updates display and downloadable report artifact.

### A.3 MCP Tool Trace

Narrative:
- User uploads MCP JSON config.
- Controller closes existing MCP client.
- New MultiServerMCPClient is started.
- Server tools are introspected.
- Each tool is registered with generated parameter model.
- Agent can now call mcp.server.tool actions through common act path.

---

## Appendix B: Explicit File-by-File Responsibility Matrix

Root files matrix:
- webui.py
  - Runtime bootstrap and CLI argument parsing.
- Dockerfile
  - Build-time package installation and executable startup command.
- docker-compose.yml
  - Runtime env and networking mapping.
- supervisord.conf
  - Process startup order and restart policy.
- requirements.txt
  - Python dependency manifest.
- README.md
  - End-user overview and setup guide.
- SECURITY.md
  - Security reporting policy.
- docs/update-2026-03-22.md
  - Release notes and change summary.

Source matrix:
- src/agent/browser_use/browser_use_agent.py
  - Reliability-enhanced browser-use loop.
- src/agent/deep_research/deep_research_agent.py
  - Graph-orchestrated research planning and report synthesis.
- src/browser/custom_browser.py
  - Browser launch customization and context construction.
- src/browser/custom_context.py
  - Context extension wrapper.
- src/browser/profile_utils.py
  - Profile discovery and selection resolution.
- src/controller/custom_controller.py
  - Custom actions and MCP tool binding.
- src/utils/config.py
  - Provider and model maps.
- src/utils/llm_provider.py
  - Unified model factory and DeepSeek wrappers.
- src/utils/mcp_client.py
  - MCP client setup and schema conversion.
- src/utils/memory_manager.py
  - Rolling short-term run memory.
- src/utils/utils.py
  - Utility functions for image and artifact operations.
- src/webui/interface.py
  - Global UI composition and styling.
- src/webui/webui_manager.py
  - Shared component and runtime state manager.
- src/webui/components/agent_settings_tab.py
  - LLM/planner/MCP setting controls.
- src/webui/components/browser_settings_tab.py
  - Browser configuration controls and profile options.
- src/webui/components/browser_use_agent_tab.py
  - Interactive browser task execution and streaming UI.
- src/webui/components/deep_research_agent_tab.py
  - Deep research run controls and report monitoring.
- src/webui/components/load_save_config_tab.py
  - Save/load UI settings.

Test matrix:
- tests/test_agents.py
  - Agent and parallel task script checks.
- tests/test_controller.py
  - MCP and controller action script checks.
- tests/test_llm_api.py
  - Provider smoke scripts.
- tests/test_playwright.py
  - Browser connection smoke script.

---

## Appendix C: Risk Register (Code-Derived)

High-priority risks:
- Untrusted MCP command execution risk.
- Prompt injection risk from uploaded textual content.
- Shared profile and session leakage risk in reused browser contexts.
- Weak test automation and CI confidence for production hardening.

Medium-priority risks:
- Provider endpoint misconfiguration due to many optional overrides.
- Potential file artifact growth under tmp without retention policy.
- Mixed exception handling quality in long async flows.

Low-priority risks:
- Cosmetic UI or theming regressions.
- Minor utility import cleanliness and style inconsistencies.

Mitigations suggested:
- Sandbox MCP servers.
- Add input sanitization and scanning on uploads.
- Add retention and cleanup policies for tmp artifacts.
- Build deterministic tests with mocks and CI gates.

---

## Appendix D: Suggested 60-page Expansion Blueprint

Volume I: Product and Architecture Foundations
- Chapter 1: Problem framing and user personas.
- Chapter 2: System architecture and module boundaries.
- Chapter 3: Deployment topology and environment management.

Volume II: Core Runtime Internals
- Chapter 4: Browser agent execution lifecycle.
- Chapter 5: Deep research graph methodology.
- Chapter 6: Provider abstraction and model interoperability.

Volume III: Tooling, State, and Persistence
- Chapter 7: MCP integration and schema translation.
- Chapter 8: State model and file persistence semantics.
- Chapter 9: UI manager design and cross-tab component linkage.

Volume IV: Reliability, Security, and Evaluation
- Chapter 10: Reliability heuristics and failure strategies.
- Chapter 11: Security model and threat analysis.
- Chapter 12: Testing status, gaps, and validation roadmap.

Volume V: Research Contribution and Future Work
- Chapter 13: Methodological novelty and reproducibility.
- Chapter 14: Benchmark design and metrics.
- Chapter 15: Future architecture and research directions.

---

## Appendix E: Slide Deck Seed Outline (PPT Source)

Slide 1:
- SmartBrowser title and one-line mission.

Slide 2:
- Why this product exists.

Slide 3:
- End-to-end architecture diagram.

Slide 4:
- Browser Use runtime flow.

Slide 5:
- Deep Research graph flow.

Slide 6:
- LLM provider abstraction and model coverage.

Slide 7:
- Browser profile and session persistence strategy.

Slide 8:
- MCP integration and dynamic tool registration.

Slide 9:
- Reliability controls (backoff, fail-fast, stop/pause).

Slide 10:
- Security posture and key risks.

Slide 11:
- Test posture and quality roadmap.

Slide 12:
- Future scope and research opportunities.

---

## Appendix F: Structured AI-Readable Context Block

System identity:
- Name: SmartBrowser
- Category: AI browser automation plus deep research
- Runtime: Python monolith with Gradio UI

Core capabilities:
- Natural-language task execution on live browser pages
- Planner-enhanced automation with optional fallback
- Parallel research query execution and synthesis
- Optional MCP tool augmentation
- File and voice grounded workflows

Control and observability:
- Step callbacks with screenshot and action output
- Stop and pause controls
- Task history JSON and optional GIF artifact generation

Persistence:
- tmp/memory.json for rolling run memory
- tmp/agent_history for execution histories
- tmp/deep_research for plan, search, and report artifacts
- tmp/webui_settings for UI state snapshots

Provider abstraction:
- Unified get_llm_model factory
- Provider-specific base URL and key routing
- Specialized DeepSeek reasoner wrappers for reasoning extraction

Research graph:
- Plan node
- Execute node
- Synthesis node
- Conditional routing with stop and completion checks

Known constraints:
- No database and no built-in auth
- Script-style tests and limited CI-grade deterministic coverage
- External tool trust concerns via MCP

---

## Conclusion

This master document captures the complete architecture, module mechanics, data lifecycle, algorithms, state model, security posture, limitations, and expansion roadmap of the SmartBrowser repository as currently implemented. It is intentionally structured to be reusable by four downstream activities: human onboarding, AI contextual understanding, slide deck creation, and long-form technical and academic writing.

---

## Appendix G: Function and Class Catalog (Exhaustive Source Index)

### G.1 src/agent/browser_use/browser_use_agent.py

Class: BrowserUseAgent
- Parent type:
  - browser_use.agent.service.Agent
- Responsibility:
  - Reliability-enhanced run loop for browser-use task execution.
- Notable state usage:
  - self.state.paused
  - self.state.stopped
  - self.state.consecutive_failures
  - self.state.history

Method: _set_tool_calling_method
- Inputs:
  - none (reads settings and model metadata).
- Output:
  - tool calling method or None.
- Behavior:
  - Auto maps based on model capabilities and chat model library.

Method: run
- Inputs:
  - max_steps
  - on_step_start
  - on_step_end
- Output:
  - AgentHistoryList
- Side effects:
  - Registers signal handler.
  - Performs backoff sleeps.
  - Calls step loop.
  - May save Playwright script.
  - Closes resources and may generate GIF.
- Reliability features:
  - repeated URL fail-fast.
  - anti-bot title checks.
  - auto page reload on repeated failures.

### G.2 src/agent/deep_research/deep_research_agent.py

Function: run_single_browser_task
- Inputs:
  - task_query
  - task_id
  - llm
  - browser_config
  - stop_event
  - use_vision
- Output:
  - dict with query, result/error, status.
- Side effects:
  - Creates and closes browser/context.
  - Instantiates BrowserUseAgent.
  - Registers instance in global map.

Class: BrowserSearchInput
- Field:
  - queries list of strings.
- Purpose:
  - Validated arguments for parallel browser search tool.

Function: _run_browser_search_tool
- Inputs:
  - queries
  - task_id
  - llm
  - browser_config
  - stop_event
  - max_parallel_browsers
- Output:
  - list of per-query execution dicts.
- Algorithm:
  - normalize
  - deduplicate
  - semaphore-constrained parallel execution
  - exception-safe result projection

Function: create_browser_search_tool
- Inputs:
  - llm
  - browser_config
  - task_id
  - stop_event
  - max_parallel_browsers
- Output:
  - StructuredTool named parallel_browser_search.
- Side effects:
  - binds runtime dependencies with partial.

TypedDict: ResearchTaskItem
- Fields:
  - task_description
  - status
  - queries
  - result_summary

TypedDict: ResearchCategoryItem
- Fields:
  - category_name
  - tasks

TypedDict: DeepResearchState
- Fields:
  - task_id
  - topic
  - research_plan
  - search_results
  - llm
  - tools
  - output_dir
  - browser_config
  - final_report
  - current_category_index
  - current_task_index_in_category
  - stop_requested
  - error_message
  - messages

Function: _load_previous_state
- Inputs:
  - task_id
  - output_dir
- Output:
  - state updates dict.
- Side effects:
  - reads plan and search files from disk.
- Recovery behavior:
  - finds first pending task location.

Function: _save_plan_to_md
- Inputs:
  - plan
  - output_dir
- Output:
  - none.
- Side effects:
  - writes research_plan.md.

Function: _save_search_results_to_json
- Inputs:
  - results
  - output_dir
- Output:
  - none.
- Side effects:
  - writes search_info.json.

Function: _save_report_to_md
- Inputs:
  - report
  - output_dir
- Output:
  - none.
- Side effects:
  - writes report.md.

Function: planning_node
- Inputs:
  - DeepResearchState
- Output:
  - partial state update dict.
- Behavior:
  - resumes prior plan or generates new hierarchical JSON plan.
  - normalizes tasks and category structures.

Function: research_execution_node
- Inputs:
  - DeepResearchState
- Output:
  - state updates including task progression and message history.
- Behavior:
  - binds tools to LLM
  - asks model to invoke relevant tools for current task
  - stores tool outputs and updates task status

Function: synthesis_node
- Inputs:
  - DeepResearchState
- Output:
  - final_report or error_message state updates.
- Behavior:
  - formats findings and plan summary
  - calls LLM to produce markdown report
  - persists output

Function: should_continue
- Inputs:
  - DeepResearchState
- Output:
  - route label string
- Behavior:
  - determines loop, synthesis, or early end routing.

Class: DeepResearchAgent
- Constructor fields:
  - llm
  - browser_config
  - mcp_server_config
  - mcp_client
  - stopped
  - graph
  - current_task_id
  - stop_event
  - runner

Method: _setup_tools
- Inputs:
  - task_id
  - stop_event
  - max_parallel_browsers
- Output:
  - iterable of tools
- Behavior:
  - includes file tools, browser search tool, optional MCP tools.

Method: close_mcp_client
- Behavior:
  - closes async MCP context if active.

Method: _compile_graph
- Behavior:
  - creates state graph with planning, execution, synthesis, and end nodes.

Method: run
- Inputs:
  - topic
  - task_id
  - save_dir
  - max_parallel_browsers
- Output:
  - dict with status, message, task_id, final_state.
- Side effects:
  - creates task directories
  - writes artifacts
  - sets and clears global stop flags

Method: _stop_lingering_browsers
- Behavior:
  - stops BrowserUseAgent instances associated with task id prefix.

Method: stop
- Behavior:
  - sets stop event
  - marks state and attempts browser instance stop.

Method: close
- Behavior:
  - resets stopped state.

### G.3 src/browser/custom_browser.py

Class: CustomBrowser
- Parent:
  - browser_use.browser.browser.Browser

Method: new_context
- Inputs:
  - optional BrowserContextConfig
- Output:
  - CustomBrowserContext

Method: _setup_builtin_browser
- Inputs:
  - Playwright
- Output:
  - Playwright Browser instance
- Features:
  - dynamic screen sizing
  - docker/headless/security args
  - remote debugging port collision detection

### G.4 src/browser/custom_context.py

Class: CustomBrowserContext
- Parent:
  - browser_use.browser.context.BrowserContext
- Constructor:
  - browser
  - config
  - state

### G.5 src/browser/profile_utils.py

Function: _first_existing
- Returns first existing path in ordered list.

Function: _profile_dirs
- Lists allowed Chromium profile dirs excluding system and guest.

Function: _read_profile_name_map
- Parses Local State to map profile folder names to display names.

Function: _normalize_manual_profile_path
- Splits manual path into user_data_dir and optional profile directory.

Function: discover_browser_profiles
- Detects Chrome and Edge binaries and profile presets.

Function: resolve_profile_selection
- Combines dropdown preset with manual overrides.

### G.6 src/controller/custom_controller.py

Class: CustomController
- Parent:
  - browser_use.controller.service.Controller

Method: __init__
- Sets callbacks and MCP state.

Method: _register_custom_actions
- Registers:
  - ask_for_assistant
  - upload_file

Action: ask_for_assistant
- Inputs:
  - query
  - browser
- Output:
  - ActionResult containing user response linkage.

Action: upload_file
- Inputs:
  - index
  - path
  - browser
  - available_file_paths
- Output:
  - ActionResult success or error.

Method: act
- Executes action model entries and returns normalized ActionResult.

Method: setup_mcp_client
- Initializes MCP client and registers tools.

Method: register_mcp_tools
- Adds mcp.server.tool actions into registry with generated param model.

Method: close_mcp_client
- Closes MCP async context.

### G.7 src/utils/config.py

Data object: PROVIDER_DISPLAY_NAMES
- Human-readable provider names for UI and errors.

Data object: model_names
- Curated model list per provider key.

### G.8 src/utils/llm_provider.py

Class: DeepSeekR1ChatOpenAI
- Specialized invoke and ainvoke behavior to extract reasoning content.

Class: DeepSeekR1ChatOllama
- Specialized parsing of think blocks for reasoning and answer split.

Function: get_llm_model
- Dispatches provider selection and returns provider-specific chat model.
- Supports provider base URLs and credential fallback from environment.

### G.9 src/utils/mcp_client.py

Function: setup_mcp_client_and_tools
- Starts MultiServerMCPClient from config.

Function: create_tool_param_model
- Converts tool schema or function signature to ActionModel-based param model.

Function: resolve_type
- Recursive JSON schema to Python typing conversion.

### G.10 src/utils/memory_manager.py

Class: MemoryManager
- Constructor:
  - db_path default tmp/memory.json

Method: add_memory
- Appends task-result entry and keeps last 10.

Method: get_memory_context
- Renders saved entries to textual prompt context.

Method: clear_memory
- Empties memory file.

### G.11 src/utils/utils.py

Function: encode_image
- Base64 encodes image path content.

Function: get_latest_files
- Returns latest files for requested types if write-age threshold satisfied.

### G.12 src/webui/interface.py

Function: create_ui
- Builds Gradio blocks layout and applies theme/CSS/JS.
- Creates tabs and mounts tab components.

### G.13 src/webui/webui_manager.py

Class: WebuiManager
- Core role:
  - component registry and runtime state holder.

Method: init_browser_use_agent
- Initializes browser-use runtime fields.

Method: init_deep_research_agent
- Initializes deep-research runtime fields.

Method: add_components
- Registers component IDs by tab.

Method: get_components
- Returns registered components list.

Method: get_component_by_id
- ID to component lookup.

Method: get_id_by_component
- Reverse lookup.

Method: save_config
- Serializes non-button and non-file values to JSON file.

Method: load_config
- Loads config JSON and yields component updates progressively.

### G.14 src/webui/components/agent_settings_tab.py

Function: update_model_dropdown
- Returns dropdown update with provider-specific model choices.

Function: update_mcp_server
- Validates MCP file and closes existing controller MCP client if needed.

Function: create_agent_settings_tab
- Builds settings UI and wires dynamic updates.

### G.15 src/webui/components/browser_settings_tab.py

Function: close_browser
- Cancels active browser-use task and closes browser/context resources.

Function: create_browser_settings_tab
- Builds browser settings controls, profile dropdown, and refresh handler.

### G.16 src/webui/components/browser_use_agent_tab.py

Function: _extract_uploaded_file_context
- Extracts bounded text context from txt, md, csv, json, log, docx, pdf.

Function: _build_task_with_guardrails
- Appends execution policy guidance to user task.

Function: _initialize_llm
- Creates provider model instance with safe defaults.

Function: _initialize_llm_with_fallback
- Retries model initialization with fallback model candidates by provider.

Function: _get_config_value
- Utility cross-tab config getter by component suffix.

Function: _format_agent_output
- Renders action and state as HTML-wrapped JSON code block.

Function: _extract_last_public_page
- Pulls last non-internal URL/title from agent history.

Function: _build_site_description
- Creates concise URL/title summary text.

Function: _handle_new_step
- Pushes screenshot plus model output summary into chat history.

Function: _handle_done
- Adds completion summary and detected final page context.

Function: _ask_assistant_callback
- Human assistance handshake during blocked tasks.

Function: run_agent_task
- Full lifecycle orchestration from task intake to final UI reset.

Function: handle_submit
- Distinguishes between new task submit and assistant-response submit.

Function: handle_stop
- Signals stop on active agent.

Function: handle_pause_resume
- Toggles paused state.

Function: handle_clear
- Clears runtime objects and resets relevant components.

Function: create_browser_use_agent_tab
- Constructs all controls, upload flow, voice flow, and event bindings.

Nested helper: handle_mic_click
- Reveals voice recorder input.

Nested helper: handle_voice_input
- Sends audio to Groq transcription endpoint and fills textbox.

Nested helper: handle_file_upload
- Updates file preview and file path states.

Nested helper: clear_uploaded_file
- Resets upload states.

### G.17 src/webui/components/deep_research_agent_tab.py

Function: _initialize_llm
- Creates LLM instance for deep research mode.

Function: _read_file_safe
- Reads text file with existence checks.

Function: run_deep_research
- Full deep-research lifecycle with UI state updates and file monitoring.

Function: stop_deep_research
- Stops active deep research task and attempts to surface report if present.

Function: update_mcp_server
- Updates MCP config for deep research and closes existing client.

Function: create_deep_research_agent_tab
- Builds UI and binds start/stop event wrappers.

### G.18 src/webui/components/load_save_config_tab.py

Function: create_load_save_config_tab
- Builds config import/export controls and click handlers.

### G.19 tests directory catalog

tests/test_agents.py
- async test_browser_use_agent
- async test_browser_use_parallel
- additional example routines for deep research and agent behavior.

tests/test_controller.py
- async test_mcp_client
- async test_controller_with_mcp

tests/test_llm_api.py
- helper and provider-specific test functions:
  - test_openai_model
  - test_google_model
  - test_azure_openai_model
  - test_deepseek_model
  - test_deepseek_r1_model
  - test_ollama_model
  - test_deepseek_r1_ollama_model
  - test_mistral_model
  - test_moonshot_model
  - test_ibm_model
  - test_qwen_model

tests/test_playwright.py
- test_connect_browser

---

## Appendix H: Environment Contract and Runtime Configuration Ledger

### H.1 Core launch arguments

webui.py arguments:
- --ip
  - default: 127.0.0.1
  - purpose: server bind address
- --port
  - default: 7788
  - purpose: server port
- --theme
  - default: Ocean
  - choices: Default, Soft, Monochrome, Glass, Origin, Citrus, Ocean, Base

### H.2 Provider API environment variables

Primary keys and endpoints referenced by code and compose:
- OPENAI_API_KEY
- OPENAI_ENDPOINT
- ANTHROPIC_API_KEY
- ANTHROPIC_ENDPOINT
- GOOGLE_API_KEY
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_API_VERSION
- DEEPSEEK_API_KEY
- DEEPSEEK_ENDPOINT
- OLLAMA_ENDPOINT
- MISTRAL_API_KEY
- MISTRAL_ENDPOINT
- ALIBABA_API_KEY
- ALIBABA_ENDPOINT
- MOONSHOT_API_KEY
- MOONSHOT_ENDPOINT
- UNBOUND_API_KEY
- UNBOUND_ENDPOINT
- GROQ_API_KEY
- GROQ_ENDPOINT
- OPENROUTER_API_KEY
- OPENROUTER_ENDPOINT
- GROK_ENDPOINT
- SiliconFLOW_API_KEY
- SiliconFLOW_ENDPOINT
- MODELSCOPE_API_KEY
- MODELSCOPE_ENDPOINT
- IBM_API_KEY
- IBM_PROJECT_ID
- IBM_ENDPOINT

Behavioral flags:
- SKIP_LLM_API_KEY_VERIFICATION
- ANONYMIZED_TELEMETRY
- BROWSER_USE_LOGGING_LEVEL

### H.3 Browser and display runtime variables

- BROWSER_PATH
- BROWSER_USER_DATA
- BROWSER_CDP
- BROWSER_DEBUGGING_PORT
- BROWSER_DEBUGGING_HOST
- USE_OWN_BROWSER
- KEEP_BROWSER_OPEN
- DISPLAY
- PLAYWRIGHT_BROWSERS_PATH
- RESOLUTION
- RESOLUTION_WIDTH
- RESOLUTION_HEIGHT
- VNC_PASSWORD

### H.4 Path and artifact conventions

Default artifact roots:
- tmp/agent_history
- tmp/deep_research
- tmp/downloads
- tmp/webui_settings
- tmp/memory.json

Deep research task paths:
- tmp/deep_research/{task_id}/research_plan.md
- tmp/deep_research/{task_id}/search_info.json
- tmp/deep_research/{task_id}/report.md

Browser use task paths:
- tmp/agent_history/{task_id}/{task_id}.json
- tmp/agent_history/{task_id}/{task_id}.gif

### H.5 Runtime process layout in container mode

supervisord programs:
- xvfb
- vnc_setup
- x11vnc
- x11vnc_log
- novnc
- webui

Exposed ports:
- 7788 (Gradio)
- 6080 (noVNC)
- 5901 (VNC)
- 9222 (CDP)

### H.6 Configuration ownership map

UI-driven config values:
- agent settings tab components
- browser settings tab components
- deep research tab fields

Environment-driven fallback values:
- provider keys and endpoints
- browser path and user data defaults
- compose display and VNC configuration

Code-driven defaults:
- model defaults in config maps and provider factory
- path defaults in tabs and agent modules

---

## Appendix I: Artifact Schemas and Data Contracts

### I.1 tmp/memory.json contract

Shape:
- list of objects

Each object fields:
- task: string
- result: string

Retention rule:
- keep only last 10 entries.

### I.2 Browser use agent history artifact

Path pattern:
- tmp/agent_history/{task_id}/{task_id}.json

Logical content summary:
- serialized agent step history
- includes model output, action result, browser state snapshots
- final result and error list are derivable through browser-use history helpers

### I.3 Deep research artifacts

research_plan.md:
- heading plus categories
- checkbox markers:
  - [ ] pending
  - [x] completed
  - [-] failed

search_info.json:
- list of execution result objects
- browser search entries include:
  - query
  - result or error
  - status
- non-browser tool entries may include:
  - tool_name
  - args
  - output
  - status

report.md:
- markdown synthesis output from synthesis node

### I.4 UI settings snapshots

Path pattern:
- tmp/webui_settings/{timestamp}.json

Content:
- map of component IDs to stored values
- excludes non-interactive and selected component classes

### I.5 Profile preset contract

discover_browser_profiles output item fields:
- label
- user_data_dir
- profile_directory
- binary_path

resolve_profile_selection output fields:
- user_data_dir
- profile_directory
- binary_path

---

## Appendix J: Research Paper Seed Material

### J.1 Problem statement candidates

Candidate statement 1:
- Large language models are powerful at reasoning but not inherently connected to dynamic web environments. SmartBrowser addresses this by combining model planning with grounded browser execution.

Candidate statement 2:
- Autonomous browsing systems frequently fail under anti-bot controls, unstable URLs, and noisy tool interfaces. SmartBrowser contributes operational heuristics and configurable orchestration to improve reliability.

Candidate statement 3:
- Multi-source deep research is often fragmented across manual tools. SmartBrowser introduces a unified graph-driven method for planning, parallel information gathering, and structured synthesis.

### J.2 Methodology framing

Method component A:
- LLM-driven planning and tool-call generation.

Method component B:
- Browser-grounded execution with asynchronous callbacks.

Method component C:
- Graph-based state transition for repeatable multi-step research.

Method component D:
- Tool extensibility through MCP schema adaptation.

### J.3 Evaluation dimensions

Quality metrics:
- Task completion rate.
- Number of retries per successful task.
- Hallucinated URL incidence.
- Research report factual grounding score.

Cost metrics:
- Tokens consumed per task.
- Token savings from dedupe and fallback strategies.

Runtime metrics:
- Median and P95 completion latency.
- Parallel deep-research throughput.
- Browser resource utilization.

Safety metrics:
- Stop intervention frequency.
- MCP tool misuse rate.
- Sensitive data leakage incidents in artifacts.

### J.4 Reproducibility notes

Minimal reproducibility protocol:
- Use fixed provider model.
- Disable random prompt variance where possible.
- Fix browser size and headless setting.
- Fix max steps and parallel counts.
- Record full artifacts and seed prompts.

Threats to validity:
- Provider API variability.
- Website content drift over time.
- Network and anti-bot conditions.

---

## Appendix K: Glossary and Terminology

Agent:
- Autonomous execution unit that uses model reasoning plus tools.

BrowserUseAgent:
- Project-specific extension of browser-use Agent with reliability heuristics.

DeepResearchAgent:
- LangGraph-based orchestrator for plan-execute-synthesize workflows.

MCP:
- Model Context Protocol, used for external tool server integration.

StructuredTool:
- LangChain tool type with schema-validated parameters.

ActionResult:
- browser-use result envelope for action outcomes.

AgentHistoryList:
- browser-use history object containing step-level records.

Planner LLM:
- Optional second model used before or alongside main execution model.

Main LLM:
- Primary model used for run-time decision making in browser tasks.

Guardrails:
- Prompt-level behavioral rules injected into task text.

Fail-fast:
- Early termination when repeated failure patterns are detected.

Backoff:
- Controlled delay increase after failures.

CDP:
- Chrome DevTools Protocol endpoint for browser attachment.

WSS URL:
- Websocket endpoint for browser remote control.

Headless:
- Browser mode without visible GUI window.

Use Own Browser:
- Setting to run using existing browser binary and user data context.

Keep Browser Open:
- Setting to retain browser instance between tasks.

UI snapshot:
- Saved JSON record of currently configured UI component values.

Report synthesis:
- Final LLM composition stage over collected findings.

Task artifact:
- Persisted execution outputs such as history JSON and report markdown.

---

## Appendix L: Actionable Engineering Checklist

### L.1 Reliability checklist

- Add provider timeout wrappers around model invocations.
- Add retry policy by exception class and status code.
- Add deterministic fallback policy per provider and model family.
- Add watchdog for hung browser contexts.
- Add artifact write integrity checks.

### L.2 Security checklist

- Add MCP command allowlist and sandbox mode.
- Add upload scanner and MIME validation.
- Add prompt injection detector for uploaded context.
- Add role-based UI access controls for hosted mode.
- Add secure cleanup for sensitive tmp files.

### L.3 Testing checklist

- Convert script tests to pytest assertions and fixtures.
- Isolate external dependencies using mocks.
- Add integration test path for browser use run.
- Add integration test path for deep research run.
- Add regression suite for profile discovery and resolution.

### L.4 Observability checklist

- Add structured logging with correlation IDs.
- Add per-task latency and token metrics.
- Add dashboard for run statuses and failures.
- Add alerting on repeated failure spikes.

### L.5 Documentation checklist

- Keep README aligned with shipped features.
- Maintain changelog updates for each release.
- Publish architecture diagrams and sequence charts.
- Maintain public security and hardening notes.

---

## Appendix M: Sequence Narratives for Diagram Conversion

### M.1 Browser Use sequence narrative

Sequence actor list:
- User
- Gradio UI
- WebuiManager
- BrowserUse tab handler
- LLM provider factory
- CustomController
- CustomBrowser and context
- BrowserUseAgent
- External website
- Artifact storage

Message flow:
1. User submits task.
2. UI handler gathers cross-tab settings.
3. Provider factory returns model instance.
4. Controller and browser context are prepared.
5. Agent run loop begins.
6. Agent invokes tool action.
7. Browser performs action and returns state.
8. Callback streams step output to UI.
9. Loop continues until done or stop.
10. Artifacts are saved and UI resets.

### M.2 Deep Research sequence narrative

Sequence actor list:
- User
- Deep Research tab handler
- DeepResearchAgent graph
- Planning node
- Execution node
- Browser search tool
- BrowserUseAgent instances
- Synthesis node
- File artifact layer
- UI markdown monitor

Message flow:
1. User starts research topic.
2. Graph planning node emits plan.
3. Plan file saved and shown.
4. Execution node requests tool calls.
5. Browser search tool executes parallel tasks.
6. Results persisted.
7. Condition routes to more execution or synthesis.
8. Synthesis writes report.
9. UI exposes report for download.

---

## Appendix N: Compliance Notes for AI Consumer Systems

AI consumer readiness:
- This document is structured with explicit module boundaries and deterministic naming to aid retrieval and chunking.
- Data flow sections are sequenced and normalized for graph extraction.
- Function catalog enables static indexing and tool-assisted code navigation.

Recommended chunk strategy for downstream AI:
- Chunk by heading level two and three.
- Keep each chunk under 1000 to 1500 tokens.
- Preserve section labels for hierarchical retrieval.

Suggested embedding metadata fields:
- section_name
- module_path
- capability_type
- risk_level
- persistence_type

---

## End of Master Project Document
