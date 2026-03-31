# 🔋 Deye Battery Monitor & WhatsApp Warner

A lightweight, 100% free automation script that monitors your Deye solar inverter's battery level and sends WhatsApp alerts when it gets dangerously low or fully charged. 

Built to run entirely in the cloud using GitHub Actions—no Raspberry Pi, Home Assistant, or always-on servers required.

## ✨ Features
* **Real-Time Monitoring:** Pulls live BMS State of Charge (SOC) directly from the official Deye Cloud API.
* **WhatsApp Integration:** Sends instant push notifications to your phone via CallMeBot.
* **Smart Thresholds:** Configurable alerts for both Low Battery (e.g., `< 20%`) and High Battery (e.g., `> 95%`).
* **Anti-Spam Memory:** Built-in cooldown timer prevents the bot from spamming you with messages every 15 minutes.
* **Zero Cost:** Runs on GitHub's free tier. 
* **Bank-Grade Security:** Your master Deye passwords and API keys are locked in GitHub Vault and never exposed in the code.

---

## 🛠️ Prerequisites
Before setting this up, you will need three things:
1. **A GitHub Account:** (Free) To host and run the code.
2. **Deye Developer Credentials:** Register at [developer.deyecloud.com](https://developer.deyecloud.com/) to get an `App ID` and `App Secret`.
3. **CallMeBot WhatsApp API Key:** (Free) Get it by sending a WhatsApp message to the CallMeBot API. Instructions [here](https://www.callmebot.com/blog/free-api-whatsapp-messages/).

---

## 🚀 Setup Guide

### Step 1: Create your Repository
1. Create a **Private** repository on GitHub.
2. Go to **Settings** > **Secrets and variables** > **Actions**.

### Step 2: Add your Secrets (Passwords)
Click the **Secrets** tab and add the following keys. *These are hidden forever once saved.*
* `APP_ID` - Your Deye Developer App ID
* `APP_SECRET` - Your Deye Developer App Secret
* `DEYE_EMAIL` - The email you use to log into the Deye app
* `DEYE_PASSWORD` - Your Deye app password
* `DEVICE_SN` - Your Inverter's Serial Number
* `WA_PHONE_NUMBER` - Your WhatsApp number (with country code, e.g., `+1234567890`)
* `WA_API_KEY` - Your CallMeBot API key

### Step 3: Add your Variables (Settings)
Click the **Variables** tab and add your preferred settings. *You can change these anytime without touching the code.*
* `ALERT_THRESHOLD` - The low battery % to warn you at (e.g., `20`)
* `HIGH_ALERT_THRESHOLD` - The high battery % to warn you at (e.g., `95`)
* `ALERT_COOLDOWN` - How many minutes to wait before sending another text (e.g., `60`)

### Step 4: Upload the Code
Create two files in your repository:
1. `deye_monitor.py` (Paste the Python script here).
2. `.github/workflows/monitor.yml` (Paste the GitHub Actions configuration here).

Once both files are committed, GitHub will automatically take over and start checking your battery every 15 minutes!

---

## ⚙️ How it Works Under the Hood
1. Every 15 minutes, GitHub wakes up a micro-server.
2. It securely injects your Secrets and Variables into the Python environment.
3. The script pings the Deye `/v1.0/device/latest` endpoint to fetch your `BMSSOC`.
4. If the battery crosses your threshold, it checks the `last_alert_time.txt` file. 
5. If the cooldown period has passed, it fires off a WhatsApp message and saves the new timestamp.
6. The server shuts down, costing you nothing.

---

## 📝 Disclaimer
This project is not officially affiliated with Deye. It uses their public Developer API. Always ensure your inverter's internal hardware safety limits are set correctly on the physical machine, as API delays can occur.
