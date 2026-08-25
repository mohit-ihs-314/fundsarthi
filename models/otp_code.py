from extensions import db
from datetime import datetime


class OtpCode(db.Model):
    __tablename__ = "otp_codes"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    mobile = db.Column(
        db.String(15),
        unique=True,
        nullable=False
    )

    otp = db.Column(
        db.String(6),
        nullable=False
    )

    expires_at = db.Column(
        db.DateTime,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )