from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SALESLOFT_API_KEY = os.getenv("SALESLOFT_API_KEY")
CUSTOM_FIELD_ID = "custom email template"

@app.route('/add-to-cadence', methods=['POST'])
def add_to_cadence():
    data = request.json

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    memo = data.get("custom_email_template")
    cadence_id = data.get("cadence_id")
    owner_crm_id = data.get("owner_crm_id")
    account_crm_id = data.get("account_crm_id")
    phone = data.get("phone")

    if not all([first_name, last_name, email, memo, cadence_id]):
        return jsonify({
            "success": False,
            "message": "Missing required fields."
        }), 400

    headers = {
        "Authorization": f"Bearer {SALESLOFT_API_KEY}",
        "Content-Type": "application/json"
    }

    # Step 1: Search for contact by email
    search_resp = requests.get(
        "https://api.salesloft.com/v2/people.json",
        params={"email_address": email},
        headers=headers
    )
    if search_resp.status_code != 200:
        return jsonify({
            "success": False,
            "message": "Failed to search for contact",
            "details": search_resp.text
        }), 400

    search_data = search_resp.json()
    person_id = None

    contact_payload = {
        "first_name": first_name,
        "last_name": last_name,
        "email_address": email,
        "custom_fields": {
            CUSTOM_FIELD_ID: memo
        },
        "owner_crm_id": owner_crm_id,
        "account_crm_id": account_crm_id,
        "phone": phone
    }

    if search_data.get("data"):
        person_id = search_data["data"][0].get("id")
        update_resp = requests.put(
            f"https://api.salesloft.com/v2/people/{person_id}.json",
            json=contact_payload,
            headers=headers
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
            headers=headers
        )
        if create_resp.status_code >= 400:
            return jsonify({
                "success": False,
                "message": "Failed to create contact",
                "details": create_resp.text
            }), 400
        person_id = create_resp.json().get("data", {}).get("id")

    if not person_id:
        return jsonify({
            "success": False,
            "message": "Person ID missing after contact creation or update",
        }), 400

    # Step 2: Enroll in cadence
    enroll_payload = {
        "cadence_membership": {
            "person_id": person_id,
            "cadence_id": cadence_id
        }
    }
    enroll_resp = requests.post(
        "https://api.salesloft.com/v2/cadence_memberships.json",
        json=enroll_payload,
        headers=headers
    )

    if enroll_resp.status_code >= 400:
        return jsonify({
            "success": False,
            "message": "Failed to enroll contact in cadence",
            "details": enroll_resp.text
        }), 400

    return jsonify({
        "success": True,
        "message": f"{first_name} {last_name} successfully added to cadence ID {cadence_id}."
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))
