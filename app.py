from flask import Flask, request, jsonify
import requests
import os
import datetime

app = Flask(__name__)
LOG_FILE = "/tmp/simple-contact.log"

SALESLOFT_API_KEY = os.getenv("SALESLOFT_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {SALESLOFT_API_KEY}",
    "Content-Type": "application/json"
}
CADENCE_ID = 102094  # Hardcoded cadence ID

def log(message):
    timestamp = datetime.datetime.utcnow().isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

@app.route("/simple-upsert", methods=["POST"])
def simple_upsert():
    data = request.json or {}
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    email = data.get("email", "").strip().lower()

    if not (first_name and last_name and email):
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "email_address": email,
        "person_company_website": "http://example.com"
    }

    log(f"Attempting to create contact with payload: {payload}")

    response = requests.post(
        "https://api.salesloft.com/v2/people.json",
        headers=HEADERS,
        json=payload
    )

    log(f"Salesloft response: {response.status_code} {response.text}")

    if response.status_code in [200, 201]:
        contact_data = response.json().get("data", {})
        return jsonify({
            "success": True,
            "message": "Contact created.",
            "person_id": contact_data.get("id"),
            "raw_response": contact_data
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": "Failed to create contact.",
            "status_code": response.status_code,
            "error": response.text
        }), response.status_code

@app.route("/simple-upsert-and-enroll", methods=["POST"])
def upsert_and_enroll():
    data = request.json or {}
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    email = data.get("email", "").strip().lower()

    if not (first_name and last_name and email):
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "email_address": email,
        "person_company_website": "http://example.com"
    }

    log(f"Upsert-and-enroll payload: {payload}")

    response = requests.post(
        "https://api.salesloft.com/v2/people.json",
        headers=HEADERS,
        json=payload
    )

    log(f"Create contact response: {response.status_code} {response.text}")

    if response.status_code not in [200, 201]:
        return jsonify({
            "success": False,
            "message": "Failed to create contact.",
            "details": response.text
        }), response.status_code

    contact_id = response.json().get("data", {}).get("id")

    if not contact_id:
        return jsonify({
            "success": False,
            "message": "Contact creation succeeded but no ID returned.",
            "details": response.text
        }), 500

    enroll_payload = {
        "cadence_id": CADENCE_ID,
        "recipient_id": contact_id
    }

    enroll_resp = requests.post(
        "https://api.salesloft.com/v2/cadence_memberships.json",
        headers=HEADERS,
        json=enroll_payload
    )

    log(f"Enroll response: {enroll_resp.status_code} {enroll_resp.text}")

    if enroll_resp.status_code not in [200, 201]:
        return jsonify({
            "success": False,
            "message": "Contact created but failed to enroll in cadence.",
            "details": enroll_resp.text
        }), enroll_resp.status_code

    return jsonify({
        "success": True,
        "message": "Contact created and enrolled in cadence.",
        "person_id": contact_id
    })

@app.route("/logs", methods=["GET"])
def simple_log():
    try:
        with open(LOG_FILE, "r") as f:
            return f"<pre>{f.read()}</pre>"
    except FileNotFoundError:
        return "Log file not found.", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
