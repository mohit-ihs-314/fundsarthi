import requests
from datetime import datetime, timedelta
from utils.otp_helper import verify_otp
from models.cibil_model import CibilReport
from extensions import db
import json

HEADERS = {
    "API-Key": "8eecf271c85e388bcb2aaac446e0ef74",
    "Username": "dtivratrackfs@gmail.com",
    "Password": "HTQZ8UPD",
    "Content-Type": "application/json"
}


# ---------------- CLEANUP ----------------
def cleanup_old_records():
    expiry_date = datetime.utcnow() - timedelta(days=30)

    CibilReport.query.filter(
        CibilReport.created_at < expiry_date
    ).delete()

    db.session.commit()


# ---------------- PAYLOAD ----------------
def build_payload(data):
    return {
        "merchantId": 38999,
        "firstname": data.get("firstname"),
        "lastname": data.get("lastname"),
        "email": data.get("email"),
        "mobile": data.get("mobile"),
        "dob": data.get("dob"),
        "address": data.get("address"),
        "pinCode": data.get("pincode"),
        "stateCode": int(data.get("stateCode", 0)),
        "pancard": data.get("pan"),
        "consent": "Y"
    }


# ---------------- SCORE ----------------
def extract_score(cibil_res):
    try:
        xml = cibil_res.get("data", {}).get("response", {}).get("xmlJsonResponse", {})
        score_obj = xml.get("score")

        if isinstance(score_obj, dict):
            return int(score_obj.get("bureauScore"))

    except Exception as e:
        print("Score Error:", e)

    return 650


# ---------------- MAIN SERVICE ----------------
def check_cibil_service(data):

    cleanup_old_records()

    mobile = data.get("mobile")
    pan = data.get("pan")
    otp = data.get("otp")

    # OTP VERIFY
    valid, msg = verify_otp(mobile, otp)
    if not valid:
        return {"status": "error", "message": msg}, 400

    # 🔍 CHECK EXISTING
    existing = CibilReport.query.filter(
        (CibilReport.mobile == mobile) | (CibilReport.pan == pan)
    ).order_by(CibilReport.created_at.desc()).first()

    if existing:
        if datetime.utcnow() - existing.created_at < timedelta(days=30):
            return {
                "status": "success",
                "score": existing.score,
                "pdf_url": existing.pdf_url,
                "cached": True,
                "message": "Showing previously fetched report"
            }, 200

    # 🆕 CALL API
    payload = build_payload(data)

    try:
        res = requests.post(
            "https://megmacibil.com/Payout/UApi/check_cibil_api.php",
            json=payload,
            headers=HEADERS,
            timeout=20
        )

        cibil_res = res.json()

        if not cibil_res.get("success"):
            return {"status": "error", "message": "CIBIL failed"}, 400

        score = extract_score(cibil_res)

        # 💾 SAVE
        new_record = CibilReport(
            mobile=mobile,
            pan=pan,
            score=score,
            pdf_url=cibil_res.get("file_url"),
            response_json=cibil_res
        )

        db.session.add(new_record)
        db.session.commit()

        return {
            "status": "success",
            "score": score,
            "pdf_url": cibil_res.get("file_url"),
            "cached": False
        }, 200

    except Exception as e:
        print("API Error:", e)
        return {"status": "error", "message": "API failed"}, 500