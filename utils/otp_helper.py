import random
import time

otp_store = {}

def generate_otp():
    return random.randint(100000, 999999)  # 6 digit OTP

def save_otp(mobile, otp):
    otp_store[mobile] = {
        "otp": otp,
        "expiry": time.time() + 300  # 5 min expiry
    }

def verify_otp(mobile, user_otp):
    data = otp_store.get(mobile)

    if not data:
        return False, "OTP not found"

    if time.time() > data["expiry"]:
        return False, "OTP expired"

    if str(data["otp"]) != str(user_otp):
        return False, "Invalid OTP"

    return True, "OTP verified"