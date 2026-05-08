import hashlib
import os
import re

import requests

# Deye Cloud (GitHub Actions secrets)
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
DEYE_EMAIL = os.environ.get("DEYE_EMAIL")
DEYE_PASSWORD = os.environ.get("DEYE_PASSWORD")
DEVICE_SN = os.environ.get("DEVICE_SN")

# Hive OS API v2 (secrets / vars)
HIVEOS_API_TOKEN = os.environ.get("HIVEOS_API_TOKEN", "").strip()
HIVE_FARM_IDS = os.environ.get("HIVE_FARM_IDS", "").strip()


def _env_str(name, default):
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip()


def _env_float(name, default):
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return float(raw)


HIVEOS_API_BASE = _env_str("HIVEOS_API_BASE", "https://api2.hiveos.farm/api/v2").rstrip("/")
MINING_START_SOC = _env_float("MINING_START_SOC", 95)
MINING_STOP_SOC = _env_float("MINING_STOP_SOC", 40)

REGION_URL = "https://eu1-developer.deyecloud.com/v1.0"
MINING_STATE_FILE = "mining_control_state.txt"


def hash_password(pwd):
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


def get_deye_token():
    url = f"{REGION_URL}/account/token?appId={APP_ID}"
    payload = {"appSecret": APP_SECRET, "email": DEYE_EMAIL, "password": hash_password(DEYE_PASSWORD)}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
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
        response = requests.post(url, json=payload, headers=headers, timeout=60)
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


def _hive_auth_headers():
    """Hive accepts either a raw personal API token or a full Bearer value in Authorization."""
    token = HIVEOS_API_TOKEN
    if not token:
        return {}
    if token.lower().startswith("bearer "):
        return {"Authorization": token}
    return {"Authorization": f"Bearer {token}"}


def _parse_farm_ids():
    out = []
    for part in re.split(r"[\s,]+", HIVE_FARM_IDS):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            print(f"WARNING: skip invalid farm id {part!r}")
    return out


def hive_list_worker_ids(farm_id, session):
    url = f"{HIVEOS_API_BASE}/farms/{farm_id}/workers"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        **_hive_auth_headers(),
    }
    r = session.get(url, headers=headers, timeout=120)
    if r.status_code != 200:
        print(f"Hive GET workers farm={farm_id} failed HTTP {r.status_code}: {r.text[:500]}")
        return []
    payload = r.json()
    rows = payload.get("data")
    if rows is None:
        print(f"Hive GET workers farm={farm_id}: unexpected JSON (no 'data'): {str(payload)[:300]}")
        return []
    ids = []
    for w in rows:
        wid = w.get("id")
        if wid is not None:
            ids.append(int(wid))
    return ids


def hive_worker_command(farm_id, worker_id, body, session):
    url = f"{HIVEOS_API_BASE}/farms/{farm_id}/workers/{worker_id}/command"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        **_hive_auth_headers(),
    }
    r = session.post(url, headers=headers, json=body, timeout=120)
    if r.status_code not in (200, 201):
        print(f"Hive POST command farm={farm_id} worker={worker_id} HTTP {r.status_code}: {r.text[:500]}")
        return False
    return True


def hive_set_mining(mining_on):
    """
    mining_on True -> miner start; False -> miner stop.
    Uses command 'exec' so behavior matches shell `miner start` / `miner stop` on Hiveon OS workers.
    """
    farm_ids = _parse_farm_ids()
    if not farm_ids:
        print("ERROR: HIVE_FARM_IDS is empty or invalid.")
        return False
    cmd = "miner start" if mining_on else "miner stop"
    body = {"command": "exec", "data": {"cmd": cmd}}
    session = requests.Session()
    ok_all = True
    for farm_id in farm_ids:
        worker_ids = hive_list_worker_ids(farm_id, session)
        if not worker_ids:
            print(f"Farm {farm_id}: no workers found (or list failed); skipping.")
            ok_all = False
            continue
        for wid in worker_ids:
            if not hive_worker_command(farm_id, wid, body, session):
                ok_all = False
    return ok_all


def read_mining_state():
    """
    Persisted last successful Hive intent: 'on' or 'off'.
    Missing file -> 'off' so the first time SOC >= start threshold we issue miner start.
    """
    if not os.path.exists(MINING_STATE_FILE):
        return "off"
    try:
        with open(MINING_STATE_FILE, "r", encoding="utf-8") as f:
            v = f.read().strip().lower()
        return v if v in ("on", "off") else "off"
    except OSError:
        return "off"


def write_mining_state(state):
    with open(MINING_STATE_FILE, "w", encoding="utf-8") as f:
        f.write(state)


def main():
    if MINING_START_SOC <= MINING_STOP_SOC:
        print(
            f"ERROR: MINING_START_SOC ({MINING_START_SOC}) must be greater than "
            f"MINING_STOP_SOC ({MINING_STOP_SOC})."
        )
        return
    if not HIVEOS_API_TOKEN or not HIVE_FARM_IDS:
        print("ERROR: Set HIVEOS_API_TOKEN and HIVE_FARM_IDS in the environment (GitHub secrets).")
        return

    token = get_deye_token()
    if not token:
        print("Could not obtain Deye access token.")
        return

    soc = get_battery_soc(token)
    if soc is None:
        print("Could not find BMSSOC in the data.")
        return

    print(f"Current Battery SOC: {soc}%")

    if soc >= MINING_START_SOC:
        desired = "on"
    elif soc < MINING_STOP_SOC:
        desired = "off"
    else:
        print(
            f"SOC between stop ({MINING_STOP_SOC}%) and start ({MINING_START_SOC}%) — "
            "no Hive action (hysteresis dead band)."
        )
        return

    persisted = read_mining_state()
    if desired == persisted:
        print(f"Hive mining state already {persisted!r}; no API calls.")
        return

    action = "START" if desired == "on" else "STOP"
    print(f"Applying Hive {action} (persisted={persisted!r} -> target={desired!r}).")
    if hive_set_mining(desired == "on"):
        write_mining_state(desired)
        print(f"Hive {action} succeeded; wrote {MINING_STATE_FILE} = {desired!r}.")
    else:
        print(f"Hive {action} failed; leaving {MINING_STATE_FILE} unchanged for retry.")


if __name__ == "__main__":
    main()
