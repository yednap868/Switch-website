"""
Service for AI-powered job applications.
Handles navigating to career pages, filling forms, and submitting applications.
"""

import os
import time
import base64
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from playwright.async_api import Page, Browser

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    # Define dummy types for runtime when Playwright is not available
    Page = None  # type: ignore
    Browser = None  # type: ignore
    print("⚠️ [JOB_APPLICATION] Playwright not available - install with: pip install playwright")

from utils.db import fs, get_user_profile


class CandidateApplicationData(BaseModel):
    """Structured candidate data for job applications."""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    location: Optional[str] = None
    years_of_experience: Optional[str] = None
    current_role: Optional[str] = None
    skills: list[str] = []
    resume_text: Optional[str] = None
    resume_path: Optional[str] = None
    cover_letter: Optional[str] = None
    call_insights: Optional[Dict[str, Any]] = None  # Insights from voice calls


class JobApplicationService:
    """Service for handling AI job applications."""

    def __init__(self):
        self.browser: Optional[Any] = None  # Type: playwright.async_api.Browser (only available if Playwright installed)

    def _extract_candidate_data(self, user_id: str) -> Optional[CandidateApplicationData]:
        """
        Extract candidate data from resume and voice calls.
        
        Sources (in priority order):
        1. extractions/{user_id} - PRIMARY source (direct from resume upload)
        2. user_profiles/{user_id} - extraction_data (synced data)
        3. users/{user_id} - basic profile data
        4. user_calls/{user_id}/calls - call transcripts and insights
        """
        try:
            # PRIMARY SOURCE: Check extractions collection first (direct from resume upload)
            extraction_ref = fs.collection("extractions").document(user_id).get()
            extraction_data = extraction_ref.to_dict() if extraction_ref.exists else {}
            
            print(f"📋 [JOB_APPLICATION] Checking extractions/{user_id}: found={extraction_ref.exists}")
            if extraction_ref.exists:
                print(f"   Name: {extraction_data.get('name')}, Email: {extraction_data.get('email')}, Phone: {extraction_data.get('phone_number')}")
            
            # Get user profile (fallback)
            user_profile = get_user_profile(user_id) or {}
            
            # Get profile data (fallback)
            profile_ref = fs.collection("user_profiles").document(user_id).get()
            profile_data = profile_ref.to_dict() if profile_ref.exists else {}
            
            # Merge profile extraction_data if extractions collection is empty
            if not extraction_data and profile_data.get("extraction_data"):
                extraction_data = profile_data.get("extraction_data", {})
                print(f"📋 [JOB_APPLICATION] Using user_profiles.extraction_data as fallback")

            # Get basic info (NEVER use "Candidate" as fallback - fail if no name)
            name = (
                extraction_data.get("name")
                or user_profile.get("name")
                or profile_data.get("name")
                or user_profile.get("profile", {}).get("name")
            )
            
            if not name or name == "Candidate":
                print(f"❌ [JOB_APPLICATION] CRITICAL: No name found in any source for {user_id}")
                print(f"   extraction_data.name: {extraction_data.get('name')}")
                print(f"   user_profile.name: {user_profile.get('name')}")
                print(f"   profile_data.name: {profile_data.get('name')}")
                # Try to extract from resume_text if available
                if extraction_data.get("resume_text"):
                    import re
                    name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})', extraction_data["resume_text"][:200], re.MULTILINE)
                    if name_match:
                        name = name_match.group(1)
                        print(f"   ✅ Extracted name from resume_text: {name}")
                
                # If still no name, return None (don't create CandidateApplicationData with None name)
                if not name or name == "Candidate":
                    print(f"   ❌ Cannot proceed without a valid name. Returning None.")
                    return None

            email = (
                extraction_data.get("email")
                or user_profile.get("email")
                or profile_data.get("email")
                or user_profile.get("profile", {}).get("email")
            )

            phone = (
                extraction_data.get("phone_number")
                or extraction_data.get("resume_extracted_numbers", {}).get("phone_number")
                or user_profile.get("phone")
                or user_profile.get("wa_id")
                or user_id
            )

            linkedin_url = (
                extraction_data.get("linkedin_url")
                or profile_data.get("linkedin_url")
                or user_profile.get("profile", {}).get("linkedin_url")
            )

            location = extraction_data.get("location") or extraction_data.get("current_location")
            
            years_of_experience = (
                extraction_data.get("resume_extracted_numbers", {}).get("years_of_experience")
                or extraction_data.get("work_experience")
            )

            current_role = extraction_data.get("current_role") or extraction_data.get("role")

            # Get skills (try multiple sources)
            skills = []
            if extraction_data.get("skills"):
                if isinstance(extraction_data["skills"], list):
                    skills = extraction_data["skills"]
                elif isinstance(extraction_data["skills"], str):
                    skills = [s.strip() for s in extraction_data["skills"].split(",")]
            
            # Get resume path and text (resolve relative paths)
            resume_path = extraction_data.get("resume_path") or extraction_data.get("resume_url")
            if resume_path and not os.path.isabs(resume_path):
                # Try common locations
                possible_paths = [
                    resume_path,  # Try as-is first
                    os.path.join(os.path.expanduser("~"), "Vance-1", "storage", "resumes", os.path.basename(resume_path)),
                    os.path.join(os.path.expanduser("~"), "Vance-1", "uploads", os.path.basename(resume_path)),
                    os.path.join("/tmp", os.path.basename(resume_path)),
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        resume_path = path
                        print(f"✅ [JOB_APPLICATION] Resolved resume path: {resume_path}")
                        break
                else:
                    print(f"⚠️ [JOB_APPLICATION] Resume path not found: {extraction_data.get('resume_path')}")
            
            resume_text = extraction_data.get("resume_text") or extraction_data.get("summary") or extraction_data.get("the_story")
            
            # Debug: Print what we extracted
            print(f"✅ [JOB_APPLICATION] Extracted candidate data:")
            print(f"   Name: {name}")
            print(f"   Email: {email}")
            print(f"   Phone: {phone}")
            print(f"   LinkedIn: {linkedin_url}")
            print(f"   Resume Path: {resume_path} (exists: {os.path.exists(resume_path) if resume_path else False})")

            # Get latest call insights
            call_insights = self._get_latest_call_insights(user_id)

            return CandidateApplicationData(
                name=name,
                email=email,
                phone=phone,
                linkedin_url=linkedin_url,
                location=location,
                years_of_experience=years_of_experience,
                current_role=current_role,
                skills=skills,
                resume_text=resume_text,
                resume_path=resume_path,
                call_insights=call_insights,
            )

        except Exception as e:
            print(f"❌ [JOB_APPLICATION] Error extracting candidate data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_latest_call_insights(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get latest voice call insights for the candidate."""
        try:
            # Try user_call_summaries first (summary data)
            summary_ref = fs.collection("user_call_summaries").document(user_id).get()
            if summary_ref.exists:
                summary_data = summary_ref.to_dict() or {}
                if summary_data.get("extraction_data"):
                    return {
                        "call_data": summary_data.get("extraction_data", {}),
                        "key_insights": summary_data.get("key_insights", {}),
                    }

            # Try latest call from user_calls collection
            calls_ref = fs.collection("user_calls").document(user_id).collection("calls")
            calls_query = calls_ref.order_by("timestamp", direction="DESCENDING").limit(1)
            latest_calls = list(calls_query.stream())
            
            if latest_calls:
                call_data = latest_calls[0].to_dict() or {}
                return {
                    "call_data": call_data.get("extraction_data", {}),
                    "key_insights": call_data.get("key_insights", {}),
                    "transcript": call_data.get("full_transcript") or call_data.get("transcript"),
                }

            return None

        except Exception as e:
            print(f"⚠️ [JOB_APPLICATION] Error getting call insights: {e}")
            return None

    async def _generate_cover_letter(
        self,
        candidate_data: CandidateApplicationData,
        job_title: str,
        company: str,
        job_description: Optional[str] = None
    ) -> str:
        """Generate a personalized cover letter using LLM."""
        try:
            from anthropic import Anthropic
            
            client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            
            # Build context from candidate data
            experience_text = f"{candidate_data.years_of_experience} years of experience" if candidate_data.years_of_experience else "professional experience"
            skills_text = ", ".join(candidate_data.skills[:10]) if candidate_data.skills else "relevant technical skills"
            
            context_parts = [
                f"Name: {candidate_data.name}",
                f"Current Role: {candidate_data.current_role}" if candidate_data.current_role else None,
                f"Experience: {experience_text}",
                f"Skills: {skills_text}",
            ]
            
            if candidate_data.resume_text:
                context_parts.append(f"Background: {candidate_data.resume_text[:500]}...")
            
            context = "\n".join([p for p in context_parts if p])
            
            prompt = f"""Write a professional, concise cover letter for the following candidate applying for {job_title} at {company}.

Candidate Information:
{context}

{f'Job Description: {job_description[:500]}...' if job_description else ''}

Requirements:
- Keep it under 300 words
- Professional and authentic tone
- Highlight relevant experience and skills
- Show enthusiasm for the role and company
- No generic phrases or cliches

Write the cover letter:"""

            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            cover_letter = response.content[0].text if response.content else ""
            print(f"✅ [JOB_APPLICATION] Generated cover letter for {candidate_data.name}")
            return cover_letter.strip()

        except Exception as e:
            print(f"⚠️ [JOB_APPLICATION] Error generating cover letter: {e}")
            # Return a simple fallback
            return f"I am writing to express my interest in the {job_title} position at {company}. Based on my experience and skills, I believe I would be a great fit for this role."

    async def _detect_form_fields(self, page: Any) -> Dict[str, List[Dict[str, str]]]:
        """
        Intelligently detect all form fields on the page and categorize them.
        Returns a dict mapping field types to lists of detected fields.
        """
        try:
            detected_fields = {
                "name": [],
                "email": [],
                "phone": [],
                "linkedin": [],
                "location": [],
                "resume": [],
                "cover_letter": [],
                "experience": [],
                "skills": [],
                "other": []
            }
            
            # Get all input and textarea elements on the page
            all_inputs = await page.locator('input, textarea, select').all()
            
            for input_elem in all_inputs:
                try:
                    tag_name = await input_elem.evaluate('el => el.tagName.toLowerCase()')
                    input_type = await input_elem.get_attribute('type') or ''
                    name_attr = await input_elem.get_attribute('name') or ''
                    id_attr = await input_elem.get_attribute('id') or ''
                    placeholder = await input_elem.get_attribute('placeholder') or ''
                    label_text = ''
                    
                    # Try to find associated label
                    try:
                        if id_attr:
                            label = page.locator(f'label[for="{id_attr}"]')
                            if await label.count() > 0:
                                label_text = (await label.first.inner_text()).strip()[:50]
                    except:
                        pass
                    
                    # Build field identifier
                    field_info = {
                        "tag": tag_name,
                        "type": input_type,
                        "name": name_attr,
                        "id": id_attr,
                        "placeholder": placeholder,
                        "label": label_text,
                        "selector": f'{tag_name}[name="{name_attr}"]' if name_attr else f'{tag_name}#{id_attr}' if id_attr else tag_name
                    }
                    
                    # Categorize field based on attributes
                    search_text = f"{name_attr} {id_attr} {placeholder} {label_text}".lower()
                    
                    # Name fields: contains name-related terms (but not username, companyname, etc.)
                    if any(term in search_text for term in ['firstname', 'first_name', 'first name', 'lastname', 'last_name', 'last name', 'fullname', 'full_name', 'full name']) or \
                       (('name' in search_text or 'first' in search_text or 'last' in search_text) and 
                        not any(skip in search_text for skip in ['user', 'company', 'organization', 'business', 'account'])):
                        detected_fields["name"].append(field_info)
                    elif 'email' in search_text or input_type == 'email':
                        detected_fields["email"].append(field_info)
                    elif 'phone' in search_text or 'tel' in search_text or input_type == 'tel':
                        detected_fields["phone"].append(field_info)
                    elif 'linkedin' in search_text:
                        detected_fields["linkedin"].append(field_info)
                    elif 'location' in search_text or 'city' in search_text or 'address' in search_text:
                        detected_fields["location"].append(field_info)
                    elif 'resume' in search_text or 'cv' in search_text or 'upload' in search_text or input_type == 'file':
                        detected_fields["resume"].append(field_info)
                    elif 'cover' in search_text or 'letter' in search_text or 'message' in search_text or tag_name == 'textarea':
                        detected_fields["cover_letter"].append(field_info)
                    elif 'experience' in search_text or 'years' in search_text or 'yoe' in search_text:
                        detected_fields["experience"].append(field_info)
                    elif 'skill' in search_text:
                        detected_fields["skills"].append(field_info)
                    else:
                        detected_fields["other"].append(field_info)
                        
                except Exception as e:
                    continue
            
            print(f"🔍 [JOB_APPLICATION] Detected form fields:")
            for field_type, fields in detected_fields.items():
                if fields:
                    print(f"   {field_type}: {len(fields)} field(s)")
            
            return detected_fields
            
        except Exception as e:
            print(f"⚠️ [JOB_APPLICATION] Error detecting form fields: {e}")
            return {}

    async def _fill_application_form(
        self,
        page: Any,  # Type: playwright.async_api.Page (only available if Playwright installed)
        candidate_data: CandidateApplicationData,
        job_title: str,
        company: str,
        cover_letter: str,
        timeline: Optional[List[Dict[str, Any]]] = None,
        screenshots: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Intelligently fill out job application form using Playwright.
        
        Steps:
        1. Detect all form fields on the page
        2. Match detected fields to candidate data
        3. Fill fields with appropriate values
        4. Upload resume
        """
        try:
            filled_fields = []  # Track fields that were filled
            
            # First, detect all form fields on the page
            detected_fields = await self._detect_form_fields(page)
            
            # Common form field selectors to try (fallback if detection fails)
            field_mappings = {
                "name": [
                    'input[name*="name" i]',
                    'input[id*="name" i]',
                    'input[placeholder*="name" i]',
                    'input[type="text"]:nth-of-type(1)',
                ],
                "email": [
                    'input[name*="email" i]',
                    'input[id*="email" i]',
                    'input[type="email"]',
                    'input[placeholder*="email" i]',
                ],
                "phone": [
                    'input[name*="phone" i]',
                    'input[id*="phone" i]',
                    'input[type="tel"]',
                    'input[placeholder*="phone" i]',
                ],
                "linkedin": [
                    'input[name*="linkedin" i]',
                    'input[id*="linkedin" i]',
                    'input[placeholder*="linkedin" i]',
                ],
                "location": [
                    'input[name*="location" i]',
                    'input[id*="location" i]',
                    'input[placeholder*="location" i]',
                ],
                "resume": [
                    'input[name*="resume" i]',
                    'input[name*="cv" i]',
                    'input[type="file"]',
                    'input[id*="resume" i]',
                ],
                "cover_letter": [
                    'textarea[name*="cover" i]',
                    'textarea[name*="letter" i]',
                    'textarea[id*="cover" i]',
                    'textarea[id*="message" i]',
                ],
            }

            # Fill name fields (use detected fields first, then fallback to selectors)
            if candidate_data.name and candidate_data.name != "Candidate":
                name_parts = candidate_data.name.split(" ", 1)
                first_name = name_parts[0] if name_parts else candidate_data.name
                last_name = name_parts[1] if len(name_parts) > 1 else ""
                
                name_filled = False
                
                # Try detected name fields first
                if detected_fields.get("name"):
                    for field_info in detected_fields["name"]:
                        try:
                            selector = field_info["selector"]
                            field = page.locator(selector).first
                            if await field.is_visible():
                                current_value = await field.input_value()
                                if not current_value:  # Only fill if empty
                                    # Check if this looks like first/last name field
                                    search_text = f"{field_info['name']} {field_info['id']} {field_info['placeholder']} {field_info['label']}".lower()
                                    if 'first' in search_text and first_name:
                                        await field.fill(first_name)
                                        filled_fields.append({"field_name": "first_name", "label": field_info.get("label", "First Name"), "value": first_name, "selector": selector})
                                        name_filled = True
                                    elif 'last' in search_text and last_name:
                                        await field.fill(last_name)
                                        filled_fields.append({"field_name": "last_name", "label": field_info.get("label", "Last Name"), "value": last_name, "selector": selector})
                                        name_filled = True
                                    elif not name_filled:  # Fill with full name if not first/last specific
                                        await field.fill(candidate_data.name)
                                        filled_fields.append({"field_name": "name", "label": field_info.get("label", "Full Name"), "value": candidate_data.name, "selector": selector})
                                        name_filled = True
                                        break
                        except:
                            continue
                
                # Fallback to selector-based matching if detected fields didn't work
                if not name_filled:
                    # Try first name
                    for selector in ['input[name*="first" i]', 'input[id*="first" i]']:
                        try:
                            field = page.locator(selector).first
                            if await field.is_visible():
                                await field.fill(first_name)
                                filled_fields.append({"field_name": "first_name", "label": "First Name", "value": first_name, "selector": selector})
                                name_filled = True
                                break
                        except:
                            pass
                    
                    # Try last name
                    if last_name and not name_filled:
                        for selector in ['input[name*="last" i]', 'input[id*="last" i]']:
                            try:
                                field = page.locator(selector).first
                                if await field.is_visible():
                                    await field.fill(last_name)
                                    filled_fields.append({"field_name": "last_name", "label": "Last Name", "value": last_name, "selector": selector})
                                    name_filled = True
                                    break
                            except:
                                pass
                    
                    # Try full name
                    if not name_filled:
                        for selector in field_mappings["name"]:
                            try:
                                field = page.locator(selector).first
                                if await field.is_visible() and not await field.input_value():
                                    await field.fill(candidate_data.name)
                                    filled_fields.append({"field_name": "name", "label": "Full Name", "value": candidate_data.name, "selector": selector})
                                    name_filled = True
                                    break
                            except:
                                pass

            # Fill email (try detected fields first)
            if candidate_data.email:
                email_filled = False
                if detected_fields.get("email"):
                    for field_info in detected_fields["email"]:
                        try:
                            selector = field_info["selector"]
                            field = page.locator(selector).first
                            if await field.is_visible():
                                await field.fill(candidate_data.email)
                                filled_fields.append({"field_name": "email", "label": field_info.get("label", "Email"), "value": candidate_data.email, "selector": selector})
                                email_filled = True
                                break
                        except:
                            continue
                
                # Fallback to selectors
                if not email_filled:
                    for selector in field_mappings["email"]:
                        try:
                            field = page.locator(selector).first
                            if await field.is_visible():
                                await field.fill(candidate_data.email)
                                filled_fields.append({"field_name": "email", "label": "Email", "value": candidate_data.email, "selector": selector})
                                break
                        except:
                            pass

            # Fill phone (try detected fields first)
            if candidate_data.phone:
                phone_filled = False
                if detected_fields.get("phone"):
                    for field_info in detected_fields["phone"]:
                        try:
                            selector = field_info["selector"]
                            field = page.locator(selector).first
                            if await field.is_visible():
                                await field.fill(candidate_data.phone)
                                filled_fields.append({"field_name": "phone", "label": field_info.get("label", "Phone"), "value": candidate_data.phone, "selector": selector})
                                phone_filled = True
                                break
                        except:
                            continue
                
                # Fallback to selectors
                if not phone_filled:
                    for selector in field_mappings["phone"]:
                        try:
                            field = page.locator(selector).first
                            if await field.is_visible():
                                await field.fill(candidate_data.phone)
                                filled_fields.append({"field_name": "phone", "label": "Phone", "value": candidate_data.phone, "selector": selector})
                                break
                        except:
                            pass

            # Fill LinkedIn (try detected fields first)
            if candidate_data.linkedin_url:
                linkedin_filled = False
                if detected_fields.get("linkedin"):
                    for field_info in detected_fields["linkedin"]:
                        try:
                            selector = field_info["selector"]
                            field = page.locator(selector).first
                            if await field.is_visible():
                                await field.fill(candidate_data.linkedin_url)
                                filled_fields.append({"field_name": "linkedin", "label": field_info.get("label", "LinkedIn"), "value": candidate_data.linkedin_url, "selector": selector})
                                linkedin_filled = True
                                break
                        except:
                            continue
                
                # Fallback to selectors
                if not linkedin_filled:
                    for selector in field_mappings["linkedin"]:
                        try:
                            field = page.locator(selector).first
                            if await field.is_visible():
                                await field.fill(candidate_data.linkedin_url)
                                filled_fields.append({"field_name": "linkedin", "label": "LinkedIn", "value": candidate_data.linkedin_url, "selector": selector})
                                break
                        except:
                            pass

            # Fill location (try detected fields first)
            if candidate_data.location:
                location_filled = False
                if detected_fields.get("location"):
                    for field_info in detected_fields["location"]:
                        try:
                            selector = field_info["selector"]
                            field = page.locator(selector).first
                            if await field.is_visible():
                                await field.fill(candidate_data.location)
                                filled_fields.append({"field_name": "location", "label": field_info.get("label", "Location"), "value": candidate_data.location, "selector": selector})
                                location_filled = True
                                break
                        except:
                            continue
                
                # Fallback to selectors
                if not location_filled:
                    for selector in field_mappings["location"]:
                        try:
                            field = page.locator(selector).first
                            if await field.is_visible():
                                await field.fill(candidate_data.location)
                                filled_fields.append({"field_name": "location", "label": "Location", "value": candidate_data.location, "selector": selector})
                                break
                        except:
                            pass

            # Upload resume (CRITICAL - try detected fields first, then all file inputs)
            if candidate_data.resume_path and os.path.exists(candidate_data.resume_path):
                resume_uploaded = False
                
                # Try detected resume fields first
                if detected_fields.get("resume"):
                    for field_info in detected_fields["resume"]:
                        try:
                            selector = field_info["selector"]
                            file_input = page.locator(selector).first
                            if await file_input.is_visible():
                                await file_input.set_input_files(candidate_data.resume_path)
                                filled_fields.append({"field_name": "resume", "label": field_info.get("label", "Resume"), "value": os.path.basename(candidate_data.resume_path), "selector": selector})
                                print(f"✅ [JOB_APPLICATION] Uploaded resume via detected field: {candidate_data.resume_path}")
                                resume_uploaded = True
                                break
                        except Exception as e:
                            print(f"⚠️ [JOB_APPLICATION] Error uploading to detected field: {e}")
                            continue
                
                # Fallback: Try all file inputs on the page
                if not resume_uploaded:
                    try:
                        file_inputs = await page.locator('input[type="file"]').all()
                        for file_input in file_inputs:
                            try:
                                if await file_input.is_visible():
                                    await file_input.set_input_files(candidate_data.resume_path)
                                    name_attr = await file_input.get_attribute('name') or ''
                                    id_attr = await file_input.get_attribute('id') or ''
                                    filled_fields.append({"field_name": "resume", "label": "Resume", "value": os.path.basename(candidate_data.resume_path), "selector": f'input[type="file"][name="{name_attr}"]' if name_attr else f'input[type="file"]#{id_attr}' if id_attr else 'input[type="file"]'})
                                    print(f"✅ [JOB_APPLICATION] Uploaded resume via file input: {candidate_data.resume_path}")
                                    resume_uploaded = True
                                    break
                            except Exception as e:
                                continue
                    except:
                        pass
                
                # Last resort: Try selector-based approach
                if not resume_uploaded:
                    for selector in field_mappings["resume"]:
                        try:
                            file_input = page.locator(selector).first
                            if await file_input.is_visible():
                                await file_input.set_input_files(candidate_data.resume_path)
                                filled_fields.append({"field_name": "resume", "label": "Resume", "value": os.path.basename(candidate_data.resume_path), "selector": selector})
                                print(f"✅ [JOB_APPLICATION] Uploaded resume via selector: {candidate_data.resume_path}")
                                break
                        except:
                            pass

            # Fill cover letter (try detected fields first)
            if cover_letter:
                cover_filled = False
                if detected_fields.get("cover_letter"):
                    for field_info in detected_fields["cover_letter"]:
                        try:
                            selector = field_info["selector"]
                            textarea = page.locator(selector).first
                            if await textarea.is_visible():
                                await textarea.fill(cover_letter)
                                filled_fields.append({"field_name": "cover_letter", "label": field_info.get("label", "Cover Letter"), "value": cover_letter[:100] + "..." if len(cover_letter) > 100 else cover_letter, "selector": selector})
                                cover_filled = True
                                break
                        except:
                            continue
                
                # Fallback to selectors
                if not cover_filled:
                    for selector in field_mappings["cover_letter"]:
                        try:
                            textarea = page.locator(selector).first
                            if await textarea.is_visible():
                                await textarea.fill(cover_letter)
                                filled_fields.append({"field_name": "cover_letter", "label": "Cover Letter", "value": cover_letter[:100] + "..." if len(cover_letter) > 100 else cover_letter, "selector": selector})
                                break
                        except:
                            pass

            # Wait a bit for any async updates
            await page.wait_for_timeout(1000)
            
            return {
                "success": len(filled_fields) > 0,
                "form_fields": filled_fields
            }

        except Exception as e:
            print(f"⚠️ [JOB_APPLICATION] Error filling form: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "form_fields": []}

    async def apply_to_job(
        self,
        user_id: str,
        job_title: str,
        company: str,
        application_url: str,
        job_url: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply to a job on behalf of a candidate using AI.
        
        Uses the new AI Apply orchestrator for intelligent form filling.
        
        Steps:
        1. Extract candidate data from resume and call transcripts
        2. Use orchestrator to navigate, map fields with LLM, fill form, and submit
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                "status": "error",
                "message": "Playwright not available. Please install: pip install playwright && playwright install",
            }

        try:
            # Extract candidate data
            candidate_data = self._extract_candidate_data(user_id)
            if not candidate_data:
                return {
                    "status": "error",
                    "message": "Could not extract candidate data. Please ensure profile is complete.",
                }

            print(f"✅ [JOB_APPLICATION] Extracted data for {candidate_data.name}")

            # Convert candidate_data to dict format for orchestrator
            candidate_profile = {
                "full_name": candidate_data.name,
                "email": candidate_data.email,
                "phone": candidate_data.phone,
                "current_company": None,  # Extract from resume if available
                "current_role": candidate_data.current_role,
                "experience_years": int(candidate_data.years_of_experience) if candidate_data.years_of_experience and candidate_data.years_of_experience.isdigit() else None,
                "skills": candidate_data.skills,
                "location": candidate_data.location,
                "linkedin_url": candidate_data.linkedin_url,
                "github_url": None,  # Extract if available
                "portfolio_url": None,  # Extract if available
                "summary": candidate_data.resume_text[:500] if candidate_data.resume_text else None,
            }
            
            # Use the new orchestrator
            from services.ai_apply.application_orchestrator import ApplicationOrchestrator
            
            orchestrator = ApplicationOrchestrator()

            # Update status: processing
            doc_id = f"{user_id}_{job_id}" if job_id else f"{user_id}_{job_title.replace(' ', '_')}"
            application_ref = fs.collection("job_applications").document(doc_id)
            
            def update_status(step: str, data: Dict[str, Any] = None):
                """Update application status in Firestore."""
                update_data = {
                "status": "processing",
                    "current_step": step,
                "updated_at": time.time(),
                }
                if data:
                    update_data.update(data)
                application_ref.set(update_data, merge=True)
            
            update_status("extracting_data")
            update_status("navigating")
            
            # Process application
            result = await orchestrator.process_application(
                candidate_profile=candidate_profile,
                job_url=application_url or job_url,
                job_title=job_title,
                company=company,
                resume_path=candidate_data.resume_path
            )
            
            # Map orchestrator status to our status
            status_map = {
                "submitted": "submitted",
                "failed": "failed",
                "failed_login_required": "failed",
                "failed_captcha": "failed",
            }
            application_status = status_map.get(result["status"], "failed")
            
            # Update Firestore with final result
            application_data = {
                "status": application_status,
                "applied_at": result.get("applied_at", time.time()),
                "current_step": "complete",
                "updated_at": time.time(),
            }
            
            if result.get("error"):
                application_data["error_message"] = result["error"]
            
            if result.get("form_fields"):
                application_data["form_fields"] = result["form_fields"]
                application_data["form_data_captured"] = True
            
            if result.get("screenshots"):
                application_data["screenshots"] = result["screenshots"]
                application_data["has_screenshots"] = True
            
            application_ref.set(application_data, merge=True)

            return {
                "status": "success" if application_status == "submitted" else "error",
                "application_status": application_status,
                "message": "Application submitted successfully" if application_status == "submitted" else result.get("error", "Application failed"),
                "error": result.get("error"),
            }

        except Exception as e:
            print(f"❌ [JOB_APPLICATION] Error in apply_to_job: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": f"Error processing application: {str(e)}",
            }


# Singleton instance
job_application_service = JobApplicationService()

