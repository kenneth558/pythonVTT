#!/usr/bin/env python3
"""
speech_to_text.py

- Multi-word key phrases do not get typed. Example:
    ("return","key") => press Enter, skipping "return" + "key"
- Any leftover words get typed into whichever OS window currently has focus
  at that moment. If the user changes focus mid-typing, subsequent keystrokes
  go to the new window.
- If DEBUG=True, recognized text is also printed to the console with no prefix.
- No-join approach => avoids multi-second shutdown delays.
- Reverse resource closure => stop STT => destroy Tk => sys.exit.

System-wide packages required: vosk, speech_recognition, pyaudio, pynput, etc.
"""

###############################################################################
# 1) Imports & SIGINT Handler
###############################################################################
import sys
import signal
import os
import threading

import tkinter as tk
from pynput.keyboard import Controller, Key

import speech_recognition as sr
import pyaudio
import vosk  # Not necessarily used, but installed system-wide

DEBUG = False  # If True, recognized text is also printed in the console

stop_listening = None  # Will be set once we start the background STT

def debug_print(msg):
    if DEBUG:
        print(f"DEBUG: {msg}")

def forcibly_exit():
    """
    Reverse-close:
      1) stop background STT (no thread join),
      2) destroy Tk window,
      3) sys.exit(0).
    """
    debug_print("forcibly_exit() => stopping STT, destroying window, then exiting.")
    if stop_listening is not None:
        debug_print("Stopping background STT (no-join approach)...")
        stop_listening()

    try:
        debug_print("Destroying Tkinter window...")
        help_root.destroy()
    except:
        pass

    debug_print("Exiting script now.")
    sys.exit(0)

def signal_handler(sig, frame):
    debug_print("Caught physical Ctrl+C => forcibly_exit.")
    forcibly_exit()

signal.signal(signal.SIGINT, signal_handler)

###############################################################################
# 2) Global Setup
###############################################################################
keyboard = Controller()
typed_words = []
recognizer = sr.Recognizer()

###############################################################################
# 3) Multi-Word Key Phrases, Single Word Keys, & Homophones
###############################################################################
# For multi-word key phrases, each tuple => a special key
PHRASE_KEY_MAP = {
    ("return", "key"): Key.enter,
    ("enter", "key"): Key.enter,
    ("escape", "key"): Key.esc,
    ("esc", "key"): Key.esc,
    ("up", "arrow"): Key.up,
    ("down", "arrow"): Key.down,
    ("left", "arrow"): Key.left,
    ("right", "arrow"): Key.right,
    # Add more as needed
}

LOCK_MAP = {
    "caps lock": Key.caps_lock,
    "num lock": Key.num_lock
}

homophone_fixes = {
    "there": ["their", "they're"],
    "to": ["too", "two"],
}

###############################################################################
# 4) Tk Help Window
###############################################################################
help_root = tk.Tk()
help_root.title("Dictation Help Window")
help_root.geometry("400x250")

help_label = tk.Label(
    help_root,
    text="""
=== Voice Dictation Help ===

Multi-word key phrases: "return key", "enter key", "up arrow", etc.
These tokens are NOT typed; they trigger special keys.

Leftover words are typed via pynput into the OS window in focus.
Switching windows mid-typing will direct subsequent keystrokes to the new window.

"control c" => forcibly kill script
""",
    justify="left"
)
help_label.pack(expand=True, fill="both", padx=10, pady=10)

def bring_help_window_front():
    help_root.lift()
    help_root.attributes("-topmost", True)
    help_root.attributes("-topmost", False)

help_root.withdraw()

###############################################################################
# 5) No-Join listen_in_background with Fresh Microphone
###############################################################################
def listen_in_background_no_join(recognizer, callback, phrase_time_limit=None):
    """
    Creates a background thread that repeatedly:
      with sr.Microphone() as source: audio = recognizer.listen(source)
    We skip thread.join => near-instant shutdown.
    """
    running = [True]

    def threaded_listen():
        while running[0]:
            try:
                with sr.Microphone() as source:
                    audio = recognizer.listen(source, phrase_time_limit=phrase_time_limit)
                if running[0]:
                    callback(recognizer, audio)
            except Exception as e:
                debug_print(f"Background listen caught exception: {e}")
                continue

    stt_thread = threading.Thread(target=threaded_listen, name="NoJoinSTT")
    stt_thread.daemon = True
    stt_thread.start()

    def stopper():
        debug_print("No-join stopper => set running=False, skip thread join")
        running[0] = False

    return stopper

def start_listening():
    global stop_listening
    debug_print("Starting background listener (fresh mic, no-join).")
    stop_listening = listen_in_background_no_join(recognizer, recognize_callback)
    debug_print("Background listener started. Running until Ctrl+C...")

###############################################################################
# 6) Typing & Mechanical Backspacing
###############################################################################
def type_word(word):
    """
    Types 'word' + trailing space into whichever window is in focus
    at the moment these keystrokes are sent.
    If the user changes focus mid-typing, subsequent chars go to the new window.
    """
    typed_words.append(word)
    for ch in word:
        keyboard.press(ch)
        keyboard.release(ch)
    keyboard.press(" ")
    keyboard.release(" ")

def press_key(k):
    keyboard.press(k)
    keyboard.release(k)

def backspace_word(w):
    n = len(w) + 1
    debug_print(f"Backspacing {n} chars for word '{w}'")
    for _ in range(n):
        press_key(Key.backspace)

###############################################################################
# 7) Fix Spelling & Homophone
###############################################################################
def fix_spelling_command(word):
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
    debug_print(f"Fix spelling => removing {to_remove}, then retyping {subsequent}")
    typed_words[:] = typed_words[:idx]

    for w in reversed(to_remove):
        backspace_word(w)
    for w in subsequent:
        type_word(w)

def homophone_replace_command(word):
    if word.lower() not in homophone_fixes or not homophone_fixes[word.lower()]:
        debug_print(f"No homophone known for '{word}'.")
        return

    replacements = homophone_fixes[word.lower()]
    new_word = replacements[0]

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

    typed_words[:] = typed_words[:idx]
    for w in reversed(to_remove):
        backspace_word(w)
    type_word(new_word)
    for w in subsequent:
        type_word(w)

###############################################################################
# 8) Multi-Word Phrase Checking
###############################################################################
def match_multi_word_key_phrase(tokens):
    """
    Check if tokens[:plen] match a known multi-word phrase => (key_obj, plen).
    If none matched => (None, 0).
    """
    for phrase_tokens, key_obj in PHRASE_KEY_MAP.items():
        plen = len(phrase_tokens)
        if tokens[:plen] == list(phrase_tokens):
            return (key_obj, plen)
    return (None, 0)

def request_exit_on_main_thread():
    debug_print("Scheduling forcibly_exit() from main Tk thread...")
    help_root.after(0, forcibly_exit)

###############################################################################
# 9) Main Parser
###############################################################################
def process_spoken_phrase(spoken_text):
    """
    If DEBUG=True => also prints recognized text to console (no prefix).
    Then parse multi-word phrases or single tokens => typed leftover words
    into whichever app is in focus.
    """
    if DEBUG:
        print(spoken_text)

    debug_print(f"process_spoken_phrase => '{spoken_text}'")

    text = spoken_text.lower().strip()

    # short commands
    if text == "dictation help":
        help_root.deiconify()
        bring_help_window_front()
        return

    # "control c" synonyms => typed Ctrl+C => forcibly exit
    ctrl_c_syns = ("control c", "control see", "ctrl c", "control sea")
    if text in ctrl_c_syns:
        debug_print("Voice => typed ctrl+c => request exit on main thread.")
        keyboard.press(Key.ctrl)
        keyboard.press('c')
        keyboard.release('c')
        keyboard.release(Key.ctrl)
        request_exit_on_main_thread()
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

    # lock keys => e.g. "caps lock"
    if text in LOCK_MAP:
        debug_print(f"Lock key => toggling {text}")
        press_key(LOCK_MAP[text])
        return

    # parse tokens => multi-word phrase or leftover typed
    tokens = text.split()
    i = 0
    while i < len(tokens):
        # multi-word phrase?
        key_obj, used = match_multi_word_key_phrase(tokens[i:])
        if key_obj is not None:
            debug_print(f"Matched multi-word => {tokens[i:i+used]} => press {key_obj}")
            press_key(key_obj)
            i += used
            continue

        single_token = tokens[i]
        # single word special key?
        # e.g. "escape", "up", "down", "backspace"
        # If recognized that way
        # but typically "escape" => we'll parse as "escape key" if multi-word
        # so this is fallback for single synonyms
        i += 1
        debug_print(f"Typing leftover => '{single_token}'")
        type_word(single_token)

def recognize_callback(recognizer_instance, audio_data):
    try:
        text = recognizer_instance.recognize_google(audio_data)
        debug_print(f"[Callback] Recognized text => {text}")
        process_spoken_phrase(text)
    except sr.UnknownValueError:
        debug_print("[Callback] Could not understand audio.")
    except sr.RequestError as e:
        debug_print(f"[Callback] Request error => {e}")

###############################################################################
# 10) main()
###############################################################################
def main():
    help_root.withdraw()

    def on_start():
        start_listening()

    help_root.after(200, on_start)
    help_root.mainloop()

if __name__ == "__main__":
    main()
