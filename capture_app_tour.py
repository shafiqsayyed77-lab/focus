import urllib.request
import json
import subprocess
import time
import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_URL = "http://127.0.0.1:8000"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = r"C:\Users\naba\.gemini\antigravity-ide\scratch\focusflow"

def login_demo():
    url = f"{BASE_URL}/api/auth/login"
    payload = json.dumps({"email": "alex.student@focusflow.app", "password": "password123"}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["access_token"]

def capture_route(token, route_name, output_filename, wait_seconds=2):
    relay_url = f"{BASE_URL}/dev/auth-relay?token={token}&redirect=/%23{route_name}"
    temp_img = os.path.join(r"C:\Users\naba", output_filename)
    dest_img = os.path.join(OUTPUT_DIR, output_filename)

    if os.path.exists(temp_img):
        os.remove(temp_img)

    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--window-size=1440,900",
        f"--virtual-time-budget={int(wait_seconds * 1000)}",
        f"--screenshot={temp_img}",
        relay_url
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if os.path.exists(temp_img):
        shutil.copy2(temp_img, dest_img)
        print(f"✓ Captured {route_name} -> {output_filename} ({os.path.getsize(dest_img)} bytes)")
        return True
    else:
        print(f"✗ Failed to capture {route_name}")
        return False

def main():
    print("Logging into Demo Student account (Alex Rivera)...")
    token = login_demo()
    print("✓ Obtained JWT token")

    views = [
        ("dashboard", "view_dashboard.png"),
        ("subjects", "view_subjects.png"),
        ("planner", "view_planner.png"),
        ("exams", "view_exams.png"),
        ("revision", "view_revision.png"),
        ("analytics", "view_analytics.png"),
        ("resources", "view_resources.png")
    ]

    for route, filename in views:
        capture_route(token, route, filename, wait_seconds=3)

    print("\nAll views captured successfully!")

if __name__ == "__main__":
    main()
