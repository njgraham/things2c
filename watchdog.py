import datetime
import os
import sys
from ConfigParser import SafeConfigParser
import time
import paho.mqtt.client as mqtt


def mk_client(host, port, on_connect=None, on_message=None):
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, 60)
    return client


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe('/motion/#')


def on_message(client, userdata, msg):
    global last_update
    print(msg.topic + " " + str(msg.payload))
    if '/motion/status' == msg.topic:
        last_update = datetime.datetime.now()


if __name__ == '__main__':
    global last_update
    last_update = None

    cp = SafeConfigParser()
    cp.read(sys.argv[1])
    token = cp.get('pushover', 'token')
    user = cp.get('pushover', 'user')
    host = cp.get('broker', 'host')
    port = cp.get('broker', 'port')

    def cmd(c):
        os.system(c)

    client = mk_client(host, port,
                       on_connect=on_connect, on_message=on_message)
    client.loop_start()

    start = datetime.datetime.now()
    while True:
        print 'check'
        if(datetime.datetime.now() -
           (last_update or start)).total_seconds() > 30:
            print 'WATCHDOG'
            cmd('curl -s --form-string "token=%(token)s" '
                '--form-string "user=%(user)s" '
                '--form-string "message=%(message)s" '
                'https://api.pushover.net/1/messages.json' %
                dict(user=user, token=token, message='WATCHDOG'))
        time.sleep(10)

    