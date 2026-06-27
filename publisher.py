import smtplib
import ssl
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime


DATA_DIR = Path(__file__).parent / "data"
PUBLISH_LOG = DATA_DIR / "publish_log.json"
DRAFTS_DIR = DATA_DIR / "drafts"


def get_next_issue_number() -> int:
    if not PUBLISH_LOG.exists():
        return 1
    with open(PUBLISH_LOG, "r", encoding="utf-8") as f:
        logs = json.load(f)
    if not logs:
        return 1
    last_issue = max(log["issue_number"] for log in logs)
    return last_issue + 1


def log_publish(issue_data: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logs = []
    if PUBLISH_LOG.exists():
        with open(PUBLISH_LOG, "r", encoding="utf-8") as f:
            logs = json.load(f)
    logs.append(issue_data)
    with open(PUBLISH_LOG, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)


def _save_as_draft(subject: str, body: str, issue_number: int) -> str:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = subject[:50].replace(" ", "_").replace("/", "-")
    filename = f"issue_{issue_number}_{safe_name}.html"
    draft_path = DRAFTS_DIR / filename
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(f"<h1>{subject}</h1>\n{body}")
    return str(draft_path)


def publish_to_substack(content: dict, config: dict = None) -> dict:
    """
    Publish newsletter content to Substack via email-to-publish.

    Args:
        content: {"subject": str, "body": str}  (body is HTML)
        config:  optional override dict; falls back to env vars

    Returns:
        {"status": "published"|"draft", "issue_number": int, "path"?: str}
    """
    config = config or {}
    gmail_password = config.get("GMAIL_APP_PASSWORD") or os.environ.get("GMAIL_APP_PASSWORD", "")
    sender_email = config.get("SENDER_EMAIL") or os.environ.get("SENDER_EMAIL", "")
    substack_email = config.get("SUBSTACK_EMAIL") or os.environ.get("SUBSTACK_EMAIL", "")

    subject = content["subject"]
    body = content["body"]
    issue_number = get_next_issue_number()
    word_count = len(body.split())

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = substack_email
    msg.attach(MIMEText(body, "html"))

    published = False
    draft_path = None

    if gmail_password and sender_email and substack_email:
        context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(sender_email, gmail_password)
                server.sendmail(sender_email, substack_email, msg.as_string())
            published = True
        except Exception as e:
            print(f"SMTP publish failed: {e}")

    if not published:
        draft_path = _save_as_draft(subject, body, issue_number)
        status = "draft"
    else:
        status = "published"

    issue_data = {
        "issue_number": issue_number,
        "date": datetime.utcnow().isoformat() + "Z",
        "subject_line": subject,
        "status": status,
        "word_count": word_count,
    }
    if draft_path:
        issue_data["draft_path"] = draft_path

    log_publish(issue_data)

    result = {"status": status, "issue_number": issue_number}
    if draft_path:
        result["path"] = draft_path
    return result
