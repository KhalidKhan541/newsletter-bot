import smtplib
import ssl
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime, timezone


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


def send_newsletter_to_email(content: dict, config: dict = None) -> dict:
    """
    Send newsletter to your email so you can copy-paste into Substack.

    Args:
        content: {"subject": str, "body": str}  (body is HTML)
        config:  optional override dict; falls back to env vars

    Returns:
        {"status": "sent"|"draft", "issue_number": int, "path"?: str}
    """
    config = config or {}
    gmail_password = config.get("GMAIL_APP_PASSWORD") or os.environ.get("GMAIL_APP_PASSWORD", "")
    sender_email = config.get("SENDER_EMAIL") or os.environ.get("SENDER_EMAIL", "")
    recipient_email = config.get("RECIPIENT_EMAIL") or os.environ.get("RECIPIENT_EMAIL", "")

    subject = content.get("subject", "Untitled")
    body = content.get("body", "")
    issue_number = get_next_issue_number()
    word_count = len(body.split())

    # Build a nice email with the newsletter content
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Newsletter Issue #{issue_number}: {subject}"
    msg["From"] = f"Al Polymath Bot <{sender_email}>"
    msg["To"] = recipient_email

    # Plain text version
    plain_text = f"""Newsletter Issue #{issue_number}
Subject: {subject}

{body}

---
Copy the HTML version above and paste it into Substack editor.
"""

    # HTML version with instructions
    html_body = f"""
<div style="background:#f5f5f5;padding:20px;font-family:Arial;">
<div style="background:white;max-width:600px;margin:0 auto;padding:30px;border-radius:8px;">
<div style="background:#e94560;color:white;padding:15px;border-radius:8px;margin-bottom:20px;">
<h2 style="margin:0;">Newsletter Issue #{issue_number}</h2>
<p style="margin:5px 0 0 0;">Ready to publish on Substack</p>
</div>

<div style="background:#fff3cd;padding:15px;border-radius:8px;margin-bottom:20px;">
<strong>How to publish:</strong>
<ol>
<li>Copy the newsletter content below</li>
<li>Go to Substack → New post</li>
<li>Paste the content</li>
<li>Add the subject line: <em>{subject}</em></li>
<li>Click Publish</li>
</ol>
</div>

<h1>{subject}</h1>
{body}
</div>
</div>
"""

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    sent = False
    draft_path = None

    if gmail_password and sender_email and recipient_email:
        context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(sender_email, gmail_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())
            sent = True
            print(f"Newsletter sent to {recipient_email}")
        except Exception as e:
            print(f"SMTP failed: {e}")

    if not sent:
        draft_path = _save_as_draft(subject, body, issue_number)
        status = "draft"
    else:
        status = "sent"

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


# Keep old function name as alias
publish_to_substack = send_newsletter_to_email
