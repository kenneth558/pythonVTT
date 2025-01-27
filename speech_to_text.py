#!/usr/bin/env python3
# File: speech_to_text.py

import speech_recognition as sr
from pynput.keyboard import Controller, Key, Listener
import time
import threading
import sys

DEBUG = False

###############################################################################
# 1) Dictionaries & Maps (same as stable base + a few symbol keys if you want)
###############################################################################

MODIFIER_MAP = {
    "shift": Key.shift,
    "control": Key.ctrl,
    "ctrl": Key.ctrl,
    "alt": Key.alt
}

LOCK_MAP = {
    "caps lock": Key.caps_lock,
    "num lock": Key.num_lock
}

ARROW_SYNONYMS = {
    "left arrow": "left arrow",
    "arrow left": "left arrow",
    "leftarrow": "left arrow",
    "go left": "left arrow",

    "right arrow": "right arrow",
    "arrow right": "right arrow",
    "rightarrow": "right arrow",
    "go right": "right arrow",

    "up arrow": "up arrow",
    "arrow up": "up arrow",
    "uparrow": "up arrow",
    "go up": "up arrow",

    "down arrow": "down arrow",
    "arrow down": "down arrow",
    "downarrow": "down arrow",
    "go down": "down arrow"
}

MAIN_KEY_MAP = {
    "enter": Key.enter,
    "return": Key.enter,
    "escape": Key.esc,
    "esc": Key.esc,
    "backspace": Key.backspace,
    "space": Key.space,
    "tab": Key.tab,
    "home": Key.home,
    "end": Key.end,
    "page up": Key.page_up,
    "page down": Key.page_down,
    "left arrow": Key.left,
    "right arrow": Key.right,
    "up arrow": Key.up,
    "down arrow": Key.down,
    # ...
    # If you have other keys like "equal key", "period key", etc., add them here
}

CUSTOM_ACTIONS = {
    "delete line": "delete_line_action"
}

###############################################################################
# 2) Helper Functions
###############################################################################

keyboard = Controller()

def debug_print(msg):
    if DEBUG:
        print(f"DEBUG: {msg}")

def press_and_release(key_obj):
    keyboard.press(key_obj)
    keyboard.release(key_obj)

def delete_line_action():
    debug_print("Performing 'delete line' action.")
    press_and_release(Key.home)
    keyboard.press(Key.shift)
    press_and_release(Key.down)
    keyboard.release(Key.shift)
    press_and_release(Key.delete)

def release_all_modifiers():
    debug_print("Releasing all modifiers (Shift, Ctrl, Alt).")
    for mod_key in [Key.shift, Key.ctrl, Key.alt]:
        keyboard.release(mod_key)

###############################################################################
# 3) Parsing & Processing Logic
###############################################################################

def parse_tokens_for_modifiers_and_main(tokens):
    modifiers = []
    main_key = None
    idx = 0

    while idx < len(tokens):
        token = tokens[idx]
        if token in MODIFIER_MAP:
            modifiers.append(MODIFIER_MAP[token])
            idx += 1
        else:
            main_key = token
            idx += 1
            # If user said "shift a key", skip 'key'
            if idx < len(tokens) and tokens[idx] == "key":
                idx += 1
            break

    return modifiers, main_key, idx

def process_spoken_phrase(spoken_text):
    text = spoken_text.lower().strip()
    debug_print(f"process_spoken_phrase received: '{text}'")

    if text in CUSTOM_ACTIONS:
        action_val = CUSTOM_ACTIONS[text]
        if action_val == "delete_line_action":
            delete_line_action()
        return

    # lock keys
    if text in LOCK_MAP:
        debug_print(f"Lock key => {text}")
        press_and_release(LOCK_MAP[text])
        return

    # arrow synonyms
    if text in ARROW_SYNONYMS:
        text = ARROW_SYNONYMS[text]
        debug_print(f"Synonym matched => '{text}'")

    tokens = text.split()
    if not tokens:
        return

    modifiers, main_key, idx = parse_tokens_for_modifiers_and_main(tokens)

    if not main_key and modifiers:
        main_key = tokens[-1]

    # hold modifiers
    for m in modifiers:
        debug_print(f"Holding modifier: {m}")
        keyboard.press(m)

    # check main key
    if main_key in MAIN_KEY_MAP:
        debug_print(f"Recognized special key => {main_key}")
        press_and_release(MAIN_KEY_MAP[main_key])
        for mod in reversed(modifiers):
            debug_print(f"Releasing modifier: {mod}")
            keyboard.release(mod)
        return
    elif main_key and len(main_key) == 1:
        debug_print(f"Typing single char => '{main_key}'")
        keyboard.press(main_key)
        keyboard.release(main_key)
        for mod in reversed(modifiers):
            debug_print(f"Releasing modifier: {mod}")
            keyboard.release(mod)
        return

    # fallback => type entire text
    for mod in reversed(modifiers):
        debug_print(f"Releasing modifier (unused): {mod}")
        keyboard.release(mod)

    debug_print("No recognized key => typing text verbatim.")
    keyboard.type(spoken_text + " ")

###############################################################################
# 4) Physical Keyboard Listener for Enter => release modifiers
###############################################################################

def on_press(key):
    if key == Key.enter:
        debug_print("Physical Enter pressed => release all modifiers.")
        release_all_modifiers()

def on_release(key):
    pass

def start_physical_key_listener():
    from pynput.keyboard import Listener
    listener = Listener(on_press=on_press, on_release=on_release)
    listener.start()
    return listener

###############################################################################
# 5) Background Listening for Speech with concurrency=1 (Ignore partial)
###############################################################################

recognizer = sr.Recognizer()
microphone = sr.Microphone()

stop_listening = None

def callback_for_final_only(recognizer_instance, audio_data):
    """
    This callback is invoked whenever a chunk is recognized as final
    (NOT partial). If partial triggers are used, we'll skip them.
    """
    try:
        # Recognize final text
        text = recognizer_instance.recognize_google(audio_data)
        debug_print(f"[Callback] Recognized text => {text}")
        process_spoken_phrase(text)
    except sr.UnknownValueError:
        debug_print("[Callback] Could not understand audio.")
    except sr.RequestError as e:
        debug_print(f"[Callback] Request error => {e}")

def main():
    global stop_listening

    # 1) Start physical key listener
    start_physical_key_listener()

    # 2) Setup microphone
    with microphone as source:
        debug_print("Adjusting for ambient noise, please wait...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
        debug_print("Starting background listener...")

    # 3) concurrency=1 => we use `listen_in_background` just once
    stop_listening = recognizer.listen_in_background(microphone, callback_for_final_only)

    debug_print("Background listener started. Running indefinitely until Ctrl+C...")

    try:
        while True:
            time.sleep(1)  # Keep main thread alive
    except KeyboardInterrupt:
        debug_print("KeyboardInterrupt => shutting down.")
        if stop_listening:
            stop_listening()
        # ensure all modifiers released
        release_all_modifiers()
        sys.exit(0)

if __name__ == "__main__":
    main()

