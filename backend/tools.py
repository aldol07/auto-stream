"""
Tool Definitions for AutoStream Agent
Contains mock API functions for lead capture.
"""

import json
import datetime
from pathlib import Path


# ─────────────────────────────────────────────
# MOCK LEAD CAPTURE TOOL
# ─────────────────────────────────────────────

def mock_lead_capture(name: str, email: str, platform: str) -> dict:
    """
    Mock API function to capture a qualified lead.
    
    In production, this would call a real CRM API (HubSpot, Salesforce, etc.)
    For now, it prints success and logs to a local JSON file.
    
    Args:
        name: Lead's full name
        email: Lead's email address
        platform: Creator platform (YouTube, Instagram, TikTok, etc.)
    
    Returns:
        dict with status and lead_id
    """
    print("\n" + "="*50)
    print("🎯 LEAD CAPTURED SUCCESSFULLY")
    print("="*50)
    print(f"  Name     : {name}")
    print(f"  Email    : {email}")
    print(f"  Platform : {platform}")
    print(f"  Time     : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50 + "\n")

    # Save to local leads log
    lead_data = {
        "lead_id": f"LEAD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "name": name,
        "email": email,
        "platform": platform,
        "captured_at": datetime.datetime.now().isoformat(),
        "status": "new",
        "source": "autostream_agent"
    }

    _save_lead_to_log(lead_data)

    return {
        "status": "success",
        "lead_id": lead_data["lead_id"],
        "message": f"Lead for {name} captured successfully."
    }


def _save_lead_to_log(lead_data: dict):
    """Append lead data to a local JSON log file."""
    log_path = Path(__file__).parent / "leads_log.json"
    
    # Load existing leads
    existing = []
    if log_path.exists():
        try:
            with open(log_path, "r") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = []
    
    # Append new lead
    existing.append(lead_data)
    
    # Save back
    with open(log_path, "w") as f:
        json.dump(existing, f, indent=2)
    
    print(f"📁 Lead saved to: {log_path}")


# ─────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    result = mock_lead_capture(
        name="Ravi Kumar",
        email="ravi@example.com",
        platform="YouTube"
    )
    print("Return value:", result)
