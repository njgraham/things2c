# Motion Sensor System with Mobile Notifications and NFC Activation
I call the project [things2c](https://github.com/njgraham/things2c) or "things to see" - a reference to both the video recording aspect and the [Internet of Things (IoT)](https://en.wikipedia.org/wiki/Internet_of_Things).  Basically, I had a solution looking for a problem (a couple Raspberry Pis, some NFC gadgetry, etc.) and was inspired by an article describing how to use a [Raspberry Pi as low-cost HD surveillance camera](http://www.instructables.com/id/Raspberry-Pi-as-low-cost-HD-surveillance-camera/).

## What does it it do?
The system sends me alerts on my phone when motion is detected in my apartment unless the NFC tag on my keychain is close to the sensor inside my front door.  Once the NFC tag is detected and the motion detection is turned off, a nice calming green LED flashes periodically.  Video clips/previews are uploaded to Amazon S3 or ownCloud where they may be synced to a mobile device.

## What is it not?
I do **not** claim this is a serious security appliance.  There are various ways to thwart the system and I haven't given any serious thought to hardening it.  For me, it was just a fun project.

## Hardware
* [Raspberry Pi 2, Model B](https://www.raspberrypi.org/products/raspberry-pi-2-model-b/)
* [Raspberry Pi Zero](https://www.raspberrypi.org/products/pi-zero/)
* [Digital Logic NFC RFID USB Stick DL533N](http://www.d-logic.net/nfc-rfid-reader-sdk/products/nfc-usb-stick-dl533n)
* [blink(1) indicator light](https://blink1.thingm.com/)
* [Edimax N150 Wi-Fi Nano USB Adapter](http://www.edimax.com/edimax/merchandise/merchandise_detail/data/edimax/global/wireless_adapters_n150/ew-7811un)
* [Logitec C270 webcam](http://www.logitech.com/en-us/product/hd-webcam-c270)

## Software
* [things2c](https://github.com/njgraham/things2c)
* [nfcpy - A Python module for near field communication (NFC)](https://nfcpy.readthedocs.org/en/latest/)
* [blink(1) tools](https://github.com/todbot/blink1)
* [motion](http://www.lavrsen.dk/foswiki/bin/view/Motion/WebHome)
* [Mosquitto - An Open Source MQTT Broker](http://mosquitto.org/)
* [Supervisor - A Process Control System](http://supervisord.org/)
* [S3cmd - A Command Line S3 Client](http://s3tools.org/s3cmd)
* [Docker - Optionally containerize the message broker, motion, and motionctl](https://www.docker.com/)
* [Ansible - For deployment](https://www.ansible.com/)

## Cloud Services
* [Pushover](https://pushover.net/)
* [Amazon S3](https://aws.amazon.com/s3/)
* [ownCloud](https://owncloud.org/)

## Design Diagram
![things2c design](https://github.com/njgraham/things2c/raw/master/design.png)

## Usage
    :::text
    $ python things2c.py --help
    Usage:
      things2c [options] nfc_scan
      things2c [options] motionctl
      things2c [options] watchdog
      things2c [options] blinkctl
      things2c [options] notify <notify_text>
      things2c [options] publish
      things2c [options] snoop
      things2c [options] filemanager
      things2c version

    Sub-commands:
      nfc_scan          NFC scan/report
      motionctl         Control motion sensor
      watchdog          Watchdog for motion control
      blinkctl          Control status blink(1)
      notify            Send notifications
      publish           Publish topic/payload to MQ
      snoop             Output all MQTT traffic
      filemanager       Upload/delete video files
      version           Display version and exit

    Options:
      -h --help         Print usage
      -c --config=FILE  Configuration file [default: /etc/things2c/things2c.ini]
      -v --verbose      Verbose/debug output
      -t --topic=TOPIC  Topic to publish
      -p --payload=PL   Payload for publish
      -e --encode       Encode payload
  
## Build Notes
To build a standalone binary using [pyinstaller](http://pythonhosted.org/PyInstaller), refer to [Dockerfile_things2c](https://raw.githubusercontent.com/njgraham/things2c/master/Dockerfile_things2c) for x86.  To build for the Raspberry PI, I used the following after installing the needed Python modules ([requirements.txt](https://raw.githubusercontent.com/njgraham/things2c/master/requirements.txt)):

    :::text
    $ pyinstaller --hidden-import nfc.clf.pn533 --onefile ./things2c.py

## Deployment Notes
I deploy with [Ansible](https://www.ansible.com/) - refer to [playbook.yml](https://raw.githubusercontent.com/njgraham/things2c/master/deployment/playbook.yml).

## License for [things2c](https://github.com/njgraham/things2c)
[MIT](https://opensource.org/licenses/MIT)
