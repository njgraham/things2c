import paho.mqtt.client as mqtt
from functools import partial


def main(mk_mqtt_client):
    import logging
    logging.basicConfig(format='%(asctime)s: %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S', level=logging.INFO)
    log = logging.getLogger(__name__)
    client = mk_mqtt_client(log=log, topics=['/#'])
    client.loop_forever()


class MqttClient(mqtt.Client):
    def __init__(self, host, port, log, topics):
        super(MqttClient, self).__init__()
        self._log = log
        self._topics = topics

        self.on_connect = self._on_connect
        self.on_message = self._on_message

        self.connect(host, port, 60)

    @classmethod
    def make(cls, host, port, log, topics):
        return MqttClient(host, port, log, topics)

    def _on_connect(self, client, userdata, flags, rc):
        self._log.info("Connected with result code " + str(rc))
        for topic in self._topics:
            self.subscribe(topic)

    def _on_message(self, client, userdata, msg):
        self._log.info(msg.topic + " " + str(msg.payload))

if __name__ == '__main__':
    def _tcb_():
        from sys import argv
        return dict(mk_mqtt_client=partial(MqttClient.make,
                                           host=argv[1],
                                           port=int(argv[2])))
    main(**_tcb_())
