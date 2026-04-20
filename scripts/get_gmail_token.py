"""
Run this once to get your Gmail OAuth refresh token.
No local server needed — just copy a URL from your browser.

Prerequisites:
  1. console.cloud.google.com → create a project
  2. Enable the Gmail API
  3. APIs & Services → Credentials → Create OAuth Client ID → Desktop app
  4. Note the Client ID and Client Secret
  5. Run: python3 scripts/get_gmail_token.py
"""

import json
import urllib.parse
import urllib.request

CLIENT_ID     = input("Paste your Google OAuth Client ID: ").strip()
CLIENT_SECRET = input("Paste your Google OAuth Client Secret: ").strip()

REDIRECT_URI = "http://localhost:8080"
SCOPES       = "https://www.googleapis.com/auth/gmail.readonly"

auth_url = (
    "https://accounts.google.com/o/oauth2/v2/auth?"
    + urllib.parse.urlencode({
        "client_id":     CLIENT_ID,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         SCOPES,
        "access_type":   "offline",
        "prompt":        "consent",
    })
)

print("\n" + "="*60)
print("STEP 1: Open this URL in your browser:")
print("="*60)
print(auth_url)
print("="*60)
print("\nSign in with your Gmail account and click Allow.")
print("The browser will then show a connection error — that's OK.")
print("\nSTEP 2: Copy the full URL from your browser's address bar")
print("and paste it below (it starts with http://localhost:8080/?code=...)\n")

redirect_url = input("Paste the full redirect URL here: ").strip()
params = urllib.parse.parse_qs(urllib.parse.urlparse(redirect_url).query)
auth_code = params.get("code", [None])[0]

if not auth_code:
    print("Error: could not find code in URL. Make sure you copied the full address bar URL.")
    exit(1)

data = urllib.parse.urlencode({
    "code":          auth_code,
    "client_id":     CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri":  REDIRECT_URI,
    "grant_type":    "authorization_code",
}).encode()

req    = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
resp   = urllib.request.urlopen(req)
tokens = json.loads(resp.read())

print("\n" + "="*60)
print("SUCCESS \u2014 add these three secrets to GitHub:")
print("="*60)
print(f"GOOGLE_CLIENT_ID     = {CLIENT_ID}")
print(f"GOOGLE_CLIENT_SECRET = {CLIENT_SECRET}")
print(f"GOOGLE_REFRESH_TOKEN = {tokens['refresh_token']}")
print("="*60)
