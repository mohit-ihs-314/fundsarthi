from models.loan import Loan, LoanStep
from models.user import User
from extensions import db
import uuid
import json

def apply_loan_service(data):
    mobile = data.get("mobile")

    user = User.query.filter_by(mobile=mobile).first()

    if not user:
        return {"status": "error", "message": "User not found"}, 404

    application_id = str(uuid.uuid4())[:8].upper()

    # ✅ Separate CR fields
    cr_name = data.get("customer_name")
    cr_number = data.get("mobile")

    # ✅ Clean extra_data (exclude CR also)
    extra_data = {
        k: v for k, v in data.items()
        if k not in ["mobile", "amount", "type", "existingEmi", "notes", "customer_name"]
    }

    loan = Loan(
        user_id=user.id,
        loan_amount=data.get("amount"),
        loan_type=data.get("type"),
        existing_emi=data.get("existingEmi"),
        notes=data.get("notes"),
        status="New",
        application_id=application_id,

        # ✅ FIX HERE
        extra_data=json.dumps(extra_data),

        customer_name=cr_name,
        mobile=cr_number
    )

    db.session.add(loan)
    db.session.commit()

    # steps same
    steps = [
        "Application Submitted",
        "Document Verification",
        "Bank Processing",
        "Approval"
    ]

    for i, step in enumerate(steps):
        db.session.add(LoanStep(
            loan_id=loan.id,
            step_name=step,
            is_done=True if i == 0 else False
        ))

    db.session.commit()

    return {
        "status": "success",
        "application_id": application_id
    }, 200

def get_all_loans_service():
    from models.loan import Loan
    from models.user import User

    loans = Loan.query.all()

    result = []

    for loan in loans:
        user = User.query.get(loan.user_id)

        result.append({
            "id": loan.id,
            "name": user.name if user else "",
            "mobile": user.mobile if user else "",
            "amount": loan.loan_amount,
            "type": loan.loan_type,
            "status": loan.status
        })

    return {"status": "success", "data": result}, 200

def update_loan_status_service(data):
    loan_id = data.get("loan_id")
    status = data.get("status")

    loan = Loan.query.get(loan_id)

    if not loan:
        return {"status": "error", "message": "Loan not found"}, 404

    loan.status = status

    # ✅ UPDATE STEPS ALSO
    steps = LoanStep.query.filter_by(loan_id=loan.id).all()

    for step in steps:
        if status == "In Process":
            if step.step_name in ["Application Submitted", "Document Verification"]:
                step.is_done = True

        elif status == "Approved":
            step.is_done = True

        elif status == "Rejected":
            if step.step_name == "Approval":
                step.is_done = False

    db.session.commit()

    return {"status": "success", "message": "Status updated"}, 200