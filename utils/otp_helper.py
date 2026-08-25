import random
from datetime import datetime, timedelta

from extensions import db
from models.otp_code import OtpCode

OTP_VALIDITY_SECONDS = 300  # 5 minutes


def generate_otp():
    return random.randint(100000, 999999)


def save_otp(mobile, otp):
    mobile = str(mobile).strip()
    otp = str(otp).strip()

    expires_at = datetime.utcnow() + timedelta(
        seconds=OTP_VALIDITY_SECONDS
    )

    record = OtpCode.query.filter_by(
        mobile=mobile
    ).first()

    if record:
        record.otp = otp
        record.expires_at = expires_at
    else:
        record = OtpCode(
            mobile=mobile,
            otp=otp,
            expires_at=expires_at
        )

        db.session.add(record)

    db.session.commit()


def verify_otp(mobile, user_otp):
    mobile = str(mobile).strip()
    user_otp = str(user_otp).strip()

    record = OtpCode.query.filter_by(
        mobile=mobile
    ).first()

    if not record:
        return False, "OTP not found"

    if datetime.utcnow() > record.expires_at:
        return False, "OTP expired"

    if str(record.otp) != user_otp:
        return False, "Invalid OTP"

    db.session.delete(record)
    db.session.commit()

    return True, "OTP verified"