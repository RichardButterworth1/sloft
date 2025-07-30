from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)
SALESLOFT_API_KEY = os.getenv("SALESLOFT_API_KEY")

@app.route('/add-to-cadence', methods=['POST'])
def add_to_cadence():
    try:
        data = request.json
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        memo = data.get("custom_email_template")
        cadence_name = data.get("cadence_name")
        cadence_id = data.get("cadence_id")

        if not all([first_name, last_name, email, memo]):
            return jsonify({"success": False, "message": "Missing required fields."}), 400

        headers = {
            "Authorization": f"Bearer {SALESLOFT_API_KEY}",
            "Content-Type": "application/json"
        }

        # Check if contact exists
        person_id = None
        search_resp = requests.get(
            "https://api.salesloft.com/v2/people.json",
            params={"email_address": email},
            headers=headers
        )

        if search_resp.status_code >= 400:
            return jsonify({"success": False, "message": "Failed to search for contact", "details": search_resp.text}), 400

        people_data = search_resp.json().get("data", [])

        if people_data:
            person_id = people_data[0]["id"]
            update_resp = requests.put(
                f"https://api.salesloft.com/v2/people/{person_id}.json",
                json={"custom_fields": {"custom email text": memo}},
                headers=headers
            )
            if update_resp.status_code >= 400:
                return jsonify({"success": False, "message": "Failed to update contact", "details": update_resp.text}), 400
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
                return jsonify({"success": False, "message": "Failed to create contact", "details": create_resp.text}), 400

            created = create_resp.json()
            person_id = created.get("data", {}).get("id")
            if not person_id:
                return jsonify({"success": False, "message": "Contact created but no ID returned", "details": created}), 500

        # Resolve cadence_id if only name was provided
        if not cadence_id:
            if not cadence_name:
                return jsonify({"success": False, "message": "Must provide cadence_id or cadence_name"}), 400

            cadence_resp = requests.get(
                "https://api.salesloft.com/v2/cadences.json",
                params={"external_identifier": cadence_name},
                headers=headers
            )
            if cadence_resp.status_code >= 400:
                return jsonify({"success": False, "message": "Failed to retrieve cadence", "details": cadence_resp.text}), 400

            cadence_data = cadence_resp.json().get("data", [])
            if not cadence_data:
                return jsonify({"success": False, "message": f"Cadence '{cadence_name}' not found"}), 404

            cadence_id = cadence_data[0]["id"]

        # Enroll contact into cadence
        enroll_resp = requests.post(
            "https://api.salesloft.com/v2/cadence_memberships.json",
            json={
                "cadence_membership": {
                    "person_id": person_id,
                    "cadence_id": cadence_id,
                    "state": "active"
                }
            },
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

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Unhandled server error",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))
