import os
import requests
import hashlib
import time

# Securely pull credentials from GitHub Vault
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
DEYE_EMAIL = os.environ.get("DEYE_EMAIL")
DEYE_PASSWORD = os.environ.get("DEYE_PASSWORD")
DEVICE_SN = os.environ.get("DEVICE_SN")

# Pull the comma-separated lists!
WA_PHONE_NUMBER = os.environ.get("WA_PHONE_NUMBER")
WA_API_KEY = os.environ.get("WA_API_KEY")
WA_PHONE_NUMBERS = os.environ.get("WA_PHONE_NUMBERS", "")
WA_API_KEYS = os.environ.get("WA_API_KEYS", "")

ALERT_THRESHOLD = float(os.environ.get("ALERT_THRESHOLD", 20))
HIGH_ALERT_THRESHOLD = float(os.environ.get("HIGH_ALERT_THRESHOLD", 95))
ALERT_COOLDOWN = int(os.environ.get("ALERT_COOLDOWN", 60)) * 60  

REGION_URL = "https://eu1-developer.deyecloud.com/v1.0"
STATE_FILE = "last_alert_time.txt"

def hash_password(pwd):
    return hashlib.sha256(pwd.encode('utf-8')).hexdigest()

def get_deye_token():
    url = f"{REGION_URL}/account/token?appId={APP_ID}"
    payload = {"appSecret": APP_SECRET, "email": DEYE_EMAIL, "password": hash_password(DEYE_PASSWORD)}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        if data.get("success"):
            return data.get("accessToken")
    except Exception as e:
        print(f"Error connecting to Deye: {e}")
    return None

def get_battery_soc(token):
    url = f"{REGION_URL}/device/latest"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"deviceList": [DEVICE_SN]}
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        device_data_list = data.get("deviceDataList", [])
        if not device_data_list:
            return None
        sensors = device_data_list[0].get("dataList", [])
        for sensor in sensors:
            if sensor.get("key") == "BMSSOC":
                return float(sensor.get("value"))
        return None
    except Exception as e:
        print(f"Error reading battery: {e}")
        return None

def can_send_alert():
    if not os.path.exists(STATE_FILE):
        return True
    try:
        with open(STATE_FILE, "r") as f:
            last_alert_time = float(f.read().strip())
        return (time.time() - last_alert_time) >= ALERT_COOLDOWN
    except Exception:
        return True

def update_alert_time():
    with open(STATE_FILE, "w") as f:
        f.write(str(time.time()))

def send_whatsapp_alert(message):
    # Turn the comma-separated strings into actual Python lists
    phones = [p.strip() for p in WA_PHONE_NUMBERS.split(",") if p.strip()]
    keys = [k.strip() for k in WA_API_KEYS.split(",") if k.strip()]

    # Safety check: Make sure we have a key for every phone number
    if len(phones) != len(keys):
        print("ERROR: The number of phones doesn't match the number of API keys in GitHub Secrets!")
        return

    url = "https://api.callmebot.com/whatsapp.php"
    
    # Loop through the list and send a message to each person
    for i in range(len(phones)):
        params = {"phone": phones[i], "text": message, "apikey": keys[i]}
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                print(f"Alert successfully sent to {phones[i]}")
            else:
                print(f"CallMeBot failed for {phones[i]}: {response.text}")
        except Exception as e:
            print(f"Error sending to {phones[i]}: {e}")
            
    # Save the timestamp after attempting to send to everyone
    update_alert_time()

def main():
    token = get_deye_token()
    if token:
        soc = get_battery_soc(token)
        if soc is not None:
            print(f"Current Battery SOC: {soc}%")
            alert_msg = None
            if soc <= ALERT_THRESHOLD:
                alert_msg = f"⚠️ Батерията е почти изтощена! Нивото на батерията е {soc}%."
            elif soc >= HIGH_ALERT_THRESHOLD:
                alert_msg = f"✅ Батерията е почти заредена! Нивото на батерията е {soc}%."
                
            if alert_msg:
                if can_send_alert():
                    send_whatsapp_alert(alert_msg)
                else:
                    print(f"Alert condition met, but still in {ALERT_COOLDOWN/60} min cooldown. No message sent.")
            else:
                print("Battery is within normal range. No alert sent.")
        else:
            print("Could not find BMSSOC in the data.")

if __name__ == "__main__":
    main()
