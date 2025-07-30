from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SALESLOFT_API_KEY = os.getenv("SALESLOFT_API_KEY")
CUSTOM_FIELD_ID = "custom email template"  # ID for 'custom email template'

@app.route('/add-to-cadence', methods=['POST'])
def add_to_cadence():
    data = request.json

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    memo = data.get("custom_email_template")
    cadence_id = data.get("cadence_id")

    if not all([first_name, last_name, email, memo, cadence_id]):
        return jsonify({
            "success": False,
            "message": "Missing required fields."
        }), 400

    headers = {
        "Authorization": f"Bearer {SALESLOFT_API_KEY}",
        "Content-Type": "application/json"
    }

    # Step 1: Check if contact exists
    search_resp = requests.get(
        "https://api.salesloft.com/v2/people.json",
        params={"email_address": email},
        headers=headers
    )
    if search_resp.status_code != 200:
        return jsonify({
            "success": False,
            "message": "Failed to search for existing contact",
            "details": search_resp.json()
        }), 400

    search_data = search_resp.json()
    if search_data.get("data"):
        person_id = search_data["data"][0]["id"]
    else:
        # Step 2: Create contact
        create_resp = requests.post(
            "https://api.salesloft.com/v2/people.json",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email_address": email
            },
            headers=headers
        )
        if create_resp.status_code >= 400:
            return jsonify({
                "success": False,
                "message": "Failed to create contact",
                "details": create_resp.json()
            }), 400

        person_id = create_resp.json().get("data", {}).get("id")
        if not person_id:
            return jsonify({
                "success": False,
                "message": "No person ID returned after creation",
                "details": create_resp.json()
            }), 400

    # Step 3: Update custom field
    update_resp = requests.put(
        f"https://api.salesloft.com/v2/people/{person_id}.json",
        json={"custom_fields": {CUSTOM_FIELD_ID: memo}},
        headers=headers
    )
    if update_resp.status_code >= 400:
        return jsonify({
            "success": False,
            "message": "Failed to update custom field",
            "details": update_resp.text
        }), 400

    # Step 4: Enroll in cadence
    enroll_resp = requests.post(
        "https://api.salesloft.com/v2/cadence_memberships.json",
        json={"cadence_membership": {"person_id": person_id, "cadence_id": cadence_id}},
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
        "message": f"{first_name} {last_name} successfully added to cadence ID '{cadence_id}'."
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))
