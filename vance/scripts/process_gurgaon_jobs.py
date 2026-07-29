"""
Script to process gurgaon_startup_jobs.json:
1. Find company websites and career pages
2. Add website and career page links to jobs
3. Generate job cards for candidate side
"""

import json
import os
import time
import requests
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse

# Try to use DuckDuckGo search or Google search API, or fall back to simple pattern matching
def search_company_website(company_name: str) -> Optional[str]:
    """Search for company website using DuckDuckGo or simple heuristics."""
    try:
        # Try DuckDuckGo instant answer API (free, no API key needed)
        search_query = f"{company_name} official website"
        ddg_url = f"https://api.duckduckgo.com/?q={search_query}&format=json&no_html=1&skip_disambig=1"
        
        response = requests.get(ddg_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Try to get AbstractURL first
            if data.get("AbstractURL"):
                return data["AbstractURL"]
            # Try Results
            if data.get("Results") and len(data["Results"]) > 0:
                return data["Results"][0].get("FirstURL")
            # Try RelatedTopics
            if data.get("RelatedTopics") and len(data["RelatedTopics"]) > 0:
                first_topic = data["RelatedTopics"][0]
                if isinstance(first_topic, dict) and first_topic.get("FirstURL"):
                    return first_topic["FirstURL"]
        
        # Fallback: try simple pattern (company name + .com)
        company_slug = company_name.lower().replace(" ", "").replace(".", "").replace("(", "").replace(")", "")
        potential_urls = [
            f"https://www.{company_slug}.com",
            f"https://{company_slug}.com",
            f"https://www.{company_slug}.in",
            f"https://{company_slug}.in",
        ]
        
        # Try to validate URLs
        for url in potential_urls:
            try:
                test_response = requests.head(url, timeout=3, allow_redirects=True)
                if test_response.status_code < 400:
                    return url
            except:
                continue
        
        return None
    except Exception as e:
        print(f"⚠️  Error searching website for {company_name}: {e}")
        return None


def find_career_page(website_url: str, company_name: str) -> Optional[str]:
    """Find career page URL from company website."""
    if not website_url:
        return None
    
    try:
        # Common career page patterns
        career_paths = [
            "/careers",
            "/career",
            "/jobs",
            "/job",
            "/hiring",
            "/we-are-hiring",
            "/join-us",
            "/open-positions",
        ]
        
        base_url = website_url.rstrip("/")
        
        # Try common paths
        for path in career_paths:
            career_url = base_url + path
            try:
                response = requests.head(career_url, timeout=3, allow_redirects=True)
                if response.status_code < 400:
                    return career_url
            except:
                continue
        
        # Try to scrape the website and look for career links
        try:
            response = requests.get(website_url, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                html = response.text.lower()
                # Look for career/jobs links in HTML
                for path in career_paths:
                    if path in html:
                        return base_url + path
        except:
            pass
        
        return None
    except Exception as e:
        print(f"⚠️  Error finding career page for {website_url}: {e}")
        return None


def normalize_work_arrangement(work_arrangement: str) -> str:
    """Normalize work arrangement to match Job type."""
    mapping = {
        "In Office": "On-site",
        "Hybrid": "Hybrid",
        "Remote": "Remote",
    }
    return mapping.get(work_arrangement, "Hybrid")


def normalize_company_stage(company_stage: str) -> str:
    """Normalize company stage to match Job type."""
    mapping = {
        "Early Stage": "Startup",
        "Seed": "Startup",
        "Series A": "Growth",
        "Series B": "Growth",
        "Series C": "Growth",
        "Series E": "Growth",
        "Growth Stage": "Growth",
        "Late Stage": "Enterprise",
        "Public": "Enterprise",
        "Established": "Enterprise",
    }
    return mapping.get(company_stage, "Startup")


def process_jobs(input_file: str, output_file: str):
    """Process jobs from JSON file and add website/career page links."""
    print(f"📂 Reading jobs from: {input_file}")
    
    with open(input_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    
    print(f"📊 Found {len(jobs)} jobs")
    print(f"🔍 Starting to find company websites and career pages...\n")
    
    processed_jobs = []
    companies_found = {}
    
    for i, job in enumerate(jobs, 1):
        company = job.get("company", "")
        print(f"[{i}/{len(jobs)}] Processing: {company} - {job.get('title', '')}")
        
        # Check if we already found this company
        if company in companies_found:
            website = companies_found[company].get("website")
            career_page = companies_found[company].get("career_page")
            print(f"   ✅ Using cached: website={website}, career={career_page}")
        else:
            # Search for website
            website = search_company_website(company)
            time.sleep(1)  # Rate limiting
            
            # Find career page
            career_page = None
            if website:
                career_page = find_career_page(website, company)
                time.sleep(1)  # Rate limiting
            
            # Cache result
            companies_found[company] = {
                "website": website,
                "career_page": career_page,
            }
            
            if website:
                print(f"   ✅ Found website: {website}")
            else:
                print(f"   ⚠️  Website not found")
            
            if career_page:
                print(f"   ✅ Found career page: {career_page}")
            else:
                print(f"   ⚠️  Career page not found")
        
        # Create processed job object matching Job type
        processed_job = {
            "id": f"gurgaon_{i}_{company.lower().replace(' ', '_')}",
            "title": job.get("title", ""),
            "company": company,
            "location": job.get("location", "Gurgaon, Haryana, India"),
            "category": "Technology",  # Default, could be extracted from title
            "workArrangement": normalize_work_arrangement(job.get("work_arrangement", "Hybrid")),
            "employmentType": job.get("employment_type", "Full Time"),
            "experienceLevel": job.get("experience_level", "Mid Level"),
            "companyStage": normalize_company_stage(job.get("company_stage", "Early Stage")),
            "description": job.get("description", ""),
            "requiredQualifications": job.get("requirements", []),
            "salaryRange": job.get("salary_range"),
            "website": website,  # For display in card
            "applicationUrl": career_page,  # For AI agent to use when applying (hidden from card)
        }
        
        processed_jobs.append(processed_job)
        print()
    
    # Save processed jobs
    print(f"💾 Saving processed jobs to: {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed_jobs, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Processed {len(processed_jobs)} jobs")
    print(f"📊 Stats:")
    print(f"   - Companies with website: {sum(1 for j in processed_jobs if j.get('website'))}")
    print(f"   - Companies with career page: {sum(1 for j in processed_jobs if j.get('applicationUrl'))}")
    
    return processed_jobs


if __name__ == "__main__":
    # Use fixed file if it exists, otherwise try original
    fixed_file = os.path.expanduser("~/Downloads/gurgaon_startup_jobs_fixed.json")
    original_file = os.path.expanduser("~/Downloads/gurgaon_startup_jobs.json")
    input_file = fixed_file if os.path.exists(fixed_file) else original_file
    output_file = os.path.expanduser("~/Downloads/gurgaon_jobs_processed.json")
    
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        exit(1)
    
    processed_jobs = process_jobs(input_file, output_file)
    print(f"\n✅ Done! Processed jobs saved to: {output_file}")

