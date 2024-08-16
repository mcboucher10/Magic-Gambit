# ------------------------------------------------------------------------------------
# Author: Mason Boucher
# Project: Cyber-Physical Systems Engineering Jumpstart - Magic Gambit
# Teammates: Alex Angeloff, Michael Habib, Nima Sichani
# Special Thanks: Dr. Nestor Tiglao, Dr. Romel Gomez, Anuj Zore, Amna Hayat, Reta Gela
# ------------------------------------------------------------------------------------
import paho.mqtt.client as paho
import ssl
import pygame
import threading

# Global variable to store the current board state
current_piece_list = [[]]

def on_connect(client, userdata, flags, rc, properties=None):
    print("Connected with result code " + str(rc))
    client.subscribe("test/fen")  # Subscribe to a test topic

def on_message(client, userdata, message):
    global current_piece_list
    # Decode the FEN string from the received MQTT message
    fen = message.payload.decode()
    print('message received')
    if len(fen) > 10:
        print(f"Received FEN: {fen} on topic {message.topic}")

        # Convert the FEN string to a 2D list (array)
        current_piece_list = FEN_to_array(fen)

def display_board():
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("Chess Board")

    screen_width, screen_height = screen.get_size()
    square_size = min(screen_width, screen_height) // 8

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        for row in range(8):
            for col in range(8):
                # Determine the color of the tile
                if (row + col) % 2 == 0:
                    color = (227, 193, 111)
                else:
                    color = (184, 139, 74)

                # Draw the tile
                pygame.draw.rect(screen, color,
                                 pygame.Rect(col * square_size, row * square_size, square_size, square_size))

                # Draw the piece, if any
                piece = current_piece_list[row][col]
                if piece != '':
                    if piece.upper() == piece:
                        piece_image = r'pieces\w' + piece.lower() + '.png'
                    else:
                        piece_image = r'pieces\b' + piece.lower() + '.png'
                    piece_image = pygame.image.load(piece_image)
                    piece_image = pygame.transform.scale(piece_image, (square_size, square_size))
                    piece_rect = piece_image.get_rect(
                        center=(col * square_size + square_size // 2, row * square_size + square_size // 2))
                    screen.blit(piece_image, piece_rect)

        pygame.display.flip()

    pygame.quit()

def FEN_to_array(fen):
    result = [[]]
    for char in fen:
        if char.isdigit():
            for i in range(int(char)):
                result[-1].append('')
        elif char == '/':
            result.append([])
        else:
            result[-1].append(char)
    return result

def start_mqtt():
    client = paho.Client(client_id="subscriber", protocol=paho.MQTTv5)
    client.tls_set(tls_version=ssl.PROTOCOL_TLS)
    client.username_pw_set("fensetup", "Magicgambit10")

    client.on_connect = on_connect  # Set the on_connect callback
    client.on_message = on_message  # Set the on_message callback

    client.connect("c424fde2a0ed48538e2b798a0d0e4c38.s1.eu.hivemq.cloud", 8883)

    client.loop_forever()  # Run the MQTT loop continuously

# Start the MQTT client in a separate thread
mqtt_thread = threading.Thread(target=start_mqtt)
mqtt_thread.start()

# Start the Pygame display loop in fullscreen mode
current_piece_list = FEN_to_array("8/8/8/8/8/8/8/8")  # Start with an empty board
display_board()