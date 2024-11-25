import paho.mqtt.client as paho
import ssl

def on_connect(client, userdata, flags, rc, properties=None):
    print("Connected with result code " + str(rc))
    client.subscribe("test/topic")  # Subscribe to a test topic

def on_message(client, userdata, message):
    print(f"Received message: {message.payload.decode()} on topic {message.topic}")

client = paho.Client(client_id="subscriber", protocol=paho.MQTTv5)
client.tls_set(tls_version=ssl.PROTOCOL_TLS)
client.username_pw_set("MQTTpi", "Magicgambit10")

client.on_connect = on_connect  # Set the on_connect callback
client.on_message = on_message  # Set the on_message callback

client.connect("dc3a7b985e0541f69572b6ccc2ff6a0c.s1.eu.hivemq.cloud", 8883)

client.loop_forever()  # Start processing network traffic
