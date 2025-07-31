from flask import Flask, request, jsonify
import requests
import os
import datetime
import time

app = Flask(__name__)

SALESLOFT_API_KEY = os.getenv("SALESLOFT_API_KEY")
CUSTOM_FIELD_ID = "8014"
HEADERS = {
    "Authorization": f"Bearer {SALESLOFT_API_KEY}",
    "Content-Type": "application/json"
}
LOG_PATH = "/tmp/upsert-contact.log"


def log_to_file(entry):
    with open(LOG_PATH, "a") as f:
        f.write(f"[{datetime.datetime.utcnow().isoformat()}] {entry}\n\n")


@app.route('/upsert-contact', methods=['POST'])
def upsert_contact():
    data = request.json or {}

    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    email = data.get("email", "").strip().lower()
    memo = data.get("8014", "").strip()
    owner_crm_id = data.get("owner_crm_id")
    account_crm_id = data.get("account_crm_id")
    phone = data.get("phone", "").strip()

    log_to_file(f"Received request data: {data}")

    if not all([first_name, last_name, email, memo]):
        error_msg = "Missing one or more required fields: first_name, last_name, email, custom_email_template"
        log_to_file(error_msg)
        return jsonify({"success": False, "message": error_msg}), 400

    contact_payload = {
        "first_name": first_name,
        "last_name": last_name,
        "email_address": email,
        "custom_fields": {CUSTOM_FIELD_ID: memo}
    }
    if phone:
        contact_payload["phone"] = phone
    if owner_crm_id:
        contact_payload["owner_crm_id"] = owner_crm_id
    if account_crm_id:
        contact_payload["account_crm_id"] = account_crm_id

    log_to_file(f"Prepared payload: {contact_payload}")

    search_resp = requests.get(
        "https://api.salesloft.com/v2/people.json",
        params={"email_address": email},
        headers=HEADERS
    )
    log_to_file(f"Search response: {search_resp.status_code} {search_resp.text}")

    if search_resp.status_code != 200:
        return jsonify({
            "success": False,
            "message": "Failed to search for existing contact",
            "details": search_resp.text
        }), 400

    search_data = search_resp.json()
    person_id = None

    if search_data.get("data"):
        person_id = search_data["data"][0].get("id")
        update_resp = requests.put(
            f"https://api.salesloft.com/v2/people/{person_id}.json",
            json=contact_payload,
            headers=HEADERS
        )
        log_to_file(f"Update response: {update_resp.status_code} {update_resp.text}")

        if update_resp.status_code >= 400:
            return jsonify({
                "success": False,
                "message": "Failed to update contact",
                "details": update_resp.text
            }), 400
    else:
        create_resp = requests.post(
            "https://api.salesloft.com/v2/people.json",
            json=contact_payload,
            headers=HEADERS
        )
        log_to_file(f"Create response: {create_resp.status_code} {create_resp.text}")

        if create_resp.status_code == 202:
            log_to_file("202 Accepted received. Waiting before verifying contact creation...")
            time.sleep(3)
            verify_resp = requests.get(
                "https://api.salesloft.com/v2/people.json",
                headers=HEADERS,
                params={"email_address": email}
            )
            log_to_file(f"Verification response after 202: {verify_resp.status_code} {verify_resp.text}")
            verify_data = verify_resp.json().get("data", [])
            if verify_data:
                person_id = verify_data[0].get("id")
            else:
                return jsonify({
                    "success": False,
                    "message": "Contact creation was accepted (202) but couldn't be verified.",
                    "details": verify_resp.text
                }), 500
        elif create_resp.status_code >= 400:
            return jsonify({
                "success": False,
                "message": "Failed to create contact",
                "details": create_resp.text
            }), 400
        else:
            create_data = create_resp.json()
            person_id = create_data.get("data", {}).get("id")

            if not person_id:
                log_to_file("No person_id returned, attempting recheck...")
                recheck_resp = requests.get(
                    "https://api.salesloft.com/v2/people.json",
                    params={"email_address": email},
                    headers=HEADERS
                )
                log_to_file(f"Recheck response: {recheck_resp.status_code} {recheck_resp.text}")
                if recheck_resp.status_code == 200:
                    recheck_data = recheck_resp.json().get("data", [])
                    if recheck_data:
                        person_id = recheck_data[0].get("id")

    log_to_file(f"Final result: person_id = {person_id}")

    return jsonify({
        "success": True,
        "message": f"Contact '{first_name} {last_name}' processed successfully.",
        "person_id": person_id,
        "email": email,
        "created_payload": contact_payload
    })


@app.route('/logs', methods=['GET'])
def view_logs():
    try:
        with open(LOG_PATH, "r") as f:
            content = f.read()
        return f"<pre>{content}</pre>", 200
    except FileNotFoundError:
        return "Log file not found.", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))
