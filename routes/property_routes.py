from flask import Blueprint, request, jsonify
from models.property import Property, PropertyEnquiry
from extensions import db
import random
import cloudinary.uploader
import json
from sqlalchemy import desc
from services.activity_service import add_activity
from services.sms_service import send_property_enquiry_sms
import math

property_bp = Blueprint("property", __name__)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)

    a = (
        math.sin(dLat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dLon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def generate_property_id():
    return "PROP" + str(random.randint(10000000, 99999999))

@property_bp.route("/add-property", methods=["POST"])
def add_property():
    data = request.json

    property_id = generate_property_id()

    new_property = Property(
        property_id=property_id,
        title=data.get("title"),
        property_type=(
            data.get("category")
            or data.get("propertyType")
            or "residential"
        ).lower().strip(),
        purpose=data.get("purpose"),
        city=data.get("city"),
        locality=data.get("locality"),
        price=data.get("price"),
        size=data.get("size"),
        bedrooms=data.get("bedrooms"),
        bathrooms=data.get("bathrooms"),
        description=data.get("description"),
        name=data.get("name"),
        mobile=data.get("mobile"),
        email=data.get("email"),
        listing_type="normal",

        # ✅ MEDIA
        photos=json.dumps(data.get("photos") or []),
        videos=json.dumps(data.get("videos") or []),
        floor_plans=json.dumps(data.get("floorPlans") or []),

        # ✅ 🔥 MAIN FIX (STORE EVERYTHING HERE)
        features=json.dumps({
            "highlights": data.get("features", {}).get("highlights", []),
            "facilities": data.get("features", {}).get("facilities", []),

            "extra": {
                "project_name": data.get("projectName"),
                "balconies": data.get("balconies"),
                "floor_number": data.get("floorNumber"),
                "furnishing": data.get("furnishingStatus"),
                "parking": data.get("parking"),
                "power_backup": data.get("powerBackup"),
                "construction_status": data.get("constructionStatus"),
                "possession": data.get("possession"),
                "builder": data.get("builder"),
            }
        })
    )

    db.session.add(new_property)
    db.session.commit()
    add_activity(
        data.get("mobile"),
        "property",
        "Property Listed",
        f"{data.get('title')} was submitted successfully"
    )

    return jsonify({
        "status": "success",
        "property_id": property_id
    })

@property_bp.route("/upload-image", methods=["POST"])
def upload_image():
    file = request.files.get("file")

    if not file:
        return jsonify({"status": "error", "message": "No file"}), 400

    # ✅ size check
    if request.content_length and request.content_length > 10 * 1024 * 1024:
        return jsonify({
            "status": "error",
            "message": "File too large (max 10MB)"
        }), 400
    
    if not file.mimetype.startswith(("image", "video")) and file.mimetype != "application/pdf":
        return jsonify({
            "status": "error",
            "message": "Unsupported file type"
        }), 400

    try:
        # ✅ TYPE DETECTION (MAIN FIX)
        if file.mimetype.startswith("video"):
            result = cloudinary.uploader.upload(file, resource_type="video")

        elif file.mimetype == "application/pdf":
            result = cloudinary.uploader.upload(file, resource_type="raw")

        else:
            result = cloudinary.uploader.upload(file, resource_type="image")

        return jsonify({
            "status": "success",
            "url": result["secure_url"]
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
@property_bp.route("/properties", methods=["GET"])
def get_properties():
    properties = Property.query.filter_by(status="approved").all()

    result = []
    for p in properties:

        # ✅ SAFE PARSE FEATURES
        try:
            features = json.loads(p.features) if p.features else {}
        except:
            features = {}

        result.append({
            "id": p.id,
            "title": p.title,

            "property_type": p.property_type,

            "city": p.city,
            "locality": p.locality,
            "location": f"{p.locality}, {p.city}",

            "price": p.price,
            "beds": p.bedrooms,
            "baths": p.bathrooms,
            "area": p.size,
            "purpose": p.purpose,
            "type": "buy",
            "image": json.loads(p.photos)[0] if p.photos else "",
            "mobile": p.mobile,
            "listing_type": p.listing_type,
            "features": features
        })

    return jsonify(result)

@property_bp.route("/properties/nearby", methods=["GET"])
def nearby_properties():

    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)

    print("USER LOCATION:", lat, lng)

    if lat is None or lng is None:
        return jsonify({
            "status": "error",
            "message": "Latitude & Longitude required"
        }), 400

    properties = Property.query.filter_by(status="approved").all()

    # Increase radius until enough properties are found
    radius = 10
    max_radius = 100
    required_count = 20

    nearby = []

    while radius <= max_radius:

        nearby = []

        for p in properties:

            if not p.latitude or not p.longitude:
                continue

            distance = haversine(
                lat,
                lng,
                p.latitude,
                p.longitude
            )

            if distance <= radius:

                try:
                    features = json.loads(p.features) if p.features else {}
                except:
                    features = {}

                nearby.append({
                    "id": p.id,
                    "title": p.title,
                    "location": f"{p.locality}, {p.city}",
                    "price": p.price,
                    "beds": p.bedrooms,
                    "baths": p.bathrooms,
                    "area": p.size,
                    "image": json.loads(p.photos)[0] if p.photos else "",
                    "distance": round(distance, 2),
                    "features": features,
                    "property_type": p.property_type,
                })

        if len(nearby) >= required_count:
            break

        radius += 10

    nearby.sort(key=lambda x: x["distance"])

    return jsonify({
        "status": "success",
        "count": len(nearby),
        "data": nearby
    })

@property_bp.route("/property/<int:id>", methods=["GET"])
def get_property(id):
    property = Property.query.get(id)

    if not property:
        return jsonify({"status": "error"}), 404

    # ✅ SAFE JSON PARSE
    try:
        features = json.loads(property.features) if property.features else {}
    except:
        features = {}

    extra = features.get("extra", {})

    mobile = request.args.get("mobile")

    if mobile:
        add_activity(
            mobile,
            "view",
            "Viewed Property",
            property.title
        )

    return jsonify({
        "status": "success",
        "data": {
            "id": property.id,
            "property_id": property.property_id,
            "title": property.title,
            "location": f"{property.locality}, {property.city}",
            "price": property.price,
            "beds": property.bedrooms,
            "baths": property.bathrooms,
            "area": property.size,
            "description": property.description,
            "property_type": property.property_type,
            "photos": json.loads(property.photos) if property.photos else [],
            "videos": json.loads(property.videos) if property.videos else [],
            "floor_plans": json.loads(property.floor_plans) if property.floor_plans else [],

            # ✅ FULL FEATURES JSON
            "features": features,

            # ✅ EXTRA FIELDS (FROM JSON)
            "project_name": extra.get("project_name"),
            "balconies": extra.get("balconies"),
            "floor_number": extra.get("floor_number"),
            "furnishing": extra.get("furnishing"),
            "parking": extra.get("parking"),
            "power_backup": extra.get("power_backup"),
            "construction_status": extra.get("construction_status"),
            "possession": extra.get("possession"),
            "builder": extra.get("builder"),

            "name": property.name,
            "mobile": property.mobile,
            "email": property.email
        }
    })


@property_bp.route("/schedule-visit", methods=["POST"])
def schedule_visit():
    data = request.json

    enquiry = PropertyEnquiry(
        property_id=data.get("property_id"),
        property_title=data.get("property_title"),
        name=data.get("name"),
        mobile=data.get("mobile"),
        email=data.get("email"),
        message=data.get("message"),
    )

    db.session.add(enquiry)
    db.session.commit()

    property = Property.query.get(
        data.get("property_id")
    )

    if property:

        print("\n========== BEFORE SMS CALL ==========")
        print("Owner Mobile:", property.mobile)
        print("Property Title:", property.title)
        print("Customer Mobile:", data.get("mobile"))

        sms_result = send_property_enquiry_sms(
            owner_mobile=property.mobile,
            property_title=property.title,
            customer_mobile=data.get("mobile")
        )

        print("\n========== SMS RESULT ==========")
        print(sms_result)

    add_activity(
        data.get("mobile"),
        "visit",
        "Property Visit Scheduled",
        f"Visit scheduled for {data.get('property_title')}"
    )

    return jsonify({
        "status": "success",
        "message": "Enquiry submitted successfully"
    })

@property_bp.route("/my-properties", methods=["GET"])
def my_properties():

    mobile = request.args.get("mobile")

    if not mobile:
        return jsonify({
            "status": "error",
            "message": "Mobile required"
        }), 400

    properties = Property.query.filter_by(
        mobile=mobile
    ).order_by(Property.id.desc()).all()

    result = []

    for p in properties:

        try:
            photos = json.loads(p.photos) if p.photos else []
        except:
            photos = []

        result.append({
            "id": p.id,
            "property_id": p.property_id,
            "title": p.title,
            "location": f"{p.locality}, {p.city}",
            "price": p.price,
            "status": p.status,
            "image": photos[0] if len(photos) > 0 else "",
            "created_at": str(p.created_at) if hasattr(p, "created_at") else ""
        })

    return jsonify({
        "status": "success",
        "data": result
    })