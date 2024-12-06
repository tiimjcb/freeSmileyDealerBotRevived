import discord
from discord import app_commands
from dotenv import load_dotenv
import os
import logging
import re
from datetime import datetime, timedelta
import sqlite3

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



def process_message_for_smiley(message):
    """
    return the smileys of the emojis in a string that has an occurence in the database.
    if no emoji is in the string, or if none of the emojis in the string have an occurence, it returns None.
    """
    guild_id = message.guild.id if message.guild else "DM"
    guild_name = message.guild.name if message.guild else "DM"
    user_name = message.author.name

    # break the message into words
    words = [normalize_emoji(word) for word in message.content.split()]
    smileys = []

    # connect to the database
    conn = sqlite3.connect('databases/bot.db')
    cursor = conn.cursor()

    # first : scan for special triggers
    for word in words:
        cursor.execute("SELECT * FROM special_triggers WHERE word = ?", (word,))
        result = cursor.fetchone()
        # smiley is in result[2]
        if result:
            logger.info(f"{user_name} in {guild_name} ({guild_id}) said the word {word}")
            logger.info(f"Special trigger word found - ID: {result[0]}, Trigger : {result[1]}, Response: {result[2]}, isEmoji : {result[3]}")
            smileys.append(result[2])
            return smileys # we return at the first special trigger found because they have priority

    # second : scan for regular triggers
    for word in words:
        cursor.execute("SELECT * FROM trigger_words WHERE word = ?", (word,))
        result = cursor.fetchone()
        # smiley is in result[2]
        if result:
            logger.info(f"{user_name} in {guild_name} ({guild_id}) said the word {word}")
            logger.info(f"Trigger word found - ID: {result[0]}, Trigger : {result[1]}, Response: {result[2]}, isEmoji : {result[3]}")
            smileys.append(result[2])

    conn.close()
    return smileys if smileys else None






# get the token
load_dotenv("token.env")
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    logger.error("There is no token!")
    raise ValueError("There is no token!")


# basic bot configuration
intents = discord.Intents.all()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

@bot.event
async def on_ready():
    print(f"Bot loaded and connected as {bot.user} !")
    logger.info("Bot started!")
    activity = discord.Activity(type=discord.ActivityType.watching, name="free smiley faces !")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    try:
        await tree.sync()
        print("Command tree synced globally!")
        logger.info("Command tree synced globally!")
    except Exception as e:
        print(f"Error syncing command tree: {e}")
        logger.error(f"Error syncing command tree: {e}")


# slash commands
@tree.command(name="ping", description="A simple ping command")
async def ping(interaction):
    await interaction.response.send_message("Pong !")

@tree.command(name="help", description="A simple help command")
async def help_command(interaction):
    await interaction.response.send_message("Never use paid smileys. <:happyFaceSecondary:1313929340974530692>")

# main program
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    smileys = process_message_for_smiley(message)
    if smileys:
        smiley_message = " ".join(smileys)
        await message.channel.send(smiley_message)


bot.run(TOKEN)
