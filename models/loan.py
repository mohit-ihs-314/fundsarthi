from extensions import db
from sqlalchemy.dialects.mysql import JSON

class Loan(db.Model):
    __tablename__ = "loans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    loan_amount = db.Column(db.String(20))
    loan_type = db.Column(db.String(50))
    existing_emi = db.Column(db.String(20))
    notes = db.Column(db.Text)
    status = db.Column(db.String(50))
    application_id = db.Column(db.String(20), unique=True)
    extra_data = db.Column(JSON)
    customer_name = db.Column(db.String(100))
    mobile = db.Column(db.String(15))

class LoanStep(db.Model):
    __tablename__ = "loan_steps"

    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, nullable=False)
    step_name = db.Column(db.String(255))
    is_done = db.Column(db.Boolean, default=False)    