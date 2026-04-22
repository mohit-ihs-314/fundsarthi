from extensions import db

class Property(db.Model):
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.String(20), unique=True, nullable=False)

    title = db.Column(db.String(255))
    property_type = db.Column(db.String(50))
    city = db.Column(db.String(100))
    locality = db.Column(db.String(255))

    price = db.Column(db.String(50))
    size = db.Column(db.String(50))

    bedrooms = db.Column(db.String(10))
    bathrooms = db.Column(db.String(10))

    description = db.Column(db.Text)

    name = db.Column(db.String(100))
    mobile = db.Column(db.String(20))
    email = db.Column(db.String(100))

    status = db.Column(db.String(20), default="pending")

    photos = db.Column(db.Text)       # JSON string
    videos = db.Column(db.Text)       # JSON string
    floor_plans = db.Column(db.Text)  # JSON string

    purpose = db.Column(db.String(10))
    features = db.Column(db.Text)


class PropertyEnquiry(db.Model):
    __tablename__ = "property_enquiries"  

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer)
    property_title = db.Column(db.String(255))

    name = db.Column(db.String(100))
    mobile = db.Column(db.String(15))
    email = db.Column(db.String(100))

    visit_date = db.Column(db.String(50))
    message = db.Column(db.Text)

    status = db.Column(db.String(20), default="new")
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())