from flask import Blueprint, request, jsonify
from models.loan import Loan, LoanStep
from extensions import db
from services.loan_service import apply_loan_service
from models.user import User

loan_bp = Blueprint("loan", __name__)

# ✅ APPLY LOAN ROUTE
@loan_bp.route("/apply-loan", methods=["POST"])
def apply_loan():
    data = request.json
    res, status = apply_loan_service(data)
    return jsonify(res), status

# GET ALL LOANS
@loan_bp.route("/loans", methods=["GET"])
def get_loans():
    loans = Loan.query.all()

    data = []
    for loan in loans:
        data.append({
            "id": loan.application_id,
            "amount": loan.loan_amount,
            "type": loan.loan_type,
            "status": loan.status,
            "extra": loan.extra_data,
            "name": loan.customer_name,
            "number": loan.mobile
        })  

    return jsonify({
        "status": "success",
        "data": data
    })


# ✅ ADD THIS
@loan_bp.route("/update-loan-status", methods=["POST"])
def update_status():
    data = request.json

    loan = Loan.query.get(data["loan_id"])

    if not loan:
        return jsonify({"status": "error", "message": "Loan not found"})

    loan.status = data["status"]

    # ✅ UPDATE STEPS
    steps = LoanStep.query.filter_by(loan_id=loan.id).all()

    for step in steps:
        if data["status"] == "In Process":
            if step.step_name in ["Application Submitted", "Document Verification"]:
                step.is_done = True

        elif data["status"] == "Approved":
            step.is_done = True

        elif data["status"] == "Rejected":
            if step.step_name == "Approval":
                step.is_done = False

    db.session.commit()

    return jsonify({"status": "success"})

@loan_bp.route("/track-loan/<application_id>", methods=["GET"])
def track_loan(application_id):
    loan = Loan.query.filter_by(application_id=application_id).first()

    if not loan:
        return jsonify({"status": "error", "message": "Not found"}), 404

    # ✅ GET STEPS
    steps = LoanStep.query.filter_by(loan_id=loan.id).all()

    return jsonify({
        "status": "success",
        "data": {
            "application_id": loan.application_id,
            "amount": loan.loan_amount,
            "type": loan.loan_type,
            "status": loan.status,
            "steps": [
                {
                    "step_name": step.step_name,
                    "is_done": step.is_done
                } for step in steps
            ]
        }
    })

@loan_bp.route("/my-loans", methods=["GET"])
def my_loans():
    mobile = request.args.get("mobile")

    user = User.query.filter_by(mobile=mobile).first()

    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    loans = Loan.query.filter_by(user_id=user.id).order_by(Loan.id.desc()).all()

    return jsonify({
        "status": "success",
        "data": [
            {
                "id": loan.application_id,   # 🔥 IMPORTANT (use this in frontend)
                "amount": loan.loan_amount,
                "type": loan.loan_type,
                "status": loan.status,
                "date": str(loan.created_at) if hasattr(loan, "created_at") else ""
            } for loan in loans
        ]
    })