import asyncio
import logging
import os
import socket
import subprocess
from pathlib import Path
from tempfile import gettempdir

import httpx
import psutil
from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import Playwright
from browser_use.browser.browser import Browser, IN_DOCKER
from browser_use.browser.context import BrowserContextConfig

from browser_use.browser.chrome import (
    CHROME_ARGS,
    CHROME_DEBUG_PORT,
    CHROME_DETERMINISTIC_RENDERING_ARGS,
    CHROME_DISABLE_SECURITY_ARGS,
    CHROME_DOCKER_ARGS,
    CHROME_HEADLESS_ARGS,
)
from browser_use.browser.utils.screen_resolution import get_screen_resolution, get_window_adjustments

from .custom_context import CustomBrowserContext

logger = logging.getLogger(__name__)


class CustomBrowser(Browser):

    async def _debug_endpoint_ready(self, endpoint: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{endpoint}/json/version", timeout=1.2)
            return response.status_code == 200
        except Exception:
            return False

    async def _wait_for_debug_endpoint(
            self,
            endpoint: str,
            chrome_process: asyncio.subprocess.Process,
            timeout_seconds: float = 8.0,
    ) -> bool:
        """Wait for DevTools endpoint and fail fast if the spawned browser exits."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds

        while loop.time() < deadline:
            if chrome_process.returncode is not None:
                logger.error(
                    "Browser process exited early with code %s while waiting for DevTools endpoint.",
                    chrome_process.returncode,
                )
                return False
            if await self._debug_endpoint_ready(endpoint):
                return True
            await asyncio.sleep(0.3)

        return False

    async def new_context(self, config: BrowserContextConfig | None = None) -> CustomBrowserContext:
        """Create a browser context"""
        browser_config = self.config.model_dump() if self.config else {}
        context_config = config.model_dump() if config else {}
        merged_config = {**browser_config, **context_config}
        return CustomBrowserContext(config=BrowserContextConfig(**merged_config), browser=self)

    async def _setup_user_provided_browser(self, playwright: Playwright) -> PlaywrightBrowser:
        """Launch/connect to an installed Chromium browser with robust local CDP handling."""
        if not self.config.browser_binary_path:
            raise ValueError("A browser_binary_path is required")

        assert self.config.browser_class == "chromium", (
            "browser_binary_path only supports chromium browsers (make sure browser_class=chromium)"
        )

        debug_port = self.config.chrome_remote_debugging_port or CHROME_DEBUG_PORT
        cdp_endpoint = f"http://127.0.0.1:{debug_port}"

        # Reuse an already-running debug session if available.
        if await self._debug_endpoint_ready(cdp_endpoint):
            logger.info("🔌  Reusing existing browser found on %s", cdp_endpoint)
            browser_class = getattr(playwright, self.config.browser_class)
            return await browser_class.connect_over_cdp(endpoint_url=cdp_endpoint, timeout=10000)

        provided_user_data_dir = [
            arg for arg in self.config.extra_browser_args if "--user-data-dir=" in arg
        ]
        if provided_user_data_dir:
            user_data_dir = Path(provided_user_data_dir[0].split("=", 1)[-1])
        else:
            fallback_user_data_dir = Path(gettempdir()) / "browseruse" / "profiles" / "default"
            try:
                user_data_dir = (Path("~/.config") / "browseruse" / "profiles" / "default").expanduser()
                user_data_dir.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                logger.warning(
                    "Failed to create ~/.config/browseruse directory (%s). Falling back to temp dir.",
                    exc,
                )
                user_data_dir = fallback_user_data_dir
                user_data_dir.mkdir(parents=True, exist_ok=True)

        logger.info("🌐  Storing Browser Profile user data dir in: %s", user_data_dir)

        # Preserve arg order while dropping duplicates.
        launch_arg_candidates: list[str] = [
            f"--remote-debugging-port={debug_port}",
            *([f"--user-data-dir={user_data_dir.resolve()}"] if not provided_user_data_dir else []),
            *CHROME_ARGS,
            *(CHROME_DOCKER_ARGS if IN_DOCKER else []),
            *(CHROME_HEADLESS_ARGS if self.config.headless else []),
            *(CHROME_DISABLE_SECURITY_ARGS if self.config.disable_security else []),
            *(CHROME_DETERMINISTIC_RENDERING_ARGS if self.config.deterministic_rendering else []),
            *self.config.extra_browser_args,
        ]
        chrome_launch_args = list(dict.fromkeys(launch_arg_candidates))

        chrome_process = await asyncio.create_subprocess_exec(
            self.config.browser_binary_path,
            *chrome_launch_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        self._chrome_subprocess = psutil.Process(chrome_process.pid)

        endpoint_ready = await self._wait_for_debug_endpoint(cdp_endpoint, chrome_process, timeout_seconds=8.0)
        if not endpoint_ready:
            raise RuntimeError(
                "Browser debug endpoint did not come up in time. This usually means the selected profile is locked "
                "by a background browser process (Edge/Chrome startup boost) or the browser path is invalid."
            )

        try:
            browser_class = getattr(playwright, self.config.browser_class)
            return await browser_class.connect_over_cdp(endpoint_url=cdp_endpoint, timeout=10000)
        except Exception as exc:
            logger.error("❌  Failed to connect to browser debug endpoint %s: %s", cdp_endpoint, exc)
            raise RuntimeError(
                "Failed to connect to browser debug endpoint. Close background browser processes and try again."
            ) from exc

    async def _setup_builtin_browser(self, playwright: Playwright) -> PlaywrightBrowser:
        """Sets up and returns a Playwright Browser instance with anti-detection measures."""
        assert self.config.browser_binary_path is None, 'browser_binary_path should be None if trying to use the builtin browsers'

        # Use the configured window size from new_context_config if available
        if (
                not self.config.headless
                and hasattr(self.config, 'new_context_config')
                and hasattr(self.config.new_context_config, 'window_width')
                and hasattr(self.config.new_context_config, 'window_height')
        ):
            screen_size = {
                'width': self.config.new_context_config.window_width,
                'height': self.config.new_context_config.window_height,
            }
            offset_x, offset_y = get_window_adjustments()
        elif self.config.headless:
            screen_size = {'width': 1920, 'height': 1080}
            offset_x, offset_y = 0, 0
        else:
            screen_size = get_screen_resolution()
            offset_x, offset_y = get_window_adjustments()

        chrome_args = {
            f'--remote-debugging-port={self.config.chrome_remote_debugging_port}',
            *CHROME_ARGS,
            *(CHROME_DOCKER_ARGS if IN_DOCKER else []),
            *(CHROME_HEADLESS_ARGS if self.config.headless else []),
            *(CHROME_DISABLE_SECURITY_ARGS if self.config.disable_security else []),
            *(CHROME_DETERMINISTIC_RENDERING_ARGS if self.config.deterministic_rendering else []),
            f'--window-position={offset_x},{offset_y}',
            f'--window-size={screen_size["width"]},{screen_size["height"]}',
            *self.config.extra_browser_args,
        }

        # check if chrome remote debugging port is already taken,
        # if so remove the remote-debugging-port arg to prevent conflicts
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', self.config.chrome_remote_debugging_port)) == 0:
                chrome_args.remove(f'--remote-debugging-port={self.config.chrome_remote_debugging_port}')

        browser_class = getattr(playwright, self.config.browser_class)
        args = {
            'chromium': list(chrome_args),
            'firefox': [
                *{
                    '-no-remote',
                    *self.config.extra_browser_args,
                }
            ],
            'webkit': [
                *{
                    '--no-startup-window',
                    *self.config.extra_browser_args,
                }
            ],
        }

        browser = await browser_class.launch(
            channel='chromium',  # https://github.com/microsoft/playwright/issues/33566
            headless=self.config.headless,
            args=args[self.config.browser_class],
            proxy=self.config.proxy.model_dump() if self.config.proxy else None,
            handle_sigterm=False,
            handle_sigint=False,
        )
        return browser
