"""
Cover Letter Generator for AI Apply Feature.
Generates personalized cover letters using Claude.
"""

import os
from typing import Dict, Any, Optional

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️ [COVER_LETTER] Anthropic not available - install with: pip install anthropic")


class CoverLetterGenerator:
    """Generates cover letters using Claude."""
    
    def __init__(self, api_key: Optional[str] = None):
        if not ANTHROPIC_AVAILABLE:
            raise RuntimeError("Anthropic SDK not available")
        
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        self.client = Anthropic(api_key=self.api_key)
    
    async def generate_cover_letter(
        self,
        candidate: Dict[str, Any],
        job_title: str,
        company_name: str,
        job_description: Optional[str] = None
    ) -> str:
        """Generate a personalized cover letter."""
        prompt = self._build_cover_letter_prompt(candidate, job_title, company_name, job_description)
        
        try:
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            cover_letter = response.content[0].text if response.content else ""
            return cover_letter.strip()
        
        except Exception as e:
            print(f"❌ [COVER_LETTER] Error generating cover letter: {e}")
            raise
    
    def _build_cover_letter_prompt(
        self,
        candidate: Dict[str, Any],
        job_title: str,
        company_name: str,
        job_description: Optional[str] = None
    ) -> str:
        """Build the prompt for cover letter generation."""
        candidate_name = candidate.get("full_name") or candidate.get("name", "Professional")
        current_role = candidate.get("current_role") or candidate.get("current_company", "Professional")
        experience_years = candidate.get("experience_years") or candidate.get("years_of_experience", "Several")
        skills = candidate.get("skills", [])
        skills_text = ", ".join(skills[:10]) if skills else "relevant technical skills"
        summary = candidate.get("summary") or "Experienced professional"
        
        return f"""You are writing a professional, concise cover letter for a job application.

CANDIDATE:
Name: {candidate_name}
Current Role: {current_role}
Experience: {experience_years} years
Skills: {skills_text}
Summary: {summary}

JOB:
Position: {job_title}
Company: {company_name}
{f'Description: {job_description[:500]}...' if job_description else ''}

REQUIREMENTS:
1. Keep it 150-300 words maximum
2. Professional but warm tone
3. Highlight 2-3 most relevant experiences/skills
4. Show genuine interest in the role and company
5. Founder-facing language (startups value builders and problem-solvers)
6. No generic phrases or fluff
7. Direct and confident
8. End with clear interest in next steps

OUTPUT:
Write ONLY the cover letter text (no subject line, no signature block).
Start directly with the greeting."""

