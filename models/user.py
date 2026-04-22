from extensions import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    mobile = db.Column(db.String(15), unique=True)
    name = db.Column(db.String(100))
    city = db.Column(db.String(50))
    employment = db.Column(db.String(50))
    income = db.Column(db.String(20))