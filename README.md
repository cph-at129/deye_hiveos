# Deye battery to Hive OS mining control

This repository runs a small Python script on a schedule (GitHub Actions) that reads your Deye inverter battery state of charge (SOC) from the official Deye Cloud API and sends **Hive OS API** commands to start or stop mining on your farms.

## Behavior

- **Start mining** when SOC is at or above `MINING_START_SOC` (default **95%**).
- **Stop mining** when SOC is **below** `MINING_STOP_SOC` (default **40%**).
- **Between** those two levels, the script does nothing so rigs are not toggled every run (hysteresis / dead band).
- The last successful Hive intent (`on` or `off`) is stored in `mining_control_state.txt` in the repo so Actions only calls Hive when the desired state **changes**, not every 15 minutes while SOC stays high or low.

Workers are controlled with Hive’s `exec` command and the same shell commands as on the rig: `miner start` and `miner stop`.

## Prerequisites

1. A **GitHub** account and a (preferably private) repository for this project.
2. **Deye Developer API** access: [developer.deyecloud.com](https://developer.deyecloud.com/) — `APP_ID`, `APP_SECRET`, and credentials for the Deye cloud account linked to your plant.
3. **Hive OS** personal API token with permission to run worker commands, and the numeric **farm IDs** you want to control (comma-separated if more than one). Farm IDs appear in the Hive web URL when you open a farm.

## GitHub configuration

### Secrets (Settings → Secrets and variables → Actions → Secrets)

| Name | Description |
|------|-------------|
| `APP_ID` | Deye developer app ID |
| `APP_SECRET` | Deye developer app secret |
| `DEYE_EMAIL` | Deye app login email |
| `DEYE_PASSWORD` | Deye app password |
| `DEVICE_SN` | Inverter serial number used in Deye Cloud |
| `HIVEOS_API_TOKEN` | Hive OS personal API token (JWT). The script sends `Authorization: Bearer <token>`. If your token already includes the `Bearer ` prefix, paste it as stored and it will be sent unchanged. |
| `HIVE_FARM_IDS` | Comma- or space-separated farm IDs, e.g. `12345` or `12345, 67890` |

### Variables (optional, Settings → Variables → Actions)

| Name | Default | Description |
|------|---------|-------------|
| `MINING_START_SOC` | `95` | Start mining when SOC ≥ this value |
| `MINING_STOP_SOC` | `40` | Stop mining when SOC is lower than this value |
| `HIVEOS_API_BASE` | `https://api2.hiveos.farm/api/v2` | Override only if Hive documents a different API base |

## Files

- `deye_monitor.py` — Deye SOC polling and Hive worker commands.
- `.github/workflows/monitor.yml` — Runs every 15 minutes and commits `mining_control_state.txt` when it changes.

## Disclaimer

This project is not affiliated with Deye or Hiveon. It uses public APIs. API and schedule delays can lag real battery conditions; keep safe limits configured on the inverter and rigs.
