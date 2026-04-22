from flask import Blueprint
from controllers.auth_controller import (
    send_otp,
    verify_otp,
    get_user_profile,
    get_loan_status,
    update_profile,
    check_cibil   
)

auth_bp = Blueprint("auth", __name__)

auth_bp.route("/send-otp", methods=["POST"])(send_otp)
auth_bp.route("/verify-otp", methods=["POST"])(verify_otp)
auth_bp.route("/user-profile", methods=["GET"])(get_user_profile)
auth_bp.route("/loan-status", methods=["GET"])(get_loan_status)
auth_bp.route("/update-profile", methods=["POST"])(update_profile)
auth_bp.route("/check-cibil", methods=["POST"])(check_cibil)