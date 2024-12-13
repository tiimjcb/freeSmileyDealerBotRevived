import discord
from discord import app_commands
from dotenv import load_dotenv
from utils import *
from discord.ext import tasks
import random
import sys
import subprocess


##################### VARIABLES #####################

# list of messages to send on friday
friday_messages = [
    "its fridey yoohoo <:partying_face:1313934941658021888>",
    "lest go is friday <:yellow:1313941466862587997>",
    "friday friday friday <a:crazy_laugh:1313932126026203216>",
    "todey is fridnay <:lore:1314281452204068966>",
    "hey everione its friday <a:wink2:1313941408738050098>",
    "sorry was sleping thought it was thursday <a:bigCry:1313925251108835348>, but its friday yahoo <:smirk:1313938566484852839>",
    "FRIDAY <a:stuck_out_tongue:1313938771804422285>",
    "yall know its friday right??????? <:redAngry:1313876421227057193>",
    "are yo guys talking enough about fridey???? <:weary:1313940711627948164>",
    "is it friday? <:hushed_1:1313930520702226482>",
    "bruh friday is lit <:hot_face:1313930434761068574>",
    "what should we eat?? FRIES, BECAUSE ITS FRIES DAY <:fries_1:1313929014599225405>",
    "fish <:fish:1313927965519773818>",
    "i am the fridnay king <:king:1313883436129194064>",
    "IM NOT SURE YOU ALL KNOW THAT ITS FRIDAY <:tv:1313884206149144628>",
    "attention guys, it's fridya !! <:exclamation_1:1313927841322373261>",
    "today is friday, the best day of the week <:happy:1313889573876662323>",
]


# get the token
load_dotenv("../var.env")
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    logger.critical("============================================================")
    logger.critical("There is no token!!!")
    logger.critical("============================================================")
    sys.exit("There is no token!")

ADMINGUILD = os.getenv("ADMIN_GUILD")
ADMINGUILD_YAP_CHANNEL = os.getenv("ADMIN_GUILD_YAP_CHANNEL")
ADMINUSER_T = os.getenv("ADMIN_USER_T")
ADMINUSER_A = os.getenv("ADMIN_USER_A")
SUPPORTGUILD = os.getenv("SUPPORT_GUILD")
UPDATE_PATH = os.getenv("UPDATE_PATH")

if not ADMINGUILD or not ADMINUSER_T or not ADMINUSER_A or not SUPPORTGUILD or not ADMINGUILD_YAP_CHANNEL:
    logger.critical("============================================================")
    logger.critical("There is no admin guild or admin user or support guild! -> There should be a problem with the .env file!")
    logger.critical("============================================================")
    sys.exit("There is no admin guild!")

if not UPDATE_PATH:
    logger.critical("============================================================")
    logger.critical("There is no update path! -> There should be a problem with the .env file!")
    logger.critical("============================================================")
    sys.exit("There is no update path!")

##################### DISCORD BOT CONFIGURATION #####################

intents = discord.Intents.all()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


##################### DISCORD SLASH COMMANDS #####################

@tree.command(name="ping", description="A simple ping command")
async def ping(interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"pong! ({latency}ms) <a:soccer:1313938627104866394>")
    logger.info(f"{interaction.user} used the /ping command with latency {latency}ms")


@tree.command(name="help", description="A simple help command")
async def help_command(interaction):
    await interaction.response.send_message(
        f"hey there <:yellow:1313941466862587997> \n"
        "i'm a bot that reacts to specific words and paid smileys with free smileys. <:lore:1314281452204068966> \n"
        "# Commands\n"
        "- /ping : a simple ping command \n"
        "- /help : this help message \n"
        "# Admin commands \n"
        "- /set_text_triggers : toggles on or off the text triggers (like 'hi')\n"
        "- /set_smiley_messages : toggles on or off the smiley messages (bot sends emojis as messages)\n"
        "- /set_smiley_reactions : toggles on or off the smiley reactions (bot reacts to messages with emojis)\n"
        "- /blacklist : toggles on or off the blacklist for the channel you're using the command in\n",
        ephemeral=True
    )
    logger.info(f"{interaction.user} used the /help command")

@tree.command(name="random", description="Get a random smiley")
async def random_smiley(interaction):
    smiley = get_random_smiley()
    if smiley == "CRIT_ERR":
        await interaction.response.send_message("There's a critical error. Please IMMEDIATLY contact my creator. @tiim.jcb", ephemeral=True)
    elif smiley == "ERR":
        await interaction.response.send_message("There was an error fetching a random smiley. Please try again later.", ephemeral=True)
    elif smiley:
        await interaction.response.send_message(smiley)
        logger.info(f"{interaction.user} used the /random_smiley command and got the smiley {smiley}")
    else:
        raise Exception("Error with the get_random_smiley function.")


##################### GET FRIDAY SCHEDULE COMMAND #########################

@tree.command(name="friday_schedule", description="See the Friday yapping schedule")
@app_commands.guilds(discord.Object(id=1231115041432928326))
async def friday_schedule(interaction):
    if datetime.datetime.now().weekday() != 4:
        await interaction.response.send_message(
            "It's not Friday yet (at least in France), there's no schedule to show. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    sorted_schedule = sorted(friday_hours)
    now = datetime.datetime.now()

    message = "### Today, I'll yap at:\n"
    for hour, minute in sorted_schedule:
        target_time = datetime.datetime.combine(now.date(), datetime.time(hour, minute))
        timestamp = int(target_time.timestamp())


        if now > target_time:
            message += f"> - ~~<t:{timestamp}:t>~~\n"
        else:
            message += f"> - <t:{timestamp}:t>\n"

    await interaction.response.send_message(message, ephemeral=True)
    logger.info(f"{interaction.user} used the /friday_schedule command to see the Friday schedule.")


##################### GUILD ADMINISTRATIVE COMMANDS #####################

# text triggers settings - server_settings[1]
@tree.command(name="set_text_triggers", description="Enable or disable text triggers (e.g., 'hi')")
@app_commands.describe(enable="True to enable text triggers, False to disable them")
async def set_text_triggers(interaction, enable: bool):

    # admin check
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command. Only administrators can toggle text triggers. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    guild_id = interaction.guild_id
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    # check if the guild exists in the database
    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()

    # if the guild is not in the database, add it
    if not result:
        cursor.execute("INSERT INTO server_settings (guild_id, text_reactions_enabled) VALUES (?, ?)", (guild_id, int(enable)))
        conn.commit()
        status_message = "enabled" if enable else "disabled"
        await interaction.response.send_message(f"Text triggers {status_message}. <:yellow:1313941466862587997>")
    else:
        # if it's in the db, update the setting for the guild
        cursor.execute("UPDATE server_settings SET text_reactions_enabled = ? WHERE guild_id = ?", (int(enable), guild_id))
        conn.commit()
        status_message = "enabled" if enable else "disabled"
        await interaction.response.send_message(f"Text triggers {status_message}. <:yellow:1313941466862587997>")

    # log the change
    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()
    logger.info(f"Text triggers settings modified for guild {guild_id}. Current status: {result[1]}")

    conn.close()


# smiley messages settings - server_settings[2]
@tree.command(name="set_smiley_messages", description="Enable or disable smiley messages (bot sends emojis as messages)")
@app_commands.describe(enable="True to enable smiley messages, False to disable them")
async def set_smiley_messages(interaction, enable: bool):

    # admin check
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command. Only administrators can toggle smiley messages. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    guild_id = interaction.guild_id
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()

    # if the guild is not in the db
    if not result:
        cursor.execute("INSERT INTO server_settings (guild_id, smiley_messages) VALUES (?, ?)", (guild_id, int(enable)))
        conn.commit()
        status_message = "enabled" if enable else "disabled"
        await interaction.response.send_message(f"Smiley messages {status_message}. <:yellow:1313941466862587997>")
    else:
        cursor.execute("UPDATE server_settings SET smiley_messages = ? WHERE guild_id = ?", (int(enable), guild_id))
        conn.commit()
        status_message = "enabled" if enable else "disabled"
        await interaction.response.send_message(f"Smiley messages {status_message}. <:yellow:1313941466862587997>")

    # and we log as always
    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()
    logger.info(f"Smiley messages settings modified for guild {guild_id}. Current status: {result[2]}")

    conn.close()


# smiley reactions settings - server_settings[3]
@tree.command(name="set_smiley_reactions", description="Enable or disable smiley reactions (bot reacts to messages with emojis)")
@app_commands.describe(enable="True to enable smiley reactions, False to disable them")
async def set_smiley_reactions(interaction, enable: bool):

    # usual admin check
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command. Only administrators can toggle smiley reactions. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    guild_id = interaction.guild_id
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()

    # if the guild is not in db
    if not result:
        cursor.execute("INSERT INTO server_settings (guild_id, smiley_reactions) VALUES (?, ?)", (guild_id, int(enable)))
        conn.commit()
        status_message = "enabled" if enable else "disabled"
        await interaction.response.send_message(f"Smiley reactions {status_message}. <:yellow:1313941466862587997>")
    else:
        cursor.execute("UPDATE server_settings SET smiley_reactions = ? WHERE guild_id = ?", (int(enable), guild_id))
        conn.commit()
        status_message = "enabled" if enable else "disabled"
        await interaction.response.send_message(f"Smiley reactions {status_message}. <:yellow:1313941466862587997>")

    # log
    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()
    logger.info(f"Smiley reactions settings modified for guild {guild_id}. Current status: {result[3]}")

    conn.close()


# blacklist channels -- different table in the db (channel_blacklist)
@tree.command(name="blacklist", description="Toggle blacklist status for a channel")
@app_commands.describe(channel="Mention the channel (e.g., #general) you want to toggle blacklist status for")
async def blacklist_channel(interaction, channel: discord.TextChannel):

    # Usual admin check
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command. Only administrators can manage the blacklist. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    guild_id = interaction.guild_id
    channel_id = channel.id

    result = is_blacklisted(guild_id, channel_id)

    if result:
        remove_channel_from_blacklist(guild_id, channel_id)
        await interaction.response.send_message(f"The channel {channel.mention} has been removed from the blacklist. <:yellow:1313941466862587997>", ephemeral=True)
        logger.info(f"Channel {channel_id} in guild {guild_id} removed from blacklist by {interaction.user}.")
    else:
        add_channel_to_blacklist(guild_id, channel_id)
        await interaction.response.send_message(f"The channel {channel.mention} has been blacklisted. <a:bigCry:1313925251108835348>", ephemeral=True)
        logger.info(f"Channel {channel_id} in guild {guild_id} blacklisted by {interaction.user}.")




##################### BOT ADMINISTRATIVE COMMANDS #####################

@tree.command(name="add_trigger", description="Add a trigger to the database")
@app_commands.guilds(discord.Object(id=ADMINGUILD))
@app_commands.describe( trigger="The trigger word", response="The response for the trigger", is_emoji="True if the trigger is a smiley, false otherwise", is_special="True if this is a special trigger, false otherwise")
async def add_trigger(interaction, trigger: str, response: str, is_emoji: bool, is_special: bool):
    # administrator check
    if interaction.user.id != int(ADMINUSER_T) and interaction.user.id != int(ADMINUSER_A):
        await interaction.response.send_message(
            "You do not have permission to use this command. Only the administrators of the bot can use this! <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    # connect to the db
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    try:
        # insert
        cursor.execute(
            "INSERT INTO triggers (word, smiley, is_emoji, is_special) VALUES (?, ?, ?, ?)",
            (trigger, response, is_emoji, is_special)
        )
        conn.commit()

        # check
        if cursor.execute("SELECT * FROM triggers WHERE word = ?", (trigger,)).fetchone():
            await interaction.response.send_message(
                f"Trigger '{trigger}' with the response '{response}' successfully added to the database. Special: {is_special}, Emoji: {is_emoji}"
            )
            logger.info(f"Trigger '{trigger}' with the response '{response}' successfully added to the database. Special: {is_special}, Emoji: {is_emoji}")
        else:
            raise Exception("Insertion failed")

    except sqlite3.IntegrityError:  # trigger already exists
        await interaction.response.send_message(
            f"Error: Trigger '{trigger}' already exists in the database. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        logger.error(f"Error: Trigger '{trigger}' already exists in the database.")

    except Exception as e:  # other errors
        await interaction.response.send_message(
            f"Error adding trigger '{trigger}' with the response '{response}' to the database: {e}. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        logger.error(f"Error adding trigger '{trigger}' with the response '{response}' to the database: {e}")

    finally:
        conn.close()


@tree.command(name="remove_trigger", description="Remove a trigger from the database")
@app_commands.guilds(discord.Object(id=ADMINGUILD))
@app_commands.describe(trigger="The trigger word to remove")
async def remove_trigger(interaction, trigger: str):
    # admin check
    if interaction.user.id != int(ADMINUSER_T) and interaction.user.id != int(ADMINUSER_A):
        await interaction.response.send_message(
            "You do not have permission to use this command. Only the administrators of the bot can use this! <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    # db connection
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    try:
        # delete trigger
        cursor.execute("DELETE FROM triggers WHERE word = ?", (trigger,))
        conn.commit()

        # check
        if not cursor.execute("SELECT * FROM triggers WHERE word = ?", (trigger,)).fetchone():
            await interaction.response.send_message(
                f"Trigger '{trigger}' successfully removed from the database. <:yellow:1313941466862587997>",
                ephemeral=True
            )
            logger.info(f"Trigger '{trigger}' successfully removed from the database.")
        else:
            raise Exception("Deletion failed")

    except Exception as e:
        await interaction.response.send_message(
            f"Error removing trigger '{trigger}' from the database: {e}. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        logger.error(f"Error removing trigger '{trigger}' from the database: {e}")

    finally:
        conn.close()


@tree.command(name="logs", description="Get the n last lines of logs")
@app_commands.guilds(discord.Object(id=ADMINGUILD))
@app_commands.describe(n="Number of lines to get -- max 10, otherwise Discord won't allow it.")
async def logs(interaction, n: int):
    if interaction.user.id != int(ADMINUSER_T) and interaction.user.id != int(ADMINUSER_A):
        await interaction.response.send_message(
            "You do not have permission to use this command. Only the administators of the bot can use this! <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    if n > 10:
        await interaction.response.send_message(
            "You can't get more than 10 lines of logs at once.",
            ephemeral=True
        )
        return

    log_dir = "../logs"  # Replace with your actual log directory
    log_content = get_last_log_lines(n, log_dir)

    # Send the response
    await interaction.response.send_message(
        f"```plaintext\n{log_content}\n```",
        ephemeral=True
    )


@tree.command(name="update_bot", description="Update the bot code and restart it")
@app_commands.guilds(discord.Object(id=ADMINGUILD))
async def update_bot(interaction):
    if interaction.user.id not in {int(ADMINUSER_T), int(ADMINUSER_A)}:
        await interaction.response.send_message(
            "You do not have permission to use this command. Only the administrators of the bot can use this! <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "Updating the bot... The bot will restart shortly. Please wait. <:yellow:1313941466862587997>",
    )

    try:
        subprocess.Popen([UPDATE_PATH], shell=False)

        await interaction.followup.send(
            "The bot is restarting. This might take a few seconds. <:yellow:1313941466862587997>",
        )
    except Exception as e:
        await interaction.followup.send(
            f"An error occurred while updating the bot: <:redAngry:1313876421227057193> \n```plaintext\n{str(e)}\n```",
        )



##################### TIME BASED EVENTS #####################

@tasks.loop(minutes=1)
async def friday_message():
    if is_friday_random_time():
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
                logger.error(f"Channel with ID {channel_id} not found in guild {guild_id}. Can't send the Friday message.")
        else:
            logger.error(f"Guild with ID {guild_id} not found. Can't send the Friday message.")


##################### DISCORD BOT FUNCTIONS #####################

async def update_activity_status():
        activity = discord.Activity(type=discord.ActivityType.competing,
                                    name=f" {len(bot.guilds)} servers to use free smileys")
        await bot.change_presence(status=discord.Status.online, activity=activity)




##################### DISCORD BOT EVENTS #####################

## Bot events
@bot.event
async def on_ready():
    ## create the server settings database if it don't exist
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='server_settings';")
    if not cursor.fetchone():
        logger.warning("The server_settings table does not exist in the database.")

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

    if datetime.datetime.now().weekday() == 4:
        generate_friday_schedule()
        logger.info(f"Generated Friday schedule: {friday_hours}")
        friday_message.start()

    logger.info(f"Bot started and connected as {bot.user} in {len(guild_list)} server!")
    await update_activity_status()

    # sync the global command tree
    try:
        await tree.sync()
        logger.info("Command tree synced globally!")
    except Exception as e:
        logger.critical(f"Error syncing command tree: {e}")

    # sync the command tree in the admin guild
    try :
        guild = discord.Object(id=ADMINGUILD)
        await tree.sync(guild=guild)
        logger.info("Command tree synced in admin guild!")
    except Exception as e:
        logger.critical(f"Error syncing command tree in admin guild: {e}")

    # sync the command tree in the support guild
    try:
        guild = discord.Object(id=SUPPORTGUILD)
        await tree.sync(guild=guild)
        logger.info("Command tree synced in support guild!")
    except Exception as e:
        logger.critical(f"Error syncing command tree in support guild: {e}")

    # sync the command tree in the community guild
    try:
        guild = discord.Object(id=1231115041432928326)
        await tree.sync(guild=guild)
        logger.info("Command tree synced for the community server !")
    except Exception as e:
        logger.critical(f"Error syncing command tree for the community server : {e}")


## Guild events
@bot.event
async def on_guild_join(guild):
    logger.info("============================================================")
    logger.info(f"Bot has joined a new guild: {guild.name} (ID: {guild.id})")
    logger.info("============================================================")
    admin_guild = bot.get_guild(int(ADMINGUILD))
    channel = admin_guild.get_channel(int(ADMINGUILD_YAP_CHANNEL))
    await channel.send(f"i joined a new guild: '{guild.name}' <:yellow:1313941466862587997>")
    add_guild_to_db(guild.id)
    await update_activity_status()

@bot.event
async def on_guild_remove(guild):
    logger.info("============================================================")
    logger.info(f"Bot has been removed from a guild: {guild.name} (ID: {guild.id})")
    logger.info("============================================================")
    admin_guild = bot.get_guild(int(ADMINGUILD))
    channel = admin_guild.get_channel(int(ADMINGUILD_YAP_CHANNEL))
    await channel.send(f"i got kicked from the guild : '{guild.name}' <:redAngry:1313876421227057193>")
    remove_guild_from_db(guild.id)
    await update_activity_status()



## Message event -- basically the main function of the bot lol
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if is_blacklisted(message.guild.id, message.channel.id):
        return

    # get server settings
    guild_id = message.guild.id if message.guild else None
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT smiley_messages, smiley_reactions FROM server_settings WHERE guild_id = ?", (guild_id,))
    settings = cursor.fetchone()
    conn.close()

    # if there's no config we apply default settings -- should not happen, but just in case
    if not settings:
        smiley_messages_enabled = True
        smiley_reactions_enabled = False
    else:
        smiley_messages_enabled, smiley_reactions_enabled = settings


    smileys = process_message_for_smiley(message)
    if smileys:
        # sends a message
        if smiley_messages_enabled:
            smiley_message = " ".join(smileys)
            await message.channel.send(smiley_message)

        # adds reactions
        if smiley_reactions_enabled:
            for smiley in smileys:
                try:
                    emoji_id = smiley.split(":")[-1][:-1]
                    emoji_object = discord.PartialEmoji(name=smiley.split(":")[1], id=int(emoji_id))
                    await message.add_reaction(emoji_object)
                except Exception:
                    logger.error(f"Failed to add reaction {smiley} to message -> might be because it's a special trigger. if it is, all good.")


bot.run(TOKEN)
