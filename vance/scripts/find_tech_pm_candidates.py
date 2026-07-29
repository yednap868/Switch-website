#!/usr/bin/env python3
"""
Find relevant candidates for Tech PM role.

Requirements:
- Must have tech experience before transitioning to PM
- At least 1 YOE
- Good to have: startup experience, Web3 exposure, Tier 1 education (or great projects/work ex)
"""

import sys
import os
import re
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_extraction_data, get_user_profile


def extract_years_of_experience(experience_str: str, work_experience: List) -> float:
    """Extract years of experience from string or work experience array."""
    yoe = 0.0
    
    # First, try to extract from years_of_experience field
    if experience_str:
        # Look for patterns like "2 years", "1.5 years", "3+ years", "7+ years"
        patterns = [
            r'(\d+\.?\d*)\s*\+?\s*years?',
            r'(\d+\.?\d*)\s*\+?\s*yr',
            r'(\d+\.?\d*)\s*\+?\s*y\.?o\.?e',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, str(experience_str).lower())
            if match:
                try:
                    yoe = float(match.group(1))
                    if yoe > 0:
                        return yoe
                except:
                    pass
    
    # Also check work_experience string/array for embedded YOE
    if work_experience:
        # If work_experience is a string, check it directly
        if isinstance(work_experience, str):
            patterns = [
                r'(\d+\.?\d*)\s*\+?\s*years?',
                r'(\d+\.?\d*)\s*\+?\s*yr',
            ]
            for pattern in patterns:
                match = re.search(pattern, work_experience.lower())
                if match:
                    try:
                        yoe = float(match.group(1))
                        if yoe > 0:
                            return yoe
                    except:
                        pass
    
    # If not found, try to calculate from work_experience dates
    if work_experience:
        from datetime import datetime
        
        total_months = 0
        for exp in work_experience:
            if isinstance(exp, dict):
                start_date = exp.get("start_date") or exp.get("start") or exp.get("from")
                end_date = exp.get("end_date") or exp.get("end") or exp.get("to") or "present"
                
                if start_date:
                    try:
                        # Try to parse dates in various formats
                        start = None
                        if isinstance(start_date, str):
                            # Try common date formats
                            for fmt in ["%Y-%m", "%Y-%m-%d", "%m/%Y", "%B %Y", "%Y"]:
                                try:
                                    start = datetime.strptime(start_date, fmt)
                                    break
                                except:
                                    continue
                        
                        if start:
                            end = datetime.now()
                            if end_date and end_date.lower() not in ["present", "current", "now"]:
                                for fmt in ["%Y-%m", "%Y-%m-%d", "%m/%Y", "%B %Y", "%Y"]:
                                    try:
                                        end = datetime.strptime(end_date, fmt)
                                        break
                                    except:
                                        continue
                            
                            # Calculate months
                            months = (end.year - start.year) * 12 + (end.month - start.month)
                            if months > 0:
                                total_months += months
                    except:
                        pass
        
        if total_months > 0:
            yoe = total_months / 12.0
            return yoe
    
    # If still 0, check if work_experience has multiple entries (likely has experience)
    if work_experience and len(work_experience) > 1:
        # Multiple roles likely means at least 1+ years
        return 1.0
    
    return yoe


def has_tech_background(extraction_data: Dict, user_profile: Dict) -> bool:
    """Check if candidate has tech experience before PM."""
    # Check for tech roles in work experience
    work_experience = extraction_data.get("work_experience", [])
    if isinstance(work_experience, str):
        work_experience = [work_experience]
    
    tech_keywords = [
        "developer", "engineer", "software", "programming", "coding",
        "full stack", "backend", "frontend", "devops", "sde", "swe",
        "tech lead", "technical", "architect", "programmer", "coder"
    ]
    
    # Check extraction data
    for exp in work_experience:
        if isinstance(exp, dict):
            exp_text = str(exp.get("role", "") + " " + exp.get("company", "") + " " + exp.get("description", "")).lower()
        else:
            exp_text = str(exp).lower()
        
        for keyword in tech_keywords:
            if keyword in exp_text:
                return True
    
    # Check core_skills for tech skills
    core_skills = extraction_data.get("core_skills", "")
    if core_skills:
        tech_skill_keywords = [
            "python", "javascript", "java", "react", "node", "aws", "docker",
            "kubernetes", "sql", "mongodb", "postgres", "redis", "api",
            "microservices", "system design", "algorithms", "data structures"
        ]
        skills_lower = str(core_skills).lower()
        for keyword in tech_skill_keywords:
            if keyword in skills_lower:
                return True
    
    return False


def has_pm_experience(extraction_data: Dict, user_profile: Dict) -> bool:
    """Check if candidate has PM/product manager experience."""
    target_role = str(extraction_data.get("target_role", "")).lower()
    work_experience = extraction_data.get("work_experience", [])
    if isinstance(work_experience, str):
        work_experience = [work_experience]
    
    pm_keywords = [
        "product manager", "pm", "product management", "product owner",
        "technical pm", "tech pm", "tpm", "apm", "associate pm"
    ]
    
    # Check target role
    for keyword in pm_keywords:
        if keyword in target_role:
            return True
    
    # Check work experience
    for exp in work_experience:
        if isinstance(exp, dict):
            exp_text = str(exp.get("role", "") + " " + exp.get("company", "") + " " + exp.get("description", "")).lower()
        else:
            exp_text = str(exp).lower()
        
        for keyword in pm_keywords:
            if keyword in exp_text:
                return True
    
    return False


def has_startup_experience(extraction_data: Dict, user_profile: Dict) -> bool:
    """Check if candidate has startup experience."""
    work_experience = extraction_data.get("work_experience", [])
    if isinstance(work_experience, str):
        work_experience = [work_experience]
    
    startup_keywords = [
        "startup", "early stage", "seed", "series a", "founded", "co-founder",
        "founder", "entrepreneur", "0 to 1", "mvp", "pivoted"
    ]
    
    for exp in work_experience:
        if isinstance(exp, dict):
            exp_text = str(exp.get("role", "") + " " + exp.get("company", "") + " " + exp.get("description", "")).lower()
        else:
            exp_text = str(exp).lower()
        
        for keyword in startup_keywords:
            if keyword in exp_text:
                return True
    
    return False


def has_web3_experience(extraction_data: Dict, user_profile: Dict) -> bool:
    """Check if candidate has Web3 exposure."""
    work_experience = extraction_data.get("work_experience", [])
    if isinstance(work_experience, str):
        work_experience = [work_experience]
    
    core_skills = str(extraction_data.get("core_skills", "")).lower()
    target_role = str(extraction_data.get("target_role", "")).lower()
    
    web3_keywords = [
        "web3", "blockchain", "crypto", "cryptocurrency", "defi", "nft",
        "ethereum", "solidity", "smart contract", "dapp", "dao", "metaverse"
    ]
    
    # Check skills and target role
    combined_text = core_skills + " " + target_role
    for keyword in web3_keywords:
        if keyword in combined_text:
            return True
    
    # Check work experience
    for exp in work_experience:
        if isinstance(exp, dict):
            exp_text = str(exp.get("role", "") + " " + exp.get("company", "") + " " + exp.get("description", "")).lower()
        else:
            exp_text = str(exp).lower()
        
        for keyword in web3_keywords:
            if keyword in exp_text:
                return True
    
    return False


def has_tier1_education(extraction_data: Dict, user_profile: Dict) -> bool:
    """Check if candidate has Tier 1 education or great projects/work ex."""
    education = extraction_data.get("education", [])
    if isinstance(education, str):
        education = [education]
    
    tier1_keywords = [
        "iit", "nit", "bits", "iiit", "iisc", "stanford", "mit", "harvard",
        "carnegie mellon", "cmu", "berkeley", "caltech", "princeton",
        "yale", "columbia", "cornell", "upenn", "wharton", "oxford", "cambridge"
    ]
    
    # Check education
    for edu in education:
        if isinstance(edu, dict):
            edu_text = str(edu.get("institution", "") + " " + edu.get("degree", "")).lower()
        else:
            edu_text = str(edu).lower()
        
        for keyword in tier1_keywords:
            if keyword in edu_text:
                return True
    
    # Check for great projects/work ex indicators
    work_experience = extraction_data.get("work_experience", [])
    if isinstance(work_experience, str):
        work_experience = [work_experience]
    
    project_keywords = [
        "open source", "github", "portfolio", "side project", "personal project",
        "built", "developed", "architected", "led", "scaled", "impact"
    ]
    
    for exp in work_experience:
        if isinstance(exp, dict):
            exp_text = str(exp.get("description", "")).lower()
        else:
            exp_text = str(exp).lower()
        
        for keyword in project_keywords:
            if keyword in exp_text:
                return True
    
    return False


def score_candidate(extraction_data: Dict, user_profile: Dict) -> Dict[str, Any]:
    """Score a candidate based on requirements."""
    score = 0
    reasons = []
    
    # Must have: Tech background before PM
    has_tech = has_tech_background(extraction_data, user_profile)
    if has_tech:
        score += 30
        reasons.append("✅ Has tech background")
    else:
        reasons.append("❌ No tech background found")
    
    # Must have: PM experience or interest
    has_pm = has_pm_experience(extraction_data, user_profile)
    if has_pm:
        score += 30
        reasons.append("✅ Has PM experience/interest")
    else:
        reasons.append("⚠️ No explicit PM experience found")
    
    # Must have: At least 1 YOE
    experience = extraction_data.get("years_of_experience", "")
    work_experience_raw = extraction_data.get("work_experience", [])
    
    # Convert to list for processing, but keep original for YOE extraction
    if isinstance(work_experience_raw, str):
        work_experience = [work_experience_raw]
    else:
        work_experience = work_experience_raw if isinstance(work_experience_raw, list) else []
    
    if isinstance(experience, (int, float)):
        yoe = float(experience)
    else:
        # Try extracting from both years_of_experience and work_experience
        yoe = extract_years_of_experience(str(experience), work_experience_raw)
    
    if yoe >= 1.0:
        score += 20
        reasons.append(f"✅ {yoe} years of experience")
    else:
        reasons.append(f"❌ Less than 1 year experience ({yoe})")
    
    # Good to have: Startup experience
    if has_startup_experience(extraction_data, user_profile):
        score += 10
        reasons.append("✅ Has startup experience")
    
    # Good to have: Web3 exposure
    if has_web3_experience(extraction_data, user_profile):
        score += 10
        reasons.append("✅ Has Web3 exposure")
    
    # Good to have: Tier 1 education or great projects
    if has_tier1_education(extraction_data, user_profile):
        score += 10
        reasons.append("✅ Tier 1 education or great projects")
    
    return {
        "score": score,
        "reasons": reasons,
        "has_tech": has_tech,
        "has_pm": has_pm,
        "yoe": yoe,
        "has_startup": has_startup_experience(extraction_data, user_profile),
        "has_web3": has_web3_experience(extraction_data, user_profile),
        "has_tier1": has_tier1_education(extraction_data, user_profile),
    }


def get_all_job_seekers():
    """Get all job seekers from extractions collection."""
    extractions_ref = fs.collection("extractions")
    all_extractions = extractions_ref.stream()
    
    job_seekers = []
    for ext_doc in all_extractions:
        ext_data = ext_doc.to_dict() or {}
        uid = ext_doc.id
        
        # Check if it's a job seeker (has target_role or core_skills)
        if ext_data.get("target_role") or ext_data.get("core_skills"):
            user_profile = get_user_profile(uid) or {}
            name = user_profile.get("name") or ext_data.get("name") or uid
            
            job_seekers.append({
                "uid": uid,
                "name": name,
                "extraction_data": ext_data,
                "user_profile": user_profile,
            })
    
    return job_seekers


def main():
    print("=" * 70)
    print("FINDING TECH PM CANDIDATES")
    print("=" * 70)
    print("\nRequirements:")
    print("  - Must have tech experience before transitioning to PM")
    print("  - At least 1 YOE")
    print("  - Good to have: startup experience, Web3 exposure, Tier 1 education")
    print("\n" + "=" * 70)
    
    print("\n1. Fetching all job seekers...")
    all_candidates = get_all_job_seekers()
    print(f"   Found {len(all_candidates)} total job seekers")
    
    print("\n2. Filtering and scoring candidates...")
    scored_candidates = []
    
    for candidate in all_candidates:
        uid = candidate["uid"]
        name = candidate["name"]
        extraction_data = candidate["extraction_data"]
        user_profile = candidate["user_profile"]
        
        # Score the candidate
        scoring = score_candidate(extraction_data, user_profile)
        
        # Include if they have tech background AND (PM experience OR at least 1 YOE OR multiple work experiences)
        work_experience = extraction_data.get("work_experience", [])
        if isinstance(work_experience, str):
            work_experience = [work_experience]
        has_multiple_roles = len(work_experience) > 1
        
        # Include candidates with tech background who have PM interest OR sufficient experience
        if scoring["has_tech"] and (scoring["has_pm"] or scoring["yoe"] >= 1.0 or has_multiple_roles):
            scored_candidates.append({
                "uid": uid,
                "name": name,
                "extraction_data": extraction_data,
                "user_profile": user_profile,
                "scoring": scoring,
            })
    
    # Sort by score (descending)
    scored_candidates.sort(key=lambda x: x["scoring"]["score"], reverse=True)
    
    print(f"   Found {len(scored_candidates)} relevant candidates")
    
    print("\n" + "=" * 70)
    print("TOP CANDIDATES")
    print("=" * 70)
    
    for i, candidate in enumerate(scored_candidates[:20], 1):  # Show top 20
        uid = candidate["uid"]
        name = candidate["name"]
        extraction_data = candidate["extraction_data"]
        user_profile = candidate["user_profile"]
        scoring = candidate["scoring"]
        
        print(f"\n{i}. {name} (UID: {uid})")
        print(f"   Score: {scoring['score']}/100")
        print(f"   YOE: {scoring['yoe']}")
        print(f"   Tech Background: {'Yes' if scoring['has_tech'] else 'No'}")
        print(f"   PM Experience: {'Yes' if scoring['has_pm'] else 'No'}")
        print(f"   Startup: {'Yes' if scoring['has_startup'] else 'No'}")
        print(f"   Web3: {'Yes' if scoring['has_web3'] else 'No'}")
        print(f"   Tier 1 Education: {'Yes' if scoring['has_tier1'] else 'No'}")
        
        # Show key details
        target_role = extraction_data.get("target_role", "N/A")
        core_skills = extraction_data.get("core_skills", "N/A")
        location = extraction_data.get("current_location", user_profile.get("location", "N/A"))
        linkedin = user_profile.get("linkedin_url") or user_profile.get("linkedin") or extraction_data.get("linkedin_url", "N/A")
        
        print(f"   Target Role: {target_role}")
        print(f"   Core Skills: {core_skills[:100] if len(str(core_skills)) > 100 else core_skills}")
        print(f"   Location: {location}")
        print(f"   LinkedIn: {linkedin}")
        
        # Show scoring reasons
        print(f"   Reasons:")
        for reason in scoring["reasons"]:
            print(f"     {reason}")
        
        # Show profile link if exists
        public_profile = fs.collection("public_profiles").where("user_id", "==", uid).limit(1).stream()
        public_profile_list = list(public_profile)
        if public_profile_list:
            slug = public_profile_list[0].id
            print(f"   Profile: https://profiles.vance.so/{slug}")
        
        print("-" * 70)
    
    print("\n" + "=" * 70)
    print(f"SUMMARY: Found {len(scored_candidates)} relevant candidates")
    print("=" * 70)


if __name__ == "__main__":
    main()

