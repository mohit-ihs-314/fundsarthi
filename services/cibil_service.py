import requests
import json
from datetime import datetime, timedelta
import mysql.connector
from utils.otp_helper import verify_otp

# ---------------- DB CONNECTION ----------------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="your_db_name"
    )


HEADERS = {
    "API-Key": "YOUR_KEY",
    "Username": "YOUR_USERNAME",
    "Password": "YOUR_PASSWORD",
    "Content-Type": "application/json"
}


def cleanup_old_records():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        DELETE FROM cibil_reports
        WHERE created_at < NOW() - INTERVAL 30 DAY
    """)

    db.commit()
    cursor.close()
    db.close()

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


# ---------------- CHECK EXISTING ----------------
def get_existing_record(mobile, pan):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT * FROM cibil_reports
        WHERE mobile=%s OR pan=%s
        ORDER BY created_at DESC
        LIMIT 1
    """
    cursor.execute(query, (mobile, pan))
    result = cursor.fetchone()

    cursor.close()
    db.close()

    return result


# ---------------- SAVE RECORD ----------------
def save_record(data, score, pdf_url, full_response):
    db = get_db()
    cursor = db.cursor()

    query = """
        INSERT INTO cibil_reports (mobile, pan, score, pdf_url, response_json)
        VALUES (%s, %s, %s, %s, %s)
    """

    cursor.execute(query, (
        data.get("mobile"),
        data.get("pan"),
        score,
        pdf_url,
        json.dumps(full_response)
    ))

    db.commit()
    cursor.close()
    db.close()


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
    existing = get_existing_record(mobile, pan)

    if existing:
        created_at = existing["created_at"]
        if datetime.now() - created_at < timedelta(days=30):
            return {
                "status": "success",
                "score": existing["score"],
                "pdf_url": existing["pdf_url"],
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
        save_record(data, score, cibil_res.get("file_url"), cibil_res)

        return {
            "status": "success",
            "score": score,
            "pdf_url": cibil_res.get("file_url"),
            "cached": False
        }, 200

    except Exception as e:
        print("API Error:", e)
        return {"status": "error", "message": "API failed"}, 500