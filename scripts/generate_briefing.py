import anthropic
import json
import os
import re
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# ── Full Daily Workout Plans ─────────────────────────────────────────────────────
# Weights: Lower body 30 lb, Upper body 15-20 lb
# Week 3: increase 5-10%. Week 4: drop sets on final set of each exercise.
# Walk to/from 622 Third Ave (~30 min each way Mon-Thu) = warm-up + cool-down.

WORKOUTS = {
    0: {  # Monday — Upper Body A
        "name": "Upper Body A",
        "duration": "45 min",
        "log": "strength 45 min (~220 cal) + walk x2 (~300 cal)",
        "detail": """WARM-UP (5 min)
Arm circles, band pull-aparts, shoulder rolls, light cardio

MAIN (35 min) — 60 sec rest between sets
• Dumbbell Bench Press — 4x10 @ 20 lb
• Bent-Over Dumbbell Rows — 4x10 @ 20 lb each arm
• Dumbbell Overhead Press — 3x12 @ 15 lb
• Lateral Raises — 3x15 @ 10 lb (slow and controlled)
• Bicep Curls — 3x12 @ 15 lb
• Tricep Kickbacks — 3x12 @ 15 lb
• Front Raises — 3x12 @ 10 lb

COOL-DOWN (5 min)
Chest stretch, shoulder cross-body stretch, tricep overhead stretch

Week 3: increase all weights 2.5-5 lb
Week 4: final set of each exercise — drop weight 20%, go to failure""",
    },
    1: {  # Tuesday — Lower Body A
        "name": "Lower Body A",
        "duration": "45 min",
        "log": "strength 45 min (~220 cal) + walk x2 (~300 cal)",
        "detail": """WARM-UP (5 min)
Bodyweight squats x15, hip circles, leg swings, glute bridges x10

MAIN (35 min) — 60 sec rest between sets
• Goblet Squat — 4x12 @ 30 lb
• Romanian Deadlift — 4x10 @ 30 lb each hand
• Reverse Lunges — 3x10 each leg @ 20 lb each hand
• Hip Thrusts — 4x12 @ 30 lb across hips
• Calf Raises — 3x20 @ 30 lb each hand
• Sumo Squat — 3x12 @ 30 lb

COOL-DOWN (5 min)
Pigeon pose, hamstring stretch, standing quad stretch

Week 3: increase all weights 5 lb
Week 4: final set of each exercise — drop weight 20%, go to failure""",
    },
    2: {  # Wednesday — HIIT + Core
        "name": "HIIT + Core",
        "duration": "40 min",
        "log": "HIIT 25 min (~300 cal) + walk x2 (~300 cal)",
        "detail": """HIIT BLOCK (25 min)
40 sec work / 20 sec rest — 5 rounds, 90 sec rest between rounds:
1. Burpees
2. Jump Squats
3. Mountain Climbers
4. Alternating Reverse Lunges
5. High Knees

CORE BLOCK (15 min)
• Plank — 3x45 sec
• Dead Bug — 3x12 each side (slow and controlled)
• Hollow Body Hold — 3x30 sec
• Russian Twists — 3x20 @ 10 lb dumbbell
• Bicycle Crunches — 3x20
• Side Plank — 2x30 sec each side

Week 3: push harder on HIIT intervals, add 1 round
Week 4: max effort every interval — final push""",
    },
    3: {  # Thursday — Lower Body B
        "name": "Lower Body B",
        "duration": "45 min",
        "log": "strength 45 min (~220 cal) + walk x2 (~300 cal)",
        "detail": """WARM-UP (5 min)
Bodyweight squats x15, hip circles, leg swings, glute bridges x10

MAIN (35 min) — 60 sec rest between sets
• Deadlift — 4x8 @ 30 lb each hand (heavier, lower reps)
• Bulgarian Split Squat — 3x10 each leg @ 20 lb each hand
• Glute Bridges — 3x15 @ 30 lb across hips
• Step-Ups — 3x12 each leg @ 20 lb each hand (use sturdy chair)
• Hamstring Curl — 3x12 @ 15 lb dumbbell between feet
• Wall Sit — 3x45 sec bodyweight

COOL-DOWN (5 min)
Figure four stretch, hamstring stretch, hip flexor lunge stretch

Week 3: increase all weights 5 lb
Week 4: final set of each exercise — drop weight 20%, go to failure""",
    },
    4: {  # Friday — Upper Body B
        "name": "Upper Body B",
        "duration": "45 min",
        "log": "strength 45 min (~220 cal)",
        "detail": """WARM-UP (5 min)
Arm circles, band pull-aparts, shoulder rolls, light cardio

MAIN (35 min) — 60 sec rest between sets
• Dumbbell Chest Flyes — 4x12 @ 15 lb
• Single Arm Dumbbell Row — 4x10 @ 20 lb each arm
• Arnold Press — 3x12 @ 15 lb
• Hammer Curls — 3x12 @ 15 lb
• Skull Crushers — 3x12 @ 15 lb
• Rear Delt Flyes — 3x15 @ 10 lb
• Dumbbell Pullover — 3x12 @ 20 lb

COOL-DOWN (5 min)
Lat stretch, chest doorframe stretch, child's pose

Week 3: increase all weights 2.5-5 lb
Week 4: final set of each exercise — drop weight 20%, go to failure""",
    },
    5: {  # Saturday — Lower Body C + Cardio
        "name": "Lower Body C + Cardio Finisher",
        "duration": "60 min",
        "log": "strength + cardio 60 min (~380 cal)",
        "detail": """WARM-UP (5 min)
Bodyweight squats x15, hip circles, leg swings, glute bridges x10

MAIN (35 min) — 60 sec rest between sets
• Hip Thrusts — 4x12 @ 30 lb (heavier than Lower A if possible)
• Sumo Squats — 4x12 @ 30 lb
• Step-Ups — 3x10 each leg @ 20 lb each hand
• Curtsy Lunges — 3x12 each leg @ 15 lb each hand
• Hamstring Curls — 3x12 @ 15 lb dumbbell between feet
• Standing Abductions — 3x15 each leg bodyweight

CARDIO FINISHER (15 min)
Incline treadmill walk — incline 8-10, speed 3.0-3.5
OR bike at moderate resistance

COOL-DOWN (5 min)
Full lower body stretch — hip flexors, hamstrings, glutes, calves

Week 3: increase all weights 5 lb
Week 4: drop sets + push cardio finisher to 20 min""",
    },
    6: {  # Sunday — Yoga
        "name": "Yoga + Full Rest",
        "duration": "60 min",
        "log": "yoga 60 min (~150 cal)",
        "detail": """60 min yoga — your existing practice.
Full rest from weights. Non-negotiable recovery day.
Foam roll after if time allows.
Meal prep for the week while you have energy.""",
    },
}

# ── Meal Plans ──────────────────────────────────────────────────────────────────
# Target: 1,400 cal / 110g+ protein. Log all exercise separately in Lose It.

MEALS = {
    0: {  # Monday
        "meals": [
            "Smoothie (300/28g): almond milk, protein powder, spinach, banana, frozen berries",
            "Lunch (400/40g): Dig — chicken grain bowl, roasted veg, no bread",
            "Snack (150/15g): Greek yogurt + mixed berries",
            "Dinner (450/38g): Sheet pan salmon + roasted asparagus + half cup quinoa",
        ],
    },
    1: {  # Tuesday
        "meals": [
            "Smoothie (300/28g): almond milk, protein powder, spinach, frozen mango, chia seeds",
            "Lunch (400/35g): Sweetgreen Harvest Bowl + grilled chicken, dressing on side",
            "Snack (130/8g): Hard boiled egg + apple",
            "Dinner (480/40g): Turkey taco bowl — turkey, black beans, salsa, half avocado",
        ],
    },
    2: {  # Wednesday
        "meals": [
            "Smoothie (300/22g): almond milk, chocolate protein powder, peanut butter, banana",
            "Lunch (400/30g): Tuna bowl — tuna, mixed greens, avocado, cherry tomatoes, lemon",
            "Snack (150/8g): String cheese + pear",
            "Dinner (450/35g): Baked cod + roasted broccoli + brown rice",
        ],
    },
    3: {  # Thursday
        "meals": [
            "Smoothie (300/26g): almond milk, protein powder, frozen pineapple, frozen mango, spinach",
            "Lunch (420/32g): Chopt or Dos Toros — salad or burrito bowl, no chips",
            "Snack (150/18g): Cottage cheese + cherry tomatoes",
            "Dinner (480/38g): Chicken stir fry — chicken, bok choy, snap peas, low sodium soy sauce, rice",
        ],
    },
    4: {  # Friday
        "meals": [
            "Smoothie (330/27g): almond milk, protein powder, blueberries, rolled oats, honey",
            "Lunch (400/35g): Grain bowl — quinoa, roasted veg, feta, lemon olive oil",
            "Snack (150/10g): Almonds + clementine",
            "Dinner (450/35g): Turkey meatballs + zucchini noodles + marinara",
        ],
    },
    5: {  # Saturday
        "meals": [
            "Breakfast (350/20g): 2 eggs + avocado toast + berries",
            "Lunch (400/25g): Cottage cheese plate + cucumber + tomato + rice cakes",
            "Snack (150/8g): Edamame + cucumber",
            "Dinner (480/35g): Grilled flank steak + roasted cauliflower + mixed greens",
        ],
    },
    6: {  # Sunday
        "meals": [
            "Breakfast (350/25g): Smoked salmon + cream cheese + whole wheat bagel thin",
            "Lunch (400/30g): Chicken vegetable soup + whole wheat crackers",
            "Snack (150/10g): Pear + string cheese",
            "Dinner (480/35g): Roasted chicken breast + Brussels sprouts + mashed cauliflower",
        ],
    },
}


def get_health_section(now):
    w = now.weekday()
    workout = WORKOUTS[w]
    meals = MEALS[w]
    meal_lines = "\n".join(f"• {m}" for m in meals["meals"])
    return (
        f"TODAY: {workout['name']} — {workout['duration']}\n\n"
        f"{workout['detail']}\n\n"
        f"MEALS (~1,400 cal / 110g+ protein)\n"
        f"{meal_lines}\n\n"
        f"Log in Lose It: {workout['log']}"
    )


def get_health_sms(now):
    w = now.weekday()
    workout = WORKOUTS[w]
    meals = MEALS[w]
    lines = [
        f"Workout: {workout['name']} ({workout['duration']})",
    ]
    # Add first 3 lines of workout detail (warm-up omitted for SMS brevity)
    detail_lines = [l.strip() for l in workout['detail'].split('\n') if l.strip() and l.strip().startswith('•')]
    lines.append("Key moves: " + ", ".join(l.lstrip('• ').split(' — ')[0] for l in detail_lines[:4]))
    lines.append("")
    for m in meals["meals"]:
        lines.append(m)
    lines.append(f"Log: {workout['log']}")
    return "\n".join(lines)


# ── Available.page schedule ─────────────────────────────────────────────────────

def fetch_available_schedule(today_str):
    try:
        resp = requests.get(
            "https://raw.githubusercontent.com/dbeg-dev/available/main/index.html",
            timeout=10,
        )
        resp.raise_for_status()
        html = resp.text
        match = re.search(r'const BUSY\s*=\s*(\[.*?\]);', html, re.DOTALL)
        if not match:
            return None
        busy = json.loads(match.group(1))
        today_blocks = [b for b in busy if b["s"].startswith(today_str)]
        if not today_blocks:
            return None
        events = sorted(today_blocks, key=lambda b: b["s"])
        merged = []
        for b in events:
            s = datetime.fromisoformat(b["s"])
            e = datetime.fromisoformat(b["e"])
            if e.date().isoformat() != today_str:
                e = datetime.fromisoformat(today_str + "T23:59")
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
            else:
                merged.append((s, e))
        lines = []
        for s, e in merged:
            lines.append(f"• {s.strftime('%-I:%M %p')} – {e.strftime('%-I:%M %p')}: Blocked")
        return "\n".join(lines)
    except Exception as ex:
        print(f"Available schedule error: {ex}")
        return None


# ── Calendar ─────────────────────────────────────────────────────────────────────

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
        day_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
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
    client_id = os.environ.get("MS_CLIENT_ID")
    client_secret = os.environ.get("MS_CLIENT_SECRET")
    tenant_id = os.environ.get("MS_TENANT_ID")
    user_email = os.environ.get("MS_USER_EMAIL")
    if not all([client_id, client_secret, tenant_id, user_email]):
        return []
    try:
        import msal
        app = msal.ConfidentialClientApplication(
            client_id, authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )
        token_result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" not in token_result:
            return []
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        resp = requests.get(
            f"https://graph.microsoft.com/v1.0/users/{user_email}/calendarView",
            headers={"Authorization": f"Bearer {token_result['access_token']}"},
            params={"startDateTime": day_start.isoformat(), "endDateTime": day_end.isoformat(),
                    "$orderby": "start/dateTime", "$select": "subject,start,end,location"},
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
        raw = start.get("dateTime") or start.get("date", "")
        label = datetime.fromisoformat(raw).astimezone(tz).strftime("%-I:%M %p") if "T" in raw else "All day"
        lines.append(f"• {label} — {e.get('summary', 'Untitled')}")
    for e in outlook_events:
        raw = e.get("start", {}).get("dateTime", "")
        label = datetime.fromisoformat(raw).astimezone(tz).strftime("%-I:%M %p") if raw else "All day"
        lines.append(f"• {label} — {e.get('subject', 'Untitled')}")
    return "\n".join(lines) if lines else None


# ── Email ─────────────────────────────────────────────────────────────────────────

def fetch_gmail_emails():
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
    if not all([client_id, client_secret, refresh_token]):
        return []
    try:
        token_resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id, "client_secret": client_secret,
            "refresh_token": refresh_token, "grant_type": "refresh_token",
        })
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        search = requests.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers=headers, params={"q": "is:unread newer_than:2d", "maxResults": 20},
        )
        search.raise_for_status()
        emails = []
        for msg in search.json().get("messages", [])[:15]:
            detail = requests.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
                headers=headers,
                params={"format": "metadata", "metadataHeaders": ["From", "Subject"]},
            )
            detail.raise_for_status()
            hdrs = {h["name"]: h["value"] for h in detail.json().get("payload", {}).get("headers", [])}
            emails.append(f"[Gmail] From: {hdrs.get('From', '?')} | Subject: {hdrs.get('Subject', '(no subject)')}")
        return emails
    except Exception as e:
        print(f"Gmail error: {e}")
        return []


def fetch_teams_messages():
    client_id = os.environ.get("MS_CLIENT_ID")
    client_secret = os.environ.get("MS_CLIENT_SECRET")
    tenant_id = os.environ.get("MS_TENANT_ID")
    user_email = os.environ.get("MS_USER_EMAIL")
    if not all([client_id, client_secret, tenant_id, user_email]):
        return []
    try:
        import msal
        app = msal.ConfidentialClientApplication(
            client_id, authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )
        token_result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" not in token_result:
            return []
        resp = requests.get(
            f"https://graph.microsoft.com/v1.0/users/{user_email}/chats",
            headers={"Authorization": f"Bearer {token_result['access_token']}"},
            params={"$expand": "lastMessagePreview", "$top": 10},
        )
        if not resp.ok:
            return []
        messages = []
        for chat in resp.json().get("value", []):
            preview = chat.get("lastMessagePreview", {})
            if not preview:
                continue
            sender = preview.get("from", {}).get("user", {}).get("displayName", "Unknown")
            body = preview.get("body", {}).get("content", "")[:120].replace("\n", " ")
            topic = chat.get("topic") or f"Chat with {sender}"
            messages.append(f"[Teams] {topic} — {sender}: {body}")
        return messages
    except Exception as e:
        print(f"Teams error: {e}")
        return []


def fetch_outlook_emails():
    client_id = os.environ.get("MS_CLIENT_ID")
    client_secret = os.environ.get("MS_CLIENT_SECRET")
    tenant_id = os.environ.get("MS_TENANT_ID")
    user_email = os.environ.get("MS_USER_EMAIL")
    if not all([client_id, client_secret, tenant_id, user_email]):
        return []
    try:
        import msal
        app = msal.ConfidentialClientApplication(
            client_id, authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )
        token_result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" not in token_result:
            return []
        resp = requests.get(
            f"https://graph.microsoft.com/v1.0/users/{user_email}/messages",
            headers={"Authorization": f"Bearer {token_result['access_token']}"},
            params={"$filter": "isRead eq false", "$orderby": "receivedDateTime desc",
                    "$select": "from,subject,receivedDateTime", "$top": 20},
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


# ── Core ──────────────────────────────────────────────────────────────────────────

def extract_section(text, start_tag, end_tag):
    start = text.find(start_tag)
    end = text.find(end_tag)
    if start == -1 or end == -1:
        return None
    return text[start + len(start_tag):end].strip()


def generate_briefing():
    client = anthropic.Anthropic()
    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)
    today = now.strftime("%A, %B %-d, %Y")
    time_str = now.strftime("%I:%M %p")

    google_events = fetch_google_events(now)
    outlook_events = fetch_outlook_events(now)
    calendar_text = format_calendar_events(google_events, outlook_events, tz)

    gmail_emails = fetch_gmail_emails()
    outlook_emails = fetch_outlook_emails()
    teams_messages = fetch_teams_messages()
    all_emails = gmail_emails + outlook_emails + teams_messages

    today_str = now.strftime("%Y-%m-%d")
    available_schedule = fetch_available_schedule(today_str)

    health_section = get_health_section(now)
    health_sms = get_health_sms(now)

    if calendar_text:
        calendar_section = f"TODAY'S CALENDAR (live):\n{calendar_text}"
    elif available_schedule:
        calendar_section = (
            f"TODAY'S SCHEDULE (from availability page):\n{available_schedule}\n"
            f"Working hours: 10:00 AM – 5:00 PM ET. Any unlisted time is free."
        )
    else:
        calendar_section = "TODAY'S CALENDAR: No data — suggest a focused job search day structure."

    email_section = (
        f"RECENT UNREAD EMAILS + TEAMS CHATS (live):\n" + "\n".join(all_emails)
        if all_emails else
        "RECENT UNREAD EMAILS + TEAMS CHATS: No credentials — use standing priorities:\n"
        "- Birthright Israel Foundation: SVP role follow-up\n"
        "- Victoria Valenti (Fi) and Somer Reznick (Kindred): SVP check-ins\n"
        "- Elissa Ganz / ZRG Partners: pending reply"
    )

    prompt = f"""Generate Dory's morning briefing for {today} at {time_str}.
Dory: Manhattan NYC (112 E 17th St, zip 10003). SVP job search. Office at 622 Third Ave Mon-Thu. Walks 30 min each way daily.

CRITICAL: Search "Manhattan NYC weather {now.strftime('%B %d %Y')}" for live weather for zip 10003.

{calendar_section}

{email_section}

HEALTH PLAN FOR TODAY (pre-generated — include verbatim):
{health_section}

Generate with EXACT delimiters:

WEATHER_START
[2-3 sentences: Manhattan-specific temp, conditions, walking suitability]
WEATHER_END

OUTFIT_START
[3-4 sentences: specific outfit for weather + day. Brands: Scanlan Theodore, Ferragamo, On Running, Lululemon, Ralph Lauren, Theory, David Yurman.]
OUTFIT_END

CALENDAR_START
[Clean schedule with prep notes. If no events, focused job search structure.]
CALENDAR_END

EMAIL_START
[Top 3-5 priority actions. Flag time-sensitive items.]
EMAIL_END

HEALTH_START
[Insert the pre-generated health plan exactly as provided — do not modify.]
HEALTH_END

WELLNESS_START
[2-3 bullet wellness tips — hydration, energy, focus. Do NOT repeat workout or meals.]
WELLNESS_END

SMS_START
Good morning Dory [day] [date]

WEATHER
[one line: temp, condition, what to bring]

WEAR
[one line: specific outfit]

TODAY
[one line per calendar block]

PRIORITIES
[one line per top 3 actions]

HEALTH
[Insert health SMS lines exactly as provided]

WELLNESS
[one line tip]

Max 55 chars per line. No markdown.
SMS_END"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )

    full_text = "\n".join(
        block.text for block in response.content if hasattr(block, "text")
    )

    weather = extract_section(full_text, "WEATHER_START", "WEATHER_END") or "—"
    outfit = extract_section(full_text, "OUTFIT_START", "OUTFIT_END") or "—"
    calendar = extract_section(full_text, "CALENDAR_START", "CALENDAR_END") or calendar_text or "—"
    emails = extract_section(full_text, "EMAIL_START", "EMAIL_END") or "—"
    health = extract_section(full_text, "HEALTH_START", "HEALTH_END") or health_section
    wellness = extract_section(full_text, "WELLNESS_START", "WELLNESS_END") or "—"
    sms = extract_section(full_text, "SMS_START", "SMS_END") or "—"

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

HEALTH

{health}

WELLNESS

{wellness}

---

SMS

{sms}

Have a great day.

"""

    with open("sms.html", "w") as f:
        f.write(content)

    with open("sms-clean.txt", "w") as f:
        f.write(sms)

    print(f"Briefing generated for {today}")
    print(content)


if __name__ == "__main__":
    generate_briefing()
