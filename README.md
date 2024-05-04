# lego_controller

Control buwizz 3 from work station.

## Description

This project is similar in spirit to [Bricknil](https://github.com/virantha/bricknil) and [pylgbst](https://github.com/undera/pylgbst) but for [Buwizz 3 controller](https://buwizz.com/buwizz-3-0-pro/).

The project is implemented following [protocol version 3.22](https://buwizz.com/BuWizz_3.0_API_3.22_web.pdf)

## Installation

```bash
pip install -r requirements.txt
```

## Life cycle

1. Scan for devices
2. Create a device object and connect to it
3. Operate device
4. Exit device

### Note

-   If you want to keep the device inoperate for a long time, it is recommended to activate the shelf mode (according to Buwizz recommendataion).

## Disclaimer

I will not be responsible for any damage caused by using this software. Use at your own risk.
