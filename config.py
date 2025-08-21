import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPERADMIN_IDS = [int(i) for i in os.getenv("SUPERADMIN_IDS", "1062838548").split(",")]