from extensions import db
from datetime import datetime


class Consultant(db.Model):
    __tablename__ = "consultants"

    id = db.Column(db.Integer, primary_key=True)
    consultant_id = db.Column(db.String(50))
    full_name = db.Column(db.String(255))
    city = db.Column(db.String(100))
    expertise = db.Column(db.Text)
    experience = db.Column(db.Integer)
    languages = db.Column(db.String(255))
    bio = db.Column(db.Text)
    phone = db.Column(db.String(20))
    photo = db.Column(db.Text)

    # ✅ NEW FIELDS
    certificate = db.Column(db.Text)
    govt_id = db.Column(db.Text)

    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(50))
    consultant_id = db.Column(db.Integer)
    consultant_name = db.Column(db.String(255))
    user_mobile = db.Column(db.String(20))

    # ✅ ADD THESE
    customer_name = db.Column(db.String(255))
    consultation_type = db.Column(db.String(50))

    date = db.Column(db.String(50))
    time = db.Column(db.String(50))
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)