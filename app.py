from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ✅ CLEAN CORS (ONLY THIS)
    CORS(
        app,
        resources={r"/api/*": {"origins": "http://localhost:5173"}},
        supports_credentials=True
    )

    # Init DB
    db.init_app(app)

    # Import routes
    from routes.auth_routes import auth_bp
    from routes.loan_routes import loan_bp
    from routes.property_routes import property_bp
    from routes.consultant_routes import consultant_bp
    from routes.booking_routes import booking_bp
    from routes.partner_routes import partner_bp

    # Register routes
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(loan_bp, url_prefix="/api")
    app.register_blueprint(property_bp, url_prefix="/api")
    app.register_blueprint(consultant_bp, url_prefix="/api")
    app.register_blueprint(booking_bp, url_prefix="/api")
    app.register_blueprint(partner_bp, url_prefix="/api")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)