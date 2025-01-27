# My first git-synchronized project

ChatGPT coded script I intend to build up to a voice-to-text (VTT) keyboard near-substitute. ChatGPT chose python as the best language to use, but why not demand a c++ version in the future? We'll see...

Whichever window has the focus receives the keystrokes or text that get generated.

General rules:

-key phrases produce keystroke actions; to wit, spoken "backspace key" sends a backspace keystroke, "bang key" sends a "#", "period key" sends a ".", "right arrow" sends a right arrow keystroke, etc.

-Modifier keys are locking as in Num lock and Caps lock, and non-locking/momentary as in shift, alt, and control. The locking modifier keys are toggled up or down by speaking their names and modify all (within reason) keystrokes while down. The non-locking modifier keys only modify a single subsequent key.

Since this script uses vosk, run it from inside a vosk environment. When you do launch this you might want to send stderr to /dev/null

Since this script uses vosk, run it from inside a vosk environment:

python3 -m venv vosk_env

source vosk_env/bin/activate

When you do launch this you might want to send stderr to /dev/null

My computer is a desktop that can run a GPU board, so I do plan on making this GPU-aware once I get the GPU. I run Linux Mint with dual-boot into Windows 10 free version for some rare HikVision camera maintenance. I have 2 TB of SSD and like 48 GB or more of RAM, maybe lots more RAM than that, actually. My CPU is AMD Ryzen 9 9950X. Sorry, but if this runs fast enough on my speedy box, I don't concern myself with making it any faster because of the headaches of writing the code.
