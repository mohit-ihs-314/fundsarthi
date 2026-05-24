from extensions import db
from sqlalchemy import text

def add_activity(
    mobile,
    activity_type,
    title,
    description=""
):

    try:

        # ✅ prevent duplicate spam within 2 mins
        recent = db.session.execute(
            text("""
                SELECT id
                FROM user_activities
                WHERE mobile = :mobile
                AND type = :type
                AND created_at >= NOW() - INTERVAL 2 MINUTE
                LIMIT 1
            """),
            {
                "mobile": mobile,
                "type": activity_type
            }
        ).fetchone()

        # ✅ skip duplicate activity
        if recent:
            return

        # ✅ insert activity
        db.session.execute(
            text("""
                INSERT INTO user_activities
                (mobile, type, title, description)
                VALUES
                (:mobile, :type, :title, :description)
            """),
            {
                "mobile": mobile,
                "type": activity_type,
                "title": title,
                "description": description
            }
        )

        db.session.commit()

    except Exception as e:

        db.session.rollback()

        print("Activity Error:", e)