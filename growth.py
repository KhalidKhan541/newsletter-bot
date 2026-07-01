import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
ANALYTICS_LOG = DATA_DIR / "analytics_log.csv"
MILESTONES_LOG = DATA_DIR / "milestones.json"
SPONSOR_KIT_DIR = DATA_DIR / "sponsor_kits"


def generate_social_clip(newsletter_content: dict, config: dict = None) -> dict:
    """Generate social media clips from newsletter content."""
    config = config or {}
    subject = newsletter_content.get("subject", "")
    body = newsletter_content.get("body", "")

    first_280 = body[:280].rsplit(" ", 1)[0] + "..."
    hook = newsletter_content.get("preview", subject)

    twitter_post = f"{hook}\n\n{first_280}"

    linkedin_post = (
        f"Just published: {subject}\n\n"
        f"Key takeaways:\n"
        f"- {body[:150].strip()}...\n\n"
        f"Read the full newsletter for more insights."
    )

    clip = {
        "twitter": twitter_post,
        "linkedin": linkedin_post,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }

    return clip


def log_analytics(issue_data: dict, subscriber_count: int = 0):
    """Log analytics data to CSV."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    headers = "date,issue_number,subject,word_count,status,subscriber_count\n"
    row = (
        f"{datetime.utcnow().isoformat()}Z,"
        f"{issue_data.get('issue_number', '')},"
        f"\"{issue_data.get('subject_line', '')}\","
        f"{issue_data.get('word_count', '')},"
        f"{issue_data.get('status', '')},"
        f"{subscriber_count}\n"
    )

    if not ANALYTICS_LOG.exists():
        with open(ANALYTICS_LOG, "w", encoding="utf-8") as f:
            f.write(headers)
    else:
        with open(ANALYTICS_LOG, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            with open(ANALYTICS_LOG, "w", encoding="utf-8") as f:
                f.write(headers)

    with open(ANALYTICS_LOG, "a", encoding="utf-8") as f:
        f.write(row)


def check_milestones(config: dict, subscriber_count: int) -> dict:
    """Check if subscriber milestones have been reached."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    milestone_record = {"milestones_reached": [], "checked_at": datetime.utcnow().isoformat() + "Z"}

    milestones = [100, 250, 500, 750, 1000, 2500, 5000, 10000]

    reached = []
    if MILESTONES_LOG.exists():
        with open(MILESTONES_LOG, "r", encoding="utf-8") as f:
            existing = json.load(f)
        reached = existing.get("milestones_reached", [])

    for m in milestones:
        if subscriber_count >= m and m not in reached:
            milestone_record["milestones_reached"].append(m)
            print(f"MILESTONE: Reached {m} subscribers!")

    if milestone_record["milestones_reached"]:
        all_reached = reached + milestone_record["milestones_reached"]
        with open(MILESTONES_LOG, "w", encoding="utf-8") as f:
            json.dump({"milestones_reached": all_reached, "last_checked": datetime.utcnow().isoformat() + "Z"}, f, indent=2)
    else:
        milestone_record["milestones_reached"] = []

    return milestone_record


def generate_sponsor_kit(config: dict, subscriber_count: int) -> dict:
    """Generate a sponsor media kit for outreach."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SPONSOR_KIT_DIR.mkdir(parents=True, exist_ok=True)

    newsletter_name = config.get("newsletter_name", "Al Polymath")
    niche = config.get("niche", "Cognitive Science & Philosophy")
    audience = config.get("target_audience", "Curious minds interested in how we think, what we know, and what it means to be human")

    kit = {
        "newsletter_name": newsletter_name,
        "niche": niche,
        "target_audience": audience,
        "subscriber_count": subscriber_count,
        "sponsor_tiers": [
            {
                "tier": "Standard",
                "price": "$200",
                "includes": "1 dedicated email + social mention"
            },
            {
                "tier": "Premium",
                "price": "$500",
                "includes": "1 dedicated email + 2 newsletter mentions + social media package"
            }
        ],
        "contact": "sponsor@yournewsletter.com",
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }

    kit_path = SPONSOR_KIT_DIR / f"sponsor_kit_{subscriber_count}_subs.json"
    with open(kit_path, "w", encoding="utf-8") as f:
        json.dump(kit, f, indent=2)

    print(f"Sponsor kit generated: {kit_path}")
    return kit
