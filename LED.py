import sys
import board
import neopixel
import time
import paho.mqtt.client as paho
import ssl

def main(r, g):
    red_led_index = int(r)
    green_led_index = int(g)

    # Initialize the NeoPixel strip
    pixels = neopixel.NeoPixel(board.D18, 75, brightness=1)

    # Clear all LEDs
    pixels.fill((0, 0, 0))

    # Set the red LED
    if 0 <= red_led_index < len(pixels):
        pixels[red_led_index] = (255, 0, 0)  # Red

    # Set the green LED
    if 0 <= green_led_index < len(pixels):
        pixels[green_led_index] = (0, 255, 0)  # Green
    time.sleep(7)
    
    pixels.fill((0,0,0))
    pixels.show()
    
def on_connect(client, userdata, flags, rc, properties=None):
    print("Connected with result code " + str(rc))
    client.subscribe("test/topic")  # Subscribe to a test topic

def on_message(client, userdata, message):
    red = message.payload.decode()[:message.payload.decode().index(' ')]
    green = message.payload.decode()[message.payload.decode().index(' ')+1:]
    main(red, green)

client = paho.Client(client_id="subscriber", protocol=paho.MQTTv5)
client.tls_set(tls_version=ssl.PROTOCOL_TLS)
client.username_pw_set("MQTTpi", "Magicgambit10")

client.on_connect = on_connect  # Set the on_connect callback
client.on_message = on_message  # Set the on_message callback

client.connect("dc3a7b985e0541f69572b6ccc2ff6a0c.s1.eu.hivemq.cloud", 8883)

client.loop_forever()  # Start processing network traffic
