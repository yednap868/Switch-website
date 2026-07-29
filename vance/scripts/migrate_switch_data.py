"""
Migration script to convert existing switch_users data to new candidates collection.
"""

import time
from utils.db import fs
from models.switch_models import Candidate, CandidateStatus


def migrate_switch_users_to_candidates():
    """
    Migrate existing switch_users documents to candidates collection.
    Maps existing fields to new schema.
    """
    print("🔄 Starting migration from switch_users to candidates...")
    
    switch_users = fs.collection("switch_users").stream()
    migrated_count = 0
    skipped_count = 0
    
    for user_doc in switch_users:
        try:
            user_data = user_doc.to_dict()
            user_id = user_doc.id
            
            # Check if candidate already exists
            candidate_doc = fs.collection("candidates").document(user_id).get()
            if candidate_doc.exists:
                print(f"⏭️  Candidate {user_id} already exists, skipping...")
                skipped_count += 1
                continue
            
            profile = user_data.get("profile", {})
            
            # Map existing fields to new schema
            candidate_data = {
                "id": user_id,
                "phone": user_data.get("phone", user_id),
                "name": profile.get("name", ""),
                "photo_url": profile.get("photoURL"),
                "aadhaar_number": None,
                "area": profile.get("location", ""),
                "preferred_areas": [],
                "experience_level": profile.get("experience", ""),
                "previous_roles": profile.get("preferredRoles", []),
                "previous_employers": [],
                "expected_salary_min": 0,
                "expected_salary_max": 0,
                "languages": profile.get("languages", []),
                "availability": "Immediate" if profile.get("isAvailable", True) else "2 weeks",
                "status": CandidateStatus.AVAILABLE.value,
                "profile_completeness_score": profile.get("profileComplete", 0),
                "screening_call_recording_url": None,
                "created_at": user_data.get("created_at", time.time()),
                "last_active_at": user_data.get("updated_at", time.time()),
            }
            
            # Create candidate document
            fs.collection("candidates").document(user_id).set(candidate_data)
            print(f"✅ Migrated candidate: {user_id} ({candidate_data['name']})")
            migrated_count += 1
            
        except Exception as e:
            print(f"❌ Error migrating {user_doc.id}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✅ Migration complete!")
    print(f"   Migrated: {migrated_count}")
    print(f"   Skipped: {skipped_count}")


if __name__ == "__main__":
    migrate_switch_users_to_candidates()
