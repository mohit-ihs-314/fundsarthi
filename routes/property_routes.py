from flask import Blueprint, request, jsonify
from models.property import Property, PropertyEnquiry
from extensions import db
import random
import cloudinary.uploader
import json
from sqlalchemy import or_
from services.activity_service import add_activity
from services.sms_service import send_property_enquiry_sms
import math


property_bp = Blueprint("property", __name__)


# ============================================================
# DISTANCE
# ============================================================

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


# ============================================================
# PROPERTY ID
# ============================================================

def generate_property_id():
    return "PROP" + str(random.randint(10000000, 99999999))


# ============================================================
# ADD PROPERTY
# ============================================================

@property_bp.route("/add-property", methods=["POST"])
def add_property():

    data = request.json or {}

    property_id = generate_property_id()

    new_property = Property(
        property_id=property_id,

        title=data.get("title"),

        property_type=(
            data.get("propertyType")
            or data.get("category")
            or "residential"
        ).lower().strip(),

        category=(
            data.get("category")
            or ""
        ).strip(),

        purpose=data.get("purpose"),

        city=data.get("city"),

        locality=data.get("locality"),

        latitude=data.get("latitude"),

        longitude=data.get("longitude"),

        price=data.get("price"),

        size=data.get("size"),

        bedrooms=data.get("bedrooms"),

        bathrooms=data.get("bathrooms"),

        description=data.get("description"),

        name=data.get("name"),

        mobile=data.get("mobile"),

        email=data.get("email"),

        listing_type="normal",

        photos=json.dumps(
            data.get("photos") or []
        ),

        videos=json.dumps(
            data.get("videos") or []
        ),

        floor_plans=json.dumps(
            data.get("floorPlans") or []
        ),

        features=json.dumps({

            "highlights": (
                data.get("features", {})
                .get("highlights", [])
            ),

            "facilities": (
                data.get("features", {})
                .get("facilities", [])
            ),

            "extra": {

                "category": data.get("category"),

                "property_type": data.get("propertyType"),

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


# ============================================================
# UPLOAD IMAGE / VIDEO / PDF
# ============================================================

@property_bp.route("/upload-image", methods=["POST"])
def upload_image():

    file = request.files.get("file")

    if not file:
        return jsonify({
            "status": "error",
            "message": "No file"
        }), 400

    if (
        request.content_length
        and request.content_length > 10 * 1024 * 1024
    ):
        return jsonify({
            "status": "error",
            "message": "File too large (max 10MB)"
        }), 400

    if (
        not file.mimetype.startswith(("image", "video"))
        and file.mimetype != "application/pdf"
    ):
        return jsonify({
            "status": "error",
            "message": "Unsupported file type"
        }), 400

    try:

        if file.mimetype.startswith("video"):

            result = cloudinary.uploader.upload(
                file,
                resource_type="video"
            )

        elif file.mimetype == "application/pdf":

            result = cloudinary.uploader.upload(
                file,
                resource_type="raw"
            )

        else:

            result = cloudinary.uploader.upload(
                file,
                resource_type="image"
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


# ============================================================
# GET PROPERTIES
# ============================================================
#
# IMPORTANT PERFORMANCE CHANGE:
#
# We DO NOT use:
#
#     query.paginate(...)
#
# because paginate() performs a COUNT(*) query.
#
# The frontend only needs:
#
#     12 properties
#     +
#     has_next
#
# Therefore we fetch 13 records.
#
# 12 = display
# 13th = tells us another page exists
#
# This removes the unnecessary COUNT query.
# ============================================================

@property_bp.route("/properties", methods=["GET"])
def get_properties():

    # ========================================================
    # PAGINATION
    # ========================================================

    page = request.args.get(
        "page",
        1,
        type=int
    )

    limit = request.args.get(
        "limit",
        12,
        type=int
    )

    page = max(page, 1)

    limit = min(
        max(limit, 1),
        50
    )

    offset = (page - 1) * limit

    # Fetch one extra property.
    fetch_limit = limit + 1

    # ========================================================
    # FILTERS
    # ========================================================

    category = request.args.get("category")

    city = request.args.get("city")

    locality = request.args.get("locality")

    builder = request.args.get("builder")

    bhk = request.args.get("bhk")

    min_price = request.args.get(
        "min_price",
        type=float
    )

    max_price = request.args.get(
        "max_price",
        type=float
    )

    search = request.args.get("search")

    sort = request.args.get("sort")

    # ========================================================
    # BASE QUERY
    # ========================================================

    query = Property.query.filter(
        Property.status == "approved"
    )

    # ========================================================
    # CATEGORY
    # ========================================================

    if category:

        query = query.filter(
            Property.category.ilike(
                f"%{category}%"
            )
        )

    # ========================================================
    # CITY
    # ========================================================

    if city:

        query = query.filter(
            Property.city.ilike(
                f"%{city}%"
            )
        )

    # ========================================================
    # LOCALITY
    # ========================================================

    if locality:

        query = query.filter(
            Property.locality.ilike(
                f"%{locality}%"
            )
        )

    # ========================================================
    # SEARCH
    # ========================================================

    if search:

        search_term = f"%{search}%"

        query = query.filter(
            or_(
                Property.title.ilike(search_term),

                Property.city.ilike(search_term),

                Property.locality.ilike(search_term)
            )
        )

    # ========================================================
    # PRICE
    # ========================================================

    if min_price is not None:

        query = query.filter(
            Property.price >= min_price
        )

    if max_price is not None:

        query = query.filter(
            Property.price <= max_price
        )

    # ========================================================
    # BUILDER
    # ========================================================
    #
    # Builder is stored inside features JSON.
    #
    # Keep this filter compatible with existing data.
    # ========================================================

    if builder:

        query = query.filter(
            Property.features.ilike(
                f"%{builder}%"
            )
        )

    # ========================================================
    # BHK
    # ========================================================

    if bhk:

        query = query.filter(
            Property.bedrooms == bhk
        )

    # ========================================================
    # SORT
    # ========================================================

    if sort == "lowToHigh":

        query = query.order_by(
            Property.price.asc(),
            Property.id.desc()
        )

    elif sort == "highToLow":

        query = query.order_by(
            Property.price.desc(),
            Property.id.desc()
        )

    else:

        # Most important/default listing query.
        #
        # Database index should be:
        #
        # (status, id DESC)
        #
        query = query.order_by(
            Property.id.desc()
        )

    # ========================================================
    # FAST PAGINATION
    # ========================================================

    properties = (
        query
        .offset(offset)
        .limit(fetch_limit)
        .all()
    )

    # ========================================================
    # HAS NEXT
    # ========================================================

    has_next = len(properties) > limit

    # Remove the extra row.
    if has_next:

        properties = properties[:limit]

    # ========================================================
    # RESPONSE
    # ========================================================

    result = []

    for p in properties:

        # ====================================================
        # FEATURES
        # ====================================================

        try:

            features = (
                json.loads(p.features)
                if p.features
                else {}
            )

        except Exception:

            features = {}

        if not isinstance(features, dict):

            features = {}

        extra = features.get(
            "extra",
            {}
        )

        if not isinstance(extra, dict):

            extra = {}

        features["extra"] = extra

        # ====================================================
        # CATEGORY
        # ====================================================

        category_value = (
            p.category
            or extra.get("category")
            or ""
        ).strip()

        if not category_value:

            property_type_lower = str(
                p.property_type or ""
            ).lower().strip()

            if (
                "sco" in property_type_lower
                and "plot" in property_type_lower
            ):

                category_value = "SCO Plot"

            elif (
                "commercial" in property_type_lower
                and "plot" in property_type_lower
            ):

                category_value = "Commercial Plot"

            elif (
                "residential" in property_type_lower
                and "plot" in property_type_lower
            ):

                category_value = "Residential Plot"

            elif property_type_lower in [
                "plot",
                "land",
                "land / plot",
                "land/plot"
            ]:

                category_value = "Residential Plot"

        extra["category"] = category_value

        # ====================================================
        # PHOTOS
        # ====================================================

        try:

            photos = (
                json.loads(p.photos)
                if p.photos
                else []
            )

        except Exception:

            photos = []

        # ====================================================
        # RESPONSE OBJECT
        # ====================================================

        result.append({

            "id": p.id,

            "property_id": p.property_id,

            "title": p.title,

            "property_type": p.property_type,

            "category": category_value,

            "city": p.city,

            "locality": p.locality,

            "location": (
                f"{p.locality}, {p.city}"
            ),

            "price": p.price,

            "beds": p.bedrooms,

            "baths": p.bathrooms,

            "area": p.size,

            "purpose": p.purpose,

            "type": "buy",

            "image": (
                photos[0]
                if photos
                else ""
            ),

            "mobile": p.mobile,

            "listing_type": p.listing_type,

            "features": features,

            # CRM promotion flags

            "is_hot_deal": bool(
                p.is_hot_deal
            ),

            "is_trending": bool(
                p.is_trending
            ),

            "hot_deal_order": (
                p.hot_deal_order or 0
            ),

            "trending_order": (
                p.trending_order or 0
            ),
        })

    # ========================================================
    # RESPONSE
    # ========================================================
    #
    # IMPORTANT:
    #
    # total/pages are intentionally removed.
    #
    # The frontend only needs has_next.
    # ========================================================

    return jsonify({

        "status": "success",

        "data": result,

        "pagination": {

            "page": page,

            "limit": limit,

            "has_next": has_next,

            "has_prev": page > 1
        }
    })


# ============================================================
# NEARBY PROPERTIES
# ============================================================
#
# This endpoint is NOT used for the main listing.
#
# The previous version loaded EVERY approved Property object
# into memory:
#
#     Property.query.filter_by(...).all()
#
# We at least restrict the columns to only what is needed.
#
# The best long-term solution is a database geographic query,
# but this version preserves your existing Haversine behavior.
# ============================================================

@property_bp.route("/properties/nearby", methods=["GET"])
def nearby_properties():

    lat = request.args.get(
        "lat",
        type=float
    )

    lng = request.args.get(
        "lng",
        type=float
    )

    print(
        "USER LOCATION:",
        lat,
        lng
    )

    if lat is None or lng is None:

        return jsonify({
            "status": "error",
            "message": "Latitude & Longitude required"
        }), 400

    # Only select fields required by nearby.
    properties = (
        db.session.query(
            Property.id,
            Property.title,
            Property.locality,
            Property.city,
            Property.price,
            Property.bedrooms,
            Property.bathrooms,
            Property.size,
            Property.photos,
            Property.features,
            Property.property_type,
            Property.latitude,
            Property.longitude,
        )
        .filter(
            Property.status == "approved"
        )
        .filter(
            Property.latitude.isnot(None)
        )
        .filter(
            Property.longitude.isnot(None)
        )
        .all()
    )

    # ========================================================
    # RADIUS
    # ========================================================

    radius = 10

    max_radius = 100

    required_count = 20

    nearby = []

    # ========================================================
    # FIND NEARBY
    # ========================================================

    while radius <= max_radius:

        nearby = []

        for p in properties:

            if (
                p.latitude is None
                or p.longitude is None
            ):
                continue

            distance = haversine(
                lat,
                lng,
                p.latitude,
                p.longitude
            )

            if distance <= radius:

                try:

                    features = (
                        json.loads(p.features)
                        if p.features
                        else {}
                    )

                except Exception:

                    features = {}

                if not isinstance(
                    features,
                    dict
                ):

                    features = {}

                extra = features.setdefault(
                    "extra",
                    {}
                )

                if not isinstance(
                    extra,
                    dict
                ):

                    extra = {}

                    features["extra"] = extra

                category = (
                    extra.get("category")
                    or getattr(
                        p,
                        "category",
                        None
                    )
                    or ""
                )

                # Safe photo parsing
                try:

                    photos = (
                        json.loads(p.photos)
                        if p.photos
                        else []
                    )

                except Exception:

                    photos = []

                nearby.append({

                    "id": p.id,

                    "title": p.title,

                    "location": (
                        f"{p.locality}, {p.city}"
                    ),

                    "price": p.price,

                    "beds": p.bedrooms,

                    "baths": p.bathrooms,

                    "area": p.size,

                    "image": (
                        photos[0]
                        if photos
                        else ""
                    ),

                    "distance": round(
                        distance,
                        2
                    ),

                    "features": features,

                    "property_type": (
                        p.property_type
                    ),

                    "category": category,
                })

        if len(nearby) >= required_count:

            break

        radius += 10

    # ========================================================
    # SORT
    # ========================================================

    nearby.sort(
        key=lambda x: x["distance"]
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    return jsonify({

        "status": "success",

        "count": len(nearby),

        "data": nearby
    })


# ============================================================
# SINGLE PROPERTY
# ============================================================

@property_bp.route("/property/<int:id>", methods=["GET"])
def get_property(id):

    property = Property.query.get(id)

    if not property:

        return jsonify({
            "status": "error"
        }), 404

    # ========================================================
    # FEATURES
    # ========================================================

    try:

        features = (
            json.loads(property.features)
            if property.features
            else {}
        )

    except Exception:

        features = {}

    if not isinstance(
        features,
        dict
    ):

        features = {}

    extra = features.get(
        "extra",
        {}
    )

    if not isinstance(
        extra,
        dict
    ):

        extra = {}

    # ========================================================
    # ACTIVITY
    # ========================================================

    mobile = request.args.get(
        "mobile"
    )

    if mobile:

        add_activity(
            mobile,
            "view",
            "Viewed Property",
            property.title
        )

    # ========================================================
    # SAFE MEDIA PARSING
    # ========================================================

    try:

        photos = (
            json.loads(property.photos)
            if property.photos
            else []
        )

    except Exception:

        photos = []

    try:

        videos = (
            json.loads(property.videos)
            if property.videos
            else []
        )

    except Exception:

        videos = []

    try:

        floor_plans = (
            json.loads(property.floor_plans)
            if property.floor_plans
            else []
        )

    except Exception:

        floor_plans = []

    # ========================================================
    # RESPONSE
    # ========================================================

    return jsonify({

        "status": "success",

        "data": {

            "id": property.id,

            "property_id": property.property_id,

            "title": property.title,

            "location": (
                f"{property.locality}, "
                f"{property.city}"
            ),

            "price": property.price,

            "beds": property.bedrooms,

            "baths": property.bathrooms,

            "area": property.size,

            "description": property.description,

            "property_type": property.property_type,

            "photos": photos,

            "videos": videos,

            "floor_plans": floor_plans,

            "features": features,

            # Extra fields

            "project_name": (
                extra.get("project_name")
            ),

            "balconies": (
                extra.get("balconies")
            ),

            "floor_number": (
                extra.get("floor_number")
            ),

            "furnishing": (
                extra.get("furnishing")
            ),

            "parking": (
                extra.get("parking")
            ),

            "power_backup": (
                extra.get("power_backup")
            ),

            "construction_status": (
                extra.get(
                    "construction_status"
                )
            ),

            "possession": (
                extra.get("possession")
            ),

            "builder": (
                extra.get("builder")
            ),

            "name": property.name,

            "mobile": property.mobile,

            "email": property.email
        }
    })


# ============================================================
# SCHEDULE VISIT
# ============================================================

@property_bp.route("/schedule-visit", methods=["POST"])
def schedule_visit():

    data = request.json or {}

    enquiry = PropertyEnquiry(

        property_id=data.get(
            "property_id"
        ),

        property_title=data.get(
            "property_title"
        ),

        name=data.get(
            "name"
        ),

        mobile=data.get(
            "mobile"
        ),

        email=data.get(
            "email"
        ),

        message=data.get(
            "message"
        ),
    )

    db.session.add(enquiry)

    db.session.commit()

    property = Property.query.get(
        data.get("property_id")
    )

    if property:

        print(
            "\n========== BEFORE SMS CALL =========="
        )

        print(
            "Owner Mobile:",
            property.mobile
        )

        print(
            "Property Title:",
            property.title
        )

        print(
            "Customer Mobile:",
            data.get("mobile")
        )

        sms_result = send_property_enquiry_sms(

            owner_mobile=property.mobile,

            property_title=property.title,

            customer_mobile=data.get(
                "mobile"
            )
        )

        print(
            "\n========== SMS RESULT =========="
        )

        print(
            sms_result
        )

    add_activity(

        data.get("mobile"),

        "visit",

        "Property Visit Scheduled",

        (
            "Visit scheduled for "
            f"{data.get('property_title')}"
        )
    )

    return jsonify({

        "status": "success",

        "message": "Enquiry submitted successfully"
    })


# ============================================================
# MY PROPERTIES
# ============================================================

@property_bp.route("/my-properties", methods=["GET"])
def my_properties():

    mobile = request.args.get(
        "mobile"
    )

    if not mobile:

        return jsonify({

            "status": "error",

            "message": "Mobile required"

        }), 400

    properties = (
        Property.query
        .filter_by(
            mobile=mobile
        )
        .order_by(
            Property.id.desc()
        )
        .all()
    )

    result = []

    for p in properties:

        try:

            photos = (
                json.loads(p.photos)
                if p.photos
                else []
            )

        except Exception:

            photos = []

        result.append({

            "id": p.id,

            "property_id": p.property_id,

            "title": p.title,

            "location": (
                f"{p.locality}, {p.city}"
            ),

            "price": p.price,

            "status": p.status,

            "image": (
                photos[0]
                if len(photos) > 0
                else ""
            ),

            "created_at": (
                str(p.created_at)
                if hasattr(
                    p,
                    "created_at"
                )
                else ""
            )
        })

    return jsonify({

        "status": "success",

        "data": result
    })