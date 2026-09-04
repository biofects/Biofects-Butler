# Biofects Butler for Home Assistant

Biofects Butler is the Home Assistant integration for the Biofects Butler Android HUD. Home Assistant remains the source of truth for authentication, entities, services, Assist pipelines, dashboard profiles, display assignments, and themes.

## Features

- Administrator-managed Butler dashboard profiles and pages.
- Grouped entity cards, quick actions, calendars, weather, media, and service controls.
- Registration for up to two Free Android devices, with per-display profile assignment and Butler Neon or Holographic themes.
- A fixed Free assistant identity of `Biofects Butler`; the app and integration do not expose name editing.
- Native Home Assistant OAuth metadata for the Android application.
- Local push updates with no Biofects cloud dependency.

## Installation with HACS

1. Open HACS in Home Assistant.
2. Add `https://github.com/biofects/Biofects-Butler` as a custom repository with category **Integration**.
3. Install **Biofects Butler** and restart Home Assistant.
4. Open **Settings > Devices & services > Add integration** and select **Biofects Butler**.

After setup, administrators can open **Butler Dashboards** from the Home Assistant sidebar.

## Manual installation

Download the integration ZIP from the matching GitHub Release and verify its SHA-256 checksum. Extract it into the Home Assistant configuration directory so this file exists:

```text
config/custom_components/biofects_butler/manifest.json
```

Restart Home Assistant, then add **Biofects Butler** from **Settings > Devices & services**.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q tests
```

## Privacy

The integration communicates locally with Home Assistant and stores Butler configuration in Home Assistant. It does not send product data to Biofects cloud services and contains no ads, analytics, billing, or licensing SDKs.

## License

MIT
