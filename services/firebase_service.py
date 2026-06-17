import os
import json
import firebase_admin

from firebase_admin import credentials
from firebase_admin import messaging

firebase_creds = json.loads(
    os.environ["FIREBASE_CREDENTIALS"]
)

cred = credentials.Certificate(
    firebase_creds
)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)


def send_push(
    token,
    title,
    body,
    data=None
):

    message = messaging.Message(
        token=token,

        notification=messaging.Notification(
            title=title,
            body=body
        ),

        data=data or {}
    )

    return messaging.send(message)