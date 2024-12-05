import discord
from discord import app_commands
from dotenv import load_dotenv
import os
import logging
import emoji
import re
from smiley_map import unicode_to_custom_smiley, text_to_custom_smiley
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



def process_message_for_smiley(message, emoji_map, text_map):
    """
    return the smileys of the emojis in a string that has an occurence in the dictionnary.
    if no emoji is in the string, or if none of the emojis in the string have an occurence, it returns None.
    """
    guild_id = message.guild.id if message.guild else "DM"
    guild_name = message.guild.name if message.guild else "DM"
    user_name = message.author.name

    smileys = []

    content = message.content
    current_index = 0

    # get the smileys and the words in the message in the order they appear
    while current_index < len(content):
        match = emoji.emoji_list(content[current_index:])

        if match and match[0]['match_start'] == 0:
            unicode_emoji = match[0]['emoji']
            normalized_emoji = normalize_emoji(unicode_emoji)

            if normalized_emoji in emoji_map:
                smileys.append(emoji_map[normalized_emoji])
                logger.info(
                    f"[GUILD : {guild_id} - {guild_name}] - [USER : {user_name}] - "
                    f"Emoji '{unicode_emoji}' detected (normalized to '{normalized_emoji}'). Matching smiley {emoji_map[normalized_emoji]} sent."
                )
            current_index += len(unicode_emoji)

        else:
            next_space = content.find(" ", current_index)
            if next_space == -1:
                next_space = len(content)
            word = content[current_index:next_space].lower()
            if word in text_map:
                smileys.append(text_map[word])
                logger.info(
                    f"[GUILD : {guild_id} - {guild_name}] - [USER : {user_name}] - "
                    f"Word '{word}' detected. Matching smiley {text_map[word]} sent."
                )
            current_index = next_space + 1

    if not smileys:
        logger.warning(
            f"[GUILD : {guild_id}] - [USER : {user_name}] - "
            f"Emoji(s) or words detected but none matched the database."
        )

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

    free_smileys = process_message_for_smiley(message, unicode_to_custom_smiley, text_to_custom_smiley)
    if free_smileys:
        smiley_message = " ".join(free_smileys)
        await message.channel.send(smiley_message)

bot.run(TOKEN)
