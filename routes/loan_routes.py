from flask import Blueprint, request, jsonify
from models.loan import Loan, LoanStep
from extensions import db
from services.loan_service import apply_loan_service
from models.user import User
from services.activity_service import add_activity
from services.firebase_service import send_push

loan_bp = Blueprint("loan", __name__)

# ✅ APPLY LOAN ROUTE
@loan_bp.route("/apply-loan", methods=["POST"])
def apply_loan():
    data = request.json
    res, status = apply_loan_service(data)

    if status == 200:

        add_activity(
            data.get("mobile"),
            "loan",
            "Loan Application Submitted",
            f"{data.get('loan_type', 'Loan')} application submitted successfully"
        )

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

            if step.step_name in [
                "Application Submitted",
                "Document Verification",
                "Approval"
            ]:
                step.is_done = True

        elif data["status"] == "Disbursed":

            step.is_done = True

        elif data["status"] == "Rejected":
            if step.step_name == "Approval":
                step.is_done = False

    db.session.commit()
    add_activity(
        loan.mobile,
        "loan_status",
        "Loan Status Updated",
        f"Your loan status changed to {loan.status}"
    )

    user = User.query.filter_by(
        mobile=loan.mobile
    ).first()

    print("USER:", user.mobile)
    print("TOKEN:", user.fcm_token)
    print("STATUS:", loan.status)

    if user and user.fcm_token:

        result = send_push(
            user.fcm_token,
            "Loan Status Updated",
            f"Your loan status is now {loan.status}"
        )

        print("FCM RESULT:", result)

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


@loan_bp.route("/save-fcm-token", methods=["POST"])
def save_fcm_token():

    data = request.json

    print("SAVE TOKEN API CALLED")
    print(data)

    user = User.query.filter_by(
        mobile=data["mobile"]
    ).first()

    print("USER FOUND:", user)

    if not user:
        return jsonify({
            "status": "error"
        }), 404

    user.fcm_token = data["fcm_token"]

    db.session.commit()

    print("TOKEN SAVED")

    return jsonify({
        "status": "success"
    })

@loan_bp.route("/send-notification", methods=["POST"])
def send_notification():

    data = request.json

    user = User.query.filter_by(
        mobile=data["mobile"]
    ).first()

    if not user:
        return jsonify({
            "status": "error",
            "message": "User not found"
        }), 404

    if not user.fcm_token:
        return jsonify({
            "status": "error",
            "message": "No FCM token"
        }), 400

    result = send_push(
        user.fcm_token,
        data["title"],
        data["body"]
    )

    return jsonify({
        "status": "success",
        "result": str(result)
    })