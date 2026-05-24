from flask import Blueprint, request, jsonify
from instance.db import get_db_connection

activity_bp = Blueprint("activity_bp", __name__)

@activity_bp.route("/api/activities", methods=["GET"])
def get_activities():

    mobile = request.args.get("mobile")

    if not mobile:
        return jsonify({
            "status": "error",
            "message": "Mobile required"
        })

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM user_activities
            WHERE mobile = %s
            ORDER BY created_at DESC
            LIMIT 50
        """, (mobile,))

        activities = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "data": activities
        })

    except Exception as e:

        print(e)

        return jsonify({
            "status": "error",
            "message": "Server error"
        })