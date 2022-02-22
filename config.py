import os

from dotenv.main import load_dotenv

load_dotenv()

# Discord config
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
BOT_PREFIX = os.getenv("TOKEN")

#Default keywords to use in our keywords collection
sad_words = ["sad", "depressed", "unhappy", "angry", "miserable", "depressing"]
filter_words = []
encouragements = ["Cheer up!", "Hang in there.", "Don't give up!", "You're amazing!"]