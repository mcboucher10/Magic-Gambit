import paho.mqtt.client as paho
import ssl
import time

def publish(red, green):
    client = paho.Client(client_id="publisher", protocol=paho.MQTTv5)
    client.tls_set(tls_version=ssl.PROTOCOL_TLS)
    client.username_pw_set("MQTTpi", "Magicgambit10")

    client.connect("dc3a7b985e0541f69572b6ccc2ff6a0c.s1.eu.hivemq.cloud", 8883)
    client.loop_start()

    # Publish a message to the test topic
    payload = str(red) + ' ' + str(green)
    client.publish("test/topic", payload=payload, qos=1)

    client.loop_stop()  # Stop the loop if you're done publishing
    client.disconnect()

# LED indices from 0-63 (inclusive)
LED_A = 5
LED_B = 10

publish(LED_A, LED_B)
