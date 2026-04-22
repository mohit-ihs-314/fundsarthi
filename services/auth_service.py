from utils.otp_helper import generate_otp, save_otp, verify_otp
from models.user import User
from extensions import db
import requests


# =========================
# SEND OTP SERVICE
# =========================

def send_otp_service(data):
    mobile = data.get("mobile")

    # ✅ Validation
    if not mobile or len(mobile) != 10 or not mobile.isdigit():
        return {"status": "error", "message": "Invalid mobile number"}, 400

    # ✅ Generate OTP
    otp = generate_otp()
    save_otp(mobile, otp)

    url = "https://api.onex-aura.com/api/jsmslist"

    message = f"Your OTP is {otp} for login authentication. It is valid for 10 minutes. Do not share it with anyone. - Fund Sarthi"

    payload = {
        "key": "YjDtvwUv",
        "listsms": [
            {
                "from": "FSARTH",
                "to": mobile,
                "body": message,
                "entityid": "1001338817429885581",
                "templateid": "1007505525018237305"
            }
        ]
    }

    try:
        response = requests.post(url, json=payload, timeout=10)

        print("SMS API Status Code:", response.status_code)
        print("SMS API Response:", response.text)

        # ✅ Parse response
        try:
            res_json = response.json()
        except:
            return {"status": "error", "message": "Invalid response from SMS API"}, 500

        # ✅ FIXED: correct parsing
        try:
            sms_data = res_json.get("smslist", {}).get("sms", [])

            if sms_data and sms_data[0].get("status") == "success":
                return {
                    "status": "success",
                    "message": "OTP sent successfully"
                }, 200

            return {
                "status": "error",
                "message": sms_data[0].get("reason", "SMS failed") if sms_data else "SMS failed"
            }, 400

        except Exception as e:
            print("Parsing Error:", str(e))
            return {
                "status": "error",
                "message": "Unexpected API response"
            }, 500

    except requests.exceptions.Timeout:
        return {"status": "error", "message": "SMS API timeout"}, 500

    except requests.exceptions.RequestException as e:
        print("SMS Error:", str(e))
        return {"status": "error", "message": "Failed to send OTP"}, 500


# =========================
# VERIFY OTP SERVICE
# =========================

def verify_otp_service(data):
    mobile = data.get("mobile")
    otp = data.get("otp")

    if not mobile or not otp:
        return {"status": "error", "message": "Mobile and OTP required"}, 400

    is_valid, message = verify_otp(mobile, otp)

    if is_valid:
        return {
            "status": "success",
            "message": "Login successful"
        }, 200

    return {
        "status": "error",
        "message": message
    }, 400


# =========================
# USER PROFILE SERVICE
# =========================

def get_user_profile_service(mobile):
    user = User.query.filter_by(mobile=mobile).first()

    if not user:
        return {"status": "success", "data": {}}, 200

    income = int(user.income or 0)

    loan_score = min(90, int(income / 1000))
    eligible_amount = income * 20

    return {
        "status": "success",
        "data": {
            "name": user.name,
            "city": user.city,
            "employment": user.employment,
            "income": user.income,
            "loan_score": loan_score,
            "eligible_amount": f"₹{eligible_amount:,}"
        }
    }, 200


# =========================
# LOAN STATUS SERVICE
# =========================

def get_loan_status_service(mobile):
    from models.loan import Loan

    user = User.query.filter_by(mobile=mobile).first()

    if not user:
        return {"status": "success", "hasLoan": False, "data": []}, 200

    loan = Loan.query.filter_by(user_id=user.id).order_by(Loan.id.desc()).first()

    if not loan:
        return {"status": "success", "hasLoan": False, "data": []}, 200

    steps = [
        {"label": "Profile", "done": True},
        {"label": "Bank Match", "done": loan.status in ["processing", "approved"]},
        {"label": "Upload Docs", "done": loan.status in ["processing", "approved"]},
        {"label": "Track Status", "done": loan.status == "approved"},
    ]

    return {
        "status": "success",
        "hasLoan": True,
        "data": steps
    }, 200


# =========================
# UPDATE PROFILE SERVICE
# =========================

def update_profile_service(data):
    mobile = data.get("mobile")

    user = User.query.filter_by(mobile=mobile).first()

    if not user:
        user = User(mobile=mobile)

    user.name = data.get("fullName")
    user.city = data.get("city")
    user.employment = data.get("employment")
    user.income = data.get("income")

    db.session.add(user)
    db.session.commit()

    return {"status": "success"}, 200

