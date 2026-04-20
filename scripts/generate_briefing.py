import anthropic
import os
from datetime import datetime
from zoneinfo import ZoneInfo


def extract_section(text, start_tag, end_tag):
    start = text.find(start_tag)
    end = text.find(end_tag)
    if start == -1 or end == -1:
        return None
    return text[start + len(start_tag):end].strip()


def generate_briefing():
    client = anthropic.Anthropic()

    now = datetime.now(ZoneInfo("America/New_York"))
    today = now.strftime("%A, %B %-d, %Y")
    time_str = now.strftime("%I:%M %p")

    prompt = f"""Generate Dory's morning briefing for {today} at {time_str}. Dory lives in Manhattan, NYC — busy professional, active job search (SVP role discussions at Birthright Israel Foundation, Fi, Kindred), young family, interests in fashion/arts/culture.

Use web search to get TODAY's live Manhattan weather forecast.

Generate these sections with EXACT delimiters:

WEATHER_START
[2-3 sentences: current temp, conditions, precipitation, walking suitability]
WEATHER_END

OUTFIT_START
[3-4 sentences: specific outfit for the weather + professional day. Reference her brands: Scanlan Theodore, Ferragamo, On Running, Lululemon, Ralph Lauren, Theory, David Yurman. Be specific — colors, layers, shoes.]
OUTFIT_END

EMAIL_START
[Bullet list of priority follow-ups:
- Ruvym Gilman / Birthright Israel Foundation: SVP role status
- Vivian Chan / Austen Riggs: LFE May 1-3 registration
- Elissa Ganz: pending reply
- Victoria Valenti (Fi) and Somer Reznick (Kindred): check in]
EMAIL_END

WELLNESS_START
[3-4 bullet wellness tips for the day — hydration, movement, energy, focus]
WELLNESS_END"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )

    full_text = "\n".join(
        block.text for block in response.content if hasattr(block, "text")
    )

    weather  = extract_section(full_text, "WEATHER_START",  "WEATHER_END")  or "—"
    outfit   = extract_section(full_text, "OUTFIT_START",   "OUTFIT_END")   or "—"
    emails   = extract_section(full_text, "EMAIL_START",    "EMAIL_END")    or "—"
    wellness = extract_section(full_text, "WELLNESS_START", "WELLNESS_END") or "—"

    sms_content = f"""GOOD MORNING DORY
{today}

WEATHER
{weather}

WEAR TODAY
{outfit}

PRIORITIES
{emails}

WELLNESS
{wellness}

Have a great day.
"""

    with open("sms.html", "w") as f:
        f.write(sms_content)

    print(f"Briefing generated for {today}")
    print(sms_content)


if __name__ == "__main__":
    generate_briefing()
