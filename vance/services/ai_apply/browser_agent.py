"""
Browser Agent for AI Apply Feature.
Handles browser automation using Playwright.
"""

import asyncio
import random
import base64
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page, Browser, ElementHandle

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = None  # type: ignore
    Browser = None  # type: ignore


class FormField:
    """Represents a form field."""
    def __init__(
        self,
        selector: str,
        field_type: str,
        label: Optional[str] = None,
        placeholder: Optional[str] = None,
        aria_label: Optional[str] = None,
        required: bool = False,
        options: Optional[List[str]] = None
    ):
        self.selector = selector
        self.type = field_type
        self.label = label
        self.placeholder = placeholder
        self.aria_label = aria_label
        self.required = required
        self.options = options or []


class PageNavigationResult:
    """Result of page navigation."""
    def __init__(
        self,
        reached_form: bool,
        page_type: str,
        error: Optional[str] = None
    ):
        self.reached_form = reached_form
        self.page_type = page_type  # 'job_description' | 'application_form' | 'login_required' | 'captcha_detected'
        self.error = error


class SubmissionResult:
    """Result of form submission."""
    def __init__(
        self,
        success: bool,
        confirmation_screenshot: Optional[str] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.confirmation_screenshot = confirmation_screenshot
        self.error = error


class BrowserAgent:
    """Handles browser automation for job applications."""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def initialize(self) -> None:
        """Initialize browser and page."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not available. Install with: pip install playwright && playwright install")
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
            ],
        )
        
        context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        
        self.page = await context.new_page()
    
    async def navigate_to_application_form(self, job_url: str) -> PageNavigationResult:
        """Navigate to the application form."""
        if not self.page:
            raise RuntimeError("Browser not initialized")
        
        try:
            # Navigate to job URL
            await self.page.goto(job_url, wait_until='networkidle', timeout=30000)
            await self._random_wait(1000, 2000)
            
            # Check for login or CAPTCHA
            if await self._detect_login_required():
                return PageNavigationResult(reached_form=False, page_type='login_required')
            
            if await self._detect_captcha():
                return PageNavigationResult(reached_form=False, page_type='captcha_detected')
            
            # Check if already on application form
            if await self._is_application_form():
                return PageNavigationResult(reached_form=True, page_type='application_form')
            
            # Try to find and click apply button
            apply_button = await self._find_apply_button()
            if apply_button:
                await self._scroll_into_view(apply_button)
                await self._human_click(apply_button)
                await self.page.wait_for_load_state('networkidle', timeout=15000)
                await self._random_wait(1000, 2000)
                
                # Check again for login/captcha after clicking
                if await self._detect_login_required():
                    return PageNavigationResult(reached_form=False, page_type='login_required')
                if await self._detect_captcha():
                    return PageNavigationResult(reached_form=False, page_type='captcha_detected')
                
                if await self._is_application_form():
                    return PageNavigationResult(reached_form=True, page_type='application_form')
            
            return PageNavigationResult(
                reached_form=False,
                page_type='job_description',
                error='Could not reach application form'
            )
        
        except Exception as e:
            return PageNavigationResult(
                reached_form=False,
                page_type='job_description',
                error=str(e)
            )
    
    async def extract_form_fields(self) -> List[FormField]:
        """Extract all form fields from the page."""
        if not self.page:
            raise RuntimeError("Browser not initialized")
        
        fields: List[FormField] = []
        
        # Extract all input fields
        inputs = await self.page.query_selector_all('input, textarea, select')
        
        for input_elem in inputs:
            try:
                input_type = await input_elem.get_attribute('type') or 'text'
                name = await input_elem.get_attribute('name') or ''
                elem_id = await input_elem.get_attribute('id') or ''
                placeholder = await input_elem.get_attribute('placeholder') or ''
                aria_label = await input_elem.get_attribute('aria-label') or ''
                required = await input_elem.get_attribute('required') is not None
                
                # Skip hidden fields
                is_hidden = await input_elem.evaluate("""
                    el => {
                        const style = window.getComputedStyle(el);
                        return style.display === 'none' || 
                               style.visibility === 'hidden' || 
                               (el.offsetParent === null);
                    }
                """)
                if is_hidden:
                    continue
                
                # Skip submit buttons
                if input_type in ['submit', 'button']:
                    continue
                
                # Get label text
                label = ''
                if elem_id:
                    label_elem = await self.page.query_selector(f'label[for="{elem_id}"]')
                    if label_elem:
                        label = (await label_elem.text_content() or '').strip()
                
                # Get surrounding text if no label
                if not label:
                    surrounding_text = await input_elem.evaluate("""
                        el => {
                            const parent = el.parentElement;
                            if (parent) {
                                const texts = Array.from(parent.childNodes)
                                    .filter(node => node.nodeType === Node.TEXT_NODE)
                                    .map(node => node.textContent?.trim())
                                    .filter(Boolean);
                                return texts.join(' ');
                            }
                            return '';
                        }
                    """)
                    label = surrounding_text.strip()
                
                # Get selector
                selector = f'#{elem_id}' if elem_id else (f'[name="{name}"]' if name else '')
                if not selector:
                    continue
                
                # Get options for select fields
                options: List[str] = []
                tag_name = await input_elem.evaluate('el => el.tagName')
                if input_type == 'select' or tag_name == 'SELECT':
                    options = await input_elem.evaluate("""
                        el => {
                            const selectEl = el;
                            return Array.from(selectEl.options).map(opt => opt.text);
                        }
                    """)
                
                # Determine field type
                field_type = 'text'
                if input_type in ['email', 'tel', 'textarea']:
                    field_type = input_type
                elif tag_name == 'SELECT':
                    field_type = 'select'
                elif input_type == 'checkbox':
                    field_type = 'checkbox'
                elif input_type == 'radio':
                    field_type = 'radio'
                elif input_type == 'file':
                    field_type = 'file'
                
                fields.append(FormField(
                    selector=selector,
                    field_type=field_type,
                    label=label,
                    placeholder=placeholder,
                    aria_label=aria_label,
                    required=required,
                    options=options
                ))
            
            except Exception as e:
                print(f"⚠️ [BROWSER_AGENT] Error extracting field: {e}")
                continue
        
        return fields
    
    async def fill_field(self, selector: str, value: str, field_type: str) -> bool:
        """Fill a form field with a value."""
        if not self.page:
            raise RuntimeError("Browser not initialized")
        
        try:
            element = await self.page.query_selector(selector)
            if not element:
                return False
            
            await self._scroll_into_view(element)
            await self._random_wait(100, 300)
            
            if field_type == 'select':
                await element.select_option(label=value)
            elif field_type == 'checkbox':
                is_checked = await element.is_checked()
                if not is_checked and value.lower() == 'true':
                    await self._human_click(element)
            elif field_type == 'radio':
                await self._human_click(element)
            else:
                # Text input
                await element.click()
                await self._random_wait(50, 150)
                await element.fill('')  # Clear existing
                await self._human_type(element, value)
                await self._random_wait(50, 150)
                await element.evaluate('el => el.blur()')
            
            return True
        
        except Exception as e:
            print(f"⚠️ [BROWSER_AGENT] Error filling field {selector}: {e}")
            return False
    
    async def upload_file(self, selector: str, file_path: str) -> bool:
        """Upload a file to a file input."""
        if not self.page:
            raise RuntimeError("Browser not initialized")
        
        try:
            file_input = await self.page.query_selector(selector)
            if not file_input:
                return False
            
            await file_input.set_input_files(file_path)
            await self._random_wait(1000, 2000)
            
            # Wait for upload confirmation
            await asyncio.sleep(2)
            
            return True
        
        except Exception as e:
            print(f"⚠️ [BROWSER_AGENT] Error uploading file to {selector}: {e}")
            return False
    
    async def submit_form(self) -> SubmissionResult:
        """Submit the application form."""
        if not self.page:
            raise RuntimeError("Browser not initialized")
        
        try:
            # Capture screenshot before submission
            filled_form_screenshot = await self.page.screenshot(full_page=True, type='png')
            
            # Find and click submit button
            submit_button = await self._find_submit_button()
            if not submit_button:
                return SubmissionResult(success=False, error='Submit button not found')
            
            await self._scroll_into_view(submit_button)
            await self._random_wait(500, 1000)
            await self._human_click(submit_button)
            
            # Wait for navigation or success message
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        self.page.wait_for_navigation(timeout=10000),
                        self.page.wait_for_selector('text=/thank you|success|submitted|confirmation/i', timeout=10000),
                        return_exceptions=True
                    ),
                    timeout=10
                )
            except asyncio.TimeoutError:
                pass  # Timeout is okay, check for success indicators anyway
            
            await self._random_wait(2000, 3000)
            
            # Check for success indicators
            has_success = await self._detect_submission_success()
            
            if has_success:
                confirmation_screenshot = await self.page.screenshot(full_page=True, type='png')
                return SubmissionResult(
                    success=True,
                    confirmation_screenshot=base64.b64encode(confirmation_screenshot).decode('utf-8')
                )
            
            return SubmissionResult(success=False, error='No confirmation detected')
        
        except Exception as e:
            return SubmissionResult(
                success=False,
                error=str(e)
            )
    
    async def capture_screenshot(self) -> str:
        """Capture a screenshot of the current page."""
        if not self.page:
            raise RuntimeError("Browser not initialized")
        screenshot = await self.page.screenshot(full_page=True, type='png')
        return base64.b64encode(screenshot).decode('utf-8')
    
    async def close(self) -> None:
        """Close browser and page."""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
    
    # Private helper methods
    
    async def _is_application_form(self) -> bool:
        """Check if current page is an application form."""
        if not self.page:
            return False
        
        has_form = await self.page.query_selector('form')
        if not has_form:
            return False
        
        # Check for typical application form elements
        input_count = await self.page.evaluate("""
            () => document.querySelectorAll('input, textarea, select').length
        """)
        has_submit = await self._find_submit_button()
        
        return input_count >= 3 and has_submit is not None
    
    async def _detect_login_required(self) -> bool:
        """Detect if login is required."""
        if not self.page:
            return False
        
        login_indicators = [
            'input[type="password"]',
            'text=/sign in|log in|login/i',
            'button:has-text("Sign in")',
            'button:has-text("Log in")',
        ]
        
        for indicator in login_indicators:
            try:
                element = await self.page.query_selector(indicator)
                if element:
                    is_visible = await element.is_visible()
                    if is_visible:
                        return True
            except:
                continue
        
        return False
    
    async def _detect_captcha(self) -> bool:
        """Detect if CAPTCHA is present."""
        if not self.page:
            return False
        
        captcha_indicators = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]',
            '.g-recaptcha',
            '#captcha',
            'text=/verify you are human/i',
        ]
        
        for indicator in captcha_indicators:
            try:
                element = await self.page.query_selector(indicator)
                if element:
                    return True
            except:
                continue
        
        return False
    
    async def _find_apply_button(self):
        """Find the apply button."""
        if not self.page:
            return None
        
        button_selectors = [
            'button:has-text("Apply")',
            'a:has-text("Apply")',
            'button:has-text("Apply Now")',
            'a:has-text("Apply Now")',
            'button:has-text("Submit Application")',
            '[data-testid*="apply"]',
            '[class*="apply-button"]',
        ]
        
        for selector in button_selectors:
            try:
                button = await self.page.query_selector(selector)
                if button:
                    is_visible = await button.is_visible()
                    if is_visible:
                        return button
            except:
                continue
        
        return None
    
    async def _find_submit_button(self):
        """Find the submit button."""
        if not self.page:
            return None
        
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Submit Application")',
            'button:has-text("Apply")',
            'button:has-text("Send")',
        ]
        
        for selector in submit_selectors:
            try:
                button = await self.page.query_selector(selector)
                if button:
                    is_visible = await button.is_visible()
                    if is_visible:
                        return button
            except:
                continue
        
        return None
    
    async def _detect_submission_success(self) -> bool:
        """Detect if submission was successful."""
        if not self.page:
            return False
        
        success_indicators = [
            'text=/thank you|success|submitted|confirmation|received your application/i',
            '[class*="success"]',
            '[class*="confirmation"]',
            '.alert-success',
        ]
        
        for indicator in success_indicators:
            try:
                element = await self.page.query_selector(indicator)
                if element:
                    is_visible = await element.is_visible()
                    if is_visible:
                        return True
            except:
                continue
        
        # Check URL for success indicators
        url = self.page.url if self.page else ""
        if any(word in url.lower() for word in ['success', 'confirmation', 'thank']):
            return True
        
        return False
    
    async def _scroll_into_view(self, element) -> None:
        """Scroll element into view."""
        await element.evaluate("""
            el => {
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        """)
        await self._random_wait(300, 600)
    
    async def _human_click(self, element) -> None:
        """Click element with human-like delay."""
        await self._random_wait(100, 300)
        await element.click()
        await self._random_wait(100, 300)
    
    async def _human_type(self, element, text: str) -> None:
        """Type text with human-like delays."""
        for char in text:
            delay = self._random_delay(30, 80)
            await element.type(char, delay=delay)
    
    def _random_delay(self, min_ms: int, max_ms: int) -> int:
        """Generate random delay in milliseconds."""
        return random.randint(min_ms, max_ms)
    
    async def _random_wait(self, min_ms: int, max_ms: int) -> None:
        """Wait for random duration."""
        delay = self._random_delay(min_ms, max_ms)
        await asyncio.sleep(delay / 1000.0)

