"""Rendering service using Playwright."""
import asyncio
import logging
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
from PIL import Image
import io

from app.config import settings
from app.models import RenderMode

logger = logging.getLogger(__name__)


class RenderService:
    """Service for rendering webpages to PDF using Playwright."""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
    
    async def initialize(self):
        """Initialize Playwright browser."""
        if self.browser:
            return
        
        logger.info("Initializing Playwright browser")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        )
        logger.info("Playwright browser initialized")
    
    async def close(self):
        """Close Playwright browser."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        logger.info("Playwright browser closed")
    
    async def render_to_pdf(
        self,
        url: str,
        output_path: Path,
        render_mode: str,
        navigation_timeout_seconds: int,
        job_timeout_seconds: int
    ) -> None:
        """
        Render webpage to PDF.
        
        Args:
            url: URL to render
            output_path: Path to save PDF
            render_mode: Render mode (print_to_pdf or screenshot_to_pdf)
            navigation_timeout_seconds: Navigation timeout
            job_timeout_seconds: Total job timeout
            
        Raises:
            Exception: If rendering fails
        """
        if not self.browser:
            await self.initialize()
        
        # Create isolated browser context
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        try:
            page = await context.new_page()
            
            # Navigate to URL
            logger.info(f"Navigating to {url}")
            await page.goto(
                url,
                wait_until='domcontentloaded',
                timeout=navigation_timeout_seconds * 1000
            )
            
            # Wait for network idle (optional, with short timeout)
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except PlaywrightTimeout:
                logger.debug("Network idle timeout, proceeding anyway")
            
            # Additional settle time
            await asyncio.sleep(2)
            
            # Render based on mode
            if render_mode == RenderMode.PRINT_TO_PDF.value:
                await self._render_print_to_pdf(page, output_path)
            elif render_mode == RenderMode.SCREENSHOT_TO_PDF.value:
                await self._render_screenshot_to_pdf(page, output_path)
            else:
                raise ValueError(f"Unknown render mode: {render_mode}")
            
            logger.info(f"Successfully rendered PDF to {output_path}")
            
        finally:
            await context.close()
    
    async def _render_print_to_pdf(self, page: Page, output_path: Path) -> None:
        """Render using browser print-to-PDF."""
        await page.pdf(
            path=str(output_path),
            format='A4',
            print_background=True,
            display_header_footer=False,
            margin={'top': '0.5cm', 'right': '0.5cm', 'bottom': '0.5cm', 'left': '0.5cm'}
        )
    
    async def _render_screenshot_to_pdf(self, page: Page, output_path: Path) -> None:
        """Render using screenshot-to-PDF."""
        # Take full page screenshot
        screenshot_bytes = await page.screenshot(full_page=True, type='png')
        
        # Convert screenshot to PDF
        image = Image.open(io.BytesIO(screenshot_bytes))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Save as PDF
        image.save(str(output_path), 'PDF', resolution=100.0)


# Global render service instance
render_service = RenderService()
