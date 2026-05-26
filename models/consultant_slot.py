from extensions import db
from datetime import datetime

class ConsultantSlot(db.Model):

    __tablename__ = "consultant_slots"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    consultant_id = db.Column(
        db.Integer,
        nullable=False
    )

    slot_date = db.Column(
        db.Date,
        nullable=False
    )

    slot_time = db.Column(
        db.Time,
        nullable=False
    )

    is_booked = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )