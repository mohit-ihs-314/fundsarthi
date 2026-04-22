from extensions import db
from datetime import datetime

class Partner(db.Model):
    __tablename__ = "partners"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    company = db.Column(db.String(150))
    service_type = db.Column(db.String(50))
    city = db.Column(db.String(50))
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100))
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)