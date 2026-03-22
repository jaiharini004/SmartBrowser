import os
from distutils.util import strtobool
import gradio as gr
import logging
from gradio.components import Component

from src.webui.webui_manager import WebuiManager
from src.utils import config
from src.browser.profile_utils import discover_browser_profiles, resolve_profile_selection

logger = logging.getLogger(__name__)

async def close_browser(webui_manager: WebuiManager):
    """
    Close browser
    """
    if webui_manager.bu_current_task and not webui_manager.bu_current_task.done():
        webui_manager.bu_current_task.cancel()
        webui_manager.bu_current_task = None

    if webui_manager.bu_browser_context:
        logger.info("⚠️ Closing browser context when changing browser config.")
        await webui_manager.bu_browser_context.close()
        webui_manager.bu_browser_context = None

    if webui_manager.bu_browser:
        logger.info("⚠️ Closing browser when changing browser config.")
        await webui_manager.bu_browser.close()
        webui_manager.bu_browser = None

def create_browser_settings_tab(webui_manager: WebuiManager):
    """
    Creates a browser settings tab.
    """
    input_components = set(webui_manager.get_components())
    tab_components = {}
    discovered_profiles = discover_browser_profiles()
    profile_choices = ["Custom (manual path)"] + [preset["label"] for preset in discovered_profiles]

    with gr.Group():
        with gr.Row():
            browser_profile = gr.Dropdown(
                label="Default Browser Profile",
                choices=profile_choices,
                value=profile_choices[0],
                info="Choose a detected Chrome/Edge profile or keep custom manual paths.",
                interactive=True,
            )
            refresh_profiles_btn = gr.Button("Refresh Profiles", variant="secondary")

    with gr.Group():
        with gr.Row():
            browser_binary_path = gr.Textbox(
                label="Browser Binary Path",
                lines=1,
                interactive=True,
                placeholder="e.g. '/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome'"
            )
            browser_user_data_dir = gr.Textbox(
                label="Browser User Data Dir",
                lines=1,
                interactive=True,
                placeholder="Leave it empty if you use your default user data",
            )
    with gr.Group():
        with gr.Row():
            use_own_browser = gr.Checkbox(
                label="Use Own Browser",
                value=bool(strtobool(os.getenv("USE_OWN_BROWSER", "false"))),
                info="Use your existing browser instance",
                interactive=True
            )
            keep_browser_open = gr.Checkbox(
                label="Keep Browser Open",
                value=bool(strtobool(os.getenv("KEEP_BROWSER_OPEN", "true"))),
                info="Keep Browser Open between Tasks",
                interactive=True
            )
            headless = gr.Checkbox(
                label="Headless Mode",
                value=False,
                info="Run browser without GUI",
                interactive=True
            )
            disable_security = gr.Checkbox(
                label="Disable Security",
                value=False,
                info="Disable browser security",
                interactive=True
            )

    with gr.Group():
        with gr.Row():
            window_w = gr.Number(
                label="Window Width",
                value=1280,
                info="Browser window width",
                interactive=True
            )
            window_h = gr.Number(
                label="Window Height",
                value=1100,
                info="Browser window height",
                interactive=True
            )
    with gr.Group():
        with gr.Row():
            cdp_url = gr.Textbox(
                label="CDP URL",
                value=os.getenv("BROWSER_CDP", None),
                info="CDP URL for browser remote debugging",
                interactive=True,
            )
            wss_url = gr.Textbox(
                label="WSS URL",
                info="WSS URL for browser remote debugging",
                interactive=True,
            )
    with gr.Group():
        with gr.Row():
            save_recording_path = gr.Textbox(
                label="Recording Path",
                placeholder="e.g. ./tmp/record_videos",
                info="Path to save browser recordings",
                interactive=True,
            )

            save_trace_path = gr.Textbox(
                label="Trace Path",
                placeholder="e.g. ./tmp/traces",
                info="Path to save Agent traces",
                interactive=True,
            )

        with gr.Row():
            save_agent_history_path = gr.Textbox(
                label="Agent History Save Path",
                value="./tmp/agent_history",
                info="Specify the directory where agent history should be saved.",
                interactive=True,
            )
            save_download_path = gr.Textbox(
                label="Save Directory for browser downloads",
                value="./tmp/downloads",
                info="Specify the directory where downloaded files should be saved.",
                interactive=True,
            )
    tab_components.update(
        dict(
            browser_profile=browser_profile,
            browser_binary_path=browser_binary_path,
            browser_user_data_dir=browser_user_data_dir,
            use_own_browser=use_own_browser,
            keep_browser_open=keep_browser_open,
            headless=headless,
            disable_security=disable_security,
            save_recording_path=save_recording_path,
            save_trace_path=save_trace_path,
            save_agent_history_path=save_agent_history_path,
            save_download_path=save_download_path,
            cdp_url=cdp_url,
            wss_url=wss_url,
            window_h=window_h,
            window_w=window_w,
        )
    )
    webui_manager.add_components("browser_settings", tab_components)

    async def close_wrapper():
        """Wrapper for handle_clear."""
        await close_browser(webui_manager)

    headless.change(close_wrapper)
    keep_browser_open.change(close_wrapper)
    disable_security.change(close_wrapper)
    use_own_browser.change(close_wrapper)

    def refresh_profile_choices():
        refreshed = discover_browser_profiles()
        choices = ["Custom (manual path)"] + [item["label"] for item in refreshed]
        return gr.update(choices=choices, value=choices[0])

    def apply_profile(profile_label, manual_user_data_dir, manual_binary_path):
        resolved = resolve_profile_selection(
            profile_label=profile_label,
            manual_user_data_dir=manual_user_data_dir,
            manual_binary_path=manual_binary_path,
        )
        own_browser_update = gr.update(value=True) if profile_label and profile_label != "Custom (manual path)" else gr.update()
        return (
            gr.update(value=resolved["user_data_dir"] or ""),
            gr.update(value=resolved["binary_path"] or ""),
            own_browser_update,
        )

    browser_profile.change(
        fn=apply_profile,
        inputs=[browser_profile, browser_user_data_dir, browser_binary_path],
        outputs=[browser_user_data_dir, browser_binary_path, use_own_browser],
    )
    refresh_profiles_btn.click(
        fn=refresh_profile_choices,
        inputs=None,
        outputs=[browser_profile],
    )
