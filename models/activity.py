from extensions import db
from datetime import datetime

class Activity(db.Model):

    __tablename__ = "user_activities"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    mobile = db.Column(
        db.String(20),
        nullable=False
    )

    type = db.Column(
        db.String(50),
        nullable=False
    )

    title = db.Column(
        db.String(255),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )