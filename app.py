from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SALESLOFT_API_KEY = os.getenv("SALESLOFT_API_KEY")

@app.route('/add-to-cadence', methods=['POST'])
def add_to_cadence():
    data = request.json

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    cadence_name = rjb0001api
    memo = data.get("custom_email_template")

    headers = {
        "Authorization": f"Bearer {SALESLOFT_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.get(
        "https://api.salesloft.com/v2/people.json",
        params={"email_address": email},
        headers=headers
    )
    person_data = response.json()

    if person_data.get("data"):
        person_id = person_data["data"][0]["id"]
        update_resp = requests.put(
            f"https://api.salesloft.com/v2/people/{person_id}.json",
            json={"custom_fields": {"custom email text": memo}},
            headers=headers
        )
    else:
        create_resp = requests.post(
            "https://api.salesloft.com/v2/people.json",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email_address": email,
                "custom_fields": {"custom email text": memo}
            },
            headers=headers
        )

        if create_resp.status_code >= 400:
            return jsonify({
                "success": False,
                "message": "Failed to create contact",
                "salesloft_response": create_resp.json()
            }), 400

        person_id = create_resp.json().get("data", {}).get("id")

        if not person_id:
            return jsonify({
                "success": False,
                "message": "No person ID returned after creation",
                "salesloft_response": create_resp.json()
            }), 400

    cadence_resp = requests.get(
        "https://api.salesloft.com/v2/cadences.json",
        params={"external_identifier": "rjb0001api"},
        headers=headers
    )

    if cadence_resp.status_code >= 400:
        return jsonify({
            "success": False,
            "message": "Failed to fetch cadence",
            "salesloft_response": cadence_resp.json()
        }), 400

    cadence_data = cadence_resp.json().get("data", [])
    if not cadence_data:
        return jsonify({
            "success": False,
            "message": f"Cadence '{cadence_name}' not found"
        }), 404

    cadence_id = cadence_data[0]["id"]

    enroll_resp = requests.post(
        "https://api.salesloft.com/v2/cadence_memberships.json",
        json={"cadence_membership": {"person_id": person_id, "cadence_id": cadence_id}},
        headers=headers
    )

    if enroll_resp.status_code >= 400:
        return jsonify({
            "success": False,
            "message": "Failed to enroll contact in cadence",
            "salesloft_response": enroll_resp.json()
        }), 400

    return jsonify({
        "success": True,
        "message": f"{first_name} {last_name} successfully added to cadence '{cadence_name}'."
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))
