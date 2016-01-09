''' motionctl - motion controller
'''

def main(mk_client):
    client = mk_client(on_connect, on_message)
    client.loop_forever()

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    for t in ['/nfc/#', '/motion/#']:
        client.subscribe(t)

def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))
            
def _tcb_():
    import paho.mqtt.client as mqtt

    def mk_client(on_connect=None, on_message=None):
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect('numbat', 1883, 60)
        return client

    return dict(mk_client=mk_client)

if __name__ == '__main__':
    main(**_tcb_())
