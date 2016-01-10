import os
from time import sleep
from motionctl import _tcb_ as mqtt

status = None


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe('/motion/#')


def on_message(client, userdata, msg):
    global status

    print(msg.topic + " " + str(msg.payload))
    if '/motion/status' == msg.topic:
        status = msg.payload


if __name__ == '__main__':
    ON_BLINKS = 3

    mk_client = mqtt()['mk_client']
    client = mk_client(on_connect=on_connect, on_message=on_message)
    client.loop_start()

    def blink(color):
        os.system('blink1-tool --rgb %(color)s --blink 1 > /dev/null'
                  % dict(color=color))

    on_blinks = ON_BLINKS
    while(True):
        if status and status == 'on':
            if on_blinks:
                blink('0xff,0x00,0x00')
                on_blinks -= 1
        else:
            on_blinks = ON_BLINKS
            if not status:
                blink('0x00,0x00,0xff')
            elif status == 'off':
                blink('0x00,0xff,0x00')
            else:
                blink('0xff,0xff,0xff')
        sleep(2)
