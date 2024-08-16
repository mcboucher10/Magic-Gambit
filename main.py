# ------------------------------------------------------------------------------------
# Author: Mason Boucher
# Project: Cyber-Physical Systems Engineering Jumpstart - Magic Gambit
# Teammates: Alex Angeloff, Michael Habib, Nima Sichani
# Special Thanks: Dr. Nestor Tiglao, Dr. Romel Gomez, Anuj Zore, Amna Hayat, Reta Gela
# ------------------------------------------------------------------------------------

from ultralytics import YOLOv10
import supervision as sv
import cv2
import numpy as np
import sys
import pygame
import chess
import chess.engine
import random
import paho.mqtt.client as paho
import ssl
import time
from pygame.locals import QUIT, MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION
# -------------------------------------------------------------------------- COMPUTER VISION -----------------------------------------------------------------------------

# Parameters: None
# Returns: Initialized camera
def initialize_camera():
    cap = cv2.VideoCapture(0)
    for i in range(30):
        cap.read()
    return cap

# Parameters: Initialized camera
# Returns: 2D array of frame

def get_frame(cam):
    ret, frame = cam.read()
    if ret:
        return frame
    else:
        print("Failed to capture image.")

# Parameters: 2D array of frame, 2D list of coordinate pairs, target image size
# Returns: 2D list of coordinate pairs

def convert_corners(img, corners, size):
    for corner in corners:
        corner[0] *= size[0]/img.shape[1]
        corner[1] *= size[1]/img.shape[0]
    return corners

# Parameters: 2D list of coordinate pairs
# Returns: 2D list of coordinate pairs

def initial_convert(corners):
    for corner in corners:
        corner[0] *= 640/960
        corner[1] *= 480/720
    return corners

# Parameter: 2D array of frame
# Returns: list of piece names, list of coordinate pairs

def detect_pieces(img):
  piece_dict = {
      0: 'b',
      1: 'k',
      2: 'n',
      3: 'p',
      4: 'q',
      5: 'r',
      6: 'B',
      7: 'K',
      8: 'N',
      9: 'P',
      10: 'Q',
      11: 'R'
  }
  results = model(source=img, conf=0.01)[0]
  detections = sv.Detections.from_ultralytics(results)
  coords = []
  pieces = []
  confs = []
  for bbox, label, confidence in zip(detections.xyxy, detections.class_id, detections.confidence):
      x_min, y_min, x_max, y_max = bbox
      coords.append(((x_min+x_max)/2, (y_min + 4*y_max)/5))
      pieces.append(piece_dict[label])
      confs.append(confidence)
      print(((x_min+x_max)/2, (y_min + 4*y_max)/5), piece_dict[label], confidence)
  return pieces, coords, confs

# Parameters: image path, board corners
# Returns: 3x3 perspective transformation matrix

def find_transformation_matrix(image, corners):

    
    if image is None:
        print("Error: Image not found or unable to load.")
        sys.exit()

    height, width = image.shape[:2]

    src_pts = np.array(corners, dtype="float32")

    dst_pts = np.array([
        [0, 0],
        [width, 0],
        [0, height],
        [width, height]
    ], dtype="float32")

    H, _ = cv2.findHomography(src_pts, dst_pts)

    return H

# Parameters: image path, transformation matrix
# Returns: None

def display_grid(image, H):
    height, width = image.shape[:2]
    top_down_view = cv2.warpPerspective(image, H, (width, height))

    cell_width = width // 8
    cell_height = height // 8
    for i in range(9):
        cv2.line(top_down_view, (0, i * cell_height), (width, i * cell_height), (0, 0, 255), 2)
        cv2.line(top_down_view, (i * cell_width, 0), (i * cell_width, height), (0, 0, 255), 2)

    H_inv = np.linalg.inv(H)
    angled_view_with_grid = cv2.warpPerspective(top_down_view, H_inv, (image.shape[1], image.shape[0]))

    cv2.imshow('grid', angled_view_with_grid)
    cv2.waitKey(0)

# Parameters: 3x3 perspective transformation array, coordinate pair, image path
# Returns: row and column of proper square (indexed from top left)

def get_grid_cell(H, coords, image):
    height, width = image.shape[:2]
    cell_width = width // 8
    cell_height = height // 8

    pt = np.array([coords[0], coords[1], 1], dtype="float32")
    
    dst_pt = np.dot(H, pt)
    dst_pt = dst_pt / dst_pt[2]
    
    x, y = int(dst_pt[0]), int(dst_pt[1])
    row, col = y // cell_height, x // cell_width
  
    if 0 <= row and row <= 7 and 0 <= col and col <= 7:
        return row, col
    return -1,-1

# Parameter: FEN string
# Returns: 2D list of position

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

# Parameter: 2D list of position
# Returns: FEN string

def array_to_FEN(array):
    fen = ""
    for i in array:
        empty_spaces = 0
        for j in i:
            if j == "":
                empty_spaces += 1
            elif empty_spaces != 0:
                fen += str(empty_spaces)
                fen += j
                empty_spaces = 0
            else:
                fen += j
        fen += str(empty_spaces) if empty_spaces > 0 else ''
        fen += "/"
    fen = fen[:len(fen)-1]
    return fen

# Parameter: 2D list of position
# Returns: printable and formatted string of position

def array_to_string(array):
    result = ''
    for row in array:
        for char in row:
            if char == '':
                result += '-'
            result += char
            result += ' '
        result += '\n'
    return result

# Parameter: 2D list of position
# Returns: None

def display_board(piece_list):
    screen = pygame.display.set_mode((480, 480))
    pygame.display.set_caption("Chess Board")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        for row in range(8):
            for col in range(8):
                # Determine the color of the tile
                if (row + col) % 2 == 0:
                    color = (227,193,111)
                else:
                    color = (184,139,74)
                
                # Draw the tile
                pygame.draw.rect(screen, color, pygame.Rect(col * 60, row * 60, 60, 60))
                
                # Draw the piece, if any
                piece = piece_list[row][col]
                if piece != '':
                    if piece.upper() == piece:
                        piece_image = r'pieces\w' + piece.lower() + '.png'
                    else:
                        piece_image = r'pieces\b' + piece.lower() + '.png'
                    piece_image = pygame.image.load(piece_image)
                    piece_rect = piece_image.get_rect(center=(col * 60 + 60 // 2, row * 60 + 60 // 2))
                    screen.blit(piece_image, piece_rect)
        pygame.display.flip()

    pygame.quit()

# Parameters: 2D array of frame, 2D list of coordinate pairs, print boolean, grid boolean, display boolean
# Returns: FEN string

def read_frame(img, corners, show_string=False, show_grid=False, show_pos=False):
    corners = convert_corners(img, corners, (IMAGE_X,IMAGE_Y))
    img = cv2.resize(img,(IMAGE_X,IMAGE_Y))
    result = '8/8/8/8/8/8/8/8'
    result = FEN_to_array(result)
    priority = ['k','q','r','p','b','n','K','N','P','R','Q','B','']
    types, coords, confs = detect_pieces(img)
    M = find_transformation_matrix(img, corners)
    for i in range(len(types)-1,-1,-1):
        y,x = get_grid_cell(M, (coords[i][0],coords[i][1]), img)
        if y != -1 and piece_threshold[types[i]] <= confs[i] and (priority.index(types[i]) < priority.index(result[y][x]) or (types[i] == 'b' and result[y][x] == 'k')):
            result[y][x] = types[i]

    if show_string:
        print(array_to_string(result))
    if show_grid:
        display_grid(img, M)
    if show_pos:
        display_board(result)
        
    return array_to_FEN(result)

# -------------------------------------------------------------------------- CHESS ENGINE -----------------------------------------------------------------------------
class ChessBot:
    def __init__(self, level):
        self.level = level
        self.engine = chess.engine.SimpleEngine.popen_uci(r"fish\stockfish\stockfish-windows-x86-64-vnni512.exe")
    
    # Parameters: Instance of ChessBot, instance of Board class
    # Returns: Instance of Move.uci class

    def choose_move(self, board):
        level_depths = {
            2: 1,
            3: 2,
            4: 3,
            5: 4
        }
        if self.level == 1:
            return self.random_move(board)
        return self.engine_move(board, depth=level_depths[self.level])
   
    # Parameters: Instance of ChessBot, instance of Board class
    # Returns: Instance of Move.uci class

    def random_move(self, board):
        return random.choice(list(board.legal_moves))
   
    # Parameters: Instance of ChessBot, instance of Board class, depth int
    # Returns: Instance of Move.uci class

    def engine_move(self, board, depth):
        result = self.engine.play(board, chess.engine.Limit(depth=depth))
        return result.move
   
    # Parameters: Instance of ChessBot
    # Returns: None

    def close(self):
        self.engine.quit()
   
    # Parameters: FEN string, level int, color char
    # Returns: Instance of Move.uci class

def get_bot_move_from_fen(fen, level, color):
    fen += ' ' + color
    board = chess.Board(fen)
    bot = ChessBot(level)
    move = bot.choose_move(board)
    return move
   
    # Parameters: Index of square int
    # Returns: Index of LED int

def square_to_LED(index):
    squares = {56:63,57:61,58:45,59:43,60:27,61:25,62:9,63:7,
               48:64,49:60,50:46,51:42,52:28,53:24,54:10,55:6,
               40:65,41:59,42:47,43:41,44:29,45:23,46:11,47:5,
               32:66,33:58,34:48,35:40,36:30,37:22,38:12,39:4,
               24:67,25:57,26:49,27:39,28:31,29:21,30:13,31:3,
               16:68,17:56,18:50,19:38,20:32,21:20,22:14,23:2,
               8:69,9:55,10:51,11:37,12:33,13:19,14:15,15:1,
               0:70,1:54,2:52,3:36,4:34,5:18,6:16,7:0}
    return squares[index]


# -------------------------------------------------------------------------- LCD DISPLAY -----------------------------------------------------------------------------
pygame.init()

time_map = {
    '5 min': 5 * 60,
    '10 min': 10 * 60,
    '30 min': 30 * 60,
    '1 hour': 60 * 60,
}
SCREEN_WIDTH, SCREEN_HEIGHT = 1024, 600
# 1382, 810

def initialize_display(width, height):
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption('LCD Display')
    return screen
# Scaling factor based on a base resolution (2048x1200)
base_width = 2048
base_height = 1200
scaling_factor = SCREEN_WIDTH / base_width

# Slider settings
slider_color = (200, 200, 200)
slider_rect = pygame.Rect(200 * scaling_factor, 700 * scaling_factor, 1648 * scaling_factor, 100 * scaling_factor)  # x, y, width, height
knob_color = (100, 100, 250)
knob_rect = pygame.Rect(slider_rect.x, slider_rect.y - 20 * scaling_factor, 60 * scaling_factor, 140 * scaling_factor)  # x, y, width, height
dragging = False

# Define the 5 snap positions
num_positions = 5
positions = [
    slider_rect.x + i * (slider_rect.width - knob_rect.width) // (num_positions - 1)
    for i in range(num_positions)
]

# Font settings
num_font = pygame.font.SysFont(None, int(80 * scaling_factor))
text_font = pygame.font.SysFont(None, int(120 * scaling_factor))
title_font = pygame.font.SysFont(None, int(200 * scaling_factor))

# Button settings
button_color = (0, 200, 0)
button_hover_color = (0, 255, 0)
button_rect = pygame.Rect(824 * scaling_factor, 400 * scaling_factor, 400 * scaling_factor, 160 * scaling_factor)
button_text = text_font.render("START", True, (0, 0, 0))

# Toggle button settings
toggle_button_color = (200, 200, 200)
toggle_button_rect = pygame.Rect(324 * scaling_factor, 400 * scaling_factor, 400 * scaling_factor, 160 * scaling_factor)
toggle_text_black = text_font.render("BLACK", True, (200, 200, 200))
toggle_text_white = text_font.render("WHITE", True, (0, 0, 0))
is_black = False

# Time control button settings
time_controls = ["5 min", "10 min", "30 min", "1 hour"]
time_index = 0
time_button_rect = pygame.Rect(1324 * scaling_factor, 400 * scaling_factor, 400 * scaling_factor, 160 * scaling_factor)

# Restart button settings
restart_button_color = (200, 0, 0)
restart_button_hover_color = (255, 0, 0)
restart_button_rect = pygame.Rect(1598 * scaling_factor, 50 * scaling_factor, 400 * scaling_factor, 160 * scaling_factor)
restart_button_text = text_font.render("RESTART", True, (200, 200, 200))

# Move confirmation button settings
confirm_button_color = (200, 200, 200)
confirm_button_hover_color = (255, 255, 255)
confirm_button_rect = pygame.Rect(624 * scaling_factor, 1000 * scaling_factor, 800 * scaling_factor, 160 * scaling_factor)
confirm_button_text = text_font.render("CONFIRM MOVE", True, (30, 30, 30))
   
# Parameters: Instance of pygame screen class
# Returns: None

def draw_slider(screen):
    pygame.draw.rect(screen, slider_color, slider_rect)
    pygame.draw.rect(screen, knob_color, knob_rect)
    title_text = title_font.render("MAGIC GAMBIT", True, (200, 200, 200))
    difficulty_text = text_font.render("DIFFICULTY", True, (200, 200, 200))
    screen.blit(difficulty_text, (800 * scaling_factor, 950 * scaling_factor))
    screen.blit(title_text, (512 * scaling_factor, 50 * scaling_factor))

    # Draw snap position lines and numbers
    for i, pos in enumerate(positions):
        num_text = num_font.render(str(i + 1), True, (200, 200, 200))
        screen.blit(num_text, (pos + knob_rect.width // 2 - num_text.get_width() // 2, slider_rect.y + slider_rect.height + 60 * scaling_factor))
   
# Parameters: Instance of pygame screen class
# Returns: None

def draw_confirm_button(screen):
    mouse_pos = pygame.mouse.get_pos()
    if confirm_button_rect.collidepoint(mouse_pos):
        color = confirm_button_hover_color
    else:
        color = confirm_button_color
    pygame.draw.rect(screen, color, confirm_button_rect)
    screen.blit(confirm_button_text, (confirm_button_rect.x + (confirm_button_rect.width - confirm_button_text.get_width()) // 2,
                              confirm_button_rect.y + (confirm_button_rect.height - confirm_button_text.get_height()) // 2))

def draw_start_button(screen):
    mouse_pos = pygame.mouse.get_pos()
    if button_rect.collidepoint(mouse_pos):
        color = button_hover_color
    else:
        color = button_color
    pygame.draw.rect(screen, color, button_rect)
    screen.blit(button_text, (button_rect.x + (button_rect.width - button_text.get_width()) // 2,
                              button_rect.y + (button_rect.height - button_text.get_height()) // 2))
   
# Parameters: Instance of pygame screen class
# Returns: None

def draw_restart_button(screen):
    mouse_pos = pygame.mouse.get_pos()
    if restart_button_rect.collidepoint(mouse_pos):
        color = restart_button_hover_color
    else:
        color = restart_button_color
    pygame.draw.rect(screen, color, restart_button_rect)
    screen.blit(restart_button_text, (restart_button_rect.x + (restart_button_rect.width - restart_button_text.get_width()) // 2,
                              restart_button_rect.y + (restart_button_rect.height - restart_button_text.get_height()) // 2))
     
# Parameters: Instance of pygame screen class
# Returns: None
  
def draw_toggle_button(screen):
    pygame.draw.rect(screen, (0, 0, 0) if is_black else toggle_button_color, toggle_button_rect)
    text = toggle_text_black if is_black else toggle_text_white
    screen.blit(text, (toggle_button_rect.x + (toggle_button_rect.width - text.get_width()) // 2,
                       toggle_button_rect.y + (toggle_button_rect.height - text.get_height()) // 2))
   
# Parameters: Instance of pygame screen class
# Returns: None

def draw_time_button(screen):
    time_text = text_font.render(time_controls[time_index], True, (0, 0, 0))
    pygame.draw.rect(screen, (200, 200, 200), time_button_rect)
    screen.blit(time_text, (time_button_rect.x + (time_button_rect.width - time_text.get_width()) // 2,
                            time_button_rect.y + (time_button_rect.height - time_text.get_height()) // 2))
   
# Parameters: int coordinate of knob x position
# Returns: int coordinate of nearest snapping point

def snap_to_position(x):
    return min(positions, key=lambda pos: abs(pos - x))
   
# Parameters: Instance of pygame screen class
# Returns: None

def display_setup(screen):
    global dragging, is_black, time_index
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if knob_rect.collidepoint(event.pos):
                dragging = True
            elif button_rect.collidepoint(event.pos):
                return positions.index(knob_rect.x) + 1, is_black, time_controls[time_index]
            elif toggle_button_rect.collidepoint(event.pos):
                is_black = not is_black
            elif time_button_rect.collidepoint(event.pos):
                time_index = (time_index + 1) % len(time_controls)
        elif event.type == pygame.MOUSEBUTTONUP:
            dragging = False
            knob_rect.x = snap_to_position(knob_rect.x)  # Ensure snapping to position
        elif event.type == pygame.MOUSEMOTION:
            if dragging:
                knob_rect.x = event.pos[0] - knob_rect.width // 2
                knob_rect.x = max(slider_rect.x, min(knob_rect.x, slider_rect.right - knob_rect.width))

    screen.fill((30, 30, 30))  # Clear screen with a background color
    draw_slider(screen)
    draw_start_button(screen)
    draw_toggle_button(screen)
    draw_time_button(screen)
    pygame.display.update()
   
# Parameters: Instance of pygame screen class
# Returns: None

def get_settings(screen):
    settings = display_setup(screen)
    while settings is None:
        settings = display_setup(screen)
    difficulty, color, time = settings
    if color:
        color = 'w'
    else:
        color = 'b'
    return difficulty, color, time
  
# Parameters: Instance of pygame screen class, time left int
# Returns: None or restart string

def display_timer(screen, total_time):
    global is_bot_turn
    font = pygame.font.SysFont(None, int(150 * scaling_factor))

    minutes = total_time // 60
    seconds = total_time % 60
    time_display = f"{minutes:02}:{seconds:02}"

    screen.fill((30, 30, 30))
    time_text = font.render(time_display, True, (200, 200, 200))
    move_text = font.render("YOUR MOVE", True, (200, 200, 200)) if not is_bot_turn else font.render("BOT'S MOVE", True, (200, 200, 200))
    screen.blit(time_text, (screen.get_width() // 2 - time_text.get_width() // 2,
                            screen.get_height() // 2 - time_text.get_height() // 2))
    screen.blit(move_text, (screen.get_width() // 2 - move_text.get_width() // 2,
                            screen.get_height() // 2 - move_text.get_height() // 2 + 200 * scaling_factor))

    draw_restart_button(screen)
    if not is_bot_turn:
        draw_confirm_button(screen)

    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if restart_button_rect.collidepoint(event.pos):
                return 'restart'
            elif confirm_button_rect.collidepoint(event.pos) and not is_bot_turn:
                is_bot_turn = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                is_bot_turn = True
            elif event.key == pygame.K_q:
                pygame.quit()
                sys.exit()

  
# Parameters: Instance of pygame screen class, win boolean
# Returns: None or restart string

def display_end(screen, win):
    screen.fill((30,30,30))
    font = pygame.font.SysFont(None, int(250 * scaling_factor))
    if win:
        win_text = font.render("YOU WIN!", True, (200, 200, 200))
    else:
        win_text = font.render("YOU LOSE!", True, (200, 200, 200))
    screen.blit(win_text, (screen.get_width() // 2 - win_text.get_width() // 2,
                            screen.get_height() // 2 - win_text.get_height() // 2))
    draw_restart_button(screen)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if restart_button_rect.collidepoint(event.pos):
                return 'restart'
    pygame.display.update()
# -------------------------------------------------------------------------- MQTT -----------------------------------------------------------------------------
  
# Parameters: red LED int, green LED int
# Returns: None

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

def publish_pos(fen):
    client = paho.Client(client_id="publisher", protocol=paho.MQTTv5)
    client.tls_set(tls_version=ssl.PROTOCOL_TLS)
    client.username_pw_set("fensetup", "Magicgambit10")

    client.connect("c424fde2a0ed48538e2b798a0d0e4c38.s1.eu.hivemq.cloud", 8883)
    client.loop_start()

    # Publish a message to the test topic
    client.publish("test/fen", payload=fen, qos=1)

    client.loop_stop()  # Stop the loop if you're done publishing
    client.disconnect()
# -------------------------------------------------------------------------- MAIN -----------------------------------------------------------------------------
# Threshold values for piece detection
piece_threshold = {
    'k': .01, #.01
    'p': .3, #.3
    'n': .1, #.1
    'b': .5, #.5
    'r': .4, #.4
    'q': .3, #.3
    'K': .2, #.2
    'P': .2, #.2
    'N': .4, #.4
    'B': .1, #.1
    'R': .05, #.05
    'Q': .01, #.01
}
# Camera setup
camera = initialize_camera()

IMAGE_X, IMAGE_Y = 480,480
# YOLO model setup
model = YOLOv10('best.pt')
game_over = None
# pygame initialization
window = initialize_display(SCREEN_WIDTH, SCREEN_HEIGHT)
def main():
    global window, time_map, is_bot_turn, camera
    # main setup
    game_over = False
    diff, bot_color, time_control = get_settings(window)
    window.fill((30, 30, 30))
    seconds = time_map[time_control]

    if bot_color == 'w':
        is_bot_turn = True
    else:
        is_bot_turn = False

    clock = pygame.time.Clock()
    win = False
    while not game_over:
        # bot move
        if is_bot_turn:
            # [top left, top right, bottom left, bottom right]
            clock.tick(1)
            x = display_timer(window, round(seconds))
            if x != None:
                return
            legal_pos = False
            while not legal_pos:
                board_corners = [[130, 270], [553, 61], [448, 667], [923, 343]]
                board_corners = initial_convert(board_corners)
                img = get_frame(camera)
                pos = read_frame(img, board_corners, True)
                if pos.count('k') != 1 or pos.count('K') != 1:
                    print('Failed to locate kings')
                    time.sleep(.5)
                    continue
                legal_pos = True
            # player checkmate
            publish_pos(pos)
            board = chess.Board(pos)
            if chess.Board(pos).is_checkmate():
                game_over = True
                win = True
                break
            response = get_bot_move_from_fen(pos, diff, bot_color)
            board = chess.Board(pos + ' ' + bot_color)
            board.push(response)
            publish_pos(board.board_fen())
            # bot checkmate
            if board.is_checkmate():
                game_over = True
                win = False

            r = square_to_LED(response.from_square)
            g = square_to_LED(response.to_square)
            publish(r,g)

            is_bot_turn = False
        # player move
        else:
            clock.tick(25)
            seconds -= .04
            # time control
            if seconds <= 0:
                game_over = True
                win = False
            x = display_timer(window, round(seconds))
            if x != None:
                return

        pygame.display.update()
    while True:
        x = display_end(window, win)
        if x != None:
            break

while True:
    main()