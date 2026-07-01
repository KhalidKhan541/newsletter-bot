import requests
import json
import re
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import Optional

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

RSS_FEEDS = [
    "https://aeon.co/feed",
    "https://www.theatlantic.com/feed/all/",
    "https://feeds.feedburner.com/neuroscience",
    "https://www.sciencedaily.com/rss/mind_brain.xml",
    "https://blog.davidchalmers.com/feed/"
]

REDDIT_SUBREDDITS = [
    "cognitivescience",
    "philosophy",
    "neuroscience",
    "psychology",
    "PhilosophyofMind"
]

FILLER_PHRASES = [
    "in today's world", "as we all know", "it goes without saying",
    "needless to say", "at the end of the day", "when it comes to",
    "it's worth noting that", "in this day and age"
]


def _groq_request(messages: list, temperature: float = 0.7, max_tokens: int = 2000) -> Optional[str]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def _fetch_rss_feed(url: str, limit: int = 10) -> list[dict]:
    items = []
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")

        for entry in soup.find_all("item")[:limit]:
            title = entry.find("title").get_text(strip=True) if entry.find("title") else ""
            link = entry.find("link").get_text(strip=True) if entry.find("link") else ""
            pub_date = ""
            if entry.find("pubDate"):
                pub_date = entry.find("pubDate").get_text(strip=True)
            elif entry.find("published"):
                pub_date = entry.find("published").get_text(strip=True)

            description = ""
            if entry.find("description"):
                raw = entry.find("description").get_text(strip=True)
                description = BeautifulSoup(raw, "html.parser").get_text(strip=True)[:300]
            elif entry.find("summary"):
                raw = entry.find("summary").get_text(strip=True)
                description = BeautifulSoup(raw, "html.parser").get_text(strip=True)[:300]

            if title:
                items.append({
                    "title": title,
                    "link": link,
                    "description": description,
                    "date": pub_date,
                    "source": url
                })
    except Exception as e:
        print(f"Error fetching RSS feed {url}: {e}")

    return items


def _scrape_google_news(keyword: str, limit: int = 5) -> list[dict]:
    items = []
    url = f"https://news.google.com/rss/search?q={keyword.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"

    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "xml")
            for entry in soup.find_all("item")[:limit]:
                title = entry.find("title").get_text(strip=True) if entry.find("title") else ""
                link = entry.find("link").get_text(strip=True) if entry.find("link") else ""
                source = entry.find("source")
                source_name = source.get_text(strip=True) if source else "Google News"

                if title:
                    items.append({
                        "title": title,
                        "link": link,
                        "description": "",
                        "date": "",
                        "source": source_name
                    })
    except Exception as e:
        print(f"Error scraping Google News for '{keyword}': {e}")

    return items


def _scrape_reddit(subreddit: str, limit: int = 10) -> list[dict]:
    items = []
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"

    try:
        response = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; NewsletterBot/1.0)"
        })
        if response.status_code == 200:
            data = response.json()
            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})
                title = post_data.get("title", "")
                permalink = post_data.get("permalink", "")
                selftext = post_data.get("selftext", "")[:300]
                score = post_data.get("score", 0)

                if title and score > 10:
                    items.append({
                        "title": title,
                        "link": f"https://reddit.com{permalink}",
                        "description": selftext,
                        "date": "",
                        "source": f"r/{subreddit}",
                        "score": score
                    })
    except Exception as e:
        print(f"Error scraping r/{subreddit}: {e}")

    return items


def research_topics(config: dict) -> list:
    all_topics = []
    keywords = config.get("keywords", ["cognitive science", "philosophy of mind", "consciousness", "neuroscience", "epistemology", "ethics", "free will", "mental models"])
    rss_feeds = config.get("rss_feeds", RSS_FEEDS)
    subreddits = config.get("subreddits", REDDIT_SUBREDDITS)

    print("Fetching RSS feeds...")
    for feed_url in rss_feeds:
        topics = _fetch_rss_feed(feed_url)
        all_topics.extend(topics)

    print("Scraping Google News...")
    for keyword in keywords:
        topics = _scrape_google_news(keyword)
        all_topics.extend(topics)

    print("Scraping Reddit...")
    for sub in subreddits:
        topics = _scrape_reddit(sub)
        all_topics.extend(topics)

    print(f"Collected {len(all_topics)} raw topics")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a newsletter editor for a Cognitive Science & Philosophy newsletter. "
                "Analyze the raw topic list and select the 3-5 most engaging, newsworthy, and relevant topics "
                "related to cognitive science, neuroscience, philosophy of mind, consciousness, epistemology, "
                "ethics, decision-making, mental models, and what it means to be human. "
                "Return a JSON array where each item has: "
                "title (string), summary (string, 1-2 sentences), link (string url), source (string). "
                "Only return valid JSON, no markdown fences."
            )
        },
        {
            "role": "user",
            "content": f"Here are the raw topics:\n{json.dumps(all_topics[:80], indent=2)}\n\nSelect the best 3-5."
        }
    ]

    print("Selecting best topics with Groq API...")
    result = _groq_request(messages, temperature=0.3, max_tokens=1500)

    cleaned = result.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        selected = json.loads(cleaned)
    except json.JSONDecodeError:
        json_match = re.search(r"\[.*\]", result, re.DOTALL)
        if json_match:
            selected = json.loads(json_match.group())
        else:
            raise ValueError(f"Could not parse topic selection: {result[:500]}")

    return selected


def write_newsletter(config: dict, topics: list) -> dict:
    tone = config.get("tone", "Thoughtful, curious, like a philosopher-scientist exploring ideas at the edge of knowledge")
    audience = config.get("target_audience", "Curious minds interested in how we think, what we know, and what it means to be human")
    brand_name = config.get("newsletter_name", "Al Polymath")
    extra_instructions = config.get("extra_instructions", "")

    topics_text = "\n".join(
        f"- {t.get('title', 'N/A')}: {t.get('summary', 'N/A')} (Source: {t.get('source', 'N/A')}, Link: {t.get('link', 'N/A')})"
        for t in topics
    )

    system_prompt = f"""You are a world-class newsletter writer for {brand_name}, a newsletter about Cognitive Science & Philosophy.
Write a newsletter in this EXACT format:

SUBJECT LINE: (under 50 characters)
PREVIEW TEXT: (one sentence, under 100 chars)
OPENING HOOK: (2-3 compelling sentences that make the reader think)
THE MAIN STORY: (200-300 words, deep analysis of the top story — explore the science, the philosophy, or both)
QUICK HITS:
- [Title](link) — One sentence summary (repeat 3 times with different stories)
IDEA OF THE DAY: Name — a fascinating concept, experiment, or philosophical thought experiment with why it matters
CLOSING THOUGHT: (1-2 sentences, thought-provoking, leave the reader questioning something)
FOOTER: (standard unsubscribe/delivery info placeholder)

Rules:
- Tone: {tone}
- Audience: {audience}
- Write about cognitive science, neuroscience, philosophy of mind, consciousness, epistemology, ethics, decision-making, mental models, and what it means to be human
- Include at least 1 specific data point, statistic, or research finding
- Avoid filler phrases like "in today's world" or "as we all know"
- Write in a way that respects the reader's intelligence
- Make the opening hook irresistible so readers continue
- Quick hits must include working links from the provided data
- Think deeply about the intersection of mind, brain, and experience
- {extra_instructions}

Return your output as a JSON object with these exact keys:
subject, preview, hook, main_story, quick_hits (array of 3 objects with title, link, summary), tool_of_the_day (object with name, description), closing, footer
Only return valid JSON, no markdown fences."""

    user_prompt = f"Write a newsletter issue based on these topics:\n\n{topics_text}\n\nToday's date: {datetime.now().strftime('%B %d, %Y')}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    print("Generating newsletter with Groq API...")
    result = _groq_request(messages, temperature=0.7, max_tokens=3000)

    cleaned = result.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        newsletter = json.loads(cleaned)
    except json.JSONDecodeError:
        json_match = re.search(r"\{.*\}", result, re.DOTALL)
        if json_match:
            newsletter = json.loads(json_match.group())
        else:
            raise ValueError(f"Could not parse newsletter output: {result[:500]}")

    body_parts = [
        f"Hey there,\n\n{newsletter.get('hook', '')}",
        f"\n\n## THE MAIN STORY\n\n{newsletter.get('main_story', '')}",
        "\n\n## QUICK HITS\n"
    ]

    for hit in newsletter.get("quick_hits", []):
        body_parts.append(f"- [{hit.get('title', '')}]({hit.get('link', '')}) — {hit.get('summary', '')}")

    tool = newsletter.get("tool_of_the_day", {})
    if isinstance(tool, dict):
        body_parts.append(f"\n\n## TOOL OF THE DAY\n\n**{tool.get('name', '')}** — {tool.get('description', '')}")
    else:
        body_parts.append(f"\n\n## TOOL OF THE DAY\n\n{tool}")

    body_parts.append(f"\n\n## CLOSING THOUGHT\n\n{newsletter.get('closing', '')}")
    body_parts.append(f"\n\n---\n\n{newsletter.get('footer', '')}")

    return {
        "subject": newsletter.get("subject", ""),
        "preview": newsletter.get("preview", ""),
        "body": "\n".join(body_parts),
        "topics": [t.get("title", "") for t in topics]
    }


def quality_check(content: dict) -> dict:
    errors = []
    warnings = []

    body = content.get("body", "")
    subject = content.get("subject", "")

    word_count = len(body.split())
    if word_count < 350:
        errors.append(f"Body too short: {word_count} words (minimum 350)")
    elif word_count > 600:
        errors.append(f"Body too long: {word_count} words (maximum 600)")

    if len(subject) > 50:
        errors.append(f"Subject line too long: {len(subject)} chars (max 50)")

    body_lower = body.lower()
    for phrase in FILLER_PHRASES:
        if phrase.lower() in body_lower:
            warnings.append(f"Filler phrase detected: '{phrase}'")

    number_pattern = r"\b\d+(?:\.\d+)?(?:\s*%|\s*(?:million|billion|trillion|k))\b"
    if not re.search(number_pattern, body_lower):
        warnings.append("No numeric data points detected in body")

    if len(body.strip()) == 0:
        errors.append("Body is empty")

    if not subject.strip():
        errors.append("Subject line is empty")

    content["quality"] = {
        "passed": len(errors) == 0,
        "word_count": word_count,
        "subject_length": len(subject),
        "errors": errors,
        "warnings": warnings,
        "checked_at": datetime.now().isoformat()
    }

    return content
