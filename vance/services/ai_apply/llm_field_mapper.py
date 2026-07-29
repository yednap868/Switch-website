"""
LLM Field Mapper for AI Apply Feature.
Uses Claude to intelligently map form fields to candidate data.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from services.ai_apply.browser_agent import FormField

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️ [LLM_FIELD_MAPPER] Anthropic not available - install with: pip install anthropic")


class FieldMapping:
    """Represents a field mapping with confidence score."""
    def __init__(
        self,
        selector: str,
        value: Optional[str],
        confidence: float,
        field_type: str
    ):
        self.selector = selector
        self.value = value
        self.confidence = confidence
        self.field_type = field_type


class LLMFieldMapper:
    """Maps form fields to candidate data using Claude."""
    
    def __init__(self, api_key: Optional[str] = None):
        if not ANTHROPIC_AVAILABLE:
            raise RuntimeError("Anthropic SDK not available")
        
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        self.client = Anthropic(api_key=self.api_key)
    
    async def map_fields(
        self,
        fields: List[FormField],
        candidate_profile: Dict[str, Any],
        job_title: str,
        company_name: str
    ) -> List[FieldMapping]:
        """Map form fields to candidate data using LLM."""
        prompt = self._build_mapping_prompt(fields, candidate_profile, job_title, company_name)
        
        try:
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            mapping_text = response.content[0].text if response.content else ""
            
            # Parse JSON response
            mappings = self._parse_mapping_response(mapping_text)
            return mappings
        
        except Exception as e:
            print(f"❌ [LLM_FIELD_MAPPER] Error mapping fields: {e}")
            raise
    
    def _build_mapping_prompt(
        self,
        fields: List[FormField],
        candidate: Dict[str, Any],
        job_title: str,
        company_name: str
    ) -> str:
        """Build the prompt for field mapping."""
        fields_json = json.dumps([
            {
                "selector": f.selector,
                "type": f.type,
                "label": f.label,
                "placeholder": f.placeholder,
                "ariaLabel": f.aria_label,
                "required": f.required,
                "options": f.options,
            }
            for f in fields
        ], indent=2)
        
        candidate_json = json.dumps(candidate, indent=2)
        
        return f"""You are an expert at mapping job application form fields to candidate data.

JOB CONTEXT:
Company: {company_name}
Position: {job_title}

CANDIDATE PROFILE:
{candidate_json}

FORM FIELDS TO MAP:
{fields_json}

TASK:
For each form field, determine the best value from the candidate profile.

RULES:
1. Only map fields where you have high confidence (≥0.7) in the value
2. For required fields with no clear mapping, return null value with low confidence
3. For select fields, choose the option that best matches candidate data
4. For checkbox fields, only return true if it's clearly consent/agreement (NOT marketing)
5. Never make up data - use only what's in the profile
6. For date fields, use appropriate format (e.g., MM/DD/YYYY)
7. For phone fields, use format: (XXX) XXX-XXXX
8. For work authorization, be conservative - only fill if explicitly known

OUTPUT FORMAT (JSON only, no other text):
{{
  "mappings": [
    {{
      "selector": "#firstName",
      "value": "John",
      "confidence": 0.95,
      "field_type": "text"
    }}
  ]
}}

Return mappings array with all fields processed."""
    
    def _parse_mapping_response(self, text: str) -> List[FieldMapping]:
        """Parse LLM response into FieldMapping objects."""
        try:
            # Remove markdown code blocks if present
            clean_text = re.sub(r'```json\n?', '', text)
            clean_text = re.sub(r'```\n?', '', clean_text)
            clean_text = clean_text.strip()
            
            # Try to extract JSON from the text
            json_match = re.search(r'\{.*"mappings".*\}', clean_text, re.DOTALL)
            if json_match:
                clean_text = json_match.group(0)
            
            parsed = json.loads(clean_text)
            
            if not parsed.get("mappings") or not isinstance(parsed["mappings"], list):
                raise ValueError("Invalid mapping response format")
            
            mappings = []
            for m in parsed["mappings"]:
                # Only return high-confidence mappings
                if m.get("confidence", 0) >= 0.7 and m.get("value") is not None:
                    mappings.append(FieldMapping(
                        selector=m["selector"],
                        value=m["value"],
                        confidence=m["confidence"],
                        field_type=m.get("field_type", "text")
                    ))
            
            return mappings
        
        except Exception as e:
            print(f"❌ [LLM_FIELD_MAPPER] Error parsing LLM response: {e}")
            print(f"   Response text: {text[:500]}")
            return []
    
    def validate_required_fields(
        self,
        fields: List[FormField],
        mappings: List[FieldMapping]
    ) -> Dict[str, Any]:
        """Validate that all required fields are mapped."""
        required_fields = [f for f in fields if f.required]
        mapped_selectors = {m.selector for m in mappings}
        
        missing_fields = [
            f.label or f.placeholder or f.selector
            for f in required_fields
            if f.selector not in mapped_selectors
        ]
        
        return {
            "valid": len(missing_fields) == 0,
            "missingFields": missing_fields
        }

