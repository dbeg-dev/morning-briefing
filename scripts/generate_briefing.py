import anthropic
import json
import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo


# ── Calendar ───────────────────────────────────────────────────────────────────────────────

def fetch_google_events(now):
    creds_json  = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
    if not creds_json:
        return []
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_info(
            json.loads(creds_json),
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        )
        service   = build("calendar", "v3", credentials=creds)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = now.replace(hour=23, minute=59, second=59, microsecond=0)
        result = service.events().list(
            calendarId=calendar_id,
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        return result.get("items", [])
    except Exception as e:
        print(f"Google Calendar error: {e}")
        return []


def fetch_outlook_events(now):
    client_id     = os.environ.get("MS_CLIENT_ID")
    client_secret = os.environ.get("MS_CLIENT_SECRET")
    tenant_id     = os.environ.get("MS_TENANT_ID")
    user_email    = os.environ.get("MS_USER_EMAIL")
    if not all([client_id, client_secret, tenant_id, user_email]):
        return []
    try:
        import msal

        app = msal.ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )
        token_result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in token_result:
            print(f"Outlook auth error: {token_result.get('error_description')}")
            return []

        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = now.replace(hour=23, minute=59, second=59, microsecond=0)
        resp = requests.get(
            f"https://graph.microsoft.com/v1.0/users/{user_email}/calendarView",
            headers={"Authorization": f"Bearer {token_result['access_token']}"},
            params={
                "startDateTime": day_start.isoformat(),
                "endDateTime":   day_end.isoformat(),
                "$orderby":      "start/dateTime",
                "$select":       "subject,start,end,location",
            },
        )
        resp.raise_for_status()
        return resp.json().get("value", [])
    except Exception as e:
        print(f"Outlook Calendar error: {e}")
        return []


def format_calendar_events(google_events, outlook_events, tz):
    lines = []
    for e in google_events:
        start = e.get("start", {})
        raw   = start.get("dateTime") or start.get("date", "")
        label = datetime.fromisoformat(raw).astimezone(tz).strftime("%-I:%M %p") if "T" in raw else "All day"
        lines.append(f"• {label} — {e.get('summary', 'Untitled')} [Google]")
    for e in outlook_events:
        raw   = e.get("start", {}).get("dateTime", "")
        label = datetime.fromisoformat(raw).astimezone(tz).strftime("%-I:%M %p") if raw else "All day"
        lines.append(f"• {label} — {e.get('subject', 'Untitled')} [Outlook]")
    return "\n".join(lines) if lines else None


# ── Email ─────────────────────────────────────────────────────────────────────────────────

def fetch_gmail_emails():
    client_id     = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
    if not all([client_id, client_secret, refresh_token]):
        return []
    try:
        token_resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id":     client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type":    "refresh_token",
        })
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        search = requests.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers=headers,
            params={"q": "is:unread newer_than:2d", "maxResults": 20},
        )
        search.raise_for_status()
        messages = search.json().get("messages", [])

        emails = []
        for msg in messages[:15]:
            detail = requests.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
                headers=headers,
                params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
            )
            detail.raise_for_status()
            hdrs = {h["name"]: h["value"] for h in detail.json().get("payload", {}).get("headers", [])}
            emails.append(f"[Gmail] From: {hdrs.get('From', '?')} | Subject: {hdrs.get('Subject', '(no subject)')}")
        return emails
    except Exception as e:
        print(f"Gmail error: {e}")
        return []


def fetch_outlook_emails():
    client_id     = os.environ.get("MS_CLIENT_ID")
    client_secret = os.environ.get("MS_CLIENT_SECRET")
    tenant_id     = os.environ.get("MS_TENANT_ID")
    user_email    = os.environ.get("MS_USER_EMAIL")
    if not all([client_id, client_secret, tenant_id, user_email]):
        return []
    try:
        import msal

        app = msal.ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )
        token_result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in token_result:
            return []

        resp = requests.get(
            f"https://graph.microsoft.com/v1.0/users/{user_email}/messages",
            headers={"Authorization": f"Bearer {token_result['access_token']}"},
            params={
                "$filter":  "isRead eq false",
                "$orderby": "receivedDateTime desc",
                "$select":  "from,subject,receivedDateTime",
                "$top":     20,
            },
        )
        resp.raise_for_status()
        emails = []
        for e in resp.json().get("value", []):
            sender = e.get("from", {}).get("emailAddress", {}).get("name", "?")
            emails.append(f"[Outlook] From: {sender} | Subject: {e.get('subject', '(no subject)')}")
        return emails
    except Exception as e:
        print(f"Outlook email error: {e}")
        return []


# ── Core ────────────────────────────────────────────────────────────────────────────────

def extract_section(text, start_tag, end_tag):
    start = text.find(start_tag)
    end   = text.find(end_tag)
    if start == -1 or end == -1:
        return None
    return text[start + len(start_tag):end].strip()


def generate_briefing():
    client = anthropic.Anthropic()

    tz       = ZoneInfo("America/New_York")
    now      = datetime.now(tz)
    today    = now.strftime("%A, %B %-d, %Y")
    time_str = now.strftime("%I:%M %p")

    google_events  = fetch_google_events(now)
    outlook_events = fetch_outlook_events(now)
    calendar_text  = format_calendar_events(google_events, outlook_events, tz)

    gmail_emails   = fetch_gmail_emails()
    outlook_emails = fetch_outlook_emails()
    all_emails     = gmail_emails + outlook_emails

    calendar_section = (
        f"TODAY'S CALENDAR (live):\n{calendar_text}"
        if calendar_text else
        "TODAY'S CALENDAR: No calendar credentials configured — suggest a productive day structure."
    )

    email_section = (
        "RECENT UNREAD EMAILS (live):\n" + "\n".join(all_emails)
        if all_emails else
        "RECENT UNREAD EMAILS: No email credentials configured — use these known standing priorities:\n"
        "- Ruvym Gilman / Birthright Israel Foundation: SVP role follow-up\n"
        "- Vivian Chan / Austen Riggs: LFE May 1-3 registration (time-sensitive)\n"
        "- Elissa Ganz: pending reply\n"
        "- Victoria Valenti (Fi) and Somer Reznick (Kindred): SVP check-ins"
    )

    prompt = f"""Generate Dory's morning briefing for {today} at {time_str}. Dory lives in Manhattan, NYC — busy professional, active job search (SVP role discussions at Birthright Israel Foundation, Fi, Kindred), young family, interests in fashion/arts/culture.

Use web search to get TODAY's live Manhattan weather forecast.

{calendar_section}

{email_section}

Generate these sections with EXACT delimiters:

WEATHER_START
[2-3 sentences: current temp, conditions, precipitation, walking suitability]
WEATHER_END

OUTFIT_START
[3-4 sentences: specific outfit suited to weather + professional day. Reference her brands: Scanlan Theodore, Ferragamo, On Running, Lululemon, Ralph Lauren, Theory, David Yurman. Be specific — colors, layers, shoes.]
OUTFIT_END

CALENDAR_START
[Format today's actual calendar events into a clean schedule with prep notes. If no live events, suggest a focused day structure for job search momentum.]
CALENDAR_END

EMAIL_START
[Using the actual unread emails above, identify and summarize the top 3-5 priority action items. Flag anything time-sensitive. If no live emails, use the standing priorities listed above.]
EMAIL_END

WELLNESS_START
[3-4 bullet wellness tips for the day — hydration, movement, energy, focus]
WELLNESS_END

SMS_START
Write a morning SMS for Dory using ACTUAL calendar events and email priorities above. Format:
"GM Dory \u2600\ufe0f [temp+condition]. [outfit tip]. \U0001f4c5 [actual events or 'Clear day']. \U0001f4ec [top 2 real priorities by name]. [1 wellness tip]."
Target 400 chars, max 480.
SMS_END"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )

    full_text = "\n".join(
        block.text for block in response.content if hasattr(block, "text")
    )

    weather  = extract_section(full_text, "WEATHER_START",  "WEATHER_END")  or "—"
    outfit   = extract_section(full_text, "OUTFIT_START",   "OUTFIT_END")   or "—"
    calendar = extract_section(full_text, "CALENDAR_START", "CALENDAR_END") or calendar_text or "—"
    emails   = extract_section(full_text, "EMAIL_START",    "EMAIL_END")    or "—"
    wellness = extract_section(full_text, "WELLNESS_START", "WELLNESS_END") or "—"
    sms      = extract_section(full_text, "SMS_START",      "SMS_END")      or "—"

    content = f"""GOOD MORNING DORY
{today}

WEATHER
{weather}

WEAR TODAY
{outfit}

YOUR DAY
{calendar}

PRIORITIES
{emails}

WELLNESS
{wellness}

---
SMS
{sms}

Have a great day.
"""

    with open("sms.html", "w") as f:
        f.write(content)

    print(f"Briefing generated for {today}")
    print(content)


if __name__ == "__main__":
    generate_briefing()
