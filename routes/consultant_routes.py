from flask import Blueprint, request, jsonify
from models.consultant import Consultant
from extensions import db
import random
import cloudinary.uploader
from models.consultant import Booking
import json
from datetime import datetime

consultant_bp = Blueprint("Consultant", __name__)

@consultant_bp.route("/apply-consultant", methods=["POST"])
def apply_consultant():
    data = request.json

    consultant = Consultant(
        consultant_id=f"CONS{random.randint(100000,999999)}",
        full_name=data.get("fullName"),
        city=data.get("city"),
        expertise=json.dumps(data.get("expertise") or []),
        experience=data.get("experience"),
        languages=data.get("languages"),
        bio=data.get("bio"),
        phone=data.get("phone"),
        photo=data.get("photo"),

        # ✅ SAFE DEFAULTS
        certificate=data.get("certificate") or "",
        govt_id=data.get("govt_id") or "",
    )

    db.session.add(consultant)
    db.session.commit()

    return jsonify({
        "status": "success",
        "id": consultant.id
    })

@consultant_bp.route("/upload-image", methods=["POST"])
def upload_image():
    file = request.files.get("file")

    if not file:
        return jsonify({"status": "error", "message": "No file"}), 400

    # ✅ size check (10MB)
    if request.content_length and request.content_length > 10 * 1024 * 1024:
        return jsonify({
            "status": "error",
            "message": "File too large (max 10MB)"
        }), 400

    # ✅ ONLY IMAGE ALLOWED
    if not file.mimetype.startswith("image"):
        return jsonify({
            "status": "error",
            "message": "Only image files allowed (JPG, PNG)"
        }), 400

    try:
        # ✅ force image upload
        result = cloudinary.uploader.upload(
            file,
            resource_type="image"   # 🔥 FIXED (no auto, no raw)
        )

        return jsonify({
            "status": "success",
            "url": result["secure_url"]
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
@consultant_bp.route("/consultants", methods=["GET"])
def get_consultants():
    consultants = Consultant.query.filter_by(status="approved").all()

    result = []

    for c in consultants:
        result.append({
            "id": c.id,
            "name": c.full_name,
            "image": c.photo,
            "experience": f"{c.experience} years",
            "specialization": ", ".join(json.loads(c.expertise)) if c.expertise else "",
            "languages": c.languages.split(",") if c.languages else [],
            "rating": 4.5,  # temp (later DB se)
            "reviews": 0,
            "location": c.city,
            "verified": True
        })

    return jsonify({
        "status": "success",
        "data": result
    })    

@consultant_bp.route("/consultant/<int:id>", methods=["GET"])
def get_consultant(id):
    consultant = Consultant.query.get(id)

    if not consultant:
        return jsonify({"status": "error"}), 404

    return jsonify({
        "status": "success",
        "data": {
            "id": consultant.id,
            "full_name": consultant.full_name,
            "city": consultant.city,
            "expertise": consultant.expertise,
            "experience": consultant.experience,
            "languages": consultant.languages,
            "bio": consultant.bio,
            "phone": consultant.phone,
            "photo": consultant.photo,
            "status": consultant.status
        }
    })

@consultant_bp.route("/book-consultation", methods=["POST"])
def book_consultation():
    data = request.json

    booking_id = "VB" + str(random.randint(10000000, 99999999))

    booking = Booking(
        booking_id=booking_id,
        consultant_id=data.get("consultant_id"),
        consultant_name=data.get("consultant_name"),
        user_mobile=data.get("user_mobile"),

        # ✅ fallback fix
        customer_name=data.get("customer_name") or "User",
        consultation_type=data.get("consultation_type") or "Residential",

        date=data.get("date") or "",
        time=data.get("time") or "",
    )
    

    db.session.add(booking)
    db.session.commit()

    return jsonify({
        "status": "success",
        "booking_id": booking_id
    })


###############################################################################################

@consultant_bp.route("/check-consultant-status", methods=["GET"])
def check_consultant_status():
    mobile = request.args.get("mobile")

    consultant = Consultant.query.filter_by(phone=mobile).first()

    if consultant and consultant.status == "approved":
        return jsonify({
            "status": "success",
            "approved": True
        })

    return jsonify({
        "status": "success",
        "approved": False
    })

@consultant_bp.route("/my-bookings", methods=["GET"])
def get_my_bookings():
    consultant_id = request.args.get("consultant_id")

    if not consultant_id:
        return jsonify({"status": "error", "message": "consultant_id required"}), 400

    consultant_id = int(consultant_id)

    bookings = Booking.query.filter_by(consultant_id=consultant_id).all()

    result = []

    for b in bookings:

        # ✅ ADD THIS HERE
        time_str = None
        if b.time:
            time_obj = datetime.strptime(str(b.time), "%H:%M:%S")
            time_str = time_obj.strftime("%I:%M %p")

        # ✅ THEN USE IT HERE
        result.append({
            "id": b.booking_id,
            "customerName": b.customer_name,
            "customerPhone": b.user_mobile,
            "consultationType": b.consultation_type,
            "bookingDate": str(b.date),
            "bookingTime": time_str,  # 👈 use here
            "status": b.status,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M:%S") if b.created_at else None
        })

    return jsonify({
        "status": "success",
        "data": result
    })

@consultant_bp.route("/update-booking-status", methods=["POST"])
def update_booking_status():
    data = request.json

    booking = Booking.query.filter_by(booking_id=data.get("booking_id")).first()

    if not booking:
        return jsonify({"status": "error"}), 404

    booking.status = data.get("status")
    db.session.commit()

    return jsonify({"status": "success"})

@consultant_bp.route("/reschedule-booking", methods=["POST"])
def reschedule_booking():
    data = request.json

    booking = Booking.query.filter_by(booking_id=data.get("booking_id")).first()

    if not booking:
        return jsonify({"status": "error"}), 404

    booking.date = data.get("date")
    booking.time = data.get("time")

    db.session.commit()

    return jsonify({"status": "success"})

@consultant_bp.route("/get-consultant-id", methods=["GET"])
def get_consultant_id():
    mobile = request.args.get("mobile")

    consultant = Consultant.query.filter_by(phone=mobile).first()

    if not consultant:
        return jsonify({"status": "error", "message": "Consultant not found"}), 404

    return jsonify({
        "status": "success",
        "consultant_id": consultant.id
    })