"""
PG staffing jobs service.

Manages open PG employer job requests from the
RentOk x Switch _ PG Staffing & Hiring Form spreadsheet (April 2026).

Provides get_pg_jobs_text() for Jyoti's {{open_jobs}} dynamic variable
and get_all_pg_jobs() for post-call matching.
"""

# All 19 open PG employer listings from spreadsheet (April 2026)
_PG_JOBS = [
    {
        "id": 1,
        "pg_name": "Om Sadan Boys Hostel",
        "location": "Rohini Sector 17, Delhi",
        "roles": ["Cook"],
        "owner_name": "Rajeev Malik",
        "owner_phone": "9350003428",
    },
    {
        "id": 2,
        "pg_name": "Vibe Living",
        "location": "Sector 45, Gurgaon",
        "roles": ["Housekeeping"],
        "owner_name": "Sunny",
        "owner_phone": "9760641578",
    },
    {
        "id": 3,
        "pg_name": "Govindam Niwas",
        "location": "Rohini Sector 17, Delhi",
        "roles": ["Housekeeping", "Security"],
        "owner_name": "Bhupesh Kansal",
        "owner_phone": "9899971235",
    },
    {
        "id": 4,
        "pg_name": "Hostel Inn",
        "location": "Janakpuri, Delhi",
        "roles": ["Housekeeping"],
        "owner_name": "Piyush Tiwary",
        "owner_phone": "8076837267",
    },
    {
        "id": 5,
        "pg_name": "Homestayz Living",
        "location": "Janakpuri, Delhi",
        "roles": ["Security"],
        "owner_name": "Piyush Tiwary",
        "owner_phone": "9667362024",
    },
    {
        "id": 6,
        "pg_name": "Hommitel Agrawal Hostel",
        "location": "South Delhi / Dwarka / Janakpuri",
        "roles": ["Sales Executive"],
        "owner_name": "Ashok Kumar Agrawal",
        "owner_phone": "9971802712",
    },
    {
        "id": 7,
        "pg_name": "Kartik PG",
        "location": "Sector 69, Gurgaon",
        "roles": ["Housekeeping"],
        "owner_name": "Sachin Beniwal",
        "owner_phone": "9354779012",
    },
    {
        "id": 8,
        "pg_name": "Mohini House",
        "location": "Jaipur, Rajasthan",
        "roles": ["Caretaker"],
        "owner_name": "Vishnu Kamal Saini",
        "owner_phone": "9079729052",
    },
    {
        "id": 9,
        "pg_name": "Aashirwad Banglow",
        "location": "Patel Nagar, Delhi",
        "roles": ["Receptionist", "Caretaker"],
        "owner_name": "Vinod",
        "owner_phone": "8447720101",
    },
    {
        "id": 10,
        "pg_name": "AHPL",
        "location": "Green Park, New Delhi",
        "roles": ["Cook"],
        "owner_name": "Gagan Agrawal",
        "owner_phone": "9811563982",
    },
    {
        "id": 11,
        "pg_name": "PG Walaah",
        "location": "Noida",
        "roles": ["Cook"],
        "owner_name": "Himanshu Raghav",
        "owner_phone": "6396235992",
    },
    {
        "id": 12,
        "pg_name": "Niwas Homes",
        "location": "Sector 43, Gurgaon",
        "roles": ["Property Manager", "Cleaner"],
        "owner_name": "Chanchal Dhakrey",
        "owner_phone": "7217252161",
    },
    {
        "id": 13,
        "pg_name": "RentDoor Services",
        "location": "Sector 46 & 39, Gurgaon",
        "roles": ["Cleaner", "Housekeeping"],
        "owner_name": "Mayank",
        "owner_phone": "7988989733",
    },
    {
        "id": 14,
        "pg_name": "As Your Home PG",
        "location": "Munirka, Delhi",
        "roles": ["Cook", "Cleaner"],
        "owner_name": "Yash Bhatia",
        "owner_phone": "8595078194",
    },
    {
        "id": 15,
        "pg_name": "Dada PG",
        "location": "Badshahpur, Gurgaon",
        "roles": ["Cook", "Cleaner (x2)"],
        "owner_name": "Surendra Chaudhary",
        "owner_phone": "9812474444",
    },
]

# Salary ranges per role (with free food + accommodation in all cases)
ROLE_SALARIES = {
    "housekeeping": "Rs 14,000/month",
    "kitchen helper": "Rs 14,000/month",
    "cook": "Rs 18,000-25,000/month",
    "security": "Rs 15,000-18,000/month",
    "security guard": "Rs 15,000-18,000/month",
    "warden": "Rs 15,000-18,000/month",
    "property manager": "Rs 18,000/month",
    "cleaner": "Rs 12,000/month",
    "caretaker": "Rs 15,000-18,000/month",
    "receptionist": "Rs 14,000-16,000/month",
    "sales executive": "Rs 15,000-20,000/month",
}


def get_pg_jobs_text() -> str:
    """
    Return formatted PG job listings for Jyoti's {{open_jobs}} dynamic variable.

    Format: one listing per line with PG name, location, roles, owner contact.
    """
    lines = [f"OPEN PG JOBS — {len(_PG_JOBS)} openings:\n"]
    for job in _PG_JOBS:
        roles = " + ".join(job["roles"])
        lines.append(
            f'{job["id"]}. {job["pg_name"]} | {job["location"]} | '
            f'Chahiye: {roles} | Owner: {job["owner_name"]} ({job["owner_phone"]})'
        )
    return "\n".join(lines)


def get_all_pg_jobs() -> list:
    return list(_PG_JOBS)


def get_salary_for_role(role: str) -> str:
    """Look up salary for a role (case-insensitive). Returns empty string if not found."""
    return ROLE_SALARIES.get(role.lower().strip(), "")
