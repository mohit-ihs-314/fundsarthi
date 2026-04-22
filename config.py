import os
import cloudinary

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "super-secret-key"

class Config:
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:@localhost/fundsarthi"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

cloudinary.config(
    cloud_name="dsfsw8im3",
    api_key="124269824567964",
    api_secret="X5rcsWfPf0YYSdNqFTcjcMNiK9A"
)    