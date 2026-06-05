import time

def spin_whell():
    spinner = r"|/-\|"
    while True:
        for char in spinner:
            print(f"\r{char}", end='', flush=True)
            time.sleep(0.1)

try:
    spin_whell()
except KeyboardInterrupt:
    print("spinning wheel stop")