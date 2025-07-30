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
    cadence_name = data.get("cadence_name")
    memo = data.get("custom_email_template")

# 1. Check if contact exists
response = requests.get(
    "https://api.salesloft.com/v2/people.json",
    params={"email_address": email},
    headers={"Authorization": f"Bearer {SALESLOFT_API_KEY}"}
)
person_data = response.json()

if person_data["data"]:
    person_id = person_data["data"][0]["id"]
    # Update existing contact with memo
    requests.put(
        f"https://api.salesloft.com/v2/people/{person_id}.json",
        json={"custom_fields": {"memo": memo}},
        headers={"Authorization": f"Bearer {SALESLOFT_API_KEY}"}
    )
else:
    # Create new contact
    create_resp = requests.post(
        "https://api.salesloft.com/v2/people.json",
        json={
            "first_name": first_name,
            "last_name": last_name,
            "email_address": email,
            "custom_fields": {"memo": memo}
        },
        headers={"Authorization": f"Bearer {SALESLOFT_API_KEY}"}
    )
    person_id = create_resp.json()["data"]["id"]

# Get cadence ID (by external identifier)
cadence_resp = requests.get(
    "https://api.salesloft.com/v2/cadences.json",
    params={"external_identifier": "rjb0001api"},
    headers={"Authorization": f"Bearer {SALESLOFT_API_KEY}"}
)
cadence_id = cadence_resp.json()["data"][0]["id"]

# Add contact to cadence
requests.post(
    "https://api.salesloft.com/v2/cadence_memberships.json",
    json={"cadence_membership": {"person_id": person_id, "cadence_id": cadence_id}},
    headers={"Authorization": f"Bearer {SALESLOFT_API_KEY}"}
)

# Return minimal response
return jsonify({
    "success": True,
    "message": f"{first_name} {last_name} successfully added to cadence '{cadence_name}'."
})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))