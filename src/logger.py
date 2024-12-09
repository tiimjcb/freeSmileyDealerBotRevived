import logging
import os
from datetime import datetime, timedelta
import colorlog

LOG_DIR = "../logs"
os.makedirs(LOG_DIR, exist_ok=True)

def cleanup_old_logs():
    """
    Clean up log files older than a week.
    """
    cutoff_date = datetime.now() - timedelta(days=7)
    for filename in os.listdir(LOG_DIR):
        if filename.startswith("log-") and filename.endswith(".log"):
            file_date_str = filename[4:-4]  # log-dd-mm-yyyy.log
            try:
                file_date = datetime.strptime(file_date_str, "%d-%m-%Y")
                if file_date < cutoff_date:
                    os.remove(os.path.join(LOG_DIR, filename))
            except ValueError:
                continue

cleanup_old_logs()

today = datetime.now().strftime("%d-%m-%Y")
log_filename = f"log-{today}.log"
log_filepath = os.path.join(LOG_DIR, log_filename)

# colors
log_colors = {
    'DEBUG': 'green',
    'INFO': 'blue',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}

# gray color for timestamp
formatter = colorlog.ColoredFormatter(
    "\033[90m%(asctime)s\033[0m [%(log_color)s\033[1m%(levelname)s\033[0m] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_colors=log_colors,
)

# file handler
file_handler = logging.FileHandler(log_filepath)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))

# log handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

logger = logging.getLogger("fsd_logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("Logger initialized.")



