from flask import Blueprint, request, jsonify
from sqlalchemy import text
from extensions import db

activity_bp = Blueprint("activity_bp", __name__)

@activity_bp.route("/api/activities", methods=["GET"])
def get_activities():

    mobile = request.args.get("mobile")

    if not mobile:
        return jsonify({
            "status": "error",
            "message": "Mobile required"
        }), 400

    try:

        result = db.session.execute(
            text("""
                SELECT *
                FROM user_activities
                WHERE mobile = :mobile
                ORDER BY created_at DESC
                LIMIT 50
            """),
            {
                "mobile": mobile
            }
        )

        activities = []

        for row in result.mappings():

            activities.append({
                "id": row["id"],
                "mobile": row["mobile"],
                "type": row["type"],
                "title": row["title"],
                "description": row["description"],
                "created_at": str(row["created_at"])
            })

        return jsonify({
            "status": "success",
            "data": activities
        })

    except Exception as e:

        print("Activities Error:", e)

        return jsonify({
            "status": "error",
            "message": "Server error"
        }), 500