''' motionctl - motion controller
'''
# not OCAP!
import datetime
last_update = None
last_authorized = None

def main(mk_client, sleep, cmd):
    global last_update
    global last_authorized
    
    client = mk_client(on_connect, on_message)
    client.loop_start()
    start = datetime.datetime.now()
    while True:
        if (datetime.datetime.now() - (last_update or start)).total_seconds() > 10:
            # print 'Too long since last update - forcing on'
            start = datetime.datetime.now()
            ensure_on(client, cmd)
        elif last_authorized and (datetime.datetime.now() - last_authorized).total_seconds() < 5:
            # print 'Authorized!'
            ensure_off(client, cmd)
        else:
            # print 'Not Authorized!'
            ensure_on(client, cmd)
        sleep(5)

def is_on(cmd):
    if cmd('pgrep -a motion') == 0:
        return True
    return False
    
def ensure_on(client, cmd):
    if not is_on(cmd):
        cmd('sudo supervisorctl start motion')
    client.publish('/motion/status', 'on')

def ensure_off(client, cmd):
    if is_on(cmd):
        cmd('sudo supervisorctl stop motion')
    client.publish('/motion/status', 'off')
    
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    for t in ['/nfc/#', '/motion/#']:
        client.subscribe(t)

def on_message(client, userdata, msg):
    global last_update
    global last_authorized

    # print(msg.topic+" "+str(msg.payload))
    if '/nfc/scan' in msg.topic:
        # EEK!  Thread safe?  Prolly not...
        last_update = datetime.datetime.now()
        if msg.topic == '/nfc/scan/authorized':
            last_authorized = datetime.datetime.now()
            
def _tcb_():
    import paho.mqtt.client as mqtt
    from time import sleep
    from os import system

    def mk_client(on_connect=None, on_message=None):
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect('numbat', 1883, 60)
        return client

    def cmd(c):
        # print c
        return system(c)

    return dict(mk_client=mk_client, sleep=sleep, cmd=cmd)

if __name__ == '__main__':
    main(**_tcb_())
