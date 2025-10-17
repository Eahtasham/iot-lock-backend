import requests
import time

RENDER_URL = "https://iot-lock-api.onrender.com/lock"


def control_lock(value):
    """Simulate lock control"""
    if value == 1:
        print("🔓 UNLOCKING (simulated)")
    elif value == 0:
        print("🔒 LOCKING (simulated)")


def poll_server():
    """Check server every 2 seconds for new commands"""
    last_value = None

    print("⏳ Waiting for commands...")

    while True:
        try:
            response = requests.get(RENDER_URL, timeout=5)
            data = response.json()
            value = data.get('value')

            # Only act if value changed
            if value is not None and value != last_value:
                print(f"\n✅ NEW COMMAND RECEIVED: {value}")
                control_lock(value)
                last_value = value

                # Clear the value on server
                requests.post(f"{RENDER_URL}/clear")
            else:
                print(".", end="", flush=True)  # Show it's polling

        except Exception as e:
            print(f"\n❌ Error: {e}")

        time.sleep(2)  # Poll every 2 seconds


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🔌 Lock Controller Starting (TEST MODE)")
    print(f"📡 Polling: {RENDER_URL}")
    print("💡 Press Ctrl+C to stop")
    print("=" * 50 + "\n")

    try:
        poll_server()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")