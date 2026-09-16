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
import os
import tempfile
import time

property_bp = Blueprint("property", __name__)


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def generate_property_id():
    return "PROP" + str(random.randint(10000000, 99999999))


# ============================================================
# PROPERTY SERIALIZATION / CLASSIFICATION
# ============================================================


def _normalize_property_text(value):
    if value is None:
        return ""
    return (
        str(value)
        .lower()
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
    )


def _property_feature_data(property_obj):
    try:
        features = json.loads(property_obj.features) if property_obj.features else {}
    except Exception:
        features = {}
    if not isinstance(features, dict):
        features = {}
    extra = features.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}
    features["extra"] = extra
    return features, extra


def is_residential_property(property_obj):
    features, extra = _property_feature_data(property_obj)
    category = _normalize_property_text(
        getattr(property_obj, "category", None) or extra.get("category")
    )
    property_type = _normalize_property_text(
        getattr(property_obj, "property_type", None) or extra.get("property_type")
    )
    text = f"{category} {property_type}".strip()

    is_plot = "plot" in text or "land" in text
    is_sco = (
        "sco" in text
        or "shop cum office" in text
        or "shop-cum-office" in text
    )
    is_commercial = any(
        word in text
        for word in (
            "commercial",
            "office",
            "shop",
            "retail",
            "warehouse",
            "showroom",
            "industrial",
        )
    )
    return not (is_plot or is_sco or is_commercial)


def serialize_property_listing(property_obj):
    features, extra = _property_feature_data(property_obj)

    category_value = (
        getattr(property_obj, "category", None)
        or extra.get("category")
        or ""
    ).strip()

    if not category_value:
        property_type_lower = str(
            getattr(property_obj, "property_type", None) or ""
        ).lower().strip()
        if "sco" in property_type_lower and "plot" in property_type_lower:
            category_value = "SCO Plot"
        elif "commercial" in property_type_lower and "plot" in property_type_lower:
            category_value = "Commercial Plot"
        elif "residential" in property_type_lower and "plot" in property_type_lower:
            category_value = "Residential Plot"
        elif property_type_lower in {"plot", "land", "land / plot", "land/plot"}:
            category_value = "Residential Plot"

    extra["category"] = category_value

    try:
        photos = json.loads(property_obj.photos) if property_obj.photos else []
    except Exception:
        photos = []
    if not isinstance(photos, list):
        photos = []

    return {
        "id": property_obj.id,
        "property_id": property_obj.property_id,
        "title": property_obj.title,
        "property_type": property_obj.property_type,
        "category": category_value,
        "city": property_obj.city,
        "locality": property_obj.locality,
        "location": f"{property_obj.locality or ''}, {property_obj.city or ''}".strip(", "),
        "price": property_obj.price,
        "beds": property_obj.bedrooms,
        "baths": property_obj.bathrooms,
        "area": property_obj.size,
        "purpose": property_obj.purpose,
        "type": "buy",
        "image": photos[0] if photos else "",
        "mobile": property_obj.mobile,
        "listing_type": property_obj.listing_type,
        "features": features,
        "is_hot_deal": bool(getattr(property_obj, "is_hot_deal", False)),
        "is_trending": bool(getattr(property_obj, "is_trending", False)),
        "hot_deal_order": getattr(property_obj, "hot_deal_order", None) or 0,
        "trending_order": getattr(property_obj, "trending_order", None) or 0,
    }


# ============================================================
# INSTANT RESIDENTIAL CACHE
# ============================================================

INSTANT_RESIDENTIAL_CACHE_LIMIT = 100
INSTANT_RESIDENTIAL_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "cache"
)
INSTANT_RESIDENTIAL_CACHE_FILE = os.path.join(
    INSTANT_RESIDENTIAL_CACHE_DIR, "residential_featured.json"
)


def _write_instant_residential_cache(data):
    os.makedirs(INSTANT_RESIDENTIAL_CACHE_DIR, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(
        prefix="residential_featured_",
        suffix=".tmp",
        dir=INSTANT_RESIDENTIAL_CACHE_DIR,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(
                {
                    "status": "success",
                    "count": len(data),
                    "limit": INSTANT_RESIDENTIAL_CACHE_LIMIT,
                    "data": data,
                },
                temp_file,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, INSTANT_RESIDENTIAL_CACHE_FILE)
    except Exception:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


def rebuild_instant_residential_cache(limit=INSTANT_RESIDENTIAL_CACHE_LIMIT):
    limit = max(1, min(int(limit), INSTANT_RESIDENTIAL_CACHE_LIMIT))
    residential = []
    batch_size = 500
    offset = 0

    while len(residential) < limit:
        candidates = (
            Property.query
            .filter(Property.status == "approved")
            .order_by(Property.id.desc())
            .offset(offset)
            .limit(batch_size)
            .all()
        )
        if not candidates:
            break

        for property_obj in candidates:
            if not is_residential_property(property_obj):
                continue
            residential.append(serialize_property_listing(property_obj))
            if len(residential) >= limit:
                break

        if len(candidates) < batch_size:
            break
        offset += batch_size

    _write_instant_residential_cache(residential)
    print("[Instant Residential Cache] rebuilt", {
        "file": INSTANT_RESIDENTIAL_CACHE_FILE,
        "count": len(residential),
    })
    return residential


def read_instant_residential_cache():
    try:
        with open(INSTANT_RESIDENTIAL_CACHE_FILE, "r", encoding="utf-8") as cache_file:
            payload = json.load(cache_file)
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, list) and len(data) >= INSTANT_RESIDENTIAL_CACHE_LIMIT:
            return data[:INSTANT_RESIDENTIAL_CACHE_LIMIT]
    except Exception as error:
        print("[Instant Residential Cache] read failed; rebuilding:", error)
    return rebuild_instant_residential_cache()


@property_bp.route("/properties/instant-residential", methods=["GET"])
def instant_residential_properties():
    started = time.perf_counter()
    data = read_instant_residential_cache()
    response = jsonify({
        "status": "success",
        "count": len(data),
        "data": data,
        "source": "server_cache",
    })
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    print("[Instant Residential API]", {
        "count": len(data),
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
    })
    return response


# ============================================================
# CATEGORY FILTER
# ============================================================


def normalized_category_text():
    category_column = func.lower(func.coalesce(Property.category, ""))
    property_type_column = func.lower(func.coalesce(Property.property_type, ""))
    return func.concat(category_column, " ", property_type_column)


def apply_tab_filter(query, tab):
    if not tab:
        return query

    tab = str(tab).lower().strip()
    text = normalized_category_text()

    is_plot = or_(text.like("%plot%"), text.like("%land%"))
    is_sco = or_(
        text.like("%sco%"),
        text.like("%shop cum office%"),
        text.like("%shop-cum-office%"),
    )
    is_commercial = or_(
        text.like("%commercial%"),
        text.like("%office%"),
        text.like("%shop%"),
        text.like("%retail%"),
        text.like("%warehouse%"),
        text.like("%showroom%"),
        text.like("%industrial%"),
    )

    if tab in ("plot", "plots", "land", "land/plot", "land / plot"):
        return query.filter(is_plot)
    if tab in ("sco", "sco plot"):
        return query.filter(and_(is_sco, ~is_plot))
    if tab in ("commercial", "commercials"):
        return query.filter(and_(is_commercial, ~is_plot, ~is_sco))
    if tab in ("residential", "residentials"):
        return query.filter(and_(~is_plot, ~is_sco, ~is_commercial))
    return query


# ============================================================
# ADD PROPERTY
# ============================================================

@property_bp.route("/add-property", methods=["POST"])
def add_property():
    data = request.json or {}
    features_data = data.get("features") or {}
    if not isinstance(features_data, dict):
        features_data = {}

    new_property = Property(
        property_id=generate_property_id(),
        title=data.get("title"),
        property_type=(data.get("propertyType") or data.get("category") or "residential").lower().strip(),
        category=(data.get("category") or "").strip(),
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
        photos=json.dumps(data.get("photos") or []),
        videos=json.dumps(data.get("videos") or []),
        floor_plans=json.dumps(data.get("floorPlans") or []),
        features=json.dumps({
            "highlights": features_data.get("highlights", []),
            "facilities": features_data.get("facilities", []),
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
            },
        }),
    )

    db.session.add(new_property)
    db.session.commit()

    try:
        rebuild_instant_residential_cache()
    except Exception as cache_error:
        print("[Instant Residential Cache] rebuild after add-property failed:", cache_error)

    add_activity(
        data.get("mobile"),
        "property",
        "Property Listed",
        f"{data.get('title')} was submitted successfully",
    )
    return jsonify({"status": "success", "property_id": new_property.property_id})


# ============================================================
# UPLOAD
# ============================================================

@property_bp.route("/upload-image", methods=["POST"])
def upload_image():
    file = request.files.get("file")
    if not file:
        return jsonify({"status": "error", "message": "No file"}), 400
    if request.content_length and request.content_length > 10 * 1024 * 1024:
        return jsonify({"status": "error", "message": "File too large (max 10MB)"}), 400
    if not file.mimetype.startswith(("image", "video")) and file.mimetype != "application/pdf":
        return jsonify({"status": "error", "message": "Unsupported file type"}), 400
    try:
        if file.mimetype.startswith("video"):
            result = cloudinary.uploader.upload(file, resource_type="video")
        elif file.mimetype == "application/pdf":
            result = cloudinary.uploader.upload(file, resource_type="raw")
        else:
            result = cloudinary.uploader.upload(file, resource_type="image")
        return jsonify({"status": "success", "url": result["secure_url"]})
    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500


# ============================================================
# GET PROPERTIES
# ============================================================

@property_bp.route("/properties", methods=["GET"])
def get_properties():
    started = time.perf_counter()
    page = max(request.args.get("page", 1, type=int), 1)
    limit = min(max(request.args.get("limit", 12, type=int), 1), 50)
    offset = (page - 1) * limit

    tab = request.args.get("tab")
    category = request.args.get("category")
    city = request.args.get("city")
    locality = request.args.get("locality")
    builder = request.args.get("builder")
    bhk = request.args.get("bhk")
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    search = request.args.get("search")
    sort = request.args.get("sort")

    query = Property.query.filter(Property.status == "approved")
    query = apply_tab_filter(query, tab)

    if category:
        query = query.filter(Property.category.ilike(f"%{category}%"))
    if city:
        query = query.filter(Property.city.ilike(f"%{city}%"))
    if locality:
        query = query.filter(Property.locality.ilike(f"%{locality}%"))
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            Property.title.ilike(term),
            Property.city.ilike(term),
            Property.locality.ilike(term),
        ))
    if min_price is not None:
        query = query.filter(Property.price >= min_price)
    if max_price is not None:
        query = query.filter(Property.price <= max_price)
    if builder:
        query = query.filter(Property.features.ilike(f"%{builder}%"))
    if bhk:
        query = query.filter(Property.bedrooms == bhk)

    if sort == "lowToHigh":
        query = query.order_by(Property.price.asc(), Property.id.desc())
    elif sort == "highToLow":
        query = query.order_by(Property.price.desc(), Property.id.desc())
    else:
        query = query.order_by(Property.id.desc())

    rows = query.offset(offset).limit(limit + 1).all()
    has_next = len(rows) > limit
    rows = rows[:limit]
    result = [serialize_property_listing(row) for row in rows]

    print("[Property API]", {
        "tab": tab,
        "page": page,
        "limit": limit,
        "returned": len(result),
        "has_next": has_next,
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
    })
    return jsonify({
        "status": "success",
        "data": result,
        "pagination": {
            "page": page,
            "limit": limit,
            "has_next": has_next,
            "has_prev": page > 1,
        },
    })


# ============================================================
# GLOBAL HOT DEALS
# ============================================================
# This endpoint is independent of the Residential cache and category tabs.
# Therefore a Commercial/Plot/SCO Hot Deal can appear immediately too.

@property_bp.route("/properties/hot-deals", methods=["GET"])
def hot_deal_properties():
    started = time.perf_counter()
    limit = min(max(request.args.get("limit", 8, type=int), 1), 20)

    rows = (
        Property.query
        .filter(
            Property.status == "approved",
            Property.is_hot_deal.is_(True),
        )
        .order_by(
            func.coalesce(Property.hot_deal_order, 0).asc(),
            Property.id.desc(),
        )
        .limit(limit)
        .all()
    )

    result = [serialize_property_listing(row) for row in rows]
    response = jsonify({
        "status": "success",
        "count": len(result),
        "data": result,
    })
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=120"
    print("[Hot Deals API]", {
        "count": len(result),
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
    })
    return response


# ============================================================
# NEARBY
# ============================================================

@property_bp.route("/properties/nearby", methods=["GET"])
def nearby_properties():
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    if lat is None or lng is None:
        return jsonify({"status": "error", "message": "Latitude & Longitude required"}), 400

    rows = (
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
            Property.category,
            Property.latitude,
            Property.longitude,
        )
        .filter(Property.status == "approved")
        .filter(Property.latitude.isnot(None))
        .filter(Property.longitude.isnot(None))
        .all()
    )

    radius = 10
    nearby = []
    while radius <= 100:
        nearby = []
        for p in rows:
            distance = haversine(lat, lng, p.latitude, p.longitude)
            if distance > radius:
                continue
            try:
                features = json.loads(p.features) if p.features else {}
            except Exception:
                features = {}
            if not isinstance(features, dict):
                features = {}
            extra = features.get("extra", {})
            if not isinstance(extra, dict):
                extra = {}
            category = extra.get("category") or p.category or ""
            try:
                photos = json.loads(p.photos) if p.photos else []
            except Exception:
                photos = []
            nearby.append({
                "id": p.id,
                "title": p.title,
                "location": f"{p.locality or ''}, {p.city or ''}".strip(", "),
                "price": p.price,
                "beds": p.bedrooms,
                "baths": p.bathrooms,
                "area": p.size,
                "image": photos[0] if photos else "",
                "distance": round(distance, 2),
                "features": features,
                "property_type": p.property_type,
                "category": category,
            })
        if len(nearby) >= 20:
            break
        radius += 10

    nearby.sort(key=lambda item: item["distance"])
    return jsonify({"status": "success", "count": len(nearby), "data": nearby})


# ============================================================
# SINGLE PROPERTY
# ============================================================

@property_bp.route("/property/<int:id>", methods=["GET"])
def get_property(id):
    property_obj = Property.query.get(id)
    if not property_obj:
        return jsonify({"status": "error"}), 404

    features, extra = _property_feature_data(property_obj)
    mobile = request.args.get("mobile")
    if mobile:
        add_activity(mobile, "view", "Viewed Property", property_obj.title)

    def load_json(value):
        try:
            parsed = json.loads(value) if value else []
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []

    return jsonify({
        "status": "success",
        "data": {
            "id": property_obj.id,
            "property_id": property_obj.property_id,
            "title": property_obj.title,
            "location": f"{property_obj.locality or ''}, {property_obj.city or ''}".strip(", "),
            "price": property_obj.price,
            "beds": property_obj.bedrooms,
            "baths": property_obj.bathrooms,
            "area": property_obj.size,
            "description": property_obj.description,
            "property_type": property_obj.property_type,
            "category": property_obj.category or extra.get("category") or "",
            "photos": load_json(property_obj.photos),
            "videos": load_json(property_obj.videos),
            "floor_plans": load_json(property_obj.floor_plans),
            "features": features,
            "project_name": extra.get("project_name"),
            "balconies": extra.get("balconies"),
            "floor_number": extra.get("floor_number"),
            "furnishing": extra.get("furnishing"),
            "parking": extra.get("parking"),
            "power_backup": extra.get("power_backup"),
            "construction_status": extra.get("construction_status"),
            "possession": extra.get("possession"),
            "builder": extra.get("builder"),
            "name": property_obj.name,
            "mobile": property_obj.mobile,
            "email": property_obj.email,
        },
    })


# ============================================================
# SCHEDULE VISIT
# ============================================================

@property_bp.route("/schedule-visit", methods=["POST"])
def schedule_visit():
    data = request.json or {}
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

    property_obj = Property.query.get(data.get("property_id"))
    if property_obj:
        try:
            sms_result = send_property_enquiry_sms(
                owner_mobile=property_obj.mobile,
                property_title=property_obj.title,
                customer_mobile=data.get("mobile"),
            )
            print("[Property Enquiry SMS]", sms_result)
        except Exception as error:
            print("[Property Enquiry SMS] failed:", error)

    add_activity(
        data.get("mobile"),
        "visit",
        "Property Visit Scheduled",
        f"Visit scheduled for {data.get('property_title')}",
    )
    return jsonify({"status": "success", "message": "Enquiry submitted successfully"})


# ============================================================
# MY PROPERTIES
# ============================================================

@property_bp.route("/my-properties", methods=["GET"])
def my_properties():
    mobile = request.args.get("mobile")
    if not mobile:
        return jsonify({"status": "error", "message": "Mobile required"}), 400

    rows = Property.query.filter_by(mobile=mobile).order_by(Property.id.desc()).all()
    result = []
    for p in rows:
        try:
            photos = json.loads(p.photos) if p.photos else []
        except Exception:
            photos = []
        result.append({
            "id": p.id,
            "property_id": p.property_id,
            "title": p.title,
            "location": f"{p.locality or ''}, {p.city or ''}".strip(", "),
            "price": p.price,
            "status": p.status,
            "image": photos[0] if photos else "",
            "created_at": str(p.created_at) if hasattr(p, "created_at") else "",
        })

    return jsonify({"status": "success", "data": result})
