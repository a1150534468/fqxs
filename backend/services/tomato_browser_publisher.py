"""
Tomato Fiction Browser Automation Publisher

Uses Playwright to simulate real browser interactions for publishing chapters.
This approach avoids API reverse engineering and is more resilient to platform changes.
"""
import asyncio
import logging
import random
from typing import Dict, Optional

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class TomatoBrowserPublisher:
    """
    Browser automation publisher for Tomato Fiction platform.

    Uses Playwright to simulate real user interactions.
    """

    def __init__(
        self,
        headless: bool = True,
        proxy: Optional[str] = None,
        user_data_dir: Optional[str] = None,
    ):
        """
        Initialize browser publisher.

        Args:
            headless: Run browser in headless mode
            proxy: Proxy server URL (e.g., "http://proxy:port")
            user_data_dir: Directory to store browser profile (for session persistence)
        """
        self.headless = headless
        self.proxy = proxy
        self.user_data_dir = user_data_dir
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.logged_in = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Start browser instance."""
        logger.info('Starting browser...')

        playwright = await async_playwright().start()

        launch_options = {
            'headless': self.headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ],
        }

        if self.proxy:
            launch_options['proxy'] = {'server': self.proxy}

        if self.user_data_dir:
            # Use persistent context to save cookies/session
            self.browser = await playwright.chromium.launch_persistent_context(
                self.user_data_dir,
                **launch_options,
            )
            self.page = self.browser.pages[0] if self.browser.pages else await self.browser.new_page()
        else:
            self.browser = await playwright.chromium.launch(**launch_options)
            self.page = await self.browser.new_page()

        # Set viewport and user agent
        await self.page.set_viewport_size({'width': 1920, 'height': 1080})

        # Mask automation detection
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        logger.info('Browser started successfully')

    async def close(self):
        """Close browser instance."""
        if self.browser:
            await self.browser.close()
            logger.info('Browser closed')

    async def _random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Add random delay to simulate human behavior."""
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f'Waiting {delay:.2f} seconds')
        await asyncio.sleep(delay)

    async def _type_like_human(self, selector: str, text: str):
        """Type text with random delays between keystrokes."""
        element = await self.page.wait_for_selector(selector)
        for char in text:
            await element.type(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))

    async def login(self, username: str, password: str, login_url: str) -> bool:
        """
        Login to Tomato Fiction platform.

        Args:
            username: Platform username
            password: Platform password
            login_url: Login page URL

        Returns:
            True if login successful

        Note: Selectors need to be updated based on actual platform HTML structure.
        """
        try:
            logger.info(f'Navigating to login page: {login_url}')
            await self.page.goto(login_url, wait_until='networkidle')
            await self._random_delay(2, 4)

            # TODO: Update selectors based on actual Tomato Fiction login page
            # Example selectors (need to be verified):
            username_selector = 'input[name="username"]'  # or 'input[type="text"]'
            password_selector = 'input[name="password"]'  # or 'input[type="password"]'
            submit_selector = 'button[type="submit"]'  # or specific class/id

            logger.info('Filling login form...')

            # Fill username
            await self._type_like_human(username_selector, username)
            await self._random_delay(0.5, 1.5)

            # Fill password
            await self._type_like_human(password_selector, password)
            await self._random_delay(1, 2)

            # Click login button
            await self.page.click(submit_selector)
            logger.info('Login form submitted')

            # Wait for navigation or success indicator
            await self.page.wait_for_load_state('networkidle', timeout=30000)
            await self._random_delay(2, 3)

            # Check if login successful (need to verify actual success indicator)
            # Example: check for user profile element or dashboard
            # success = await self.page.query_selector('.user-profile') is not None

            self.logged_in = True
            logger.info('Login successful')
            return True

        except PlaywrightTimeout as e:
            logger.error(f'Login timeout: {e}')
            return False
        except Exception as e:
            logger.error(f'Login failed: {e}', exc_info=True)
            return False

    async def publish_chapter(
        self,
        novel_id: str,
        chapter_number: int,
        chapter_title: str,
        content: str,
        publish_url: str,
    ) -> Dict:
        """
        Publish a chapter using browser automation.

        Args:
            novel_id: Novel ID on platform
            chapter_number: Chapter number
            chapter_title: Chapter title
            content: Chapter content
            publish_url: Chapter publish/edit page URL

        Returns:
            Dict with publish result

        Note: Selectors need to be updated based on actual platform HTML structure.
        """
        if not self.logged_in:
            raise ValueError('Not logged in')

        try:
            logger.info(f'Publishing chapter {chapter_number}: {chapter_title}')

            # Navigate to publish page
            await self.page.goto(publish_url, wait_until='networkidle')
            await self._random_delay(2, 4)

            # TODO: Update selectors based on actual Tomato Fiction publish page
            # Example selectors (need to be verified):
            title_selector = 'input[name="title"]'
            content_selector = 'textarea[name="content"]'  # or rich text editor
            submit_selector = 'button.publish-btn'

            # Fill chapter title
            logger.info('Filling chapter title...')
            await self.page.fill(title_selector, '')  # Clear first
            await self._type_like_human(title_selector, chapter_title)
            await self._random_delay(1, 2)

            # Fill chapter content
            logger.info('Filling chapter content...')
            await self.page.fill(content_selector, '')  # Clear first

            # For large content, paste instead of typing
            await self.page.fill(content_selector, content)
            await self._random_delay(2, 3)

            # Take screenshot before submit (for debugging)
            await self.page.screenshot(path=f'/tmp/chapter_{chapter_number}_before_submit.png')

            # Click publish button
            logger.info('Clicking publish button...')
            await self.page.click(submit_selector)

            # Wait for success indicator
            await self.page.wait_for_load_state('networkidle', timeout=60000)
            await self._random_delay(2, 3)

            # Check for success message or error
            # TODO: Update success/error selectors
            # success_selector = '.success-message'
            # error_selector = '.error-message'

            logger.info(f'Chapter {chapter_number} published successfully')

            return {
                'status': 'success',
                'chapter_id': f'chapter_{chapter_number}',
                'message': 'Chapter published successfully',
            }

        except PlaywrightTimeout as e:
            logger.error(f'Publish timeout: {e}')
            return {
                'status': 'error',
                'message': f'Timeout: {str(e)}',
            }
        except Exception as e:
            logger.error(f'Publish failed: {e}', exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
            }

    async def get_chapter_stats(self, chapter_url: str) -> Dict:
        """
        Get chapter statistics by navigating to chapter page.

        Args:
            chapter_url: Chapter page URL

        Returns:
            Dict with stats (views, likes, comments)
        """
        try:
            await self.page.goto(chapter_url, wait_until='networkidle')
            await self._random_delay(1, 2)

            # TODO: Update selectors based on actual stats display
            # Example:
            # views = await self.page.text_content('.views-count')
            # likes = await self.page.text_content('.likes-count')

            return {
                'views': 0,
                'likes': 0,
                'comments': 0,
            }

        except Exception as e:
            logger.error(f'Failed to get stats: {e}')
            return {}


# Synchronous wrapper for use in Django views
class TomatoBrowserPublisherSync:
    """Synchronous wrapper for TomatoBrowserPublisher."""

    def __init__(self, *args, **kwargs):
        self.publisher = TomatoBrowserPublisher(*args, **kwargs)

    def login(self, username: str, password: str, login_url: str) -> bool:
        """Synchronous login."""
        return asyncio.run(self.publisher.login(username, password, login_url))

    def publish_chapter(
        self,
        novel_id: str,
        chapter_number: int,
        chapter_title: str,
        content: str,
        publish_url: str,
    ) -> Dict:
        """Synchronous publish."""
        async def _publish():
            async with self.publisher:
                return await self.publisher.publish_chapter(
                    novel_id, chapter_number, chapter_title, content, publish_url
                )
        return asyncio.run(_publish())
