"""
ScrapingDog LinkedIn API client for profile search and scraping.
"""

import json
from typing import Any, Dict, List, Optional

import requests


class ScrapingDogClient:
    """Client for ScrapingDog LinkedIn API operations."""

    def __init__(self, api_key: str, search_endpoint: str, profile_endpoint: str):
        self.api_key = api_key
        self.search_endpoint = search_endpoint
        self.profile_endpoint = profile_endpoint
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def search_profiles(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search LinkedIn profiles using ScrapingDog API."""
        try:
            response = requests.post(
                self.search_endpoint,
                json=search_params,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"ScrapingDog search error: {e}")
            return []

    def get_profile_details(self, profile_url: str) -> Optional[Dict[str, Any]]:
        """Get detailed profile information from ScrapingDog API."""
        try:
            response = requests.post(
                self.profile_endpoint,
                json={"profile_url": profile_url},
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("data")
        except requests.exceptions.RequestException as e:
            print(f"ScrapingDog profile error: {e}")
            return None

    def convert_apify_params_to_scrapingdog(
        self, apify_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert Apify parameters to ScrapingDog format."""
        scrapingdog_params = {}

        # Map common parameters
        if "searchQuery" in apify_params:
            scrapingdog_params["query"] = apify_params["searchQuery"]
        if "maxResults" in apify_params:
            scrapingdog_params["limit"] = apify_params["maxResults"]
        if "locations" in apify_params:
            scrapingdog_params["location"] = (
                apify_params["locations"][0] if apify_params["locations"] else None
            )
        if "currentJobTitles" in apify_params:
            scrapingdog_params["job_titles"] = apify_params["currentJobTitles"]
        if "currentCompanies" in apify_params:
            scrapingdog_params["companies"] = apify_params["currentCompanies"]
        if "industryIds" in apify_params:
            scrapingdog_params["industry"] = self._map_industry_id(
                apify_params["industryIds"][0]
            )

        return scrapingdog_params

    def _map_industry_id(self, industry_id: int) -> str:
        """Map industry ID to industry name."""
        industry_mapping = {
            43: "Financial Services",
            6: "Technology",
            4: "Healthcare",
            8: "Education",
        }
        return industry_mapping.get(industry_id, "Technology")

    def format_search_results(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format ScrapingDog results to match expected format."""
        formatted_results = []

        for result in results:
            formatted_result = {
                "profileUrl": result.get("profile_url", ""),
                "name": result.get("full_name", ""),
                "title": result.get("headline", ""),
                "company": result.get("company_name", ""),
                "summary": result.get("about", ""),
                "location": result.get("location", ""),
                "connections": result.get("connections", ""),
                "experience": result.get("experience", []),
            }
            formatted_results.append(formatted_result)

        return formatted_results
