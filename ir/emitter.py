import pigpio
import time
import json
import sys

# Settings
CARRIER_FREQ = 38.0  # kHz, common for NEC; adjust if needed

def load_timings(json_file, button_name):
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        if button_name not in data["buttons"]:
            print(f"Error: Button '{button_name}' not found in {json_file}")
            return None
        return data["buttons"][button_name]
    except FileNotFoundError:
        print(f"Error: File {json_file} not found")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {json_file}")
        return None
    except Exception as e:
        print(f"Error loading timings: {e}")
        return None

def send_ir_signal(timings, tx_pin):
    pi = pigpio.pi()
    if not pi.connected:
        print("Failed to connect to pigpiod. Ensure 'sudo pigpiod' is running.")
        return False

    print("Connected to pigpiod successfully.")

    pi.set_mode(tx_pin, pigpio.OUTPUT)
    pi.wave_clear()

    wf = []
    cycle_us = 1000.0 / CARRIER_FREQ
    on_us = int(round(cycle_us / 2.0))  # 50% duty cycle
    off_us = int(round(cycle_us - on_us))

    for i, duration in enumerate(timings):
        if i % 2 == 0:  # Mark: generate carrier bursts
            cycles = int(round(duration / cycle_us))
            for _ in range(cycles):
                wf.append(pigpio.pulse(1 << tx_pin, 0, on_us))  # High
                wf.append(pigpio.pulse(0, 1 << tx_pin, off_us))  # Low
        else:  # Space: off (no change)
            wf.append(pigpio.pulse(0, 0, duration))

    print(f"Waveform built with {len(wf)} pulses.")

    pi.wave_add_generic(wf)
    wid = pi.wave_create()

    if wid >= 0:
        print(f"Wave created successfully (ID: {wid}). Sending...")
        pi.wave_send_once(wid)
        while pi.wave_tx_busy():
            time.sleep(0.1)
        print("Transmission complete.")
        pi.wave_delete(wid)
        pi.stop()
        return True
    else:
        print(f"Failed to create wave: error code {wid}. (Common causes: too many pulses or pigpiod resource issue. Try rebooting or reducing timings.)")
        pi.stop()
        return False

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 emitter.py <gpio_#> <json_file> <button_name>")
        return

    try:
        tx_pin = int(sys.argv[1])  # Get GPIO pin from command line
        if tx_pin < 0 or tx_pin > 31:  # Basic validation for Raspberry Pi GPIO
            print("Error: GPIO pin must be between 0 and 31")
            return
    except ValueError:
        print("Error: GPIO pin must be a valid integer")
        return

    json_file = sys.argv[2]
    button_name = sys.argv[3]

    timings = load_timings(json_file, button_name)
    if timings:
        success = send_ir_signal(timings, tx_pin)
        if not success:
            print("Failed to send IR signal.")
    else:
        print("Failed to load timings. No signal sent.")

if __name__ == "__main__":
    main()