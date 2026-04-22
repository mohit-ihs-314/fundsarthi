import requests
import json
from utils.otp_helper import verify_otp

HEADERS = {
    "API-Key": "8eecf271c85e388bcb2aaac446e0ef74",
    "Username": "dtivratrackfs@gmail.com",
    "Password": "HTQZ8UPD",
    "Content-Type": "application/json"
}


# ---------------------------
# BUILD PAYLOAD
# ---------------------------
def build_payload(data):
    return {
        "merchantId": 38999,
        "firstname": data.get("firstname"),
        "lastname": data.get("lastname"),
        "email": data.get("email"),
        "mobile": data.get("mobile"),
        "dob": data.get("dob"),  # DDMMYYYY
        "address": data.get("address"),
        "pinCode": data.get("pincode"),
        "stateCode": int(data.get("stateCode", 0)),
        "pancard": data.get("pan"),
        "consent": "Y"
    }


# ---------------------------
# EXTRACT SCORE (FIXED)
# ---------------------------
def extract_score(cibil_res):
    try:
        response = cibil_res.get("data", {}).get("response", {})

        # 🔥 CORRECT PATH (your API)
        xml = response.get("xmlJsonResponse", {})
        score_obj = xml.get("score")

        print("XML SCORE OBJECT:", score_obj)

        if isinstance(score_obj, dict):
            bureau_score = score_obj.get("bureauScore")
            print("✅ FINAL SCORE:", bureau_score)
            return int(bureau_score)

        print("⚠️ Score not found in xmlJsonResponse")

    except Exception as e:
        print("❌ SCORE ERROR:", str(e))

    return 650


# ---------------------------
# MAIN SERVICE
# ---------------------------
def check_cibil_service(data):
    mobile = data.get("mobile")
    otp = data.get("otp")

    # 🔐 OTP VERIFY
    valid, msg = verify_otp(mobile, otp)
    if not valid:
        return {"status": "error", "message": msg}, 400

    payload = build_payload(data)
    # print("📦 FINAL PAYLOAD:", payload)

    try:
        res = requests.post(
            "https://megmacibil.com/Payout/UApi/check_cibil_api.php",
            json=payload,
            headers=HEADERS,
            timeout=20
        )

        # print("🌐 STATUS CODE:", res.status_code)
        # print("📩 RAW RESPONSE:", res.text)

        cibil_res = res.json()

        # ❌ API FAILURE
        if not cibil_res.get("success"):
            return {
                "status": "error",
                "message": cibil_res.get("message", "CIBIL failed")
            }, 400

        # 🎯 EXTRACT SCORE
        score = extract_score(cibil_res)

        return {
            "status": "success",
            "score": score,
            "pdf_url": cibil_res.get("file_url")
        }, 200

    except requests.exceptions.Timeout:
        print("⏱ TIMEOUT ERROR")
        return {"status": "error", "message": "CIBIL API timeout"}, 500

    except requests.exceptions.RequestException as e:
        print("🌐 REQUEST ERROR:", str(e))
        return {"status": "error", "message": "Request failed"}, 500

    except Exception as e:
        print("🔥 API ERROR:", str(e))
        return {"status": "error", "message": "CIBIL API failed"}, 500