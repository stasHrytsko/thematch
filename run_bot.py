import subprocess
import time
import sys
import logging

logging.basicConfig(
    filename='bot_runner.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

def run_bot():
    while True:
        try:
            logging.info("Starting bot...")
            subprocess.run([sys.executable, 'bot.py'], check=True)
        except Exception as e:
            logging.error(f"Bot crashed with error: {e}")
            logging.info("Restarting in 60 seconds...")
            time.sleep(60)
        else:
            logging.info("Bot stopped normally")
            time.sleep(5)

if __name__ == '__main__':
    run_bot()