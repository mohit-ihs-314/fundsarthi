import requests

SMS_URL = "https://api.onex-aura.com/api/jsmslist"

def send_property_enquiry_sms():

    message = (
        "Dear User, You have received a new enquiry "
        "for property TEST123. "
        "Customer Mobile: 9988776655 "
        "Team Fundsarth"
    )

    payload = {
        "key": "YjDtvwUv",
        "listsms": [
            {
                "from": "FSARTH",
                "to": "9971935730",  # your mobile
                "body": message,
                "entityid": "1001338817429885581",
                "templateid": "1007091859816289556"
            }
        ]
    }

    print("================================")
    print("SMS BODY:", message)
    print("PAYLOAD:", payload)
    print("================================")

    response = requests.post(
        SMS_URL,
        json=payload,
        timeout=10
    )

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    return response.text