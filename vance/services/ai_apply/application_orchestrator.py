"""
Application Orchestrator for AI Apply Feature.
Coordinates the entire application process.
"""

import os
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from services.ai_apply.browser_agent import (
    BrowserAgent, FormField, PageNavigationResult, SubmissionResult
)
from services.ai_apply.llm_field_mapper import LLMFieldMapper, FieldMapping
from services.ai_apply.cover_letter_generator import CoverLetterGenerator


class ApplicationOrchestrator:
    """Orchestrates the job application process."""
    
    def __init__(self):
        self.browser_agent = BrowserAgent()
        self.field_mapper = LLMFieldMapper()
        self.cover_letter_generator = CoverLetterGenerator()
    
    async def process_application(
        self,
        candidate_profile: Dict[str, Any],
        job_url: str,
        job_title: str,
        company: str,
        resume_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a job application.
        
        Returns:
            Dict with status, screenshots, form_fields, and any errors
        """
        print(f"🚀 [AI_APPLY] Starting application process for {job_title} at {company}")
        
        try:
            # Initialize browser
            await self.browser_agent.initialize()
            
            # Step 1: Navigate to application form
            print("📍 [AI_APPLY] Navigating to application form...")
            nav_result = await self.browser_agent.navigate_to_application_form(job_url)
            
            if not nav_result.reached_form:
                status = self._map_page_type_to_status(nav_result.page_type)
                return {
                    "status": status,
                    "error": nav_result.error or f"Could not reach form: {nav_result.page_type}",
                    "screenshots": {},
                    "form_fields": []
                }
            
            # Step 2: Extract form fields
            print("🔍 [AI_APPLY] Extracting form fields...")
            fields = await self.browser_agent.extract_form_fields()
            
            if not fields:
                return {
                    "status": "failed",
                    "error": "No form fields detected",
                    "screenshots": {},
                    "form_fields": []
                }
            
            print(f"✅ [AI_APPLY] Found {len(fields)} form fields")
            
            # Step 3: Map fields using LLM
            print("🤖 [AI_APPLY] Mapping fields to candidate data using LLM...")
            mappings = await self.field_mapper.map_fields(
                fields,
                candidate_profile,
                job_title,
                company
            )
            
            print(f"✅ [AI_APPLY] Mapped {len(mappings)} fields")
            
            # Step 4: Validate required fields
            validation = self.field_mapper.validate_required_fields(fields, mappings)
            if not validation["valid"]:
                print(f"⚠️ [AI_APPLY] Missing required fields: {validation['missingFields']}")
                return {
                    "status": "failed",
                    "error": f"Missing required fields: {', '.join(validation['missingFields'])}",
                    "screenshots": {},
                    "form_fields": []
                }
            
            # Step 5: Fill form fields
            print("✍️ [AI_APPLY] Filling form fields...")
            filled_fields = []
            for mapping in mappings:
                if mapping.value:
                    success = await self.browser_agent.fill_field(
                        mapping.selector,
                        str(mapping.value),
                        mapping.field_type
                    )
                    if success:
                        field_info = next((f for f in fields if f.selector == mapping.selector), None)
                        filled_fields.append({
                            "field_name": mapping.selector,
                            "label": field_info.label if field_info else mapping.selector,
                            "value": mapping.value,
                            "type": mapping.field_type,
                            "selector": mapping.selector
                        })
            
            print(f"✅ [AI_APPLY] Filled {len(filled_fields)} fields")
            
            # Step 6: Handle file uploads
            if resume_path:
                print("📎 [AI_APPLY] Uploading resume...")
                await self._handle_file_uploads(fields, resume_path)
            
            # Step 7: Handle cover letter if needed
            print("📝 [AI_APPLY] Handling cover letter...")
            await self._handle_cover_letter(fields, candidate_profile, job_title, company)
            
            # Step 8: Submit application
            print("🚀 [AI_APPLY] Submitting application...")
            submit_result = await self.browser_agent.submit_form()
            
            if not submit_result.success:
                return {
                    "status": "failed",
                    "error": submit_result.error or "Submission failed",
                    "screenshots": {
                        "filled_form": await self.browser_agent.capture_screenshot()
                    },
                    "form_fields": filled_fields
                }
            
            # Step 9: Capture final screenshots
            filled_form_screenshot = await self.browser_agent.capture_screenshot()
            
            # Success!
            print(f"✅ [AI_APPLY] Application submitted successfully!")
            return {
                "status": "submitted",
                "screenshots": {
                    "filled_form": filled_form_screenshot,
                    "confirmation": submit_result.confirmation_screenshot
                },
                "form_fields": filled_fields,
                "applied_at": time.time()
            }
        
        except Exception as e:
            print(f"❌ [AI_APPLY] Error processing application: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "failed",
                "error": str(e),
                "screenshots": {},
                "form_fields": []
            }
        
        finally:
            # Always close browser
            await self.browser_agent.close()
    
    async def _handle_file_uploads(
        self,
        fields: List[FormField],
        resume_path: str
    ) -> None:
        """Handle file upload fields."""
        file_fields = [f for f in fields if f.type == 'file']
        
        for field in file_fields:
            label = (field.label or '').lower()
            placeholder = (field.placeholder or '').lower()
            
            # Resume upload
            if 'resume' in label or 'cv' in label or 'resume' in placeholder:
                success = await self.browser_agent.upload_file(field.selector, resume_path)
                if success:
                    print(f"✅ [AI_APPLY] Uploaded resume to {field.selector}")
    
    async def _handle_cover_letter(
        self,
        fields: List[FormField],
        candidate_profile: Dict[str, Any],
        job_title: str,
        company: str
    ) -> None:
        """Handle cover letter field (textarea or file upload)."""
        # Check for cover letter textarea
        cover_letter_field = None
        for field in fields:
            label = (field.label or '').lower()
            placeholder = (field.placeholder or '').lower()
            if (field.type in ['textarea', 'text']) and (
                'cover' in label or 'letter' in label or
                'cover' in placeholder or 'letter' in placeholder
            ):
                cover_letter_field = field
                break
        
        if cover_letter_field:
            cover_letter = await self.cover_letter_generator.generate_cover_letter(
                candidate_profile,
                job_title,
                company
            )
            
            success = await self.browser_agent.fill_field(
                cover_letter_field.selector,
                cover_letter,
                cover_letter_field.type
            )
            if success:
                print(f"✅ [AI_APPLY] Filled cover letter field")
    
    def _map_page_type_to_status(self, page_type: str) -> str:
        """Map page type to status."""
        status_map = {
            'login_required': 'failed_login_required',
            'captcha_detected': 'failed_captcha',
            'job_description': 'failed',
        }
        return status_map.get(page_type, 'failed')

