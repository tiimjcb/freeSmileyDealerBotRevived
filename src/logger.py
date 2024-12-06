import logging
import os
from datetime import datetime, timedelta

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

# Ensure cleanup is performed
cleanup_old_logs()

today = datetime.now().strftime("%d-%m-%Y")
log_filename = f"log-{today}.log"
log_filepath = os.path.join(LOG_DIR, log_filename)

logging.basicConfig(
    filename=log_filepath,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console.setFormatter(formatter)
logger = logging.getLogger("fsd_logger")
logger.addHandler(console)

logger.info("Logger initialized.")