import logging
import os
from dotenv import load_dotenv

load_dotenv()

log_file = os.getenv('LOG_FILE', 'bot.log')

logging.basicConfig(
    filename=log_file,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)
