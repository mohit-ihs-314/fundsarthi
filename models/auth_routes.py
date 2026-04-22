from flask import Blueprint, request
from services.auth_service import send_otp_service, verify_otp_service
from services.cibil_service import check_cibil_service

auth_bp = Blueprint("auth", __name__)
print("AUTH ROUTES LOADED")

# ✅ SEND OTP
@auth_bp.route("/send-otp", methods=["POST", "OPTIONS"])
def send_otp():
    if request.method == "OPTIONS":
        return {"status": "ok"}, 200

    return send_otp_service(request.json)


# ✅ VERIFY OTP
@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    return verify_otp_service(request.json)


# ✅ 🔥 NEW: CHECK CIBIL
@auth_bp.route("/check-cibil", methods=["POST", "OPTIONS"])
def check_cibil():
    if request.method == "OPTIONS":
        return {"status": "ok"}, 200

    return check_cibil_service(request.json)