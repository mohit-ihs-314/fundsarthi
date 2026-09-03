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
from models.user import User
from services.firebase_service import send_push
import requests


consultant_bp = Blueprint("Consultant", __name__)

@consultant_bp.route("/apply-consultant", methods=["POST"])
def get_coordinates(address, city):
    try:
        query = f"{address}, {city}, India"

        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "json",
                "limit": 1
            },
            headers={
                "User-Agent": "FundsArthi/1.0"
            },
            timeout=10
        )

        if response.status_code != 200:
            print("GEOCODING ERROR:", response.status_code)
            return None, None

        results = response.json()

        if not results:
            print("LOCATION NOT FOUND:", query)
            return None, None

        latitude = float(results[0]["lat"])
        longitude = float(results[0]["lon"])

        print("📍 LOCATION FOUND:", query)
        print("LAT:", latitude)
        print("LNG:", longitude)

        return latitude, longitude

    except Exception as e:
        print("🔥 GEOCODING ERROR:", str(e))
        return None, None

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

        # 📍 GET LOCATION AUTOMATICALLY
        address = data.get("address")
        city = data.get("city")

        latitude, longitude = get_coordinates(
            address,
            city
        )

        consultant = Consultant(
            consultant_id=consultant_id,
            full_name=data.get("fullName"),
            city=city,
            address=address,

            # 📍 SAVE COORDINATES
            latitude=latitude,
            longitude=longitude,

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
            "specialization": ", ".join(
                json.loads(c.expertise)
            ) if c.expertise else "",
            "languages": c.languages.split(",") if c.languages else [],
            "rating": 4.5,
            "reviews": 0,
            "location": c.address if c.address else c.city,
            "consultation_fee": c.consultation_fee,
            "verified": True,

            # 📍 LOCATION
            "latitude": c.latitude,
            "longitude": c.longitude
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
            "latitude": consultant.latitude,
            "longitude": consultant.longitude,
            "expertise": consultant.expertise,
            "experience": consultant.experience,
            "languages": consultant.languages,
            "consultation_fee": consultant.consultation_fee,
            "bio": consultant.bio,
            "phone": consultant.phone,
            "photo": consultant.photo,
            "status": consultant.status
        }
    })

@consultant_bp.route("/book-consultation", methods=["POST"])
def book_consultation():

    print("\n======================")
    print("BOOK CONSULTATION")
    print("======================")

    data = request.json

    print("REQUEST DATA:", data)

    booking_id = "VB" + str(
        random.randint(10000000, 99999999)
    )

    booking = Booking(

        booking_id=booking_id,

        consultant_id=data.get("consultant_id"),
        consultant_name=data.get("consultant_name"),

        user_mobile=data.get("user_mobile"),
        customer_name=data.get("customer_name"),

        consultation_type="Vastu Consultation",

        property_type=data.get("propertyType"),
        city=data.get("city"),
        floor_plan=data.get("floorPlan"),

        primary_reason=data.get("primaryReason"),

        consultation_timeline=data.get("consultationTime"),

        objective=data.get("objective"),

        preferred_consultation_type=data.get(
            "consultationType"
        ),

        property_size=data.get("propertySize"),

        date=datetime.strptime(
            data.get("date"),
            "%Y-%m-%d"
        ).date(),

        time=datetime.strptime(
            data.get("time"),
            "%H:%M:%S"
        ).time(),

        status="Pending"
    )

    db.session.add(booking)

    slot = ConsultantSlot.query.filter_by(
        consultant_id=data.get("consultant_id"),
        slot_date=data.get("date"),
        slot_time=datetime.strptime(
            data.get("time"),
            "%H:%M:%S"
        ).time()
    ).first()

    if slot:
        slot.is_booked = True

    db.session.commit()

    print("BOOKING CREATED:", booking_id)

    # ==========================================
    # SEND NOTIFICATION TO CONSULTANT
    # ==========================================

    consultant = Consultant.query.get(
        data.get("consultant_id")
    )

    print("CONSULTANT:", consultant)

    if not consultant:

        print("CONSULTANT NOT FOUND")

    else:

        print("CONSULTANT ID:", consultant.id)
        print("CONSULTANT PHONE:", consultant.phone)

        consultant_user = User.query.filter_by(
            mobile=consultant.phone
        ).first()

        print("CONSULTANT USER:", consultant_user)

        if not consultant_user:

            print("CONSULTANT USER NOT FOUND")

        elif not consultant_user.fcm_token:

            print("CONSULTANT HAS NO FCM TOKEN")

        else:

            print("CONSULTANT TOKEN FOUND")
            print(
                consultant_user.fcm_token[:50] + "..."
            )

            try:

                result = send_push(
                    consultant_user.fcm_token,
                    "New Consultation Request",
                    f"{data.get('customer_name')} has requested a consultation."
                )

                print("CONSULTANT PUSH SENT")
                print("FIREBASE RESPONSE:", result)

            except Exception as e:

                print("CONSULTANT PUSH ERROR")
                print(str(e))

    # ==========================================
    # ACTIVITY
    # ==========================================

    add_activity(
        data.get("user_mobile"),
        "consultation",
        "Consultation Request Submitted",
        f"Request submitted for {data.get('consultant_name')}"
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
            "property_type": b.property_type,
            "city": b.city,
            "consultation_type": b.preferred_consultation_type,

            "date": str(b.date) if b.date else None,

            "time": b.time.strftime("%I:%M %p")
            if b.time else None,

            "status": b.status,

            "created_at":
                b.created_at.strftime("%Y-%m-%d %H:%M:%S")
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

    print("\n==============================")
    print("UPDATE BOOKING STATUS CALLED")
    print("==============================")

    data = request.json

    print("REQUEST DATA:", data)

    booking = Booking.query.filter_by(
        booking_id=data.get("booking_id")
    ).first()

    if not booking:
        print("BOOKING NOT FOUND")
        return jsonify({"status": "error"}), 404

    print("BOOKING FOUND:", booking.booking_id)
    print("OLD STATUS:", booking.status)

    booking.status = data.get("status")

    db.session.commit()

    print("NEW STATUS:", booking.status)
    print("BOOKING UPDATED SUCCESSFULLY")

    # ====================================
    # SEND PUSH TO CUSTOMER
    # ====================================

    user = User.query.filter_by(
        mobile=booking.user_mobile
    ).first()

    print("CUSTOMER MOBILE:", booking.user_mobile)
    print("USER FOUND:", user)

    if not user:
        print("USER NOT FOUND")

    elif not user.fcm_token:
        print("USER HAS NO FCM TOKEN")

    else:

        print("FCM TOKEN FOUND")
        print(user.fcm_token[:50] + "...")

        title = "Consultation Status Updated"

        if booking.status.lower() == "confirmed":

            body = (
                f"Your consultation booking "
                f"{booking.booking_id} has been approved."
            )

        elif booking.status.lower() == "rejected":

            body = (
                f"Your consultation booking "
                f"{booking.booking_id} has been rejected."
            )

        elif booking.status.lower() == "rescheduled":

            body = (
                f"Your consultation booking "
                f"{booking.booking_id} has been rescheduled."
            )

        else:

            body = (
                f"Booking status changed to "
                f"{booking.status}"
            )

        print("TITLE:", title)
        print("BODY:", body)

        try:

            result = send_push(
                user.fcm_token,
                title,
                body,
                {
                    "route": "/my-consultations"
                }
            )

            print("PUSH SENT SUCCESSFULLY")
            print("FIREBASE RESPONSE:", result)

        except Exception as e:

            print("PUSH ERROR")
            print(str(e))

    # ====================================
    # ACTIVITY LOG
    # ====================================

    add_activity(
        booking.user_mobile,
        "consultation_status",
        "Consultation Status Updated",
        f"Booking status changed to {booking.status}"
    )

    print("ACTIVITY ADDED")

    return jsonify({
        "status": "success"
    })

@consultant_bp.route("/reschedule-booking", methods=["POST"])
def reschedule_booking():
    data = request.json

    booking = Booking.query.filter_by(booking_id=data.get("booking_id")).first()

    if not booking:
        return jsonify({"status": "error"}), 404

    booking.date = data.get("date")
    booking.time = data.get("time")

    db.session.commit()

    user = User.query.filter_by(
        mobile=booking.user_mobile
    ).first()

    if user and user.fcm_token:

        send_push(
            user.fcm_token,
            "Consultation Rescheduled",
            f"Your consultation has been moved to {booking.date} {booking.time}."
        )

    add_activity(
        booking.user_mobile,
        "consultation_reschedule",
        "Consultation Rescheduled",
        f"Consultation moved to {booking.date} {booking.time}"
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