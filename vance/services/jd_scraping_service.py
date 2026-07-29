"""
Service for scraping and parsing job description (JD) links.
Extracts job requirements from URLs and converts them to structured format.
"""

import re
from typing import Dict, Optional
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from utils.db import get_user_profile


class JDRequirements(BaseModel):
    """Structured job requirements extracted from JD link."""

    job_title: str = Field(
        default="",
        description="The specific job title (e.g., 'Senior Python Developer', 'Product Manager')",
    )
    role_description: str = Field(
        default="",
        description="Brief description of what the role involves and day-to-day responsibilities",
    )
    required_skills: str = Field(
        default="",
        description="Comma-separated list of must-have technical skills and technologies",
    )
    experience_level: str = Field(
        default="",
        description="Required years of experience or seniority level (e.g., '3-5 years', 'Senior', 'Mid-level')",
    )
    work_model: str = Field(
        default="",
        description="Work arrangement: 'Remote', 'Hybrid', 'On-site', or specific details",
    )
    office_location: str = Field(
        default="", description="Office location or city where the role is based"
    )
    salary_budget: str = Field(
        default="",
        description="Salary range or budget for the role (e.g., '20-30 LPA', '$150k-$180k')",
    )
    hiring_urgency: str = Field(
        default="",
        description="How urgent is the hire: 'Immediate', 'Within 1 month', 'Flexible', etc.",
    )
    ideal_candidate: str = Field(
        default="",
        description="Description of the ideal candidate profile, soft skills, or cultural fit",
    )
    must_haves: str = Field(
        default="",
        description="Critical requirements that are non-negotiable",
    )
    nice_to_haves: str = Field(
        default="",
        description="Preferred but not required qualifications",
    )
    company_info: str = Field(
        default="",
        description="Information about the company, stage, culture, etc.",
    )


# Agent for extracting structured requirements from JD content
_jd_extraction_agent = Agent(
    "anthropic:claude-sonnet-4-20250514",
    system_prompt="""You are an expert HR assistant that extracts structured job requirements from job description text.

You will receive raw text content from a job description (JD) link.
Your task is to extract structured job requirements from this content.

Guidelines:
- Extract ONLY information that is explicitly mentioned in the JD
- For job_title: Look for the specific role name in the title or header
- For required_skills: Extract technical skills, technologies, tools, frameworks mentioned
- For experience_level: Look for years of experience or seniority mentions (e.g., "3+ years", "Senior", "Mid-level")
- For work_model: Look for remote/hybrid/on-site preferences
- For office_location: Extract city or location mentions
- For salary_budget: Extract any compensation/salary/CTC mentions
- For hiring_urgency: Look for timeline mentions (immediate, ASAP, this quarter, etc.)
- For ideal_candidate: Extract soft skills, cultural fit, personality traits mentioned
- For must_haves: Extract critical, non-negotiable requirements
- For nice_to_haves: Extract preferred but optional qualifications
- Leave fields empty ("") if information is not available - DO NOT make up data
- Be concise and specific in extractions""",
    output_type=JDRequirements,
)


class JDScrapingService:
    """Service for scraping and parsing job description links."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    def extract_url_from_text(self, text: str) -> Optional[str]:
        """Extract URL from text message."""
        if not text:
            return None
        
        # Pattern to match URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        matches = re.findall(url_pattern, text)
        
        if matches:
            # Return the first URL found
            return matches[0]
        return None

    def scrape_jd_content(self, url: str) -> Optional[str]:
        """
        Scrape content from a JD URL.
        Returns the text content of the page.
        """
        try:
            print(f"[JD_SCRAPE] Fetching content from: {url}")
            
            # Fetch the page
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            print(f"[JD_SCRAPE] Extracted {len(text)} characters from JD")
            return text
            
        except Exception as e:
            print(f"[JD_SCRAPE] Error scraping {url}: {e}")
            return None

    async def extract_requirements_from_jd(
        self, jd_content: str, user_id: Optional[str] = None
    ) -> JDRequirements:
        """
        Extract structured requirements from JD content using Claude.
        
        Args:
            jd_content: Raw text content from the JD
            user_id: Optional user ID for context
            
        Returns:
            JDRequirements object with extracted fields
        """
        try:
            print(f"[JD_EXTRACT] Extracting requirements from JD content ({len(jd_content)} chars)")
            
            # Use Claude to extract structured requirements
            result = await _jd_extraction_agent.run(jd_content)
            
            requirements = result.data
            print(f"[JD_EXTRACT] Extracted requirements: job_title={requirements.job_title}")
            
            return requirements
            
        except Exception as e:
            print(f"[JD_EXTRACT] Error extracting requirements: {e}")
            # Return empty requirements on error
            return JDRequirements()

    async def process_jd_link(
        self, url: str, user_id: Optional[str] = None
    ) -> Dict:
        """
        Complete pipeline: scrape JD link and extract requirements.
        
        Args:
            url: JD URL to process
            user_id: Optional user ID for context
            
        Returns:
            Dictionary with:
            - success: bool
            - requirements: JDRequirements object
            - raw_content: str (first 500 chars for preview)
            - error: str (if failed)
        """
        try:
            # Step 1: Scrape content
            jd_content = self.scrape_jd_content(url)
            
            if not jd_content:
                return {
                    "success": False,
                    "error": "Could not scrape content from the JD link. Please check if the link is accessible.",
                }
            
            # Step 2: Extract requirements
            requirements = await self.extract_requirements_from_jd(jd_content, user_id)
            
            return {
                "success": True,
                "requirements": requirements,
                "raw_content": jd_content[:500] + "..." if len(jd_content) > 500 else jd_content,
            }
            
        except Exception as e:
            print(f"[JD_PROCESS] Error processing JD link: {e}")
            return {
                "success": False,
                "error": f"Error processing JD link: {str(e)}",
            }


# Singleton instance
jd_scraping_service = JDScrapingService()

