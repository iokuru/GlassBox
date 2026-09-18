from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CDPSession:
    url: str
    viewport: tuple = (1440, 900)
    timeout_ms: int = 30000
    _page: Any = field(default=None, repr=False)
    _browser: Any = field(default=None, repr=False)
    _playwright: Any = field(default=None, repr=False)

    async def start(self) -> None:
        try:
            from playwright.async_api import async_playwright
            pw = await async_playwright().__aenter__()
            self._playwright = pw
            self._browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                ],
            )
            ctx = await self._browser.new_context(
                viewport={"width": self.viewport[0], "height": self.viewport[1]},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
            )
            self._page = await ctx.new_page()
            await self._page.goto(self.url, wait_until="networkidle", timeout=self.timeout_ms)
        except ImportError:
            self._page = None

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.__aexit__(None, None, None)

    async def evaluate(self, script: str) -> Any:
        if self._page is None:
            return None
        return await self._page.evaluate(script)

    async def screenshot(self, full_page: bool = True) -> Optional[bytes]:
        if self._page is None:
            return None
        return await self._page.screenshot(full_page=full_page, type="png")

    async def scroll_to(self, y: int) -> None:
        if self._page is None:
            return
        await self._page.evaluate(f"window.scrollTo(0, {y})")
        await self._page.wait_for_timeout(200)

    async def scroll_height(self) -> int:
        if self._page is None:
            return 3000
        return await self._page.evaluate("document.documentElement.scrollHeight")

    async def get_cdp_session(self) -> Any:
        if self._page is None:
            return None
        return await self._page.context.new_cdp_session(self._page)

    def is_available(self) -> bool:
        return self._page is not None

    async def __aenter__(self) -> "CDPSession":
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


class MockCDPSession:
    """Offline CDP session for testing without a live browser."""

    def __init__(self, url: str, viewport: tuple = (1440, 900)) -> None:
        self.url = url
        self.viewport = viewport

    async def __aenter__(self) -> "MockCDPSession":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def is_available(self) -> bool:
        return False

    async def evaluate(self, script: str) -> Any:
        return None

    async def screenshot(self, full_page: bool = True) -> Optional[bytes]:
        return None

    async def scroll_to(self, y: int) -> None:
        pass

    async def scroll_height(self) -> int:
        return 3000
