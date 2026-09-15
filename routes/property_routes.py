from flask import Blueprint, request, jsonify
from models.property import Property, PropertyEnquiry
from extensions import db
import random
import cloudinary.uploader
import json
from sqlalchemy import or_, and_, func
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
# CATEGORY / TAB HELPERS
# ============================================================

# IMPORTANT:
# The frontend has four listing tabs:
#   Residential / Commercial / SCO / Plot
#
# Category and property_type are existing DB columns.
# We do NOT require a new DB column for this version.
#
# The frontend can call:
#
#   /properties?tab=residential
#   /properties?tab=commercial
#   /properties?tab=sco
#   /properties?tab=plot
#
# This allows the database to return the requested category
# directly instead of making the frontend download mixed pages
# and classify them after the response arrives.


def normalized_category_text():

    category_column = func.lower(
        func.coalesce(Property.category, "")
    )

    property_type_column = func.lower(
        func.coalesce(Property.property_type, "")
    )

    return func.concat(
        category_column,
        " ",
        property_type_column
    )


def apply_tab_filter(query, tab):

    if not tab:
        return query

    tab = str(tab).lower().strip()

    text = normalized_category_text()

    is_plot = or_(
        text.like("%plot%"),
        text.like("%land%")
    )

    is_sco = or_(
        text.like("%sco%"),
        text.like("%shop cum office%"),
        text.like("%shop-cum-office%")
    )

    is_commercial = or_(
        text.like("%commercial%"),
        text.like("%office%"),
        text.like("%shop%"),
        text.like("%retail%"),
        text.like("%warehouse%"),
        text.like("%showroom%"),
        text.like("%industrial%")
    )

    if tab in ("plot", "plots", "land", "land/plot", "land / plot"):
        return query.filter(is_plot)

    if tab in ("sco", "sco plot"):
        return query.filter(
            and_(
                is_sco,
                ~is_plot
            )
        )

    if tab in ("commercial", "commercials"):
        return query.filter(
            and_(
                is_commercial,
                ~is_plot,
                ~is_sco
            )
        )

    if tab in ("residential", "residentials"):
        # Same rule as the existing frontend:
        # anything that is NOT explicitly Plot / SCO / Commercial
        # remains in Residential.
        return query.filter(
            and_(
                ~is_plot,
                ~is_sco,
                ~is_commercial
            )
        )

    # Unknown tab: do not accidentally return zero records.
    return query


# ============================================================
# GET PROPERTIES
# ============================================================

@property_bp.route("/properties", methods=["GET"])
def get_properties():

    request_started_at = __import__("time").perf_counter()

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

    # Fetch one extra row.
    fetch_limit = limit + 1

    # ========================================================
    # FILTERS
    # ========================================================

    # NEW:
    # tab is specifically for the four frontend tabs.
    #
    # It is different from "category" because the database may
    # contain values such as Apartment, Flat, Villa, Plot, etc.
    tab = request.args.get("tab")

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
    # TAB
    # ========================================================
    #
    # This is the most important performance fix.
    #
    # If the frontend asks:
    #
    #   ?tab=residential
    #
    # the database returns Residential records directly.
    #
    # We no longer need to download page 1, page 2, page 3,
    # page 4 and then classify everything in React just to find
    # Residential properties.
    #
    # Existing "category" filter is still supported below.
    # ========================================================

    query = apply_tab_filter(
        query,
        tab
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

    elapsed_ms = round(
        (__import__("time").perf_counter() - request_started_at) * 1000
    )

    print(
        "[Property API]",
        {
            "tab": tab,
            "category": category,
            "page": page,
            "limit": limit,
            "returned": len(result),
            "has_next": has_next,
            "elapsed_ms": elapsed_ms,
        }
    )

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

    radius = 10
    max_radius = 100
    required_count = 20

    nearby = []

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

                if not isinstance(features, dict):
                    features = {}

                extra = features.setdefault(
                    "extra",
                    {}
                )

                if not isinstance(extra, dict):

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

    nearby.sort(
        key=lambda x: x["distance"]
    )

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

    try:

        features = (
            json.loads(property.features)
            if property.features
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
