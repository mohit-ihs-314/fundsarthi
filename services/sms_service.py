import requests

def send_property_enquiry_sms(owner_mobile, property_title, customer_mobile):

    print("\n========== PROPERTY SMS START ==========")
    print("Owner Mobile:", owner_mobile)
    print("Property Title:", property_title)
    print("Customer Mobile:", customer_mobile)

    # Validation
    if not owner_mobile or len(owner_mobile) != 10 or not owner_mobile.isdigit():
        print("❌ Invalid Owner Mobile")
        return {
            "status": "error",
            "message": "Invalid owner mobile number"
        }, 400

    url = "https://api.onex-aura.com/api/jsmslist"

    message = "Your OTP is 123456 for login authentication. It is valid for 10 minutes. Do not share it with anyone. - Fund Sarthi"

    print("\n========== SMS MESSAGE ==========")
    print(message)

    payload = {
        "key": "YjDtvwUv",
        "listsms": [
            {
                "from": "FSARTH",
                "to": "9099096937",
                "body": message,
                "entityid": "1001338817429885581",
                "templateid": "1007505525018237305"
            }
        ]
    }

    print("\n========== SMS PAYLOAD ==========")
    print(payload)

    try:
        print("\n========== CALLING SMS API ==========")

        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        print("\n========== SMS API RESPONSE ==========")
        print("Status Code:", response.status_code)
        print("Response Text:", response.text)

        try:
            res_json = response.json()

            print("\n========== PARSED RESPONSE ==========")
            print(res_json)

        except Exception as e:
            print("❌ JSON Parse Error:", str(e))
            return {
                "status": "error",
                "message": "Invalid response from SMS API"
            }, 500

        sms_data = res_json.get("smslist", {}).get("sms", [])

        print("\n========== SMS DATA ==========")
        print(sms_data)

        if sms_data:
            print("SMS Status:", sms_data[0].get("status"))
            print("SMS Reason:", sms_data[0].get("reason"))
            print("Message ID:", sms_data[0].get("messageid"))

        if sms_data and sms_data[0].get("status") == "success":
            print("✅ SMS Accepted By Gateway")

            return {
                "status": "success",
                "message": "Property enquiry SMS sent successfully"
            }, 200

        print("❌ SMS Failed")

        return {
            "status": "error",
            "message": sms_data[0].get("reason", "SMS failed")
            if sms_data else "SMS failed"
        }, 400

    except Exception as e:
        print("\n❌ SMS Exception:", str(e))

        return {
            "status": "error",
            "message": "Failed to send SMS"
        }, 500