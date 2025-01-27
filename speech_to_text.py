#!/usr/bin/env python3
# File: speech_to_text.py

import speech_recognition as sr
from pynput.keyboard import Controller, Key, Listener
import time
import threading
import sys

DEBUG = False

###############################################################################
# 1) Dictionaries & Maps
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

# Symbol Keys & synonyms: 
# "bang key" => '!', "exclamation point key" => '!', etc.
# "at key" => '@', "hash key" => '#', etc.
# Also keep previously added "equal key", "period key", "question mark key"...
MAIN_KEY_MAP = {
    # Existing from your stable base:
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

    "f1": Key.f1,
    "f2": Key.f2,
    "f3": Key.f3,
    "f4": Key.f4,
    "f5": Key.f5,
    "f6": Key.f6,
    "f7": Key.f7,
    "f8": Key.f8,
    "f9": Key.f9,
    "f10": Key.f10,
    "f11": Key.f11,
    "f12": Key.f12,

    # Existing special keys from previous step
    "equal key": "typed_equal",
    "period key": "typed_period",
    "caps lock key": Key.caps_lock,
    "question mark key": "typed_question",
    "question key": "typed_question",

    # New symbol keys
    "bang key": "typed_exclamation",
    "exclamation point key": "typed_exclamation",
    "exclamation mark key": "typed_exclamation",
    "at key": "typed_at",
    "hash key": "typed_hash",
    "dollar key": "typed_dollar",
    "percent key": "typed_percent",
    "caret key": "typed_caret",
    "ampersand key": "typed_ampersand",
    "star key": "typed_star",
    "left paren key": "typed_left_paren",
    "right paren key": "typed_right_paren",
    "plus key": "typed_plus",
    "underline key": "typed_underscore",
    "minus key": "typed_minus",
}

CUSTOM_ACTIONS = {
    "delete line": "delete_line_action"
}

###############################################################################
# 2) Helper Functions
###############################################################################

keyboard = Controller()

def debug_print(msg):
    """Print debug messages only if DEBUG is True."""
    if DEBUG:
        print(f"DEBUG: {msg}")

def press_and_release(key_obj):
    """Press and release a single key."""
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
    """Release known modifiers: shift, ctrl, alt."""
    debug_print("Releasing all modifiers (Shift, Ctrl, Alt).")
    for mod_key in [Key.shift, Key.ctrl, Key.alt]:
        keyboard.release(mod_key)

###############################################################################
# 3) Parsing & Processing Logic
###############################################################################

def parse_tokens_for_modifiers_and_main(tokens):
    """
    Gather recognized modifiers at start,
    then treat the next token as the main key.
    If the next token after the main key is 'key', skip it.
    """
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
            # If user said "shift a key", skip "key"
            if idx < len(tokens) and tokens[idx] == "key":
                idx += 1
            break

    return modifiers, main_key, idx

def process_spoken_phrase(spoken_text):
    """
    - Check if phrase is a custom action
    - Check if it's a lock key
    - Handle arrow synonyms
    - Parse for modifiers + main key
    - If main key is a special typed symbol, do so
    - Fallback: type speech verbatim
    """
    text = spoken_text.lower().strip()
    debug_print(f"process_spoken_phrase received: '{text}'")

    # 1) custom actions
    if text in CUSTOM_ACTIONS:
        action_val = CUSTOM_ACTIONS[text]
        if action_val == "delete_line_action":
            delete_line_action()
        return

    # 2) lock keys
    if text in LOCK_MAP:
        debug_print(f"Lock key => {text}")
        press_and_release(LOCK_MAP[text])
        return

    # 3) arrow synonyms
    if text in ARROW_SYNONYMS:
        text = ARROW_SYNONYMS[text]
        debug_print(f"Synonym matched => unified to '{text}'")

    tokens = text.split()
    if not tokens:
        return

    modifiers, main_key, idx = parse_tokens_for_modifiers_and_main(tokens)

    # fallback if no main_key but we have modifiers
    if not main_key and modifiers:
        main_key = tokens[-1]

    # hold modifiers
    for m in modifiers:
        debug_print(f"Holding modifier: {m}")
        keyboard.press(m)

    # check main key
    if main_key in MAIN_KEY_MAP:
        mapped = MAIN_KEY_MAP[main_key]
        if mapped == "typed_equal":
            debug_print("Typing '=' for 'equal key'")
            keyboard.type("=")
        elif mapped == "typed_period":
            debug_print("Typing '.' for 'period key'")
            keyboard.type(".")
        elif mapped == "typed_question":
            debug_print("Typing '?' for 'question mark key' or 'question key'")
            keyboard.type("?")
        elif mapped == "typed_exclamation":
            debug_print("Typing '!' for 'bang key' or 'exclamation key'")
            keyboard.type("!")
        elif mapped == "typed_at":
            debug_print("Typing '@' for 'at key'")
            keyboard.type("@")
        elif mapped == "typed_hash":
            debug_print("Typing '#' for 'hash key'")
            keyboard.type("#")
        elif mapped == "typed_dollar":
            debug_print("Typing '$' for 'dollar key'")
            keyboard.type("$")
        elif mapped == "typed_percent":
            debug_print("Typing '%' for 'percent key'")
            keyboard.type("%")
        elif mapped == "typed_caret":
            debug_print("Typing '^' for 'caret key'")
            keyboard.type("^")
        elif mapped == "typed_ampersand":
            debug_print("Typing '&' for 'ampersand key'")
            keyboard.type("&")
        elif mapped == "typed_star":
            debug_print("Typing '*' for 'star key'")
            keyboard.type("*")
        elif mapped == "typed_left_paren":
            debug_print("Typing '(' for 'left paren key'")
            keyboard.type("(")
        elif mapped == "typed_right_paren":
            debug_print("Typing ')' for 'right paren key'")
            keyboard.type(")")
        elif mapped == "typed_plus":
            debug_print("Typing '+' for 'plus key'")
            keyboard.type("+")
        elif mapped == "typed_underscore":
            debug_print("Typing '_' for 'underline key'")
            keyboard.type("_")
        elif mapped == "typed_minus":
            debug_print("Typing '-' for 'minus key'")
            keyboard.type("-")

        elif isinstance(mapped, Key):
            debug_print(f"Recognized special key => {main_key}")
            # Possibly caps lock key or a standard Key.* 
            press_and_release(mapped)
        else:
            debug_print(f"Unknown mapped => {mapped}")

        # release modifiers
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
    listener = Listener(on_press=on_press, on_release=on_release)
    listener.start()
    return listener

###############################################################################
# 5) Background Listening for Speech
###############################################################################

recognizer = sr.Recognizer()
microphone = sr.Microphone()
stop_listening = None

def recognize_callback(recognizer_instance, audio_data):
    try:
        text = recognizer_instance.recognize_google(audio_data)
        debug_print(f"[Callback] Recognized text => {text}")
        process_spoken_phrase(text)
    except sr.UnknownValueError:
        debug_print("[Callback] Could not understand audio.")
    except sr.RequestError as e:
        debug_print(f"[Callback] Request error => {e}")

def main():
    global stop_listening

    # Start physical key listener
    start_physical_key_listener()

    with microphone as source:
        debug_print("Adjusting for ambient noise, please wait...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
        debug_print("Starting background listener...")

    # Listen in background indefinitely
    stop_listening = recognizer.listen_in_background(microphone, recognize_callback)
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

