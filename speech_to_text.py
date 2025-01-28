#!/usr/bin/env python3
# File: speech_to_text.py

import speech_recognition as sr
import tkinter as tk
import time
import sys

from pynput.keyboard import Controller, Key

DEBUG = True

###############################################################################
# 1) Global Setup
###############################################################################

# We'll have a minimal help window using Tkinter. 
# The recognized text is typed into ANY app using pynput keystrokes.

keyboard = Controller()   # For typing into whichever app has focus

# We'll store every "word" we typed in a list so we can do mechanical fix/homophone
typed_words = []

# Setup indefinite STT
recognizer = sr.Recognizer()
microphone = sr.Microphone()
stop_listening = None

###############################################################################
# 2) Lock & Arrow synonyms, main keys
###############################################################################

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
    "f12": Key.f12
}

# Minimal letter map if you want a "spelling mode" approach, but we won't do it here now.
# (If you did advanced spelling, you'd do mechanical backspace approach.)
# We'll do simpler logic for "fix spelling <word>" => mechanical approach.

# For homophones
homophone_fixes = {
    "there": ["their", "they're"],
    "to": ["too","two"],
    # Add more
}

###############################################################################
# 3) Minimal Help Window with Tk (Move/Resize from OS)
###############################################################################

def debug_print(msg):
    if DEBUG:
        print(f"DEBUG: {msg}")

help_root = tk.Tk()
help_root.title("Dictation Help Window")
help_root.geometry("400x200")

# We'll place a label in it
help_label = tk.Label(help_root, text="""
=== Voice Dictation Help ===

Commands:
  fix spelling <word>
  homophone replace <word>
  left arrow / right arrow / etc.
  caps lock / num lock

All recognized text is typed as keystrokes
into whichever app has focus.

Speak "dictation help" to bring this
window to the front (without stealing focus).
""", justify="left")
help_label.pack(expand=True, fill="both", padx=10, pady=10)

# Make it resizable from edges, normal OS decoration
# We'll do no special focus logic, so user can move/resize from title bar.
# But we don't forcibly focus it on show.

def bring_help_window_front():
    help_root.lift()
    # optional trick:
    help_root.attributes("-topmost", True)
    help_root.attributes("-topmost", False)

# We'll hide the main help window from grabbing focus forcibly
# by removing focus force calls. The user can still click it though.

help_root.withdraw()  # Start hidden

###############################################################################
# 4) Indefinite Listening
###############################################################################

def start_listening():
    global stop_listening
    with microphone as source:
        debug_print("Adjusting for ambient noise, please wait...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
    debug_print("Starting background listener...")

    stop_listening = recognizer.listen_in_background(microphone, recognize_callback)
    debug_print("Background listener started. Running until Ctrl+C...")

###############################################################################
# 5) Mechanical Typing & Word Storage
###############################################################################

def type_word(word):
    """
    Type a single word + trailing space, store in typed_words
    """
    typed_words.append(word)
    # Use pynput to type the word + space
    for ch in word:
        keyboard.press(ch)
        keyboard.release(ch)
    keyboard.press(" ")
    keyboard.release(" ")

def type_phrase(phrase):
    """
    Type multiple words in one recognized phrase
    """
    words = phrase.split()
    for w in words:
        type_word(w)

def press_key(k):
    """
    Press+release a special key
    """
    keyboard.press(k)
    keyboard.release(k)

###############################################################################
# 6) Commands: fix spelling & homophone
###############################################################################

def fix_spelling_command(word):
    """
    Remove last occurrence of <word> in typed_words using mechanical approach:
      1) Move cursor left enough to reach that word
      2) backspace it + space
      3) move cursor right again if needed to restore subsequent words
    This is quite tricky if there's a big buffer. We'll do a simpler approach:
       - We find the last occurrence in typed_words
       - We'll backspace everything from that word onward, then retype subsequent
    """
    idx = -1
    for i in reversed(range(len(typed_words))):
        if typed_words[i].lower() == word.lower():
            idx = i
            break
    if idx == -1:
        debug_print(f"No occurrence of '{word}' in typed_words.")
        return

    # subsequent
    subsequent = typed_words[idx+1:]
    # We'll mechanical backspace everything from that word + subsequent
    to_remove = typed_words[idx:]  # everything from 'word' onward
    debug_print(f"Fix spelling => removing {to_remove}, then retyping {subsequent}")

    # remove them from typed_words
    typed_words[:] = typed_words[:idx]

    # mechanical approach: for each word in 'to_remove', backspace that many chars + 1 space
    for w in reversed(to_remove):
        backspace_word(w)

    # retype subsequent
    for w in subsequent:
        type_word(w)

def homophone_replace_command(word):
    """
    'homophone replace <word>' => find known homophones, pick the first,
    remove last occurrence of <word> and retype the new homophone, plus subsequent
    """
    if word.lower() not in homophone_fixes or not homophone_fixes[word.lower()]:
        debug_print(f"No homophone known for '{word}'.")
        return
    replacements = homophone_fixes[word.lower()]
    new_word = replacements[0]  # pick first

    idx = -1
    for i in reversed(range(len(typed_words))):
        if typed_words[i].lower() == word.lower():
            idx = i
            break
    if idx == -1:
        debug_print(f"No occurrence of '{word}' in typed_words.")
        return

    subsequent = typed_words[idx+1:]
    to_remove = typed_words[idx:]
    debug_print(f"Homophone => replace last '{word}' with '{new_word}'")

    # remove from typed_words
    typed_words[:] = typed_words[:idx]
    # mechanical backspace for old words
    for w in reversed(to_remove):
        backspace_word(w)

    # type the new homophone
    type_word(new_word)

    # retype subsequent
    for w in subsequent:
        type_word(w)

def backspace_word(w):
    """
    For each char + 1 space => press backspace
    """
    n = len(w) + 1  # +1 for space
    debug_print(f"Backspacing {n} chars for word '{w}'")
    for _ in range(n):
        press_key(Key.backspace)

###############################################################################
# 7) Main Parser
###############################################################################

def process_spoken_phrase(spoken_text):
    text = spoken_text.lower().strip()
    debug_print(f"process_spoken_phrase => '{text}'")

    # 'dictation help' => bring help window front
    if text == "dictation help":
        help_root.deiconify()
        bring_help_window_front()
        return

    if text.startswith("fix spelling "):
        tokens = text.split()
        if len(tokens) >= 3:
            word_to_fix = tokens[2]
            fix_spelling_command(word_to_fix)
        return

    if text.startswith("homophone replace "):
        tokens = text.split()
        if len(tokens) >= 3:
            wh = tokens[2]
            homophone_replace_command(wh)
        return

    # lock keys
    if text in LOCK_MAP:
        debug_print(f"Lock key => toggling {text}")
        # mechanical approach to toggle lock if you want
        press_key(LOCK_MAP[text])
        return

    # arrow synonyms
    if text in ARROW_SYNONYMS:
        text = ARROW_SYNONYMS[text]
        debug_print(f"Synonym matched => {text}")

    # parse tokens
    tokens = text.split()
    if not tokens:
        return

    # check if first token in MAIN_KEY_MAP
    first = tokens[0]
    if first in MAIN_KEY_MAP:
        debug_print(f"Press special => {MAIN_KEY_MAP[first]}")
        press_key(MAIN_KEY_MAP[first])
        # if multiple tokens after first, type them
        leftover = tokens[1:]
        for w in leftover:
            type_word(w)
        return

    # else type entire phrase
    type_phrase(text)


###############################################################################
# 8) Main Execution
###############################################################################

def main():
    help_root.withdraw()  # initially hide help window

    def on_start():
        start_listening()

    help_root.after(200, on_start)
    help_root.mainloop()

if __name__ == "__main__":
    main()
