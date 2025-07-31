import os
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SALESLOFT_API_BASE = os.environ.get("SALESLOFT_API_BASE", "https://api.salesloft.com")
GLOBAL_API_KEY = os.environ.get("SALESLOFT_API_KEY")

def get_auth_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

def simple_email_valid(email: str) -> bool:
    if "@" not in email:
        return False
    local, _, domain = email.partition("@")
    if not local or not domain or "." not in domain:
        return False
    return True

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "salesloft-contact-enroller"})

@app.route("/create_contact_and_enroll", methods=["POST"])
def create_contact_and_enroll():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body."}), 400

    # Required fields
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    cadence_id = data.get("cadence_id")

    if not first_name or not last_name or not email or cadence_id is None:
        return jsonify({
            "error": "Missing required field(s). Required: first_name, last_name, email, cadence_id."
        }), 400

    if not isinstance(cadence_id, int) or cadence_id <= 0:
        return jsonify({"error": "cadence_id must be a positive integer."}), 400

    if not simple_email_valid(email):
        return jsonify({"error": "Invalid email format."}), 400

    website = data.get("website")
    custom_email_template = data.get("custom_email_template")

    api_key = GLOBAL_API_KEY or request.headers.get("X-Salesloft-Api-Key")
    if not api_key:
        return jsonify({"error": "Salesloft API key not provided via environment or X-Salesloft-Api-Key header."}), 500

    headers = get_auth_headers(api_key)

    # Build contact creation payload
    contact_body = {
        "first_name": first_name,
        "last_name": last_name,
        "email_address": email,
    }
    if website:
        contact_body["person_company_website"] = website
    if custom_email_template is not None:
        contact_body["custom_fields"] = {"custom email template": custom_email_template}

    person_url = f"{SALESLOFT_API_BASE}/v2/people.json"
    try:
        resp = requests_post_with_logging(person_url, headers, contact_body)
    except Exception as e:
        logger.exception("Error creating person in Salesloft")
        return jsonify({"error": "Failed to create person in Salesloft.", "details": str(e)}), 502

    if not resp.ok:
        logger.error("Person creation failed: %s", resp.text)
        return jsonify({
            "error": "Failed to create person in Salesloft.",
            "response_text": resp.text
        }), resp.status_code

    person_data = resp.json()
    person_id = person_data.get("data", {}).get("id")
    if not person_id:
        logger.error("No person ID in response: %s", person_data)
        return jsonify({
            "error": "Salesloft returned no person ID.",
            "person_creation_response": person_data
        }), 500

    # Enroll in cadence
    cadence_url = f"{SALESLOFT_API_BASE}/v2/cadence_memberships.json"
    enroll_body = {"person_id": person_id, "cadence_id": cadence_id}
    try:
        enroll_resp = requests_post_with_logging(cadence_url, headers, enroll_body)
    except Exception as e:
        logger.exception("Error enrolling in cadence")
        return jsonify({
            "message": "Person created but failed to enroll in cadence.",
            "person": person_data,
            "error": str(e)
        }), 502

    if not enroll_resp.ok:
        logger.error("Cadence enrollment failed: %s", enroll_resp.text)
        return jsonify({
            "message": "Person created but failed to enroll in cadence.",
            "person": person_data,
            "enroll_response_text": enroll_resp.text
        }), enroll_resp.status_code

    enrollment_data = enroll_resp.json()

    return jsonify({
        "contact_creation": person_data,
        "cadence_enrollment": enrollment_data
    }), 200


def requests_post_with_logging(url: str, headers: dict, payload: dict):
    import requests
    logger.info("POST %s payload=%s", url, payload)
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    logger.info("Response status %s", response.status_code)
    return response


if __name__ == "__main__":
    # For local debugging; Render will use gunicorn
    from flask import _app_ctx_stack
    import requests  # ensure available
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
