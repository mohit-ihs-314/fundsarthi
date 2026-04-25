from extensions import db
from datetime import datetime

class CibilReport(db.Model):
    __tablename__ = "cibil_reports"

    id = db.Column(db.Integer, primary_key=True)
    mobile = db.Column(db.String(15))
    pan = db.Column(db.String(20))
    score = db.Column(db.Integer)
    pdf_url = db.Column(db.Text)
    response_json = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)