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
    consultation_fee = db.Column(
        db.Integer,
        default=500
    )

    # ✅ NEW FIELDS
    certificate = db.Column(db.Text)
    govt_id = db.Column(db.Text)
    address = db.Column(db.Text)

    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)

    booking_id = db.Column(db.String(50))

    consultant_id = db.Column(db.Integer)
    consultant_name = db.Column(db.String(255))

    user_mobile = db.Column(db.String(20))
    customer_name = db.Column(db.String(255))

    consultation_type = db.Column(db.String(50))

    property_type = db.Column(db.String(100))
    city = db.Column(db.String(100))
    floor_plan = db.Column(db.String(100))

    primary_reason = db.Column(db.String(255))

    consultation_timeline = db.Column(db.String(100))

    objective = db.Column(db.String(255))

    preferred_consultation_type = db.Column(db.String(100))

    property_size = db.Column(db.String(100))

    date = db.Column(db.Date)
    time = db.Column(db.Time)

    status = db.Column(db.String(20), default="pending")

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )