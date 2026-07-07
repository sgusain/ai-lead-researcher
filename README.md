# 🔍 AI Lead Researcher — GTM Demo

Input a company name → get company intel, decision makers, AI-generated talking points, and a ready-to-send cold email — in under 10 seconds.

## Quick Start (Demo Mode)

```bash
pip install streamlit requests
streamlit run app.py
```

Demo Mode is ON by default — no API keys needed. Uses realistic mock data so you can see the full UI and flow immediately.

## Live Mode (Real APIs)

Toggle off Demo Mode in the sidebar and add your keys:

| API | Free Tier | Get Key |
|-----|-----------|---------|
| Perplexity | 5 req/min | [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api) |
| Apollo.io | 50 credits/month | [app.apollo.io → Settings → API](https://app.apollo.io) |
| Claude (Anthropic) | Pay-as-you-go | [console.anthropic.com](https://console.anthropic.com) |

## Deploy to Streamlit Cloud (Free)

1. Push this folder to a GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo → select `app.py`
4. Add API keys in Streamlit Cloud's Secrets management
5. Done — shareable URL in 2 minutes

## What This Demonstrates

- **AI-assisted research**: Perplexity API replaces manual Google searching
- **Contact enrichment**: Apollo.io finds decision makers automatically
- **AI copywriting**: Claude generates personalized outreach that sounds human
- **Full GTM workflow**: Research → Enrich → Write → Send — one click

Built by Sandy · AI-assisted development with Claude
