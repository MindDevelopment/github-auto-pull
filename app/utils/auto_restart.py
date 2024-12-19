import os
import time
import logging

def monitor_script(main_function):
    while True:
        try:
            main_function()
        except Exception as e:
            logging.error(f"Script crashed: {e}")
            time.sleep(5)  # Wacht voordat je herstart
            logging.info("Herstarting script...")
