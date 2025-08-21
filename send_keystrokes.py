import time
import sys
import os
import fcntl
import re
import subprocess
import argparse
from textwrap import wrap

# Replace with your Firestick's IP
FIRESTICK_IP = "10.3.24.155"  # Change this to your Firestick's IP

# ADB connection function
def connect_adb():
    """Connect to Firestick via ADB."""
    result = subprocess.run(["adb", "connect", FIRESTICK_IP], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to connect to {FIRESTICK_IP}: {result.stderr}")
        return False
    return True

def send_adb_keyevent(keyevent):
    """Send an ADB keyevent to the Firestick."""
    try:
        subprocess.run(["adb", "shell", "input", "keyevent", str(keyevent)], check=True, capture_output=True, text=True)
        print(f"ADB keyevent {keyevent} sent successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error sending ADB keyevent {keyevent}: {e.stderr}")

# HID keycode map (USB HID usage IDs for US keyboard layout)
KEYCODES = {
    'A': 0x04, 'B': 0x05, 'C': 0x06, 'D': 0x07, 'E': 0x08, 'F': 0x09, 'G': 0x0A,
    'H': 0x0B, 'I': 0x0C, 'J': 0x0D, 'K': 0x0E, 'L': 0x0F, 'M': 0x10, 'N': 0x11,
    'O': 0x12, 'P': 0x13, 'Q': 0x14, 'R': 0x15, 'S': 0x16, 'T': 0x17, 'U': 0x18,
    'V': 0x19, 'W': 0x1A, 'X': 0x1B, 'Y': 0x1C, 'Z': 0x1D,
    '1': 0x1E, '2': 0x1F, '3': 0x20, '4': 0x21, '5': 0x22, '6': 0x23, '7': 0x24,
    '8': 0x25, '9': 0x26, '0': 0x27,
    ' ': 0x2C,  # Space
    '\n': 0x28,  # Enter
    '.': 0x37,  # Period
    ',': 0x36,  # Comma
    'UP': 0x52,  # Up arrow
    'DOWN': 0x51,  # Down arrow
    'LEFT': 0x50,  # Left arrow
    'RIGHT': 0x4F,  # Right arrow
    'ENTER': 0x28,  # Enter key
    'ESC': 0x29,  # Escape key
}

# Special commands
SPECIAL_COMMANDS = [
    'HOME', 'MENU', 'PLAYPAUSE', 'REWIND', 'FASTFORWARD', 'SLEEP', 'WAKEUP',
    'FIREVOLUP', 'FIREVOLDOWN', 'FIREMUTE', 'FIRESETTINGS', 'FIREREBOOT', 'RPIREBOOT',
    'PLEX', 'YOUTUBE', 'PRIME', 'NETFLIX', 'HULU', 'HBO', 'DISCOVERYPLUS', 'PARAMOUNTPLUS',
    'SLEEP=<seconds> (e.g., SLEEP=2 or SLEEP=0.5)'
]

# Modifiers
MOD_LEFT_SHIFT = 0x02

# HID report format: 8 bytes (modifier, reserved, key1-6)
NULL_REPORT = b'\x00\x00\x00\x00\x00\x00\x00\x00'

def set_nonblocking(fd):
    """Set file descriptor to non-blocking mode."""
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

def send_key(hid_fd, keycode, modifier=0x00):
    """Send a single HID key event."""
    delay = 0.02
    try:
        report = bytes([modifier, 0x00, keycode, 0x00, 0x00, 0x00, 0x00, 0x00])
        print(f"Sending report: {report.hex()}")
        hid_fd.write(report)
        hid_fd.flush()
        print("Report sent")
        time.sleep(delay)
        hid_fd.write(NULL_REPORT)
        hid_fd.flush()
        print("Release sent")
        time.sleep(delay)
        print("Key released")
        return True
    except (IOError, BlockingIOError) as e:
        print(f"Error writing to /dev/hidg0: {e}")
        return False

def type_string(hid_fd, text, delay=0):
    """Type a string using HID keycodes."""
    text = text.encode().decode('unicode_escape')  # Handle escape sequences
    for char in text:
        modifier = 0x00
        keycode = KEYCODES.get(char.upper() if char.isalpha() else char)
        if char.isupper() or char in '!@#$%^&*()':
            modifier = MOD_LEFT_SHIFT
            if char == '!': keycode = KEYCODES['1']
            elif char == '@': keycode = KEYCODES['2']
            elif char == '#': keycode = KEYCODES['3']
            elif char == '$': keycode = KEYCODES['4']
            elif char == '%': keycode = KEYCODES['5']
            elif char == '^': keycode = KEYCODES['6']
            elif char == '&': keycode = KEYCODES['7']
            elif char == '*': keycode = KEYCODES['8']
            elif char == '(': keycode = KEYCODES['9']
            elif char == ')': keycode = KEYCODES['0']
        if keycode is not None:
            print(f"Processing char: '{char}'")
            if not send_key(hid_fd, keycode, modifier):
                print(f"Failed to send key: '{char}'")
                break
            time.sleep(delay)
        else:
            print(f"Warning: No keycode for '{char}'")

def parse_commands(command_string):
    """Parse command string into a list, preserving quoted strings."""
    commands = []
    current = ''
    in_quotes = False
    i = 0
    while i < len(command_string):
        if command_string[i] == '"':
            in_quotes = not in_quotes
            if not in_quotes:
                commands.append(current)
                current = ''
            i += 1
        elif command_string[i] == ',' and not in_quotes:
            if current.strip():
                commands.append(current.strip())
            current = ''
            i += 1
        else:
            current += command_string[i]
            i += 1
    if current.strip():
        commands.append(current.strip())
    return commands

def print_commands():
    """Print the list of supported commands in a clean format."""
    print("Firestick Keystroke Sender - Supported Commands")
    print("=" * 45)
    print("\nKeycodes (case-insensitive):")
    
    navigation = sorted(k for k in KEYCODES if k in ['UP', 'DOWN', 'LEFT', 'RIGHT'])
    special_keys = sorted(k for k in KEYCODES if k in ['ENTER', 'ESC'])

    print("\n  Navigation:")
    print("    " + ", ".join(wrap(", ".join(navigation), width=70, subsequent_indent="    ")))
    print("\n  Special Keys:")
    print("    " + ", ".join(wrap(", ".join(special_keys), width=70, subsequent_indent="    ")))

    print("\nSpecial Commands:")
    for cmd in sorted(SPECIAL_COMMANDS, key=lambda x: x.lower()):
        print(f"  - {cmd}")
    
    print("\nAdditional Notes:")
    print("  - Quoted strings (e.g., \"Hello World\") are typed as text.")
    print("  - Use --delay <seconds> to add a delay between commands.")
    print("  - Example: python3 send_keystrokes.py UP,RIGHT,SLEEP=2,DOWN,'Test' --delay 0.1")

def main():
    """Main function to process commands."""
    parser = argparse.ArgumentParser(
        description="Send keystrokes to Firestick via ADB and HID.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "commands",
        nargs='?',
        default=None,
        help="Comma-separated commands (e.g., UP,RIGHT,SLEEP=2,DOWN,'Test')\n"
             "Use -commands to list all supported commands.\n"
             "Commands must be comma-separated or quoted if containing spaces."
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay between commands in seconds (e.g., 0.1)"
    )
    parser.add_argument(
        "-commands",
        action="store_true",
        dest="list_commands",
        help="List all supported commands"
    )
    args = parser.parse_args()

    # Check for -commands flag first
    if args.list_commands:
        print_commands()
        sys.exit(0)

    # Ensure commands are provided
    if not args.commands:
        print("Error: No commands provided.\n")
        print_commands()
        print("\nUsage: python3 send_keystrokes.py <commands> [--delay <seconds>]")
        sys.exit(1)

    commands = parse_commands(args.commands)
    print(f"Processing commands: {commands}")

    if not connect_adb():
        sys.exit(1)

    try:
        with open('/dev/hidg0', 'rb+', buffering=0) as hid_fd:
            set_nonblocking(hid_fd)
            for command in commands:
                # Check for SLEEP command
                sleep_match = re.match(r'SLEEP=(\d*\.?\d+)', command, re.IGNORECASE)
                if sleep_match:
                    try:
                        sleep_time = float(sleep_match.group(1))
                        print(f"Sleeping for {sleep_time} seconds")
                        time.sleep(sleep_time)
                    except ValueError:
                        print(f"Invalid sleep duration in '{command}'")
                    continue

                command_upper = command.upper()
                if command_upper == 'HOME':
                    send_adb_keyevent(3)
                elif command_upper == 'MENU':
                    send_adb_keyevent(82)
                elif command_upper == 'PLAYPAUSE':
                    send_adb_keyevent(85)
                elif command_upper == 'REWIND':
                    send_adb_keyevent(89)
                elif command_upper == 'FASTFORWARD':
                    send_adb_keyevent(90)
                elif command_upper == 'FIRESLEEP':
                    send_adb_keyevent(223)
                elif command_upper == 'FIREWAKEUP':
                    send_adb_keyevent(26)
                elif command_upper == 'FIREVOLUP':
                    send_adb_keyevent(24)
                elif command_upper == 'FIREVOLDOWN':
                    send_adb_keyevent(25)
                elif command_upper == 'FIREMUTE':
                    send_adb_keyevent(164)
                elif command_upper == 'FIRESETTINGS':
                    send_adb_keyevent(176)
                elif command_upper == 'FIREREBOOT':
                    subprocess.run(["adb", "reboot"], capture_output=True, text=True)
                elif command_upper == 'RPIREBOOT':
                    subprocess.run(["sudo", "reboot"], capture_output=True, text=True)
                elif command_upper == 'FIRESLEEP':
                    send_adb_keyevent(26)
                elif command_upper == 'FIREWAKE':
                    send_adb_keyevent(224)
                elif command_upper == 'PLEX':
                    subprocess.run(["adb", "shell", "am", "start", "-n", "com.plexapp.android/com.plexapp.plex.activities.SplashActivity"], capture_output=True, text=True)
                elif command_upper == 'YOUTUBE':
                    subprocess.run(["adb", "shell", "am", "start", "-n", "com.amazon.firetv.youtube/dev.cobalt.app.MainActivity"], capture_output=True, text=True)
                elif command_upper == 'PRIME':
                    subprocess.run(
                        [
                            "adb", "shell", "am", "start",
                             "-a", "com.amazon.firebat.action.YAC_LAUNCH",
                             "-n", "com.amazon.firebat/com.amazon.firebatcore.deeplink.DeepLinkRoutingActivity"
                        ],
                        capture_output=True,
                        text=True)           
                elif command_upper == 'NETFLIX':
                    subprocess.run(["adb", "shell", "am", "start", "-n", "com.netflix.ninja/.MainActivity"], capture_output=True, text=True)
                elif command_upper == 'HULU':
                    subprocess.run(["adb", "shell", "am", "start", "-n", "com.hulu.plus/.SplashActivity"], capture_output=True, text=True)
                elif command_upper == 'HBO':
                    subprocess.run(["adb", "shell", "am", "start", "-n", "com.hbo.hbonow/com.wbd.beam.BeamActivity"], capture_output=True, text=True)
                elif command_upper == 'DISCOVERYPLUS':
                    subprocess.run(["adb", "shell", "am", "start", "-n", "com.discovery.discoveryplus.firetv/com.wbd.beam.BeamActivity"], capture_output=True, text=True)
                elif command_upper == 'PARAMOUNTPLUS':
                    subprocess.run(["adb", "shell", "am", "start", "-n", "com.cbs.ott/com.paramount.android.pplus.features.splash.tv.SplashMediatorActivity"], capture_output=True, text=True)
                elif command_upper == 'APPLETV':
                    subprocess.run(["adb", "shell", "am", "start", "-n", "com.apple.atve.amazon.appletv/.MainActivity"], capture_output=True, text=True)
                
                
                elif command_upper == 'SOUNDBARON':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "27", "/home/jupiter/SITE/rpi_usb_firestick/ir/samsung_soundbar.json",
                             "Power"
                        ])
                elif command_upper == 'SOUNDBARVOLMUTE':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "27", "/home/jupiter/SITE/rpi_usb_firestick/ir/samsung_soundbar.json",
                             "Mute"
                        ])
                elif command_upper == 'SOUNDBARINPUT':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "27", "/home/jupiter/SITE/rpi_usb_firestick/ir/samsung_soundbar.json",
                             "Input"
                        ])
                elif command_upper == 'SOUNDBARSUBVOLUP':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "27", "/home/jupiter/SITE/rpi_usb_firestick/ir/samsung_soundbar.json",
                             "SubVolUp"
                        ])
                elif command_upper == 'SOUNDBARVOLUP':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "27", "/home/jupiter/SITE/rpi_usb_firestick/ir/samsung_soundbar.json",
                             "VolumeUp"
                        ])
                elif command_upper == 'SOUNDBARSUBVOLDOWN':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "27", "/home/jupiter/SITE/rpi_usb_firestick/ir/samsung_soundbar.json",
                             "SubVolDown"
                        ])
                elif command_upper == 'SOUNDBARVOLDOWN':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "27", "/home/jupiter/SITE/rpi_usb_firestick/ir/samsung_soundbar.json",
                             "VolumeDown"
                        ])
                    
                    
                elif command_upper == 'TVPOWER':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "17", "/home/jupiter/SITE/rpi_usb_firestick/ir/tlc_tv.json",
                             "Power"
                        ])
                elif command_upper == 'TVUP':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "17", "/home/jupiter/SITE/rpi_usb_firestick/ir/tlc_tv.json",
                             "Up"
                        ])
                elif command_upper == 'TVINPUT':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "17", "/home/jupiter/SITE/rpi_usb_firestick/ir/tlc_tv.json",
                             "Input"
                        ])
                elif command_upper == 'TVLEFT':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "17", "/home/jupiter/SITE/rpi_usb_firestick/ir/tlc_tv.json",
                             "Left"
                        ])
                    
                elif command_upper == 'TVSELECT':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "17", "/home/jupiter/SITE/rpi_usb_firestick/ir/tlc_tv.json",
                             "Select"
                        ])
                elif command_upper == 'TVRIGHT':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "17", "/home/jupiter/SITE/rpi_usb_firestick/ir/tlc_tv.json",
                             "Right"
                        ])
                elif command_upper == 'TVBACK':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "17", "/home/jupiter/SITE/rpi_usb_firestick/ir/tlc_tv.json",
                             "Back"
                        ])
                    
                elif command_upper == 'TVDOWN':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "17", "/home/jupiter/SITE/rpi_usb_firestick/ir/tlc_tv.json",
                             "Down"
                        ])
                elif command_upper == 'TVMENU':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "17", "/home/jupiter/SITE/rpi_usb_firestick/ir/tlc_tv.json",
                             "Home"
                        ])
                    
                elif command_upper == 'TVMUTE':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "17", "/home/jupiter/SITE/rpi_usb_firestick/ir/tlc_tv.json",
                             "Mute"
                        ])
                elif command_upper == 'TVVOLUP':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "17", "/home/jupiter/SITE/rpi_usb_firestick/ir/tlc_tv.json",
                             "VolumeUp"
                        ])
                elif command_upper == 'TVVOLDOWN':
                    subprocess.run(
                        [
                            "python3", "/home/jupiter/SITE/rpi_usb_firestick/ir/emitter.py", 
                            "17", "/home/jupiter/SITE/rpi_usb_firestick/ir/tlc_tv.json",
                             "VolumeDown"
                        ])
                    
                
                
                elif command_upper in KEYCODES:
                    keycode = KEYCODES[command_upper]
                    modifier = 0x00
                    print(f"Processing special key: '{command_upper}'")
                    if not send_key(hid_fd, keycode, modifier):
                        print(f"Failed to send special key: '{command_upper}'")
                else:
                    print(f"Typing string: '{command}'")
                    type_string(hid_fd, command, delay=args.delay)
                time.sleep(args.delay)  # Apply global delay between commands
    except Exception as e:
        print(f"Error opening /dev/hidg0: {e}")
        sys.exit(1)

if __name__ == "__main__":
    subprocess.run(["sudo", "pigpiod"], capture_output=True, text=True)
    main()
