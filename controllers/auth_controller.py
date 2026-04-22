from flask import request, jsonify
from services.auth_service import (
    send_otp_service,
    verify_otp_service,
    get_user_profile_service,
    get_loan_status_service,
    update_profile_service
)
from services.cibil_service import check_cibil_service

# OTP
def send_otp():
    data = request.json
    response, status = send_otp_service(data)
    return jsonify(response), status


def verify_otp():
    data = request.json
    response, status = verify_otp_service(data)
    return jsonify(response), status


# User Profile
def get_user_profile():
    mobile = request.args.get("mobile")

    response, status = get_user_profile_service(mobile)
    return jsonify(response), status


# Loan Status
def get_loan_status():
    mobile = request.args.get("mobile")
    response, status = get_loan_status_service(mobile)
    return jsonify(response), status

def update_profile():
    data = request.json
    response, status = update_profile_service(data)
    return jsonify(response), status

def check_cibil():
    data = request.json
    response, status = check_cibil_service(data)
    return jsonify(response), status