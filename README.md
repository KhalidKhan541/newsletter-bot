# AI Newsletter Bot

Fully automated AI newsletter that runs on GitHub Actions. Collects, summarizes, and delivers curated AI news to your subscribers — no manual intervention required.

## How It Works

1. **GitHub Actions triggers** on a schedule (e.g., every Monday and Thursday)
2. **Collect** — Scrapes and fetches top AI news sources (Hacker News, Reddit, AI blogs)
3. **Summarize** — Parses and ranks stories by relevance and engagement
4. **Format** — Generates a clean, readable newsletter with headlines, summaries, and links
5. **Deliver** — Sends the newsletter via your chosen email provider

## Setup Instructions (Day 1 Checklist)

- [ ] Fork or clone this repository
- [ ] Create a free account with an email service (Mailchimp, Buttondown, or Resend)
- [ ] Get your API key from the email provider
- [ ] Add secrets in **Settings → Secrets and variables → Actions**
- [ ] Configure `config.json` (see below)
- [ ] Enable GitHub Actions in your repo
- [ ] Add subscribers to your email list
- [ ] Trigger a manual run to test: **Actions → Run workflow**

## Config Options

Edit `config.json` to customize behavior:

```json
{
  "sources": ["hackernews", "reddit", "ai_blogs"],
  "max_articles": 10,
  "schedule": "monday_and_thursday",
  "subject_prefix": "AI Weekly",
  "language": "en"
}
```

| Option | Description | Default |
|---|---|---|
| `sources` | News sources to pull from | `hackernews`, `reddit`, `ai_blogs` |
| `max_articles` | Max articles per newsletter | `10` |
| `schedule` | Delivery days | `monday_and_thursday` |
| `subject_prefix` | Email subject line prefix | `AI Weekly` |
| `language` | Content language | `en` |

## Environment Variables

Add these as **Repository Secrets** (Settings → Secrets → Actions):

| Variable | Required | Description |
|---|---|---|
| `EMAIL_API_KEY` | Yes | API key for your email provider |
| `EMAIL_FROM` | Yes | Sender email address |
| `EMAIL_TO` | Yes | Recipient list or group address |
| `SMTP_HOST` | Optional | SMTP server (if using SMTP) |
| `SMTP_PORT` | Optional | SMTP port (default: 587) |
| `SMTP_USER` | Optional | SMTP username |
| `SMTP_PASS` | Optional | SMTP password |

## Monetization

Turn your newsletter into revenue from day one:

- **Sponsored placements** — Charge AI companies $50–$500 per issue to feature their product or launch
- **Affiliate links** — Add referral links to AI tools (OpenAI, Midjourney, Notion AI) and earn per signup
- **Premium tier** — Offer a free weekly digest and a paid daily deep-dive ($5–$15/month)
- **Lead generation** — Partner with AI bootcamps, courses, or SaaS products for paid leads
- **Ad networks** — Use platforms like Swapstack or Paved that connect newsletters with advertisers

Start with affiliates (zero upfront cost) and add sponsorships as your list grows past 500 subscribers.
