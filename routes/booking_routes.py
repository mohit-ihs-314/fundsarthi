import random
from flask import Blueprint, request, jsonify
from extensions import db
from models.consultant import Booking

booking_bp = Blueprint("booking", __name__)

@booking_bp.route("/book-consultation", methods=["POST"])
def book_consultation():
    try:
        data = request.get_json()

        booking_id = "VB" + str(random.randint(10000000, 99999999))

        new_booking = Booking(
            booking_id=booking_id,
            consultant_id=data.get("consultant_id"),
            consultant_name=data.get("consultant_name"),
            user_mobile=data.get("user_mobile"),
            date=data.get("date"),
            time=data.get("time"),
        )

        db.session.add(new_booking)
        db.session.commit()

        return jsonify({
            "status": "success",
            "booking_id": booking_id
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({
            "status": "error",
            "message": "Booking failed"
        }), 500