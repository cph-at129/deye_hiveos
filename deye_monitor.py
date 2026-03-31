import os
import requests
import hashlib

# Securely pull credentials from GitHub Vault
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
DEYE_EMAIL = os.environ.get("DEYE_EMAIL")
DEYE_PASSWORD = os.environ.get("DEYE_PASSWORD")
DEVICE_SN = os.environ.get("DEVICE_SN")

# WhatsApp Credentials
WA_PHONE_NUMBER = os.environ.get("WA_PHONE_NUMBER")
WA_API_KEY = os.environ.get("WA_API_KEY")

# Pulls the threshold from GitHub Variables, defaults to 20 if missing
ALERT_THRESHOLD = float(os.environ.get("ALERT_THRESHOLD", 20))
REGION_URL = "https://eu1-developer.deyecloud.com/v1.0"

def hash_password(pwd):
    return hashlib.sha256(pwd.encode('utf-8')).hexdigest()

def get_deye_token():
    url = f"{REGION_URL}/account/token?appId={APP_ID}"
    payload = {
        "appSecret": APP_SECRET,
        "email": DEYE_EMAIL,
        "password": hash_password(DEYE_PASSWORD)
    }
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
    
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {token}"
    }
    
    payload = {"deviceList": [DEVICE_SN]}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        
        # Dig into the JSON to find the array of sensor data
        device_data_list = data.get("deviceDataList", [])
        if not device_data_list:
            return None
            
        sensors = device_data_list[0].get("dataList", [])
        
        # Loop through the sensors until we find BMSSOC
        for sensor in sensors:
            if sensor.get("key") == "BMSSOC":
                return float(sensor.get("value"))
                
        return None
    except Exception as e:
        print(f"Error reading battery: {e}")
        return None

def send_whatsapp_alert(soc):
    message = f"⚠️ Low Battery Alert! Your Deye inverter battery is currently at {soc}%."
    url = "https://api.callmebot.com/whatsapp.php"
    params = {
        "phone": WA_PHONE_NUMBER,
        "text": message,
        "apikey": WA_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            print(f"Alert successfully sent to WhatsApp: {soc}%")
        else:
            print(f"CallMeBot failed: {response.text}")
    except Exception as e:
        print(f"Error sending WhatsApp alert: {e}")

def main():
    token = get_deye_token()
    if token:
        soc = get_battery_soc(token)
        if soc is not None:
            print(f"Current Battery SOC: {soc}%")
            if soc < ALERT_THRESHOLD:
                send_whatsapp_alert(soc)
            else:
                print(f"Battery is healthy ({soc}%). Threshold is {ALERT_THRESHOLD}%. No alert sent.")
        else:
            print("Could not find BMSSOC in the data.")

if __name__ == "__main__":
    main()
