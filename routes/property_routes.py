from flask import Blueprint, request, jsonify
from models.property import Property, PropertyEnquiry
from extensions import db
import random
import cloudinary.uploader
import json

property_bp = Blueprint("property", __name__)

def generate_property_id():
    return "PROP" + str(random.randint(10000000, 99999999))

@property_bp.route("/add-property", methods=["POST"])
def add_property():
    data = request.json

    property_id = generate_property_id()

    new_property = Property(
        property_id=property_id,
        title=data.get("title"),
        property_type=data.get("propertyType"),
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
            }
        })
    )

    db.session.add(new_property)
    db.session.commit()

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
        result.append({
            "id": p.id,
            "title": p.title,
            "location": f"{p.locality}, {p.city}",
            "price": int(p.price),
            "beds": p.bedrooms,
            "baths": p.bathrooms,
            "area": p.size,
            "purpose": p.purpose,
            "type": "buy",
            "image": json.loads(p.photos)[0] if p.photos else ""
        })

    return jsonify(result)

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
        visit_date=data.get("visit_date"),
        message=data.get("message"),
    )

    db.session.add(enquiry)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Enquiry submitted successfully"
    })