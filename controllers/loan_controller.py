from flask import request, jsonify
from services.loan_service import apply_loan_service

def apply_loan():
    data = request.get_json()
    response, status = apply_loan_service(data)
    return jsonify(response), status

from services.loan_service import (
    get_all_loans_service,
    update_loan_status_service
)

def get_all_loans():
    res, status = get_all_loans_service()
    return jsonify(res), status


def update_loan_status():
    data = request.get_json()
    res, status = update_loan_status_service(data)
    return jsonify(res), status