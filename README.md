# NGBS iCON Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

This integration exposes the NGBS iCON thermostats and sensors to Home Assistant using the Modbus TCP communication protocol.

For more information about the NGBS system, visit [https://www.ngbsh.hu/en/](https://www.ngbsh.hu/en/).

---

## Features

- **Climate Entities**: Control target temperature, HVAC mode (Heating / Cooling), and preset modes (Comfort / Eco) for connected NGBS iCON thermostats.
- **Sensor Entities**: Monitor current temperature, target temperature, and relative humidity per thermostat, as well as main water temperature.
- **UI Configuration**: Configure host IP and Modbus TCP port directly via Home Assistant UI integration setup flow.

---

## Installation

### Method 1: HACS (Recommended)

1. Open **HACS** in your Home Assistant UI.
2. Click on the three dots `⋮` in the top right corner and select **Custom repositories**.
3. Add repository URL: `https://github.com/adenes/ngbs-icon-home-assistant`
4. Select Category: **Integration**.
5. Click **Add**.
6. Search for **NGBS iCON** and click **Download**.
7. **Restart Home Assistant**.

### Method 2: Manual Installation

1. Download the latest release source code.
2. Copy the `custom_components/ngbs` directory into your Home Assistant `<config_dir>/custom_components/` folder.
3. Restart Home Assistant.

---

## Configuration

1. In Home Assistant, go to **Settings** -> **Devices & Services**.
2. Click **Add Integration** in the bottom right.
3. Search for **NGBS iCON** and select it.
4. Enter the **Host** (IP address of your NGBS iCON controller) and **Port** (default `502`).
5. Click **Submit**.

---

## License

Licensed under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0.html).
