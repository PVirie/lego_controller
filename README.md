# lego_controller

Control buwizz 3 from work station.

## Description

This project is similar in spirit to [Bricknil](https://github.com/virantha/bricknil) and [pylgbst](https://github.com/undera/pylgbst) but for [Buwizz 3 controller](https://buwizz.com/buwizz-3-0-pro/).

The project is implemented following [protocol version 3.22](https://buwizz.com/BuWizz_3.0_API_3.22_web.pdf)

## Installation

0. Plug in motor(s) to the Buwizz 3 controller.
   And make sure your device is on and ready to pair (LED blinking)

1. set up virtual environment

```bash
python3 -m venv .venv
```

2. activate virtual environment

```bash
source .venv/bin/activate
```

or on Windows

```
.venv\Scripts\activate
```

3. install requirements

```bash
pip install -r requirements.txt
```

4. run the program

```bash
sudo .venv/bin/python src/main.py
```

or on Windows simpy run

```bash
py src/main.py
```

5. use w/a/s/d to control motors 1 and 2.
6. to exit, press and **hold** the escape button.
7. to exit and enter the shelf mode, press and **hold** the F12.

## Life cycle

1. Scan for devices
2. Create a device object and connect to it
3. Operate device
4. Exit device

### Note

-   If you want to keep the device inoperate for a long time, it is recommended to activate the shelf mode (according to Buwizz recommendataion).

## Disclaimer

I will not be responsible for any damage caused by using this software. Use at your own risk.
