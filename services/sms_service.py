import requests

def send_property_enquiry_sms(owner_mobile, property_title, customer_mobile):

    print("\n========== PROPERTY SMS TEST ==========")

    url = "https://api.onex-aura.com/api/jsmslist"

    # HARD CODED TEST
    message = (
        "Dear User,\n"
        "You have received a new enquiry for property TEST123.\n"
        "Customer Mobile: 9999999999\n"
        "Team Fundsarth"
    )

    payload = {
        "key": "YjDtvwUv",
        "listsms": [
            {
                "from": "FSARTH",
                "to": owner_mobile,
                "body": message,
                "entityid": "1001338817429885581",
                "templateid": "1007091859816289556"
            }
        ]
    }

    print("MESSAGE:")
    print(message)

    print("\nPAYLOAD:")
    print(payload)

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        print("\nSTATUS:", response.status_code)
        print("RESPONSE:", response.text)

        return response.text

    except Exception as e:
        print("ERROR:", str(e))
        return str(e)