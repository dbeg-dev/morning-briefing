"""
Run this once locally to get your Gmail OAuth refresh token.
You'll need a Google Cloud project with the Gmail API enabled.

Steps:
  1. Go to console.cloud.google.com
  2. Create a project (or use an existing one)
  3. Enable the Gmail API
  4. Go to APIs & Services → Credentials → Create Credentials → OAuth client ID
  5. Choose "Desktop app", download the JSON, note the client_id and client_secret
  6. Run: python scripts/get_gmail_token.py
  7. Copy the refresh_token into GitHub Secrets as GOOGLE_REFRESH_TOKEN
     Also add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET as secrets.
"""

import json
import sys
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer


CLIENT_ID     = input("Paste your Google OAuth Client ID: ").strip()
CLIENT_SECRET = input("Paste your Google OAuth Client Secret: ").strip()

SCOPES       = "https://www.googleapis.com/auth/gmail.readonly"
REDIRECT_URI = "http://localhost:8080"

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

print(f"\nOpening browser for Google authorization...")
webbrowser.open(auth_url)
print(f"If it didn't open, visit:\n{auth_url}\n")

auth_code = None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>Authorization complete. You can close this tab.</h2>")

    def log_message(self, *args):
        pass

print("Waiting for authorization (listening on http://localhost:8080)...")
server = HTTPServer(("localhost", 8080), Handler)
server.handle_request()

if not auth_code:
    print("Error: no auth code received.")
    sys.exit(1)

data = urllib.parse.urlencode({
    "code":          auth_code,
    "client_id":     CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri":  REDIRECT_URI,
    "grant_type":    "authorization_code",
}).encode()

req  = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
resp = urllib.request.urlopen(req)
tokens = json.loads(resp.read())

print("\n" + "="*60)
print("SUCCESS — add these three secrets to GitHub:")
print("="*60)
print(f"GOOGLE_CLIENT_ID     = {CLIENT_ID}")
print(f"GOOGLE_CLIENT_SECRET = {CLIENT_SECRET}")
print(f"GOOGLE_REFRESH_TOKEN = {tokens['refresh_token']}")
print("="*60)
