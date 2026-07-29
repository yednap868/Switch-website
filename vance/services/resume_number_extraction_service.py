"""
Service for extracting numbers from candidate resume PDFs.

Extracts:
- Phone numbers
- Years of experience
- Salary expectations
- Years at each company
- Number of projects/companies
- Other relevant numerical data
"""

import io
import os
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse

import pdfplumber
import requests
from pydantic import BaseModel, Field

from utils.db import fs


class ExtractedNumbers(BaseModel):
    """Structured numbers extracted from a resume."""

    phone_number: Optional[str] = Field(
        default=None, description="Phone number found in resume"
    )
    years_of_experience: Optional[float] = Field(
        default=None, description="Total years of work experience"
    )
    salary_expectation: Optional[str] = Field(
        default=None, description="Salary or compensation expectation"
    )
    years_at_companies: List[float] = Field(
        default_factory=list, description="Years spent at each company"
    )
    number_of_companies: Optional[int] = Field(
        default=None, description="Total number of companies worked at"
    )
    number_of_projects: Optional[int] = Field(
        default=None, description="Number of projects mentioned"
    )
    graduation_year: Optional[int] = Field(
        default=None, description="Year of graduation"
    )
    other_numbers: List[str] = Field(
        default_factory=list, description="Other significant numbers found"
    )


class ResumeNumberExtractionService:
    """Service for extracting numbers from resume PDFs."""

    def __init__(self):
        self.phone_patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
            r'\+?\d{10,15}',  # International format
            r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',  # (123) 456-7890
        ]
        self.experience_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?|yr)\s*(?:of\s*)?(?:experience|exp)',
            r'(?:experience|exp)[:\s]+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)',
            r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s*(?:in|of)',
        ]
        self.salary_patterns = [
            r'(?:salary|compensation|expected|expecting|CTC|LPA)[:\s]*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:k|K|thousand|lakh|lakhs|L|cr|crore)?',
            r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:k|K|thousand|lakh|lakhs|L|cr|crore)?\s*(?:salary|compensation|expected|expecting|CTC|LPA)',
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:lakh|lakhs|L|cr|crore)\s*(?:per\s*annum|PA|p\.a\.)?',
        ]
        self.year_patterns = [
            r'\b(19|20)\d{2}\b',  # Years like 2010, 2020
            r'(\d{4})\s*[-–]\s*(\d{4}|\w+)',  # Date ranges
        ]
        self.duration_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?|months?|mos?)\s*(?:at|in|with)',
            r'(?:at|in|with)\s+[^,]+(?:,\s*)?(\d+(?:\.\d+)?)\s*(?:years?|yrs?|months?|mos?)',
        ]

    def extract_text_from_pdf(self, pdf_path_or_url: str) -> Optional[str]:
        """Extract text from PDF file (local path or URL)."""
        try:
            # Check if it's a local file path
            if os.path.exists(pdf_path_or_url):
                # Local file
                with pdfplumber.open(pdf_path_or_url) as pdf:
                    text = ""
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    return text.strip() if text else None
            else:
                # URL - download first
                response = requests.get(pdf_path_or_url, timeout=30)
                response.raise_for_status()

                # Extract text using pdfplumber
                text = ""
                with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"

                return text.strip() if text else None

        except Exception as e:
            print(f"❌ [RESUME_EXTRACTION] Error extracting text from PDF {pdf_path_or_url}: {e}")
            return None

    def extract_phone_number(self, text: str) -> Optional[str]:
        """Extract phone number from text."""
        for pattern in self.phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Clean up the phone number
                phone = re.sub(r'[-.\s()]', '', matches[0])
                # Validate it's a reasonable length
                if 10 <= len(phone) <= 15:
                    return phone
        return None

    def extract_years_of_experience(self, text: str) -> Optional[float]:
        """Extract total years of experience."""
        for pattern in self.experience_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    years = float(matches[0])
                    if 0 <= years <= 50:  # Reasonable range
                        return years
                except ValueError:
                    continue

        # Fallback: look for date ranges and calculate
        date_ranges = re.findall(r'(\d{4})\s*[-–]\s*(\d{4}|\w+)', text)
        if date_ranges:
            try:
                years_list = []
                for start, end in date_ranges:
                    start_year = int(start)
                    if end.isdigit():
                        end_year = int(end)
                        years_list.append(end_year - start_year)
                    elif end.lower() in ['present', 'current', 'now', 'till date']:
                        current_year = time.localtime().tm_year
                        years_list.append(current_year - start_year)

                if years_list:
                    return max(years_list)  # Return maximum experience
            except (ValueError, TypeError):
                pass

        return None

    def extract_salary_expectation(self, text: str) -> Optional[str]:
        """Extract salary expectation from text."""
        for pattern in self.salary_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        return None

    def extract_years_at_companies(self, text: str) -> List[float]:
        """Extract years spent at each company."""
        years_list = []
        for pattern in self.duration_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    years = float(match)
                    if 0 <= years <= 30:  # Reasonable range
                        years_list.append(years)
                except ValueError:
                    continue
        return sorted(set(years_list), reverse=True)  # Remove duplicates, sort descending

    def extract_number_of_companies(self, text: str) -> Optional[int]:
        """Extract number of companies worked at."""
        # Look for "Company 1", "Company 2", etc. or employment sections
        company_indicators = [
            r'(?:company|employer|organization|firm|corporation)\s*[:\d]',
            r'experience\s*[:\d]',
            r'work\s+history',
            r'employment\s+history',
        ]

        count = 0
        for indicator in company_indicators:
            matches = re.findall(indicator, text, re.IGNORECASE)
            count += len(matches)

        # Also count date ranges which typically indicate companies
        date_ranges = re.findall(r'(\d{4})\s*[-–]\s*(\d{4}|\w+)', text)
        if date_ranges:
            return len(date_ranges)

        return count if count > 0 else None

    def extract_number_of_projects(self, text: str) -> Optional[int]:
        """Extract number of projects mentioned."""
        project_patterns = [
            r'project[s]?\s*[:\d]',
            r'(?:worked\s+on|completed|developed)\s+\d+\s+project',
            r'project\s+(?:count|number|total)[:\s]*(\d+)',
        ]

        count = 0
        for pattern in project_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    # If pattern captured a number, use it
                    if isinstance(matches[0], str) and matches[0].isdigit():
                        return int(matches[0])
                    count += len(matches)
                except (ValueError, TypeError):
                    count += len(matches)

        # Count explicit "Project" mentions
        project_mentions = len(re.findall(r'\bproject\b', text, re.IGNORECASE))
        if project_mentions > 0:
            return project_mentions

        return count if count > 0 else None

    def extract_graduation_year(self, text: str) -> Optional[int]:
        """Extract graduation year."""
        graduation_patterns = [
            r'graduated?\s+(?:in\s+)?(\d{4})',
            r'(\d{4})\s*(?:graduation|degree|bachelor|master|phd)',
            r'(?:bachelor|master|phd|degree)\s+(?:in\s+)?(\d{4})',
        ]

        for pattern in graduation_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    year = int(matches[0])
                    if 1950 <= year <= time.localtime().tm_year:  # Reasonable range
                        return year
                except ValueError:
                    continue

        return None

    def extract_all_numbers(self, pdf_path_or_url: str) -> Optional[ExtractedNumbers]:
        """Extract all numbers from a resume PDF (local path or URL)."""
        if not pdf_path_or_url:
            return None

        text = self.extract_text_from_pdf(pdf_path_or_url)
        if not text:
            return None

        extracted = ExtractedNumbers(
            phone_number=self.extract_phone_number(text),
            years_of_experience=self.extract_years_of_experience(text),
            salary_expectation=self.extract_salary_expectation(text),
            years_at_companies=self.extract_years_at_companies(text),
            number_of_companies=self.extract_number_of_companies(text),
            number_of_projects=self.extract_number_of_projects(text),
            graduation_year=self.extract_graduation_year(text),
        )

        return extracted

    def update_candidate_profile_with_numbers(
        self, user_id: str, resume_path_or_url: str
    ) -> Optional[ExtractedNumbers]:
        """Extract numbers from resume (local path or URL) and update candidate profile."""
        try:
            extracted = self.extract_all_numbers(resume_path_or_url)
            if not extracted:
                print(f"⚠️ [RESUME_EXTRACTION] No numbers extracted for {user_id}")
                return None

            # Update user profile with extracted numbers
            profile_ref = fs.collection("user_profiles").document(user_id)
            profile_data = profile_ref.get().to_dict() or {}

            # Store extracted numbers in extraction_data
            extraction_data = profile_data.get("extraction_data", {})
            extraction_data["resume_extracted_numbers"] = extracted.model_dump()

            # Also update specific fields if they're missing
            if not extraction_data.get("phone_number") and extracted.phone_number:
                extraction_data["phone_number"] = extracted.phone_number

            if (
                not extraction_data.get("work_experience")
                and extracted.years_of_experience
            ):
                extraction_data["work_experience"] = f"{extracted.years_of_experience} years"

            if (
                not extraction_data.get("salary_expectations")
                and extracted.salary_expectation
            ):
                extraction_data["salary_expectations"] = extracted.salary_expectation

            # Update profile
            profile_ref.set(
                {
                    "extraction_data": extraction_data,
                    "resume_numbers_extracted_at": time.time(),
                },
                merge=True,
            )

            print(
                f"✅ [RESUME_EXTRACTION] Extracted numbers for {user_id}: "
                f"phone={extracted.phone_number}, "
                f"experience={extracted.years_of_experience} years, "
                f"salary={extracted.salary_expectation}"
            )

            return extracted

        except Exception as e:
            print(f"❌ [RESUME_EXTRACTION] Error updating profile for {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def extract_numbers_from_local_file(self, pdf_path: str) -> Optional[ExtractedNumbers]:
        """Extract numbers from a local PDF file (convenience method)."""
        return self.extract_all_numbers(pdf_path)


# Singleton instance
resume_number_extraction_service = ResumeNumberExtractionService()

