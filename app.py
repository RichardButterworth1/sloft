from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SALESLOFT_API_KEY = os.getenv("SALESLOFT_API_KEY")
CUSTOM_FIELD_ID = "custom email template"  # Exact label in Salesloft
HEADERS = {
    "Authorization": f"Bearer {SALESLOFT_API_KEY}",
    "Content-Type": "application/json"
}

@app.route('/upsert-contact', methods=['POST'])
def upsert_contact():
    data = request.json or {}

    # Extract and sanitize fields
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    email = data.get("email", "").strip().lower()
    memo = data.get("custom_email_template", "").strip()
    owner_crm_id = data.get("owner_crm_id")
    account_crm_id = data.get("account_crm_id")
    phone = data.get("phone", "").strip()

    # Validate required fields
    if not all([first_name, last_name, email, memo]):
        return jsonify({
            "success": False,
            "message": "Missing one or more required fields: first_name, last_name, email, custom_email_template"
        }), 400

    # Build contact payload
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

    # Step 1: Check if person exists
    search_resp = requests.get(
        "https://api.salesloft.com/v2/people.json",
        params={"email_address": email},
        headers=HEADERS
    )
    if search_resp.status_code != 200:
        return jsonify({
            "success": False,
            "message": "Failed to search for existing contact",
            "details": search_resp.text
        }), 400

    search_data = search_resp.json()
    person_id = None

    # Step 2: Update if exists, else create
    if search_data.get("data"):
        person_id = search_data["data"][0].get("id")
        update_resp = requests.put(
            f"https://api.salesloft.com/v2/people/{person_id}.json",
            json=contact_payload,
            headers=HEADERS
        )
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
        if create_resp.status_code >= 400:
            return jsonify({
                "success": False,
                "message": "Failed to create contact",
                "details": create_resp.text
            }), 400

        create_data = create_resp.json()
        person_id = create_data.get("data", {}).get("id")

        # Fallback: if no ID returned, recheck
        if not person_id:
            recheck_resp = requests.get(
                "https://api.salesloft.com/v2/people.json",
                params={"email_address": email},
                headers=HEADERS
            )
            if recheck_resp.status_code == 200:
                recheck_data = recheck_resp.json().get("data", [])
                if recheck_data:
                    person_id = recheck_data[0].get("id")

    return jsonify({
        "success": True,
        "message": f"Contact '{first_name} {last_name}' processed successfully.",
        "person_id": person_id
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))
