import sqlite3
import discord
from discord import app_commands
from dotenv import load_dotenv
import os
from logger import logger
from src.utils import is_friday_hour
from utils import add_guild_to_db, process_message_for_smiley
from discord.ext import tasks
import random

##################### VARIABLES #####################

friday_messages = [
    "its fridey yoohoo <:partying_face:1313934941658021888>",
    "lest go is friday <:yellow:1313941466862587997>",
    "friday friday friday <a:crazy_laugh:1313932126026203216>",
    "todey is fridnay <:lore:1314281452204068966>",
    "hey everione its friday <a:wink2:1313941408738050098>",
    "sorry was sleping thought it was thursday <:bigCry:1313925251108835348>, but its friday yahoo <:smirk:1313938566484852839>",
    "FRIDAY <a:stuck_out_tongue:1313938771804422285>",
    "yall know its friday right??????? <:redAngry:1313876421227057193>",
    "are yo guys talking enough about fridey???? <:weary:1313940711627948164>",
    "is it friday? <:hushed_1:1313930520702226482>",
    "bruh friday is lit <:hot_face:1313930434761068574>",
    "what should we eat?? FRIES, BECAUSE ITS FRIES DAY <:fries_1:1313929014599225405>",
    "fish <:fish:1313927965519773818>",
    "i am the fridnay king <:king:1313883436129194064>",
    "IM NOT SURE YOU ALL KNOW THAT ITS FRIDAY <:tv:1313884206149144628>",
    "attention guys, it's fridya !! <:exclamation_1:1313927841322373261>"
]



##################### DISCORD BOT CONFIGURATION #####################

# get the token
load_dotenv("../token.env")
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
    conn = sqlite3.connect('../databases/bot.db')
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



##################### TIME BASED EVENTS #####################

@tasks.loop(minutes=1)
async def friday_message():
    if is_friday_hour():
        # grab the right guild and channel (the best server)
        guild_id = 1231115041432928326
        channel_id = 1231369439879102496

        guild = bot.get_guild(guild_id)
        if guild:
            channel = guild.get_channel(channel_id)
            if channel:
                random_message = random.choice(friday_messages)
                await channel.send(random_message)
                await channel.send("<a:friday_1:1313928983578017843>")
            else:
                logger.warning(f"Channel with ID {channel_id} not found in guild {guild_id}. Can't send the hourly friday message.")
        else:
            logger.warning(f"Guild with ID {guild_id} not found. Can't send the hourly friday message.")







##################### DISCORD BOT EVENTS #####################

@bot.event
async def on_ready():
    ## create the server settings database if it don't exist
    conn = sqlite3.connect('../databases/bot.db')
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

    friday_message.start()

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


bot.run(TOKEN)