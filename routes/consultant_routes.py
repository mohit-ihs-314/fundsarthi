from flask import Blueprint, request, jsonify
from models.consultant import Consultant
from extensions import db
import random
import cloudinary.uploader
from models.consultant import Booking
import json
from models.consultant_slot import ConsultantSlot
from datetime import datetime
from services.activity_service import add_activity

consultant_bp = Blueprint("Consultant", __name__)

@consultant_bp.route("/apply-consultant", methods=["POST"])
def apply_consultant():
    try:
        data = request.json

        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        # ✅ SAFE TYPE CONVERSION
        experience = data.get("experience")
        try:
            experience = int(experience) if experience else None
        except ValueError:
            return jsonify({
                "status": "error",
                "message": "Experience must be a number"
            }), 400

        # ✅ GENERATE UNIQUE CONSULTANT ID
        consultant_id = f"CONS{random.randint(100000,999999)}{int(datetime.utcnow().timestamp())}"

        consultant = Consultant(
            consultant_id=consultant_id,
            full_name=data.get("fullName"),
            city=data.get("city"),
            address=data.get("address"),
            expertise=json.dumps(data.get("expertise", [])),
            experience=experience,
            languages=data.get("languages"),
            bio=data.get("bio"),
            phone=data.get("phone"),
            photo=data.get("photo") or "",
            certificate=data.get("certificate") or "",
            govt_id=data.get("govt_id") or "",
            consultation_fee=data.get("consultation_fee"),
        )

        db.session.add(consultant)
        db.session.commit()
        add_activity(
            data.get("phone"),
            "consultant_apply",
            "Consultant Application Submitted",
            "Your consultant profile was submitted for approval"
        )

        return jsonify({
            "status": "success",
            "id": consultant.id
        })

    except Exception as e:
        db.session.rollback()  # ✅ IMPORTANT
        print("🔥 APPLY CONSULTANT ERROR:", str(e))

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

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
            "location": c.address if c.address else c.city,
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
            "address": consultant.address,
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

        customer_name=data.get("customer_name") or "User",
        consultation_type=data.get("consultation_type") or "Residential",

        date=data.get("date") or "",
        time=data.get("time") or "",

        status="Pending"
    )

    db.session.add(booking)
    db.session.commit()
    add_activity(
        data.get("user_mobile"),
        "consultation",
        "Consultation Booked",
        f"Consultation booked with {data.get('consultant_name')}"
    )

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

@consultant_bp.route("/my-consultations", methods=["GET"])
def get_my_consultations():

    mobile = request.args.get("mobile")

    if not mobile:
        return jsonify({
            "status": "error",
            "message": "mobile required"
        }), 400

    bookings = Booking.query.filter_by(
        user_mobile=mobile
    ).order_by(Booking.id.desc()).all()

    result = []

    for b in bookings:

        # format time
        time_str = None

        if b.time:
            try:
                time_obj = datetime.strptime(str(b.time), "%H:%M:%S")
                time_str = time_obj.strftime("%I:%M %p")
            except:
                time_str = str(b.time)

        result.append({
            "id": b.booking_id,
            "consultant_name": b.consultant_name,
            "consultation_type": b.consultation_type,
            "date": str(b.date),
            "time": time_str,
            "status": b.status,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M:%S") if b.created_at else None
        })

    return jsonify({
        "status": "success",
        "data": result
    })

@consultant_bp.route("/track-consultation/<booking_id>", methods=["GET"])
def track_consultation(booking_id):

    booking = Booking.query.filter_by(
        booking_id=booking_id
    ).first()

    if not booking:
        return jsonify({
            "status": "error",
            "message": "Booking not found"
        }), 404

    
    # timeline logic
    steps = [
        {
            "step_name": "Booking Requested",
            "is_done": True
        },
        {
            "step_name": "Consultant Assigned",
            "is_done": booking.status in [
                "Assigned",
                "Confirmed",
                "Completed"
            ]
        },
        {
            "step_name": "Consultation Confirmed",
            "is_done": booking.status in [
                "Confirmed",
                "Completed"
            ]
        },
        {
            "step_name": "Consultation Completed",
            "is_done": booking.status == "Completed"
        }
    ]

    time_str = None

    if booking.time:
        try:
            time_obj = datetime.strptime(str(booking.time), "%H:%M:%S")
            time_str = time_obj.strftime("%I:%M %p")
        except:
            time_str = str(booking.time)

    add_activity(
        booking.user_mobile,
        "consultation_view",
        "Viewed Consultation Status",
        f"Checked booking {booking.booking_id}"
        )

    return jsonify({
        "status": "success",
        "data": {
            "id": booking.booking_id,
            "consultant_name": booking.consultant_name,
            "consultation_type": booking.consultation_type,
            "date": str(booking.date),
            "time": time_str,
            "status": booking.status,
            "steps": steps
        }
    })

@consultant_bp.route("/update-booking-status", methods=["POST"])
def update_booking_status():
    data = request.json

    booking = Booking.query.filter_by(booking_id=data.get("booking_id")).first()

    if not booking:
        return jsonify({"status": "error"}), 404

    booking.status = data.get("status")
    db.session.commit()

    add_activity(
        booking.user_mobile,
        "consultation_status",
        "Consultation Status Updated",
        f"Booking status changed to {booking.status}"
    )

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

    add_activity(
        booking.user_mobile,
        "consultation_reschedule",
        "Consultation Rescheduled",
        f"Consultation moved to {booking.date}"
    )

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


@consultant_bp.route("/add-slot", methods=["POST"])
def add_slot():

    data = request.json

    slot = ConsultantSlot(

        consultant_id=data.get("consultant_id"),

        slot_date=datetime.strptime(
            data.get("date"),
            "%Y-%m-%d"
        ).date(),

        slot_time=datetime.strptime(
            data.get("time"),
            "%H:%M"
        ).time()
    )

    db.session.add(slot)
    db.session.commit()

    return jsonify({
        "status": "success"
    })

@consultant_bp.route("/consultant-slots", methods=["GET"])
def consultant_slots():

    consultant_id = request.args.get("consultant_id")
    date = request.args.get("date")

    slots = ConsultantSlot.query.filter_by(
        consultant_id=consultant_id,
        slot_date=date,
        is_booked=False
    ).all()

    result = []

    for slot in slots:

        result.append({
            "id": slot.id,
            "time": slot.slot_time.strftime("%I:%M %p"),
            "value": slot.slot_time.strftime("%H:%M:%S")
        })

    return jsonify({
        "status": "success",
        "data": result
    })

@consultant_bp.route("/consultant-available-dates", methods=["GET"])
def consultant_available_dates():

    consultant_id = request.args.get("consultant_id")

    if not consultant_id:
        return jsonify({
            "status": "error",
            "message": "consultant_id required"
        }), 400

    slots = ConsultantSlot.query.filter_by(
        consultant_id=consultant_id,
        is_booked=False
    ).all()

    unique_dates = []

    for slot in slots:

        date_str = str(slot.slot_date)

        if date_str not in unique_dates:
            unique_dates.append(date_str)

    return jsonify({
        "status": "success",
        "data": unique_dates
    })