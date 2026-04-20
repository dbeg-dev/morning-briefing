import anthropic
import json
import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo


def fetch_google_events(now):
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
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
        service = build("calendar", "v3", credentials=creds)
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
    return "\n".join(lines) if lines else "No calendar events found for today."


def extract_section(text, start_tag, end_tag):
    start = text.find(start_tag)
    end   = text.find(end_tag)
    if start == -1 or end == -1:
        return None
    return text[start + len(start_tag):end].strip()


def generate_briefing():
    client = anthropic.Anthropic()

    tz  = ZoneInfo("America/New_York")
    now = datetime.now(tz)
    today    = now.strftime("%A, %B %-d, %Y")
    time_str = now.strftime("%I:%M %p")

    google_events  = fetch_google_events(now)
    outlook_events = fetch_outlook_events(now)
    calendar_text  = format_calendar_events(google_events, outlook_events, tz)

    prompt = f"""Generate Dory's morning briefing for {today} at {time_str}. Dory lives in Manhattan, NYC — busy professional, active job search (SVP role discussions at Birthright Israel Foundation, Fi, Kindred), young family, interests in fashion/arts/culture.

Use web search to get TODAY's live Manhattan weather forecast.

TODAY'S CALENDAR:
{calendar_text}

Generate these sections with EXACT delimiters:

WEATHER_START
[2-3 sentences: current temp, conditions, precipitation, walking suitability]
WEATHER_END

OUTFIT_START
[3-4 sentences: specific outfit suited to weather + professional day. Reference her brands: Scanlan Theodore, Ferragamo, On Running, Lululemon, Ralph Lauren, Theory, David Yurman. Be specific — colors, layers, shoes.]
OUTFIT_END

CALENDAR_START
[Format today's calendar events into a clean day-ahead schedule. Add timing or prep notes to help Dory navigate the day smoothly. If no events, suggest how to structure the day for job search momentum.]
CALENDAR_END

EMAIL_START
[Bullet list of priority follow-ups:
- Ruvym Gilman / Birthright Israel Foundation: SVP role status
- Vivian Chan / Austen Riggs: LFE May 1-3 registration
- Elissa Ganz: pending reply
- Victoria Valenti (Fi) and Somer Reznick (Kindred): check in]
EMAIL_END

WELLNESS_START
[3-4 bullet wellness tips for the day — hydration, movement, energy, focus]
WELLNESS_END

SMS_START
Write a morning SMS for Dory. Use the ACTUAL calendar events and email priorities generated above — not placeholders. Format:
"GM Dory \u2600\ufe0f [temp+condition]. [outfit tip]. \U0001f4c5 [actual calendar events, or 'Clear day']. \U0001f4ec [top 2 actual email priorities by name]. [1 wellness tip]."
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

    weather  = extract_section(full_text, "WEATHER_START",  "WEATHER_END")  or "\u2014"
    outfit   = extract_section(full_text, "OUTFIT_START",   "OUTFIT_END")   or "\u2014"
    calendar = extract_section(full_text, "CALENDAR_START", "CALENDAR_END") or calendar_text
    emails   = extract_section(full_text, "EMAIL_START",    "EMAIL_END")    or "\u2014"
    wellness = extract_section(full_text, "WELLNESS_START", "WELLNESS_END") or "\u2014"
    sms      = extract_section(full_text, "SMS_START",      "SMS_END")      or "\u2014"

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
