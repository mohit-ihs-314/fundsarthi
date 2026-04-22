import requests

def send_sms(mobile, message):
    url = "https://api.onex-aura.com/api/jsmslist"

    payload = {
        "key": "YjDtvwUv",
        "listsms": [
            {
                "from": "FSARTH",
                "to": mobile,
                "body": message,
                "entityid": "1001338817429885581",
                "templateid": "1007505525018237305"
            }
        ]
    }

    res = requests.post(url, json=payload)
    data = res.json()

    sms_data = data.get("smslist", {}).get("sms", [])

    if sms_data and sms_data[0].get("status") == "success":
        return True

    return False