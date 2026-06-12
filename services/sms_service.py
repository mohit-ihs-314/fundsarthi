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

    message = f"Dear User, You have received a new enquiry for property {property_title}. Customer Mobile: {customer_mobile} Team Fundsarth"

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

        try:
            res_json = response.json()
            print("Parsed Response:", res_json)

            sms_data = res_json.get("smslist", {}).get("sms", [])

            if sms_data:
                print("SMS Status:", sms_data[0].get("status"))
                print("SMS Reason:", sms_data[0].get("reason"))

            return res_json

        except Exception as e:
            print("Response Parse Error:", str(e))
            return False

    except Exception as e:
        print("Property SMS Error:", str(e))
        return False