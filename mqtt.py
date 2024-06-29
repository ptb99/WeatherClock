##
## MQTT wrapper class - designed for io.adafruit.com and my temp probe firmware
##

import paho.mqtt.client as mqtt
import time
import json
import logging

from secrets import secrets


class MQTT_Listener:
    """Wrapper for subscribing to weather updates from an MQTT feed."""

    def __init__(self, host, secure=False, persist=False):
        self.logger = logging.getLogger()
        self.values = {}
        self.username=secrets["AIO_USERNAME"]
        # Initialize a new MQTT Client object
        if persist:
            # use persistent conn and queued messages
            client_id = 'Clock_123'
            cleanup = False
        else:
            client_id = ''
            cleanup = True
        mqttc = mqtt.Client(
            userdata=self,
            client_id=client_id, clean_session=cleanup,
            transport='tcp'
        )
            # callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            # protocol=mqtt.MQTTProtocolVersion.MQTTv311,
        mqttc.username_pw_set(
            username=secrets["AIO_USERNAME"],
            password=secrets["AIO_KEY"],
        )
        mqttc.on_connect = self.on_connect
        mqttc.on_message = self.on_message
        # Alt:
        #mqttc.message_callback_add('Porch/#', mqtt_on_message)
        if secure:
            mqttc.tls_set_context()
            mqttc.connect(
                host=host, port=8883, keepalive=60
            )
        else:
            mqttc.connect(
                host=host, port=1883, keepalive=60
            )
        # start a new thread
        mqttc.loop_start()
        self.mqtt_client = mqttc

    # For v2, use this signature:
    #def on_connect(self, client, userdata, flags, reason_code, properties):
    def on_connect(self, client, userdata, flags, reason_code):
        # Subscribe to Group
        client.subscribe(f"{self.username}/groups/Porch/json")

    def on_message(self, client, userdata, msg):
        self.logger.debug(f"MQTT msg: {msg.topic} {str(msg.payload)}")
        data = json.loads(msg.payload.decode('utf-8'))
        for key,val in data['feeds'].items():
            #logger.info(f'MQTT update: {key} = {val}')
            self.values[key] = float(val)

    def get_curr_values(self):
        return self.values

    def publish_indoor(self, values):
        BASE = f"{self.username}/feeds"
        for topic,payload in values:
            result = self.mqtt_client.publish(f'{BASE}/{topic}', payload)
            self.logger.debug(f"MQTT publish: {topic} {str(payload)} -> {result.rc}")


def test():
    MQTT_SERVER = "io.adafruit.com"
    #MQTT_SERVER = "furberry.bogus.domain"
    mqtt = MQTT_Listener(MQTT_SERVER, secure=False, persist=False)
    data = [('Indoor-Temp', 77.0),
            ('Indoor-Humidity', 42.0),
            ('Indoor-Pressure', 30.0),
            ('Indoor-VOC', 111_000)]
    for _ in range(5):
        mqtt.publish_indoor(data)
        time.sleep(30)


if __name__ == "__main__" :
    #level = logging.INFO
    level = logging.DEBUG
    logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s',
                        level=level)
    test()
