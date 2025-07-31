import requests
import os

# === CONFIGURATION ===
API_KEY = os.getenv("SALESLOFT_API_KEY") or "YOUR_SALESLOFT_API_KEY_HERE"
BASE_URL = "https://api.salesloft.com/v2/people.json"

# === MINIMAL CONTACT PAYLOAD ===
payload = {
    "first_name": "Richard",
    "last_name": "Testcase",
    "email_address": "salesloft.testcase@example.com"
}

# === HEADERS ===
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# === MAKE API REQUEST ===
print("Sending minimal contact creation request...")

response = requests.post(BASE_URL, json=payload, headers=headers)

print(f"Status Code: {response.status_code}")
print(f"Response Body: {response.text}")

# === VERIFY RESULT ===
if response.status_code in [200, 201]:
    print("✅ Contact created successfully.")
elif response.status_code == 202:
    print("⚠️ Contact creation accepted asynchronously. Check Salesloft manually to confirm creation.")
else:
    print("❌ Contact creation failed.")
