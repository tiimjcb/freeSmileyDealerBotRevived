import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
import emoji
import re
from smiley_map import unicode_to_custom_smiley
from datetime import datetime, timedelta

# log directory
LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger():
    # get today's date
    today = datetime.now().strftime("%d-%m-%Y")
    log_filename = f"log-{today}.log"
    log_filepath = os.path.join(LOG_DIR, log_filename)

    # clean up old log files
    cleanup_old_logs()

    # setting up the logger
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
    logging.getLogger().addHandler(console)
    logging.info("Logger initialized.")
    return logging.getLogger()


def cleanup_old_logs():
    """
    function that clean up log files older than a week
    """
    cutoff_date = datetime.now() - timedelta(days=7)
    for filename in os.listdir(LOG_DIR):
        if filename.startswith("log-") and filename.endswith(".log"):
            file_date_str = filename[4:-4]  # log-dd-mm-yyyy.log
            try:
                file_date = datetime.strptime(file_date_str, "%d-%m-%Y")
                if file_date < cutoff_date:
                    os.remove(os.path.join(LOG_DIR, filename))
                    logging.info(f"Deleted old log file: {filename}")
            except ValueError:
                continue

logger = setup_logger()


def normalize_emoji(emoji):
    """
    function that normalizes an emoji by removing skin tone modifiers.
    """
    skin_tone_modifiers = re.compile(r'[\U0001F3FB-\U0001F3FF]')
    return skin_tone_modifiers.sub('', emoji)


def process_message_for_smiley(message, emoji_map):
    """
     return the smileys of the emojis in a string that has an occurence in the dictionnary.
     if no emoji is in the string, or if none of the emojis in the string have an occurence, it returns None.
     """
    guild_id = message.guild.id if message.guild else "DM"
    user_name = message.author.name

    emojis_found = emoji.emoji_list(message.content)

    if not emojis_found:
        return None

    smileys = []
    for emoji_entry in emojis_found:
        unicode_emoji = emoji_entry['emoji']
        normalized_emoji = normalize_emoji(unicode_emoji)

        if normalized_emoji in emoji_map:
            logger.info(
                f"[GUILD : {guild_id}] - [USER : {user_name}] - "
                f"Emoji '{unicode_emoji}' detected (normalized to '{normalized_emoji}'). Matching smiley sent."
            )
            smileys.append(emoji_map[normalized_emoji])

    if not smileys:
        logger.warning(
            f"[GUILD : {guild_id}] - [USER : {user_name}] - "
            f"Emoji(s) detected but none matched the database."
        )

    return smileys if smileys else None



# get the token
load_dotenv("token.env")
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("There is no token!")



# basic bot configuration
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix=">", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot loaded and connected as {bot.user} !")
    logger.info("Bot started!")


# main program
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    free_smileys = process_message_for_smiley(message, unicode_to_custom_smiley)
    if free_smileys:
        smiley_message = " ".join(free_smileys)
        await message.channel.send(smiley_message)



bot.run(TOKEN)
