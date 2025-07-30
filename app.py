from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SALESLOFT_API_KEY = os.getenv("SALESLOFT_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {SALESLOFT_API_KEY}",
    "Content-Type": "application/json"
}

@app.route("/add-to-cadence", methods=["POST"])
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

    # Step 1: Check if person exists
    resp = requests.get(
        "https://api.salesloft.com/v2/people.json",
        params={"email_address": email},
        headers=HEADERS
    )
    resp_data = resp.json()
    person_data = resp_data.get("data", [])

    if person_data:
        person_id = person_data[0]["id"]
    else:
        # Step 2: Create person
        create_resp = requests.post(
            "https://api.salesloft.com/v2/people.json",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email_address": email
            },
            headers=HEADERS
        )

        if create_resp.status_code >= 400:
            return jsonify({
                "success": False,
                "message": "Failed to create contact",
                "salesloft_response": create_resp.text
            }), 400

        person_id = create_resp.json()["data"]["id"]

    # Step 3: Update memo custom field (ID 8014)
    update_resp = requests.put(
        f"https://api.salesloft.com/v2/people/{person_id}.json",
        json={
            "custom_fields": {
                "8014": memo
            }
        },
        headers=HEADERS
    )

    if update_resp.status_code >= 400:
        return jsonify({
            "success": False,
            "message": "Failed to update contact",
            "details": update_resp.text
        }), 400

    # Step 4: Enroll in cadence
    enroll_resp = requests.post(
        "https://api.salesloft.com/v2/cadence_memberships.json",
        json={
            "cadence_membership": {
                "person_id": person_id,
                "cadence_id": cadence_id
            }
        },
        headers=HEADERS
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
