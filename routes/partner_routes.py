from flask import Blueprint, request, jsonify
from extensions import db
from models.partner import Partner

partner_bp = Blueprint("Partner", __name__)

@partner_bp.route("/become-partner", methods=["POST"])
def become_partner():
    data = request.json

    try:
        partner = Partner(
            name=data.get("name"),
            company=data.get("company"),
            service_type=data.get("serviceType"),
            city=data.get("city"),
            phone=data.get("phone"),
            email=data.get("email"),
        )

        db.session.add(partner)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Partner application submitted"
        })

    except Exception as e:
        print(e)
        return jsonify({
            "status": "error",
            "message": "Something went wrong"
        }), 500