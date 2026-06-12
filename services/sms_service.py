import requests

SMS_URL = "https://api.onex-aura.com/api/jsmslist"
SMS_KEY = "YjDtvwUv"
ENTITY_ID = "1001338817429885581"
SENDER_ID = "FSARTH"

# Property Enquiry Template ID
PROPERTY_TEMPLATE_ID = "1007091859816289556"


def send_property_enquiry_sms(owner_mobile, property_title, customer_mobile):
    """
    Send SMS to property owner when enquiry is received
    """

    message = (
        f"Dear User, "
        f"New enquiry received for property {property_title}. "
        f"Contact Number: {customer_mobile}. "
        f"Team Fundsarth"
    )

    payload = {
        "key": SMS_KEY,
        "listsms": [
            {
                "from": SENDER_ID,
                "to": owner_mobile,
                "body": message,
                "entityid": ENTITY_ID,
                "templateid": PROPERTY_TEMPLATE_ID
            }
        ]
    }

    try:
        response = requests.post(
            SMS_URL,
            json=payload,
            timeout=10
        )

        print("Property SMS Status:", response.status_code)
        print("Property SMS Response:", response.text)

        return True

    except Exception as e:
        print("Property SMS Error:", str(e))
        return False