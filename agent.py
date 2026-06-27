#!/usr/bin/env python3
"""
Newsletter Bot - Main Orchestration Script
Runs the full newsletter pipeline: research -> write -> quality check -> publish -> growth
"""

import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

import writer
import publisher
import growth

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MANUAL_ISSUE = BASE_DIR / "manual_issue.md"
LOG_FILE = DATA_DIR / "agent.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("newsletter_bot")
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


def load_config() -> dict:
    config_path = BASE_DIR / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_manual_issue() -> str | None:
    if MANUAL_ISSUE.exists():
        with open(MANUAL_ISSUE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


def run_pipeline():
    log = setup_logging()
    start_time = datetime.now()
    log.info("=" * 60)
    log.info("Newsletter Bot Pipeline Started")
    log.info("=" * 60)

    results = {}
    errors = []

    env_vars = ["GROQ_API_KEY", "GMAIL_APP_PASSWORD", "SENDER_EMAIL", "RECIPIENT_EMAIL"]
    for var in env_vars:
        if os.environ.get(var):
            log.info(f"  {var}: SET")
        else:
            log.warning(f"  {var}: NOT SET")

    # Step 1: Load config
    log.info("\n[Step 1/9] Loading config.json...")
    try:
        config = load_config()
        log.info(f"  Newsletter: {config.get('newsletter_name', 'Unknown')}")
        log.info(f"  Niche: {config.get('niche', 'Unknown')}")
        results["config"] = "ok"
    except Exception as e:
        log.error(f"  Failed to load config: {e}")
        errors.append(("load_config", str(e)))
        return

    # Check for manual issue
    manual_content = read_manual_issue()
    if manual_content:
        log.info("\n[MODE] Manual issue detected! Publishing manual_issue.md instead.")
        try:
            content = {
                "subject": "Manual Issue",
                "body": manual_content
            }
            pub_result = publisher.publish_to_substack(content)
            log.info(f"  Published manual issue #{pub_result['issue_number']} ({pub_result['status']})")

            if pub_result.get("path"):
                log.info(f"  Saved as draft: {pub_result['path']}")

            os.remove(MANUAL_ISSUE)
            log.info("  Deleted manual_issue.md")

            growth.log_analytics({
                "issue_number": pub_result["issue_number"],
                "subject_line": "Manual Issue",
                "word_count": len(manual_content.split()),
                "status": pub_result["status"]
            })

            log.info("\n" + "=" * 60)
            log.info("Pipeline Complete (Manual Mode)")
            log.info("=" * 60)
            return
        except Exception as e:
            log.error(f"  Failed to publish manual issue: {e}")
            errors.append(("publish_manual", str(e)))

    # Step 2: Research topics
    log.info("\n[Step 2/9] Researching topics...")
    try:
        sources_config = config.get("sources", {})
        research_config = {
            "keywords": sources_config.get("keywords", []),
            "rss_feeds": sources_config.get("rss", []),
            "subreddits": sources_config.get("reddit", [])
        }
        topics = writer.research_topics(research_config)
        log.info(f"  Found {len(topics)} topics")
        for i, t in enumerate(topics[:3], 1):
            log.info(f"  {i}. {t.get('title', 'N/A')[:60]}")
        results["topics"] = len(topics)
    except Exception as e:
        log.error(f"  Topic research failed: {e}")
        errors.append(("research_topics", str(e)))
        topics = []

    # Step 3: Write newsletter
    log.info("\n[Step 3/9] Writing newsletter...")
    newsletter_content = None
    if topics:
        try:
            write_config = {
                "tone": config.get("tone", "professional"),
                "audience": config.get("target_audience", "tech professionals"),
                "brand_name": config.get("newsletter_name", "TechPulse")
            }
            newsletter_content = writer.write_newsletter(write_config, topics)
            log.info(f"  Subject: {newsletter_content.get('subject', 'N/A')}")
            log.info(f"  Word count: {len(newsletter_content.get('body', '').split())}")
            results["writing"] = "ok"
        except Exception as e:
            log.error(f"  Newsletter writing failed: {e}")
            errors.append(("write_newsletter", str(e)))
    else:
        log.warning("  Skipping writing - no topics available")

    # Step 4: Quality check
    log.info("\n[Step 4/9] Running quality check...")
    quality_passed = False
    if newsletter_content:
        try:
            checked = writer.quality_check(newsletter_content)
            quality = checked.get("quality", {})
            quality_passed = quality.get("passed", False)
            log.info(f"  Quality passed: {quality_passed}")
            log.info(f"  Word count: {quality.get('word_count', 0)}")
            if quality.get("errors"):
                for err in quality["errors"]:
                    log.warning(f"  ERROR: {err}")
            if quality.get("warnings"):
                for warn in quality["warnings"]:
                    log.warning(f"  WARNING: {warn}")
            results["quality_check"] = "passed" if quality_passed else "failed"
        except Exception as e:
            log.error(f"  Quality check failed: {e}")
            errors.append(("quality_check", str(e)))
    else:
        log.warning("  Skipping quality check - no content")

    # Step 5: Publish
    log.info("\n[Step 5/9] Publishing to Substack...")
    pub_result = None
    if newsletter_content:
        try:
            pub_result = publisher.publish_to_substack(newsletter_content)
            log.info(f"  Status: {pub_result.get('status', 'unknown')}")
            log.info(f"  Issue #: {pub_result.get('issue_number', 'N/A')}")
            if pub_result.get("path"):
                log.info(f"  Draft path: {pub_result['path']}")
            results["publish"] = pub_result.get("status", "unknown")
        except Exception as e:
            log.error(f"  Publishing failed: {e}")
            errors.append(("publish", str(e)))
    else:
        log.warning("  Skipping publish - no content")

    # Step 6: Generate social clip
    log.info("\n[Step 6/9] Generating social clip...")
    social_clip = None
    if newsletter_content:
        try:
            social_clip = growth.generate_social_clip(newsletter_content, config)
            log.info(f"  Twitter post length: {len(social_clip.get('twitter', ''))} chars")
            log.info(f"  LinkedIn post length: {len(social_clip.get('linkedin', ''))} chars")
            results["social_clip"] = "ok"
        except Exception as e:
            log.error(f"  Social clip generation failed: {e}")
            errors.append(("social_clip", str(e)))

    # Step 7: Log analytics
    log.info("\n[Step 7/9] Logging analytics...")
    try:
        subscriber_count = config.get("subscriber_count", 0)
        if pub_result:
            growth.log_analytics({
                "issue_number": pub_result.get("issue_number", 0),
                "subject_line": newsletter_content.get("subject", "") if newsletter_content else "",
                "word_count": len(newsletter_content.get("body", "").split()) if newsletter_content else 0,
                "status": pub_result.get("status", "unknown")
            }, subscriber_count)
        log.info(f"  Subscriber count: {subscriber_count}")
        results["analytics"] = "ok"
    except Exception as e:
        log.error(f"  Analytics logging failed: {e}")
        errors.append(("analytics", str(e)))

    # Step 8: Check milestones
    log.info("\n[Step 8/9] Checking milestones...")
    try:
        subscriber_count = config.get("subscriber_count", 0)
        milestone_result = growth.check_milestones(config, subscriber_count)
        if milestone_result.get("milestones_reached"):
            for m in milestone_result["milestones_reached"]:
                log.info(f"  MILESTONE: {m} subscribers!")
        else:
            log.info("  No new milestones reached")
        results["milestones"] = milestone_result
    except Exception as e:
        log.error(f"  Milestone check failed: {e}")
        errors.append(("milestones", str(e)))

    # Step 9: Sponsor kit generation
    log.info("\n[Step 9/9] Checking sponsor threshold...")
    try:
        subscriber_count = config.get("subscriber_count", 0)
        sponsor_threshold = config.get("sponsor_threshold", 1000)
        if subscriber_count >= sponsor_threshold:
            log.info(f"  Subscriber count ({subscriber_count}) >= threshold ({sponsor_threshold})")
            sponsor_kit = growth.generate_sponsor_kit(config, subscriber_count)
            log.info(f"  Sponsor kit generated with {len(sponsor_kit.get('sponsor_tiers', []))} tiers")
            results["sponsor_kit"] = "generated"
        else:
            log.info(f"  Subscriber count ({subscriber_count}) < threshold ({sponsor_threshold})")
            log.info("  Sponsor kit not needed yet")
            results["sponsor_kit"] = "not_needed"
    except Exception as e:
        log.error(f"  Sponsor kit check failed: {e}")
        errors.append(("sponsor_kit", str(e)))

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    log.info("\n" + "=" * 60)
    log.info("Pipeline Summary")
    log.info("=" * 60)
    log.info(f"Duration: {elapsed:.1f}s")
    log.info(f"Steps completed: {len(results)}/9")
    log.info(f"Errors: {len(errors)}")
    if errors:
        for step, err in errors:
            log.error(f"  - {step}: {err}")
    log.info(f"Results: {json.dumps(results, indent=2, default=str)}")
    log.info("=" * 60)

    return {"results": results, "errors": errors, "elapsed": elapsed}


if __name__ == "__main__":
    run_pipeline()
