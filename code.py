import board
import displayio
import terminalio
import time
from adafruit_display_text import label  # display
from adafruit_macropad import MacroPad   # tone
from rainbowio import colorwheel

#############################
# Constants/Globals
#############################

MAX_KEYS = 12

KEY_HOLD_NS = 1000000000
ENCODER_HOLD = 4000000000

BRIGHTNESS_LOW = 0.2
BRIGHTNESS_HIGH = 1.0

GREEN = 0x00FF00
YELLOW = 0xFFFF00
ORANGE = 0xFF8C00
RED = 0xFF0000

GREEN_DIM = 0x002200
YELLOW_DIM = 0x222200
ORANGE_DIM = 0x221200
RED_DIM = 0x220000

MENU_IDLE = 0
MENU_SETUP = 1
MENU_NUM_TIMERS = 2
MENU_NUM_TIMERS_LOOP = 3
MENU_TMR_DIRECTION = 4
MENU_TMR_START = 5
MENU_TMR_SOUND = 6
MENU_DONE = 10

class Timer():
    delta = 1
    start = 0
    current = 0
    formatted = "0:00.0"
    running = False
    paused = False
    color = GREEN
    color_dim = GREEN_DIM
    current_yellow = 0
    current_orange = 0
    current_red = 0
    sound = False
    pressed_last_ns = 0

macropad = MacroPad()

text_areas = []
index_keys = 0
index_line1 = 0
index_line2 = 0
index_line3 = 0
index_line4 = 0

#############################
# Setup - Hardware
#############################

def setup_hardware():
    global text_areas
    global index_keys
    global index_line1
    global index_line2
    global index_line3
    global index_line4

    # turn off pixels
    for i in range(len(macropad.pixels)):
        macropad.pixels[i] = 0x000000
    macropad.pixels.brightness = BRIGHTNESS_HIGH

    # set up (empty) text areas in a text_group
    DISPLAY_WIDTH = 128
    DISPLAY_HEIGHT = 64
    y = -4
    ydelta = 18

    index_line1 = len(text_areas)
    ta = label.Label(terminalio.FONT, text="")
    ta.anchor_point = (0.0, 0.0)
    ta.anchored_position = (0, y)
    text_areas.append(ta)
    y = y + ydelta

    index_line2 = len(text_areas)
    ta = label.Label(terminalio.FONT, text="")
    ta.anchor_point = (0.0, 0.0)
    ta.anchored_position = (0, y-8)
    text_areas.append(ta)
    y = y + ydelta

    index_line3 = len(text_areas)
    ta = label.Label(terminalio.FONT, text="")
    ta.anchor_point = (0.0, 0.0)
    ta.anchored_position = (0, y)
    text_areas.append(ta)
    y = y + ydelta

    index_line4 = len(text_areas)
    ta = label.Label(terminalio.FONT, text="")
    ta.anchor_point = (0.0, 0.0)
    ta.anchored_position = (0, y)
    text_areas.append(ta)
    y = y + ydelta

    y = ydelta
    index_keys = len(text_areas)
    b = 0.0
    for row in range(4):
        a = 0.0
        x = 0
        for col in range(3):
            ta = label.Label(terminalio.FONT, text="")
            ta.anchor_point = (a, b)
            ta.anchored_position = (x, y)
            text_areas.append(ta)
            a = a + 0.5
            x = x + DISPLAY_WIDTH / 2
        b = b + 0.5
        y = y + ydelta

    text_group = displayio.Group()
    for ta in text_areas:
        text_group.append(ta)

    text_areas[index_line1].text = f'macropad timers  {multiplier:.02f}'

    board.DISPLAY.show(text_group)

#############################
# Macropad Functions
#############################

def sound_play():
    global macropad
    macropad.play_tone(1319, 0.1)
    macropad.play_tone(988, 0.1)

def encoder_pressed():
    global macropad

    result = False
    macropad.encoder_switch_debounced.update()
    if macropad.encoder_switch_debounced.pressed:
        result = True
    return result

encoder_last_ns = time.monotonic_ns()
encoder_active = False
def encoder_long_pressed():
    global macropad
    global encoder_last_ns
    global encoder_active

    result = False
    current_ns = time.monotonic_ns()
    if macropad.encoder_switch:
        encoder_active = True
    else:
        if encoder_active and current_ns - encoder_last_ns > ENCODER_HOLD:
            result = True
        encoder_last_ns = current_ns
    return result

def check_keys():
    event = macropad.keys.events.get()
    if event:
        i = event.key_number
        if i < len(timers):
            if event.pressed:
                timers[i].paused = not timers[i].paused
                if not timers[i].paused:
                    timers[i].running = True
                timers[i].pressed_last_ns = time.monotonic_ns()
            if event.released:
                current_ns = time.monotonic_ns()
                if timers[i].paused and (current_ns - timers[i].pressed_last_ns) > KEY_HOLD_NS:
                    timer_reset(i)
                timers[i].pressed_last_ns = current_ns

def check_encoder():
    if menu_state == MENU_IDLE and encoder_pressed():
        timers_toggle_all()

def timers_display():
    global timers
    global text_areas

    if menu_state > MENU_IDLE:
        for i in range(MAX_KEYS):
            text_areas[index_keys+i].text = ""
        return

    for i, t in enumerate(timers):
        text_areas[index_keys+i].text = t.formatted

def timers_pixels():
    global index_keys
    global menu_state

    if menu_state > MENU_IDLE:
        for i in range(MAX_KEYS):
            macropad.pixels[i] = 0x000000
        return

    for i, t in enumerate(timers):
        if not t.paused:
            macropad.pixels[i] = t.color
        if t.paused:
            macropad.pixels[i] = t.color_dim 


#############################
# Timer Functions
#############################
timers = []

def timer_formatted(current):
    # assume current is in 0.1sec
    m = (current % 10)
    s = (current // 10)
    M = (s // 60)
    s = s - (60*M)
    if M > 60:
        M = 0
    return f'{M:2}:{s:02}.{m:1}'
    #return f'{current}'

def timer_add(start, delta, sound=False):
    global timers
    t = Timer()
    t.start = 0
    t.current = 0
    
    t.running = False
    t.paused = True
    t.delta = delta
    if delta < 0:
        t.start = start
        t.current = start
    t.formatted = timer_formatted(t.current)
    t.sound = sound

    t.current_yellow = t.start // 7
    t.current_orange = t.start // 4
    t.current_red = t.start // 10

    timers.append(t)

def timer_reset(index):
    t = timers[index]
    t.current = 0
    t.paused = True
    if t.delta < 0:
        t.current = t.start
    t.formatted = timer_formatted(t.current)
    t.color = GREEN

def timers_start_all():
    global timers
    for _, t in enumerate(timers):
        t.running = True
        t.paused = False

def timers_reset_all():
    global timers
    for i, _ in enumerate(timers):
        timer_reset(i)

def timers_toggle_all():
    global timers
    for _, t in enumerate(timers):
        t.paused = not t.paused 
        if not t.running and not t.paused:
            t.running = True

multiplier = 1.0
last_ns = time.monotonic_ns()
def timers_update():
    global timers
    global last_ns

    current_ns = time.monotonic_ns()
    fdelta = multiplier * (current_ns - last_ns)
    delta = int(fdelta) // 100000000
    if delta == 0:
        return  # update is running fast
    last_ns = current_ns

    for _, t in enumerate(timers):
        if t.running:
            if not t.paused:
                # update current time
                if t.delta < 0:
                    t.current = max(0, t.current - delta)
                else:
                    t.current = max(0, t.current + delta)
                t.formatted = timer_formatted(t.current)
                if t.delta < 0:
                    # update color
                    t.color = GREEN
                    t.color_dim = GREEN_DIM
                    if t.current < t.current_yellow:
                        t.color = YELLOW
                        t.color = YELLOW_DIM
                    if t.current < t.current_orange:
                        t.color = ORANGE
                        t.color = ORANGE_DIM
                    if t.current < t.current_red:
                        t.color = RED
                        t.color = RED_DIM
                    if t.current == 0:
                        t.running = False
                        if t.sound:
                            sound_play()
                else:
                    t.color = GREEN

#############################
# Menu Functions
#############################

menu_state = MENU_IDLE
menu_timer_count = 1
menu_timer_index = -1
menu_timer_direction = "up"
menu_timer_start = 60
menu_timer_sound = "off"
menu_current_position = 0
menu_last_position = 0


def check_menu():
    global index_line1
    global menu_state
    global menu_timer_count
    global menu_timer_index
    global menu_timer_direction
    global menu_timer_start
    global menu_timer_sound
    global menu_current_position
    global menu_last_position
    global multiplier
    global text_areas

    menu_last_position = menu_current_position
    menu_current_position = macropad.encoder

    if menu_state == MENU_IDLE:
        if menu_current_position > menu_last_position:
            multiplier = multiplier + 0.1
            text_areas[index_line1].text = f'macropad timers  {multiplier:.02f}'

        if menu_current_position < menu_last_position:
            multiplier = max(0.1, multiplier - 0.1)
            text_areas[index_line1].text = f'macropad timers  {multiplier:.02f}'

    elif menu_state == MENU_SETUP:
        text_areas[index_line1].text = "setup..."
        text_areas[index_line2].text = ""
        text_areas[index_line3].text = ""
        text_areas[index_line4].text = ""
        if encoder_pressed():
            menu_state = MENU_NUM_TIMERS

    elif menu_state == MENU_NUM_TIMERS:
        text_areas[index_line1].text = "number timers: " + str(menu_timer_count)
        if menu_current_position > menu_last_position:
            menu_timer_count = min(MAX_KEYS, menu_timer_count + 1)
        if menu_current_position < menu_last_position:
            menu_timer_count = max(1, menu_timer_count - 1)
        if encoder_pressed():
            menu_state = MENU_NUM_TIMERS_LOOP

    elif menu_state == MENU_NUM_TIMERS_LOOP:
        if menu_timer_index >= (menu_timer_count - 1):
            menu_state = MENU_DONE
        else:
            menu_timer_index = menu_timer_index + 1
            menu_state = MENU_TMR_DIRECTION

    elif menu_state == MENU_TMR_DIRECTION:
        text_areas[index_line1].text = "tmr" + str(menu_timer_index+1) + " direction: " + menu_timer_direction
        if menu_current_position > menu_last_position:
            menu_timer_direction = "up"
        if menu_current_position < menu_last_position:
            menu_timer_direction = "down"
        if encoder_pressed():
            if menu_timer_direction == "up":
                timer_add(start=0, delta=1, sound=False)
                menu_timer_direction = "up"
                menu_timer_start = 60
                menu_timer_sound = "off"
                menu_state = MENU_NUM_TIMERS_LOOP
            if menu_timer_direction == "down":
                menu_state = MENU_TMR_START

    elif menu_state == MENU_TMR_START:
        M = (menu_timer_start) // 60
        s = (menu_timer_start) % 60
        text_areas[index_line1].text = "tmr" + str(menu_timer_index+1) + " start: " + f'{M:02}:{s:02}'
        if menu_current_position > menu_last_position:
            menu_timer_start = min(3600, menu_timer_start + 1)
        if menu_current_position < menu_last_position:
            menu_timer_start = max(0, menu_timer_start - 1)
        if encoder_pressed():
            menu_state = MENU_TMR_SOUND

    elif menu_state == MENU_TMR_SOUND:
        text_areas[index_line1].text = "tmr" + str(menu_timer_index+1) + " sound: " + menu_timer_sound
        if menu_current_position > menu_last_position:
            menu_timer_sound = "y"
        if menu_current_position < menu_last_position:
            menu_timer_sound = "n"
        if encoder_pressed():
            # create timer
            delta = 1
            if menu_timer_direction == "down":
                delta = -1
            sound = False
            if menu_timer_sound == "y":
                sound = True
            timer_add(start=(menu_timer_start*10), delta=delta, sound=sound)
            menu_timer_direction = "up"
            menu_timer_start = 60
            menu_timer_sound = "off"
            menu_state = MENU_NUM_TIMERS_LOOP

    elif menu_state == MENU_DONE:
        text_areas[index_line1].text = f'macropad timers  {multiplier:.02f}'
        menu_state = 0
        menu_timer_count = 1
        menu_timer_index = -1
        timers_reset_all()

#############################
# Button Functions
#############################

def check_encoder_button():
    global menu_state
    global timers

    if menu_state > MENU_SETUP:
        macropad.pixels.brightness = BRIGHTNESS_LOW
        return
    macropad.pixels.brightness = BRIGHTNESS_HIGH
    if encoder_long_pressed():
        timers_reset_all()
        timers = []
        menu_state = MENU_SETUP

#############################
# Setup - Application
#############################

# read data.txt
try:
    with open('data.txt') as file:
        lines = file.readlines()
        for line in lines:
            if len(timers) < MAX_KEYS:
                #     start, delta, sound
                # ie. 300,      -1,  True
                parts = line.split(',')
                sound = ("True" in parts[2])
                timer_add(start=int(parts[0]), delta=int(parts[1]), sound=sound)
except Exception as err:
    print(err)

setup_hardware()
timers_display()
timers_pixels()
# timers_start_all()

#############################
# Main Loop - Application
#############################
while True:
    check_encoder_button()
    check_keys()
    check_encoder()
    check_menu()
    timers_update()
    timers_display()
    timers_pixels()
