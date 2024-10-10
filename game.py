from flask import Flask, render_template_string, Response, request
import pygame
import spacy
import os
import io
from PIL import Image

# Initialize Pygame and spaCy
pygame.init()
nlp = spacy.load("en_core_web_sm")

# Set up Flask
app = Flask(__name__)

# Set up the display for Pygame (we'll capture frames)
width, height = 800, 600
screen = pygame.Surface((width, height))

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)

# Load background image
bg_image = pygame.image.load(os.path.join("assets", "Bg_Thomas (2).png"))
bg_image = pygame.transform.scale(bg_image, (width, height))

# Character properties
character_pos = [width // 2, height // 2]
character_radius = 20
character_color = RED
character_velocity = [0, 0]

# Platforms
platforms = [
    {"rect": pygame.Rect(80, 500, 929, 20), "color": WHITE},
    {"rect": pygame.Rect(135, 395, 929, 20), "color": WHITE},
    {"rect": pygame.Rect(210, 285, 929, 20), "color": WHITE}
]

# Physics
move_speed = 30
jump_speed = -15
gravity = 0.8

# Font and Input box
input_text = ''
input_active = False

clock = pygame.time.Clock()

# Colors dictionary to map names to RGB values
COLORS = {
    'red': RED,
    'blue': BLUE,
    'yellow': YELLOW,
    'green': GREEN,
    'white': WHITE,
    'black': BLACK
}

def update_character(command=None):
    global character_pos, character_velocity, character_color

    # Reset horizontal velocity to 0 before applying new commands
    character_velocity[0] = 0

    # Apply command logic if any command was sent
    if command:
        # Handle movement
        if 'left' in command:
            character_velocity[0] = -move_speed
        elif 'right' in command:
            character_velocity[0] = move_speed
        elif 'jump' in command and character_velocity[1] == 0:  # Only jump if on the ground
            character_velocity[1] = jump_speed

        # Handle color change
        if 'change color to' in command:
            doc = nlp(command)
            # Try to extract the color after 'to'
            for token in doc:
                if token.text.lower() in COLORS:
                    character_color = COLORS[token.text.lower()]
                    break

    # Apply velocity to character position
    character_pos[0] += character_velocity[0]
    character_pos[1] += character_velocity[1]

    # Apply gravity
    character_velocity[1] += gravity

    # Check for collisions with platforms (to stop the character from falling)
    for platform in platforms:
        if platform['rect'].collidepoint(character_pos[0], character_pos[1] + character_radius):
            character_velocity[1] = 0
            character_pos[1] = platform['rect'].top - character_radius
            break

def draw():
    screen.blit(bg_image, (0, 0))
    for platform in platforms:
        pygame.draw.rect(screen, platform['color'], platform['rect'])
    pygame.draw.circle(screen, character_color, [int(character_pos[0]), int(character_pos[1])], character_radius)

def capture_frame():
    # Capture the current frame from Pygame surface and convert to a PIL Image
    data = pygame.image.tostring(screen, 'RGBA')
    img = Image.frombytes('RGBA', screen.get_size(), data)
    return img

def generate():
    while True:
        update_character()
        draw()
        img = capture_frame()

        # Convert the PIL image to bytes to serve it as an HTTP response
        byte_io = io.BytesIO()
        img.save(byte_io, 'PNG')
        byte_io.seek(0)

        yield (b'--frame\r\n'
               b'Content-Type: image/png\r\n\r\n' + byte_io.read() + b'\r\n')


@app.route('/', methods=['GET', 'POST'])
def index():
    command = None
    if request.method == 'POST':
        command = request.form['command']
        update_character(command)
    return render_template_string('''
        <html>
        <head>
            <title>Thomas was never alone</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                html, body { height: 100%; overflow: hidden; display: flex; justify-content: center; align-items: center; }

                body {
                    background: url("{{ url_for('static', filename='image.png') }}") no-repeat center center fixed;
                    background-size: cover;
                }

                #game-frame {
                    display: block;
                    width: 100%;
                    height: 100%;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }

                #game-frame img {
                    max-width: 100vw;
                    max-height: 100vh;
                    width: auto;
                    height: auto;
                }

                form {
                    position: fixed;
                    bottom: 10px;
                    width: 100%;
                    text-align: center;
                }

                input[type="text"] {
                    padding: 10px;
                    font-size: 16px;
                    width: 300px;
                }

                button {
                    padding: 10px;
                    font-size: 16px;
                }
            </style>
        </head>
        <body>
            <div id="game-frame">
                <img src="{{ url_for('video_feed') }}" alt="Game">
            </div>
            <form method="POST">
                <input type="text" name="command" placeholder="Enter command (left, right, jump)" autofocus>
                <button type="submit">Send</button>
            </form>
        </body>
        </html>
    ''', command=command)


@app.route('/video_feed')
def video_feed():
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
