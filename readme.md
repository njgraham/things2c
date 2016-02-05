# Motion Sensor System with Mobile Notifications and NFC Activation
I call the project [things2c](https://bitbucket.org/njgraham/things2c) or "things to See" - a reference to both the video recording aspect and the [Internet of Things (IoT)](https://en.wikipedia.org/wiki/Internet_of_Things).  Basically, I had a solution looking for a problem (a couple Raspberry PI's, some NFC gadgetry, etc.) and was inspired by an article describing how to use a [Raspberry Pi as low-cost HD surveillance camera](http://www.instructables.com/id/Raspberry-Pi-as-low-cost-HD-surveillance-camera/).

## What does it it do?
The system sends me alerts on my phone when motion is detected in my apartment unless the NFC tag on my keychain is close to the sensor inside my front door.  Once the NFC tag is detected, a nice calming green LED flashes periodically.

## What is it not?
I do **not** claim this is a serious security appliance.  There are various ways to thwart the system and I haven't given any serious thought to hardening it.  For me, it was just a fun project.

## Hardware
* [Raspberry PI 2, Model B](https://www.raspberrypi.org/products/raspberry-pi-2-model-b/)
* [Raspberry PI Zero](https://www.raspberrypi.org/products/pi-zero/)
* [Digital Logic NFC RFID USB Stick DL533N](http://www.d-logic.net/nfc-rfid-reader-sdk/products/nfc-usb-stick-dl533n)
* [blink(1) indicator light](https://blink1.thingm.com/)
* [Edimax N150 Wi-Fi Nano USB Adapter](http://www.edimax.com/edimax/merchandise/merchandise_detail/data/edimax/global/wireless_adapters_n150/ew-7811un)

## Software
* [nfcpy - Python module for near field communication](https://nfcpy.readthedocs.org/en/latest/)
* [things2c - my custom Python scripts](https://bitbucket.org/njgraham/things2c)
* [blink(1) tools](https://github.com/todbot/blink1)
* [motion](http://www.lavrsen.dk/foswiki/bin/view/Motion/WebHome)
* [Mosquitto - An Open Source MQTT Broker](http://mosquitto.org/)
* [Supervisor: A Process Control System](http://supervisord.org/)

## Design Diagram
![things2c design](https://bytebucket.org/njgraham/things2c/raw/default/design.png)
