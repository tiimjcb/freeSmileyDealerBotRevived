import discord
from discord import app_commands
from discord.app_commands import guilds
from dotenv import load_dotenv
import os
import logging
import re
from datetime import datetime, timedelta
import sqlite3

##################### LOGGER #####################

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
                    logging.info(f"\nDeleted old log file: {filename} \n")
            except ValueError:
                continue

logger = setup_logger()

##################### DISCORD BOT METHODS #####################

# get the token
load_dotenv("token.env")
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    logger.error("====================================\n"
                 "There is no token!!!\n"
                 "====================================")
    raise ValueError("There is no token!")

# basic bot configuration
intents = discord.Intents.all()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


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

    # connect to the database
    conn = sqlite3.connect('databases/bot.db')
    cursor = conn.cursor()

    # import the server settings for this guild
    cursor.execute("SELECT text_reactions_enabled FROM server_settings WHERE guild_id = ?", (guild_id,))
    text_reactions_enabled = cursor.fetchone()[0]


    # break the message into words
    words = [normalize_emoji(word) for word in re.findall(r'\w+|[^\w\s]', message.content)]
    smileys = []


    # first : scan for special triggers
    for word in words:
        word = word.lower()
        if text_reactions_enabled:
            cursor.execute("SELECT * FROM special_triggers WHERE word = ?", (word,))
        else:
            cursor.execute("SELECT * FROM special_triggers WHERE word = ? AND isEmoji = 1", (word,))
        result = cursor.fetchone()

        # smiley is in result[2]
        if result:
            logger.info(f"\n{user_name} in {guild_name} ({guild_id}) said the word {word}")
            logger.info(f"Special trigger word found - ID: {result[0]}, Trigger : {result[1]}, Response: {result[2]}, isEmoji : {result[3]}")
            smileys.append(result[2])
            return smileys # we return at the first special trigger found because they have priority

    # second : scan for regular triggers
    for word in words:
        word = word.lower()
        if text_reactions_enabled:
            cursor.execute("SELECT * FROM trigger_words WHERE word = ?", (word,))
        else:
            cursor.execute("SELECT * FROM trigger_words WHERE word = ? AND isEmoji = 1", (word,))
        result = cursor.fetchone()
        # smiley is in result[2]
        if result:
            logger.info(f"\n{user_name} in {guild_name} ({guild_id}) said the word {word}")
            logger.info(f"Trigger word found - ID: {result[0]}, Trigger : {result[1]}, Response: {result[2]}, isEmoji : {result[3]}")
            smileys.append(result[2])

    conn.close()
    return smileys if smileys else None





def add_guild_to_db(guild_id):
    """
    function that adds a guild to the server settings database
    """
    conn = sqlite3.connect('databases/bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()
    if not result:
        logger.info(f"\nAdding guild {guild_id} to the server settings database.")
        cursor.execute("INSERT INTO server_settings (guild_id) VALUES (?)", (guild_id,))
        conn.commit()
        logger.info(f"Guild {guild_id} added to the server settings database.")
        conn.close()



##################### DISCORD BOT EVENTS #####################

@bot.event
async def on_ready():
    ## create the server settings database if it don't exist
    conn = sqlite3.connect('databases/bot.db')
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS server_settings (
        guild_id TEXT PRIMARY KEY,
        text_reactions_enabled BOOLEAN DEFAULT 1
    )
    """)
    conn.commit()
    conn.close()

    ## adding to the database all the guilds the bot is in
    guild_list = bot.guilds
    for guild in guild_list:
        add_guild_to_db(guild.id)


    logger.info(f"\nBot started and connected as {bot.user} in {len(guild_list)} server!")
    activity = discord.Activity(type=discord.ActivityType.watching, name="free smiley faces !")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    try:
        await tree.sync()
        logger.info("Command tree synced globally!")
    except Exception as e:
        logger.error(f"Error syncing command tree: {e}")


@bot.event
async def on_guild_join(guild):
    logger.info(f"\nBot has joined a new guild: {guild.name} (ID: {guild.id})")
    add_guild_to_db(guild.id)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    smileys = process_message_for_smiley(message)
    if smileys:
        smiley_message = " ".join(smileys)
        await message.channel.send(smiley_message)


##################### DISCORD SLASH COMMANDS #####################

@tree.command(name="ping", description="A simple ping command")
async def ping(interaction):
    await interaction.response.send_message("Pong ! <a:soccer:1313938627104866394>")


@tree.command(name="help", description="A simple help command")
async def help_command(interaction):
    await interaction.response.send_message("hey there <:yellow:1313941466862587997> \n"
                                            "i'm a bot that reacts to specific words and paid smileys with free smileys. <:lore:1314281452204068966> \n\n"
                                            "**List of commands:** \n"
                                            "- /ping : a simple ping command \n"
                                            "- /help : this help message \n"
                                            "- /toggle_text_triggers : toggles on or off the text triggers (like 'hi')\n")


@tree.command(name="toggle_text_triggers", description="Toggles on or off the text triggers (like 'hi'")
async def toggle_text_triggers(interaction):

    # check if the user is an administrator
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command. Only administrators can toggle text triggers. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return


    guild_id = interaction.guild_id
    conn = sqlite3.connect('databases/bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()

    ## if the guild is not in the database, which is a huge problem, we add it
    if not result:
        cursor.execute("INSERT INTO server_settings (guild_id, text_reactions_enabled) VALUES (?, 1)", (guild_id,))
        conn.commit()
        await interaction.response.send_message("Text triggers enabled. <:yellow:1313941466862587997>")
    else:
        #normal behavior
        if result[1]:
            cursor.execute("UPDATE server_settings SET text_reactions_enabled = 0 WHERE guild_id = ?", (guild_id,))
            conn.commit()
            await interaction.response.send_message("Text triggers disabled. <a:bigCry:1313925251108835348>")
        else:
            cursor.execute("UPDATE server_settings SET text_reactions_enabled = 1 WHERE guild_id = ?", (guild_id,))
            conn.commit()
            await interaction.response.send_message("Text triggers enabled. <:yellow:1313941466862587997>")
        cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        logger.info(f"Text triggers settings modified for guild {guild_id}. Current status : {result[1]}")
    conn.close()

bot.run(TOKEN)
