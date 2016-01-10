import datetime
import os
import sys
import time
import paho.mqtt.client as mqtt
from config import get_topics, get_config

last_update = None


def mk_client(host, port, on_connect=None, on_message=None):
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, 60)
    return client


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe(get_topics().motion_all)


def on_message(client, userdata, msg):
    global last_update
    print(msg.topic + " " + str(msg.payload))
    print get_topics().motion_status
    if msg.topic in get_topics().motion_status:
        last_update = datetime.datetime.now()


if __name__ == '__main__':
    global last_update

    with open(sys.argv[1]) as fin:
        config = get_config(fin)
    token = config.pushover.token
    user = config.pushover.user
    host = config.broker.host
    port = config.broker.port

    def cmd(c):
        os.system(c)

    client = mk_client(host, port,
                       on_connect=on_connect, on_message=on_message)
    client.loop_start()

    start = datetime.datetime.now()
    while True:
        print 'check'
        delta_sec = (datetime.datetime.now() -
                     (last_update or start)).total_seconds()
        print 'delta', delta_sec
        if delta_sec > 30:
            print 'WATCHDOG'
            cmd('curl -s --form-string "token=%(token)s" '
                '--form-string "user=%(user)s" '
                '--form-string "message=%(message)s" '
                'https://api.pushover.net/1/messages.json' %
                dict(user=user, token=token, message='WATCHDOG'))
        time.sleep(10)

    