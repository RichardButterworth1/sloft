#!/usr/bin/env python3
"""
app.py — Lightweight FastAPI service to:
  1. Create a Salesloft contact with a custom field ("custom email template")
  2. Enroll that contact into a cadence

Expected environment variables (for Render.com you can set these in the dashboard):
  - SALESLOFT_API_KEY : Your Salesloft bearer token (e.g. v2_ak_...)
  - (Optional) SALESLOFT_API_BASE : Defaults to https://api.salesloft.com

You can also override the API key per-request by supplying header:
  X-Salesloft-Api-Key: <your key>
"""

import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr, AnyUrl, Field
import requests
from fastapi.middleware.cors import CORSMiddleware

# ----------------------
# Models
# ----------------------
class ContactPayload(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    website: Optional[AnyUrl] = None
    custom_email_template: Optional[str] = None
    cadence_id: int = Field(..., gt=0, description="ID of cadence to enroll the contact into")


# ----------------------
# App setup
# ----------------------
app = FastAPI(title="Salesloft Contact + Cadence Enroller")

# Optional: enable CORS if needed (adjust origins as appropriate)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in production, lock this down to your frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SALESLOFT_API_BASE = os.environ.get("SALESLOFT_API_BASE", "https://api.salesloft.com")
GLOBAL_API_KEY = os.environ.get("SALESLOFT_API_KEY")  # fallback if not provided per-request

# ----------------------
# Helpers
# ----------------------
def get_auth_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


# ----------------------
# Endpoints
# ----------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "salesloft-contact-enroller"}


@app.post("/create_contact_and_enroll")
def create_contact_and_enroll(payload: ContactPayload, request: Request):
    """
    Expects JSON body with fields:
      first_name, last_name, email, cadence_id
    Optional:
      website, custom_email_template

    Returns combined response of contact creation and cadence enrollment.
    """
    # Determine API key (env var or per-request override)
    api_key = GLOBAL_API_KEY or request.headers.get("X-Salesloft-Api-Key")
    if not api_key:
        raise HTTPException(status_code=500, detail="Salesloft API key not provided via environment or header.")

    headers = get_auth_headers(api_key)

    # Build contact creation payload
    contact_body = {
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "email_address": payload.email,
    }
    if payload.website:
        contact_body["person_company_website"] = str(payload.website)
    if payload.custom_email_template is not None:
        contact_body["custom_fields"] = {"custom email template": payload.custom_email_template}

    person_url = f"{SALESLOFT_API_BASE}/v2/people.json"
    try:
        resp = requests.post(person_url, headers=headers, json=contact_body, timeout=15)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error contacting Salesloft person API: {str(e)}")

    if not resp.ok:
        raise HTTPException(
            status_code=resp.status_code,
            detail={
                "message": "Failed to create person in Salesloft.",
                "response_text": resp.text,
                "status_code": resp.status_code,
            },
        )

    person_data = resp.json()
    person_id = None
    try:
        person_id = person_data["data"]["id"]
    except (KeyError, TypeError):
        raise HTTPException(status_code=500, detail=f"Unexpected person creation response shape: {person_data}")

    if not person_id:
        raise HTTPException(status_code=500, detail="Salesloft returned empty person ID.")

    # Enroll in cadence
    cadence_url = f"{SALESLOFT_API_BASE}/v2/cadence_memberships.json"
    enroll_body = {"person_id": person_id, "cadence_id": payload.cadence_id}

    try:
        enroll_resp = requests.post(cadence_url, headers=headers, json=enroll_body, timeout=15)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error contacting Salesloft cadence API: {str(e)}")

    if not enroll_resp.ok:
        # Surface both creation and failure to enroll
        raise HTTPException(
            status_code=enroll_resp.status_code,
            detail={
                "message": "Person created but failed to enroll in cadence.",
                "person": person_data,
                "enroll_response_text": enroll_resp.text,
                "status_code": enroll_resp.status_code,
            },
        )

    enrollment_data = enroll_resp.json()

    return {
        "contact_creation": person_data,
        "cadence_enrollment": enrollment_data,
    }


# ----------------------
# Entry point for running locally (Render will typically invoke via `gunicorn app:app` or similar)
# ----------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=False)
