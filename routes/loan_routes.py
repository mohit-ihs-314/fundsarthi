from flask import Blueprint, request, jsonify
from models.loan import Loan, LoanStep
from extensions import db
from services.loan_service import apply_loan_service
from models.user import User
from services.activity_service import add_activity
from services.firebase_service import send_push
from datetime import datetime
from dateutil.relativedelta import relativedelta


loan_bp = Blueprint("loan", __name__)


# =========================================================
# APPLY LOAN
# =========================================================

@loan_bp.route("/apply-loan", methods=["POST"])
def apply_loan():

    data = request.json or {}

    res, status = apply_loan_service(data)

    if status == 200:

        loan_type = (
            data.get("type")
            or data.get("loan_type")
            or "Loan"
        )

        add_activity(
            data.get("mobile"),
            "loan",
            "Loan Application Submitted",
            f"{loan_type} application submitted successfully"
        )

    return jsonify(res), status


# =========================================================
# GET ALL LOANS
# =========================================================

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
            "number": loan.mobile,
            "date": (
                loan.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if loan.created_at
                else ""
            )
        })

    return jsonify({
        "status": "success",
        "data": data
    })


# =========================================================
# UPDATE LOAN STATUS
# =========================================================

@loan_bp.route("/update-loan-status", methods=["POST"])
def update_status():

    data = request.json or {}

    loan_id = data.get("loan_id")
    new_status = data.get("status")

    if not loan_id or not new_status:
        return jsonify({
            "status": "error",
            "message": "Loan ID and status are required"
        }), 400

    loan = Loan.query.get(loan_id)

    if not loan:
        return jsonify({
            "status": "error",
            "message": "Loan not found"
        }), 404

    loan.status = new_status

    # =====================================================
    # UPDATE LOAN STEPS
    # =====================================================

    steps = LoanStep.query.filter_by(
        loan_id=loan.id
    ).all()

    for step in steps:

        if new_status == "In Process":

            if step.step_name in [
                "Application Submitted",
                "Document Verification"
            ]:
                step.is_done = True

        elif new_status == "Approved":

            if step.step_name in [
                "Application Submitted",
                "Document Verification",
                "Approval"
            ]:
                step.is_done = True

        elif new_status == "Disbursed":

            step.is_done = True

        elif new_status == "Rejected":

            if step.step_name == "Approval":
                step.is_done = False

    db.session.commit()

    # =====================================================
    # ACTIVITY
    # =====================================================

    add_activity(
        loan.mobile,
        "loan_status",
        "Loan Status Updated",
        f"Your loan status changed to {loan.status}"
    )

    # =====================================================
    # SEND PUSH NOTIFICATION
    # =====================================================

    user = User.query.filter_by(
        mobile=loan.mobile
    ).first()

    if user:
        print("USER:", user.mobile)
        print("TOKEN:", user.fcm_token)
        print("STATUS:", loan.status)

        if user.fcm_token:

            result = send_push(
                user.fcm_token,
                "Loan Status Updated",
                f"Your loan status is now {loan.status}",
                {
                    "route": "/my-applications",
                    "loan_id": str(loan.id)
                }
            )

            print("FCM RESULT:", result)

    return jsonify({
        "status": "success",
        "message": "Loan status updated successfully"
    })


# =========================================================
# TRACK LOAN
# =========================================================

@loan_bp.route("/track-loan/<application_id>", methods=["GET"])
def track_loan(application_id):

    loan = Loan.query.filter_by(
        application_id=application_id
    ).first()

    if not loan:
        return jsonify({
            "status": "error",
            "message": "Not found"
        }), 404

    # Get loan steps
    steps = LoanStep.query.filter_by(
        loan_id=loan.id
    ).all()

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
                }
                for step in steps
            ]
        }
    })


# =========================================================
# MY LOANS
# =========================================================

@loan_bp.route("/my-loans", methods=["GET"])
def my_loans():

    mobile = request.args.get("mobile")

    if not mobile:
        return jsonify({
            "status": "error",
            "message": "Mobile number is required"
        }), 400

    user = User.query.filter_by(
        mobile=mobile
    ).first()

    if not user:
        return jsonify({
            "status": "error",
            "message": "User not found"
        }), 404

    loans = (
        Loan.query
        .filter_by(user_id=user.id)
        .order_by(Loan.id.desc())
        .all()
    )

    return jsonify({
        "status": "success",
        "data": [
            {
                "id": loan.application_id,
                "amount": loan.loan_amount,
                "type": loan.loan_type,
                "status": loan.status,
                "date": (
                    loan.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if loan.created_at
                    else ""
                )
            }
            for loan in loans
        ]
    })


# =========================================================
# SAVE FCM TOKEN
# =========================================================

@loan_bp.route("/save-fcm-token", methods=["POST"])
def save_fcm_token():

    data = request.json or {}

    print("SAVE TOKEN API CALLED")
    print(data)

    mobile = data.get("mobile")
    fcm_token = data.get("fcm_token")

    if not mobile or not fcm_token:
        return jsonify({
            "status": "error",
            "message": "Mobile and FCM token are required"
        }), 400

    user = User.query.filter_by(
        mobile=mobile
    ).first()

    print("USER FOUND:", user)

    if not user:
        return jsonify({
            "status": "error",
            "message": "User not found"
        }), 404

    user.fcm_token = fcm_token

    db.session.commit()

    print("TOKEN SAVED")

    return jsonify({
        "status": "success"
    })


# =========================================================
# SEND NOTIFICATION
# =========================================================

@loan_bp.route("/send-notification", methods=["POST"])
def send_notification():

    data = request.json or {}

    mobile = data.get("mobile")
    title = data.get("title")
    body = data.get("body")

    user = User.query.filter_by(
        mobile=mobile
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
        title,
        body
    )

    return jsonify({
        "status": "success",
        "result": str(result)
    })


# =========================================================
# CHECK LOAN ELIGIBILITY
# =========================================================
# Same mobile + same loan type cannot apply again
# for 2 months.
# =========================================================

@loan_bp.route("/check-loan-eligibility", methods=["GET"])
def check_loan_eligibility():

    mobile = request.args.get("mobile")
    loan_type = request.args.get("type")

    if not mobile or not loan_type:

        return jsonify({
            "status": "error",
            "message": "Mobile number and loan type are required"
        }), 400

    # -----------------------------------------------------
    # Find latest application for SAME MOBILE
    # + SAME LOAN TYPE
    # -----------------------------------------------------

    previous_loan = (
        Loan.query
        .filter_by(
            mobile=mobile,
            loan_type=loan_type
        )
        .order_by(
            Loan.created_at.desc()
        )
        .first()
    )

    # -----------------------------------------------------
    # No previous application
    # -----------------------------------------------------

    if not previous_loan:

        return jsonify({
            "status": "eligible",
            "message": "You are eligible to apply."
        }), 200

    # -----------------------------------------------------
    # Calculate next eligible date
    # -----------------------------------------------------

    next_eligible_date = (
        previous_loan.created_at
        + relativedelta(months=2)
    )

    now = datetime.utcnow()

    # -----------------------------------------------------
    # Still within 2 months
    # -----------------------------------------------------

    if now < next_eligible_date:

        return jsonify({
            "status": "blocked",
            "message": (
                "You have already applied for this loan. "
                "You can apply again after "
                f"{next_eligible_date.strftime('%d %B %Y')}."
            ),
            "last_application_date": (
                previous_loan.created_at.strftime("%d %B %Y")
            ),
            "eligible_date": (
                next_eligible_date.strftime("%d %B %Y")
            )
        }), 409

    # -----------------------------------------------------
    # 2 months completed
    # -----------------------------------------------------

    return jsonify({
        "status": "eligible",
        "message": "You are eligible to apply."
    }), 200