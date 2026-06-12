import requests

def send_property_enquiry_sms(owner_mobile, property_title, customer_mobile):

    # ✅ Validation
    if not owner_mobile or len(owner_mobile) != 10 or not owner_mobile.isdigit():
        return {
            "status": "error",
            "message": "Invalid owner mobile number"
        }, 400

    url = "https://api.onex-aura.com/api/jsmslist"

    message = (
        f"Dear User, You have received a new enquiry for property "
        f"{property_title}. Customer Mobile: {customer_mobile} "
        f"Team Fundsarth"
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

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        print("Property SMS Status Code:", response.status_code)
        print("Property SMS Response:", response.text)

        try:
            res_json = response.json()
        except:
            return {
                "status": "error",
                "message": "Invalid response from SMS API"
            }, 500

        try:
            sms_data = res_json.get("smslist", {}).get("sms", [])

            if sms_data and sms_data[0].get("status") == "success":
                return {
                    "status": "success",
                    "message": "Property enquiry SMS sent successfully"
                }, 200

            return {
                "status": "error",
                "message": sms_data[0].get("reason", "SMS failed")
                if sms_data else "SMS failed"
            }, 400

        except Exception as e:
            print("Parsing Error:", str(e))
            return {
                "status": "error",
                "message": "Unexpected API response"
            }, 500

    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message": "SMS API timeout"
        }, 500

    except requests.exceptions.RequestException as e:
        print("SMS Error:", str(e))
        return {
            "status": "error",
            "message": "Failed to send SMS"
        }, 500