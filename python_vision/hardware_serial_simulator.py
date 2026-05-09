from __future__ import annotations

import argparse
import math
import time


def open_serial(port: str, baud: int):
    try:
        import serial
    except ImportError as exc:
        raise SystemExit("Install pyserial first: pip install pyserial") from exc

    return serial.Serial(port=port, baudrate=baud, timeout=0.2)


def send_command(serial_port, pan: int, tilt: int, state: int, delay_s: float) -> None:
    command = f"{pan},{tilt},{state}\n"
    serial_port.write(command.encode("ascii"))
    serial_port.flush()

    response = serial_port.readline().decode("ascii", errors="replace").strip()
    if response:
        print(f"TX {command.strip()}  RX {response}")
    else:
        print(f"TX {command.strip()}")

    time.sleep(delay_s)


def center_test(serial_port, delay_s: float) -> None:
    print("Centering turret")
    send_command(serial_port, 90, 90, 0, delay_s)
    send_command(serial_port, 90, 90, 1, delay_s)
    send_command(serial_port, 90, 90, 2, delay_s)


def led_laser_test(serial_port, delay_s: float) -> None:
    print("Testing payload states")
    send_command(serial_port, 90, 90, 0, delay_s)
    send_command(serial_port, 90, 90, 1, 0.35)
    send_command(serial_port, 90, 90, 0, delay_s)
    send_command(serial_port, 90, 90, 2, delay_s)


def sweep_test(serial_port, delay_s: float) -> None:
    print("Testing pan sweep")
    for pan in range(60, 121, 5):
        send_command(serial_port, pan, 90, 0, delay_s)
    for pan in range(120, 59, -5):
        send_command(serial_port, pan, 90, 0, delay_s)

    print("Testing tilt sweep")
    for tilt in range(70, 111, 5):
        send_command(serial_port, 90, tilt, 0, delay_s)
    for tilt in range(110, 69, -5):
        send_command(serial_port, 90, tilt, 0, delay_s)


def fake_ai_lock_test(serial_port, delay_s: float) -> None:
    print("Simulating AI target lock")
    for step in range(80):
        pan = round(90 + 35 * math.sin(step / 8))
        tilt = round(90 + 18 * math.sin(step / 13))
        state = 1 if 15 <= step <= 55 else 0
        send_command(serial_port, pan, tilt, state, delay_s)

    send_command(serial_port, 90, 90, 2, delay_s)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automatically simulate AI serial commands for the ESP32 turret hardware."
    )
    parser.add_argument("--port", required=True, help="Serial port, for example COM3 or COM7.")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--delay", type=float, default=0.08, help="Delay between commands in seconds.")
    parser.add_argument(
        "--mode",
        choices=("all", "center", "payload", "sweep", "ai-lock"),
        default="all",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with open_serial(args.port, args.baud) as serial_port:
        time.sleep(2.0)
        serial_port.reset_input_buffer()

        if args.mode in ("all", "center"):
            center_test(serial_port, args.delay)
        if args.mode in ("all", "payload"):
            led_laser_test(serial_port, args.delay)
        if args.mode in ("all", "sweep"):
            sweep_test(serial_port, args.delay)
        if args.mode in ("all", "ai-lock"):
            fake_ai_lock_test(serial_port, args.delay)

        send_command(serial_port, 90, 90, 2, args.delay)
        print("Done. Turret centered and payload disabled.")


if __name__ == "__main__":
    main()
