"""
AI Lead Researcher
Input a company name → get research, decision makers, talking points, and a ready email draft.
"""

import os
import json
import time
import streamlit as st
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Lead Researcher",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { padding-top: 1rem; }
    .stApp { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); }
    
    h1, h2, h3 { color: #f1f5f9 !important; }
    p, li, span { color: #cbd5e1 !important; }
    
    .result-card {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(10px);
    }
    .result-card h3 { margin-top: 0 !important; }
    
    .accent-indigo { border-left: 4px solid #6366f1 !important; }
    .accent-emerald { border-left: 4px solid #10b981 !important; }
    .accent-amber { border-left: 4px solid #f59e0b !important; }
    .accent-rose { border-left: 4px solid #f43f5e !important; }
    
    .email-box {
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid rgba(99, 102, 241, 0.4);
        border-radius: 8px;
        padding: 1.25rem;
        font-family: 'Georgia', serif;
        line-height: 1.7;
        color: #e2e8f0 !important;
        white-space: pre-wrap;
    }
    
    .badge {
        display: inline-block;
        background: rgba(99, 102, 241, 0.2);
        border: 1px solid rgba(99, 102, 241, 0.4);
        border-radius: 20px;
        padding: 0.2rem 0.75rem;
        font-size: 0.8rem;
        color: #a5b4fc !important;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    [data-testid="stMetricValue"] { color: #6366f1 !important; font-size: 1.5rem !important; }
    [data-testid="stMetricLabel"] { color: #94a3b8 !important; }
    
    section[data-testid="stSidebar"] { background: #0f172a !important; }
    section[data-testid="stSidebar"] p { color: #94a3b8 !important; }
    
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        color: white !important;
        border: none !important;
        padding: 0.6rem 2rem !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        width: 100%;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    }
    
    .timer-text { color: #6366f1 !important; font-weight: 600; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)


import re


# ─── Helper: Get API key from secrets or sidebar ──────────────────────────────

def get_key(name: str, sidebar_value: str) -> str:
    """Try Streamlit Cloud secrets first, then sidebar input."""
    if sidebar_value:
        return sidebar_value
    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""


def clean_citations(data):
    """Remove Perplexity citation artifacts like [1], [2] from all string values."""
    if isinstance(data, str):
        return re.sub(r'\[\d+\]', '', data).strip()
    elif isinstance(data, list):
        return [clean_citations(item) for item in data]
    elif isinstance(data, dict):
        return {k: clean_citations(v) for k, v in data.items()}
    return data


# ─── API Functions ─────────────────────────────────────────────────────────────

def research_company_perplexity(company_name: str, api_key: str) -> dict:
    """Use Perplexity API (sonar) for fast company research."""
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a B2B sales researcher. Return ONLY valid JSON with no markdown fences. "
                    "Use this exact schema:\n"
                    '{"company_name":"","industry":"","founded":"","headquarters":"","employee_count":"","funding":"","revenue_estimate":"","recent_news":["","",""],"tech_stack":["",""],"competitors":["",""],"summary":""}'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Research '{company_name}' for a B2B sales call. "
                    f"Find: industry, founding year, HQ location, employee count, funding/revenue, "
                    f"3 recent news items from last 6 months with dates, "
                    f"their ENGINEERING tech stack (programming languages, frameworks, databases, cloud providers — NOT product features), "
                    f"top competitors (actual competitor companies, NOT parent companies or their own products), "
                    f"and a 2-sentence summary. "
                    f"IMPORTANT: Do NOT include citation numbers like [1] [2] [3] in any values. "
                    f"Return ONLY the JSON object."
                ),
            },
        ],
        "temperature": 0.1,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        if content.startswith("json"):
            content = content[4:].strip()
        return clean_citations(json.loads(content))
    except requests.exceptions.RequestException as e:
        return {"error": f"Perplexity API error: {str(e)}"}
    except (json.JSONDecodeError, KeyError) as e:
        return {"error": f"Failed to parse Perplexity response: {str(e)}"}


def find_people_perplexity(company_name: str, api_key: str) -> list:
    """Use Perplexity API to find current decision makers via live web search."""
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a B2B sales researcher. Return ONLY a valid JSON array with no markdown fences. "
                    "Use this exact schema for each person:\n"
                    '[{"name":"Full Name","title":"Current Job Title","email":"best guess email","linkedin_url":"personal LinkedIn URL or empty string","city":"","state":""}]'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Find 3-5 current key decision makers at '{company_name}' — C-suite executives, VPs, or Directors. "
                    f"Search LinkedIn for each person to find their EXACT profile URL. "
                    f"For linkedin_url: search LinkedIn to find each person's exact profile URL slug "
                    f"(e.g. https://www.linkedin.com/in/ivan-zhao or https://www.linkedin.com/in/abadesi). "
                    f"The slug is NOT always firstname-lastname — you MUST find the real URL. "
                    f"If you cannot confirm the exact URL, leave linkedin_url as empty string. "
                    f"For email, use the company's actual email domain in firstname.lastname@domain.com format. "
                    f"Do NOT include citation numbers like [1] [2] in any values. "
                    f"Return ONLY the JSON array."
                ),
            },
        ],
        "temperature": 0.1,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        if content.startswith("json"):
            content = content[4:].strip()
        return clean_citations(json.loads(content))
    except requests.exceptions.RequestException as e:
        return [{"error": f"Perplexity API error: {str(e)}"}]
    except (json.JSONDecodeError, KeyError) as e:
        return [{"error": f"Failed to parse people response: {str(e)}"}]


def generate_outreach(
    company_name: str, company_data: dict, people: list,
    sender_name: str, sender_role: str, api_key: str
) -> dict:
    """Use Claude API to generate talking points and personalized email. No web search = fast."""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    company_summary = json.dumps(company_data, indent=2)

    # Pick primary contact
    primary = "the relevant decision maker"
    for p in people:
        if "error" not in p:
            primary = f"{p['name']}, {p['title']}"
            break

    people_summary = json.dumps(people, indent=2)

    prompt = f"""You are a top-performing SDR. Write personalized outreach for '{company_name}'.

COMPANY RESEARCH:
{company_summary}

DECISION MAKERS FOUND:
{people_summary}

SENDER: {sender_name}, {sender_role}

Return ONLY this JSON (no markdown fences):
{{
  "talking_points": [
    "Point 1 — tied to a specific company fact or news item",
    "Point 2 — addresses a likely pain point based on their industry/size",
    "Point 3 — references their tech stack or competitors",
    "Point 4 — a trigger event angle (hiring, funding, expansion)"
  ],
  "email_subject": "Short, curiosity-driven subject line",
  "email_body": "Cold email addressed to {primary}. 4-6 sentences. Personalized to the company. Soft CTA for 15-min call. Professional but human tone.",
  "linkedin_note": "300-char LinkedIn connection request. Casual, mentions one specific company fact."
}}

Return ONLY the JSON."""

    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        content = resp.json()["content"][0]["text"]
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        if content.startswith("json"):
            content = content[4:].strip()
        return json.loads(content)
    except requests.exceptions.RequestException as e:
        return {"error": f"Claude API error: {str(e)}"}
    except (json.JSONDecodeError, KeyError) as e:
        return {"error": f"Failed to parse Claude response: {str(e)}"}


# ─── Demo Data ─────────────────────────────────────────────────────────────────

def demo_company(name: str) -> dict:
    return {
        "company_name": name,
        "industry": "Technology / SaaS (demo)",
        "founded": "2018",
        "headquarters": "San Francisco, CA",
        "employee_count": "~500",
        "funding": "Series B — $45M",
        "revenue_estimate": "$15-25M ARR",
        "recent_news": [
            f"{name} launches AI-powered analytics dashboard (June 2026)",
            f"{name} expands European operations with London office (May 2026)",
            f"{name} partners with Salesforce for CRM integration (April 2026)",
        ],
        "tech_stack": ["Python", "React", "AWS", "PostgreSQL"],
        "competitors": ["Competitor A", "Competitor B", "Competitor C"],
        "summary": (
            f"{name} is a growing SaaS company serving mid-market B2B teams. "
            f"This is demo data — toggle off Demo Mode and add API keys for real research."
        ),
    }


def demo_people(name: str) -> list:
    return [
        {"name": "Demo Contact 1", "title": "VP of Engineering", "email": "demo@example.com", "linkedin_url": "", "city": "San Francisco", "state": "CA"},
        {"name": "Demo Contact 2", "title": "Head of Sales", "email": "demo@example.com", "linkedin_url": "", "city": "New York", "state": "NY"},
    ]


def demo_outreach(name: str, sender_name: str, sender_role: str) -> dict:
    return {
        "talking_points": [
            f"Demo talking point 1 — would reference {name}'s recent news in live mode.",
            f"Demo talking point 2 — would address pain points based on their industry.",
            f"Demo talking point 3 — would reference tech stack and competitors.",
            f"Demo talking point 4 — would mention hiring signals or expansion triggers.",
        ],
        "email_subject": f"[Demo] Re: {name}'s growth — quick idea",
        "email_body": (
            f"Hi [Contact Name],\n\n"
            f"This is a demo email. In live mode, this would be a personalized cold email "
            f"referencing {name}'s recent news, addressing their specific pain points, "
            f"and ending with a soft CTA for a 15-minute call.\n\n"
            f"Toggle off Demo Mode and add your API keys to see real AI-generated outreach.\n\n"
            f"Best,\n{sender_name}\n{sender_role}"
        ),
        "linkedin_note": f"[Demo] Hi — this would be a personalized LinkedIn note about {name}. Add API keys for real output.",
    }


# ─── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown("---")

    # Check if API keys are configured in Streamlit Cloud secrets
    has_secrets = False
    try:
        has_secrets = bool(st.secrets.get("PERPLEXITY_API_KEY")) and bool(st.secrets.get("CLAUDE_API_KEY"))
    except Exception:
        pass

    if has_secrets:
        # Secrets configured — no need for demo mode toggle or key fields
        demo_mode = False
        sidebar_perplexity = ""
        sidebar_claude = ""
        st.success("✅ API keys configured")
    else:
        demo_mode = st.toggle("🎮 Demo Mode (no API keys needed)", value=True)
        if not demo_mode:
            st.markdown("### API Keys")
            st.caption("Keys entered here stay in your browser session only.")
            sidebar_perplexity = st.text_input("Perplexity API Key", type="password", help="perplexity.ai/settings/api")
            sidebar_claude = st.text_input("Claude API Key", type="password", help="console.anthropic.com")
        else:
            sidebar_perplexity = sidebar_claude = ""

    st.markdown("---")
    st.markdown("### 📧 Your Info (for email draft)")
    sender_name = st.text_input("Your Name", value="")
    sender_role = st.text_input("Your Role", value="GTM Automation Engineer")

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#475569; font-size:0.8rem;'>"
        "Powered by Perplexity AI + Claude"
        "</div>",
        unsafe_allow_html=True,
    )


# ─── Main Content ─────────────────────────────────────────────────────────────

st.markdown(
    "<h1 style='text-align:center; margin-bottom:0;'>🔍 AI Lead Researcher</h1>"
    "<p style='text-align:center; color:#6366f1 !important; font-size:1.1rem; margin-top:0.25rem;'>"
    "Company intel → Decision makers → Talking points → Ready email"
    "</p>",
    unsafe_allow_html=True,
)

st.markdown("")

# Input row
col_input, col_btn = st.columns([4, 1])
with col_input:
    company_name = st.text_input(
        "Company name",
        placeholder="e.g.  Notion, Figma, Rippling, Deel...",
        label_visibility="collapsed",
    )
with col_btn:
    st.markdown("<div style='height:0.1rem'></div>", unsafe_allow_html=True)
    run_btn = st.button("Research 🚀")


# ─── Execute ───────────────────────────────────────────────────────────────────

if run_btn and company_name.strip():
    company_name = company_name.strip()
    start_time = time.time()

    with st.status(f"🔍 Researching **{company_name}**...", expanded=True) as status:
        if demo_mode:
            time.sleep(1.5)
            company_data = demo_company(company_name)
            people = demo_people(company_name)
            outreach = demo_outreach(company_name, sender_name, sender_role)
        else:
            # Resolve API keys (sidebar → secrets fallback)
            perplexity_key = get_key("PERPLEXITY_API_KEY", sidebar_perplexity)
            claude_key = get_key("CLAUDE_API_KEY", sidebar_claude)

            if not perplexity_key:
                st.error("⚠️ Perplexity API key required for company research.")
                st.stop()
            if not claude_key:
                st.error("⚠️ Claude API key required for outreach generation.")
                st.stop()

            # Step 1: Perplexity company research + people search in PARALLEL
            st.write("📡 Researching company + finding decision makers...")
            with ThreadPoolExecutor(max_workers=2) as executor:
                company_future = executor.submit(research_company_perplexity, company_name, perplexity_key)
                people_future = executor.submit(find_people_perplexity, company_name, perplexity_key)
                company_data = company_future.result()
                people = people_future.result()

            if "error" in company_data:
                st.error(f"Research failed: {company_data['error']}")
                st.stop()

            # Handle people search failure gracefully
            if not people or (len(people) == 1 and "error" in people[0]):
                people = []

            # Step 2: Claude generates talking points + email (fast, no web search)
            st.write("✍️ Generating personalized outreach...")
            outreach = generate_outreach(
                company_name, company_data, people,
                sender_name, sender_role, claude_key
            )

            if "error" in outreach:
                st.error(f"Outreach generation failed: {outreach['error']}")
                st.stop()

        elapsed = time.time() - start_time
        status.update(label=f"✅ Research complete in {elapsed:.1f}s", state="complete", expanded=False)

    # ─── Results ───────────────────────────────────────────────────────────

    st.markdown("")

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("⏱️ Time", f"{elapsed:.1f}s")
    m2.metric("🏢 Industry", company_data.get("industry", "N/A")[:20])
    m3.metric("👥 Employees", company_data.get("employee_count", "N/A"))
    m4.metric("💰 Funding", company_data.get("funding", "N/A")[:20])

    st.markdown("")

    # Two-column layout
    left, right = st.columns(2)

    # ── LEFT: Company Brief ──
    with left:
        st.markdown(
            '<div class="result-card accent-indigo">'
            '<h3>🏢 Company Brief</h3>'
            f'<p>{company_data.get("summary", "No summary available.")}</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        details_md = ""
        if company_data.get("founded"):
            details_md += f"**Founded:** {company_data['founded']}  \n"
        if company_data.get("headquarters"):
            details_md += f"**HQ:** {company_data['headquarters']}  \n"
        if company_data.get("revenue_estimate"):
            details_md += f"**Revenue:** {company_data['revenue_estimate']}  \n"

        tech = company_data.get("tech_stack", [])
        details_html = ""
        if tech:
            badges = " ".join(f'<span class="badge">{t}</span>' for t in tech)
            details_html = f"**Tech Stack:**<br>{badges}"

        competitors = company_data.get("competitors", [])
        if competitors:
            comp_badges = " ".join(f'<span class="badge">{c}</span>' for c in competitors)
            details_html += f"<br><br>**Competitors:**<br>{comp_badges}"

        st.markdown(details_md)
        if details_html:
            st.markdown(details_html, unsafe_allow_html=True)

        # Recent News
        news = company_data.get("recent_news", [])
        if news:
            st.markdown("")
            st.markdown(
                '<div class="result-card accent-amber"><h3>📰 Recent News</h3></div>',
                unsafe_allow_html=True,
            )
            for item in news:
                if isinstance(item, dict):
                    title = item.get("title", "")
                    date = item.get("date", "")
                    source = item.get("source", "")
                    st.markdown(f"• {title} ({date}) — *{source}*" if date else f"• {title}")
                else:
                    st.markdown(f"• {item}")

    # ── RIGHT: Decision Makers ──
    with right:
        st.markdown(
            '<div class="result-card accent-emerald"><h3>👥 Key Decision Makers</h3></div>',
            unsafe_allow_html=True,
        )

        if not people:
            st.info("No decision makers found. Try a different company name.")
        else:
            for p in people:
                if "error" in p:
                    st.warning(p["error"])
                    continue
                # LinkedIn: only show if Perplexity found the real profile URL
                if p.get("linkedin_url") and "/in/" in p.get("linkedin_url", ""):
                    linkedin_link = f" · [LinkedIn]({p['linkedin_url']})"
                else:
                    linkedin_link = ""
                location = f"{p.get('city', '')}, {p.get('state', '')}".strip(", ")
                st.markdown(
                    f"**{p['name']}** — {p['title']}  \n"
                    f"📧 `{p['email']}`{linkedin_link}  \n"
                    f"{'📍 ' + location if location else ''}"
                )
                st.markdown("---")

        # Talking Points
        st.markdown(
            '<div class="result-card accent-rose"><h3>💡 Talking Points</h3></div>',
            unsafe_allow_html=True,
        )
        for i, point in enumerate(outreach.get("talking_points", []), 1):
            st.markdown(f"**{i}.** {point}")

    # ── Full-width: Email Draft ──
    st.markdown("")
    st.markdown("---")
    st.markdown("## ✉️ Ready-to-Send Email")

    e_col1, e_col2 = st.columns([3, 1])
    with e_col1:
        st.markdown(f"**Subject:** {outreach.get('email_subject', 'N/A')}")
        st.markdown(
            f'<div class="email-box">{outreach.get("email_body", "")}</div>',
            unsafe_allow_html=True,
        )
    with e_col2:
        st.markdown("**📋 LinkedIn Note**")
        st.info(outreach.get("linkedin_note", ""))

        st.markdown("")
        st.download_button(
            "📥 Download All Data (JSON)",
            data=json.dumps(
                {
                    "company": company_data,
                    "contacts": people,
                    "outreach": outreach,
                    "researched_at": datetime.now().isoformat(),
                },
                indent=2,
            ),
            file_name=f"lead_research_{company_name.lower().replace(' ', '_')}.json",
            mime="application/json",
        )

    # Footer
    st.markdown(
        f"<p style='text-align:center; margin-top:2rem;'>"
        f"<span class='timer-text'>Total research time: {elapsed:.1f} seconds</span>"
        f"</p>"
        f"<p style='text-align:center; color:#64748b !important; font-size:0.8rem;'>"
        f"⚠️ AI-generated research — always verify data and contacts before outreach."
        f"</p>",
        unsafe_allow_html=True,
    )

elif run_btn:
    st.warning("Please enter a company name.")
