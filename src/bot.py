import random

from discord import app_commands
from utils import *
from discord.ext import tasks
import sys
import os
import datetime
import subprocess


##################### VARIABLES #####################

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

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
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
    is_admin = interaction.user.guild_permissions.administrator
    message = (
        f"hey there \n"
        "i'm a bot that reacts to specific words and paid smileys with free smileys. <:lore:1314281452204068966> \n"
        "# Features <:yellow:1313941466862587997>\n"
        "> - Send a paid smiley, get a free one smiley back \n"
        "> - Ask if it's friday, and I'll answer you \n"
        "\n"
        "# Commands <:yellow:1313941466862587997>\n"
        "> - `/ignore_me [true/false]` : add or remove yourself from the bot's blacklist -- the bot will ignore you\n"
        "> - `/chat_start` - `/chat_end` : start or end a chat session with the bot -- the bot will reply to every message for 15 minutes (there are rate limits).\n"
        "> - `/help` : this help message \n"
        "> - `/random` : get a random smiley \n"
        "> - `/show_triggers` : show all of the different triggers \n"
        "> - `/experience` : see your experience points or someone else's \n"
        "> - `/leaderboard` : see the experience leaderboard for your server \n"

    )

    if is_admin:
        message += (
            "\n"
            "# Admin commands <:nerd:1313933240486203522>\n"
            "> - `/set_text_triggers [true/false]` : toggles on or off the text triggers (like 'hi')\n"
            "> - `/set_smiley_messages [true/false]` : toggles on or off the smiley messages (bot sends emojis as messages)\n"
            "> - `/set_smiley_reactions [true/false]` : toggles on or off the smiley reactions (bot reacts to messages with emojis)\n"
            "> - `/set_friday_messages [true/false]` : toggles on or off the reactions to friday related messages\n"
            "> - `/blacklist_channel [#channel]` : toggles on or off the blacklist for the channel you're using the command in\n"
            "> - `/blacklist_trigger [trigger]` : toggles on or off the blacklist for a specific trigger\n"
            "> - `/show_blacklisted_triggers` : shows the list of blacklisted triggers for this server\n"
            "> - `/set_timezone [timezone]` : sets the timezone for the server\n"
            "> - `/pause_bot [true/false]` : pauses or unpauses the bot in the server\n"
        )

    await interaction.response.send_message(message, ephemeral=True)
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

@tree.command(name="show_triggers", description="Show all of the different triggers")
async def show_triggers(interaction):
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT word
        FROM triggers
        ORDER BY is_emoji ASC, 
                 CASE WHEN is_emoji = 0 THEN word END ASC,
                 CASE WHEN is_emoji = 1 THEN word END DESC
    """)
    triggers = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not triggers:
        await interaction.response.send_message("No triggers found in the database.", ephemeral=True)
        return

    pages = [triggers[i:i + 20] for i in range(0, len(triggers), 20)]

    formatted_pages = [f"### page {index + 1}/{len(pages)} <:yellow:1313941466862587997> \n" + "\n".join(f"> - {trigger}" for trigger in page)
                      for index, page in enumerate(pages)]

    view = PaginatedView(formatted_pages, interaction.user.id)
    await interaction.response.send_message(content=formatted_pages[0], view=view, ephemeral=True)


@tree.command(name="ignore_me", description="Add or remove yourself from the bot's blacklist -- the bot will ignore you tho")
@app_commands.describe(enable="True to add yourself to the blacklist, False to remove yourself")
async def ignore_me(interaction, enable: bool):
    user_id = interaction.user.id
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    try:
        if enable:
            cursor.execute(
                "INSERT INTO users_settings (user_id, is_blacklisted) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET is_blacklisted = ?",
                (user_id, True, True))
            conn.commit()
            await interaction.response.send_message(
                "You have been added to the bot's blacklist. The bot will now ignore you.", ephemeral=True)
            logger.info(f"User {user_id} was added to the blacklist.")
        else:
            cursor.execute("UPDATE users_settings SET is_blacklisted = ? WHERE user_id = ?", (False, user_id))
            conn.commit()
            await interaction.response.send_message(
                "You have been removed from the bot's blacklist. The bot will no longer ignore you.", ephemeral=True)
            logger.info(f"User {user_id} was removed from the blacklist.")

    except Exception as e:
        logger.error(f"An error occurred while processing /ignore_me for user {user_id}: {e}")
        await interaction.response.send_message("There was an error processing your request. Please try again later.",
                                                ephemeral=True)

    finally:
        conn.close()



@tree.command(name="experience", description="See your experience points or someone else's")
@app_commands.describe(user="The user you want to see the experience points of -- leave empty to see your own")
async def experience(interaction, user: discord.Member = None):

    user_id = user.id if user else interaction.user.id
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT exp FROM users_settings WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    # if the user is the one who used the command, but they don't have any experience data yet
    if not result and not user:
        cursor.execute("INSERT INTO users_settings (user_id, exp) VALUES (?, ?)", (user_id, 0))
        conn.commit()
        response = (
            "you have **0** experience points <:yellow:1313941466862587997>\n"
            "-# gain experience by feeding me with paid smileys"
        )

        # if the user is not the one who used the command, but they don't have any experience data yet
    elif not result:
        response = (
            f"{user.mention} has **0** experience points, he's not even registered in the database.. looser... <:yellow:1313941466862587997>\n"
            "-# gain experience by feeding me with paid smileys"
        )

        # if the user has experience data
    else:
        response = (
            f"{f'{user.mention} has' if user else 'you have'} **{result[0]}** experience points <:yellow:1313941466862587997>\n"
            "-# gain experience by feeding me with paid smileys"
        )

    conn.close()
    await interaction.response.send_message(response)



@tree.command(name="leaderboard", description="See the experience leaderboard for your server")
@app_commands.checks.cooldown(1, 600.0, key=lambda i: i.guild_id)
async def leaderboard(interaction):
    """
    Displays the top 10 users in the experience leaderboard for the current server.
    Only users in the database AND in the server are shown, excluding bots.
    """
    guild = interaction.guild

    server_member_ids = {member.id for member in guild.members if not member.bot}

    if not server_member_ids:
        await interaction.response.send_message("no eligible members found in this server. seems like nobody have experience <:redAngry:1313876421227057193>", ephemeral=True)
        return

    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    query = f"SELECT user_id, exp FROM users_settings WHERE user_id IN ({','.join(['?'] * len(server_member_ids))}) ORDER BY exp DESC LIMIT 10"
    cursor.execute(query, tuple(server_member_ids))
    leaderboard = cursor.fetchall()

    conn.close()

    top_10 = leaderboard[:10]

    if not top_10:
        await interaction.response.send_message("No users in this server have experience yet.", ephemeral=True)
        return

    embed = discord.Embed(title=f"<:trophy:1313940520782925834> {guild.name} free official leaderboard ", color=discord.Color.gold())

    leaderboard_text = ""
    for rank, (user_id, exp) in enumerate(top_10, start=1):
        member = guild.get_member(user_id)
        username = member.display_name if member else f"Unknown ({user_id})"
        leaderboard_text += f"**#{rank}** {username} — **{exp} XP**\n"

    embed.description = leaderboard_text
    await interaction.response.send_message(embed=embed)



@tree.command(name="stalk", description="Stalk a user to track their emoji usage")
@app_commands.describe(user="The user you want to stalk -- leave empty to follow yourself")
async def stalk(interaction, user: discord.Member = None):
    """
    Starts or stops tracking a user's emoji usage.
    If no user is mentioned, follows the command executor.
    """
    user = user or interaction.user
    user_id = user.id
    follower_id = interaction.user.id
    channel_id = interaction.channel.id
    server_id = interaction.guild.id

    if is_user_blacklisted(user_id):
        await interaction.response.send_message(
            f"<:redAngry:1313876421227057193> i can't track {user.mention}, he's in my blacklist. too bad.",
            ephemeral=True
        )
        return

    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT follower_id FROM followed_users WHERE followed_user_id = ? AND server_id = ?", (user_id, server_id))
    followed = cursor.fetchone()

    if followed:
        existing_follower_id = followed[0]

        if follower_id != existing_follower_id and follower_id != user_id:
            await interaction.response.send_message(
                f"i already stalk {user.mention} in this server. shhhh... <:nerd:1313933240486203522> ",
                ephemeral=True
            )
            conn.close()
            return

        conn.close()
        await stop_following(user_id, server_id, channel_id, "manual", interaction)
        return
    else:

        cursor.execute(
            "INSERT INTO followed_users (followed_user_id, follower_id, channel_id, server_id) VALUES (?, ?, ?, ?)",
            (user_id, follower_id, channel_id, server_id)
        )
        conn.commit()
        conn.close()

        response = (
            f"im now stalking {user.mention}'s smiley usage in this server, don't tell them... <:eyes_1:1313927864734711858> \n"
            f"-# type `/stalk @{user}` to stop"
        )

        await interaction.response.send_message(response)



@tree.command(name="chat_start", description="Start a chat session with the bot.")
@app_commands.checks.cooldown(1, 14400, key=lambda i: i.guild_id)
async def chat_start(interaction):
    server_id = interaction.guild.id
    channel_id = interaction.channel.id
    now = datetime.datetime.now(datetime.timezone.utc)

    if not is_chat_enabled(server_id):
        await interaction.response.send_message(
            "chat sessions are disabled in this server. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM chat_sessions WHERE server_id = ?", (server_id,))
    active_session = cursor.fetchone()

    if active_session:
        await interaction.response.send_message(
            "nah man i'm already in a chat session in this server <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        conn.close()
        return

    create_chat(server_id)

    cursor.execute(
        "INSERT INTO chat_sessions (server_id, channel_id, start_time, last_message_time, message_count) VALUES (?, ?, ?, ?, ?)",
        (server_id, channel_id, now, now, 0)
    )
    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"yo the chat session is active -- i'll respond to every message here for **15 minutes**. <:yellow:1313941466862587997>\n"
        f"-# there's a 50 message limit, and 4h cooldown. sorry, it needs to stay free lol - `/chat_end` to stop"
    )





@tree.command(name="chat_end", description="End the chat session with the bot.")
async def chat_end(interaction):
    server_id = interaction.guild.id

    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM chat_sessions WHERE server_id = ?", (server_id,))
    active_session = cursor.fetchone()

    if not active_session:
        await interaction.response.send_message(
            "there's no active chat session here bruv 💀",
            ephemeral=True
        )
        conn.close()
        return

    cursor.execute("DELETE FROM chat_sessions WHERE server_id = ?", (server_id,))
    conn.commit()
    conn.close()

    remove_chat(server_id)

    await interaction.response.send_message(
        "chat session ended. see ya later nerds <:yellow:1313941466862587997>\n"
        "-# you can start again in 4 hours"
    )


@tree.command(name="dice", description="Roll a 6-faces dice")
async def dice(interaction):
    number = random.randint(0,1000)
    if number == 54:
        await interaction.response.send_message(f"wow holy shit you had one chance out of 1000 to roll this. but congrats, you rolled a **4** <a:vampire:1314355368117141547>")
    elif number == 837:
        await interaction.response.send_message(f"you rolled **absins** <:joker:1314328054713155624>")
    else:
        await interaction.response.send_message(f"you rolled a **4** <:yellow:1313941466862587997>")

##################### GUILD ADMINISTRATIVE COMMANDS #####################

# text triggers settings - server_settings[1]
@tree.command(name="set_text_triggers", description="Enable or disable text triggers (e.g., 'hi')")
@app_commands.describe(enable="True to enable text triggers, False to disable them")
@app_commands.default_permissions()
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
@app_commands.default_permissions()
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
@app_commands.default_permissions()
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

# friday messages settings - server_settings[4]
@tree.command(name="set_friday_messages", description="Enable or disable reactions to friday related messages")
@app_commands.describe(enable="True to enable friday messages, False to disable them")
@app_commands.default_permissions()
async def set_friday_messages(interaction, enable: bool):

        # usual admin check
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You do not have permission to use this command. Only administrators can toggle friday messages. <:redAngry:1313876421227057193>",
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
            cursor.execute("INSERT INTO server_settings (guild_id, friday_messages) VALUES (?, ?)", (guild_id, int(enable)))
            conn.commit()
            status_message = "enabled" if enable else "disabled"
            await interaction.response.send_message(f"Friday messages {status_message}. <:yellow:1313941466862587997>")
        else:
            cursor.execute("UPDATE server_settings SET friday_messages = ? WHERE guild_id = ?", (int(enable), guild_id))
            conn.commit()
            status_message = "enabled" if enable else "disabled"
            await interaction.response.send_message(f"Friday messages {status_message}. <:yellow:1313941466862587997>")

        # log
        cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        logger.info(f"Friday messages settings modified for guild {guild_id}. Current status: {result[4]}")

        conn.close()


# blacklist channels -- different table in the db (channel_blacklist)
@tree.command(name="blacklist_channel", description="Toggle blacklist status for a channel")
@app_commands.describe(channel="Mention the channel (e.g., #general) you want to toggle blacklist status for")
@app_commands.default_permissions()
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

    result = is_channel_blacklisted(guild_id, channel_id)

    if result:
        remove_channel_from_blacklist(guild_id, channel_id)
        await interaction.response.send_message(f"The channel {channel.mention} has been removed from the blacklist. <:yellow:1313941466862587997>", ephemeral=True)
        logger.info(f"Channel {channel_id} in guild {guild_id} removed from blacklist by {interaction.user}.")
    else:
        add_channel_to_blacklist(guild_id, channel_id)
        await interaction.response.send_message(f"The channel {channel.mention} has been blacklisted. <a:bigCry:1313925251108835348>", ephemeral=True)
        logger.info(f"Channel {channel_id} in guild {guild_id} blacklisted by {interaction.user}.")


# blacklist triggers -- different table in the db (triggers_blacklist)
@tree.command(name="blacklist_trigger", description="Set or remove blacklist for a trigger for this server")
@app_commands.describe(trigger_word="The word or emoji to (un)blacklist for this server")
@app_commands.default_permissions()
async def blacklist_trigger(interaction, trigger_word: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command. Only administrators can blacklist triggers. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    guild_id = interaction.guild_id

    # db connection
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    # we need to grab the id of the trigger
    cursor.execute("SELECT id FROM triggers WHERE word = ?", (trigger_word,))
    trigger_id = cursor.fetchone()

    # stop point : the trigger doesn't exist
    if not trigger_id:
        await interaction.response.send_message(
            f"the trigger '{trigger_word}' does not even exist <:scream:1313937550054002769>",
            ephemeral=True
        )
        conn.close()
        return

    cursor.execute("SELECT 1 FROM triggers_blacklist WHERE guild_id = ? AND trigger_id = ?", (guild_id, trigger_id[0]))
    if cursor.fetchone():
        cursor.execute("DELETE FROM triggers_blacklist WHERE guild_id = ? AND trigger_id = ?",(guild_id, trigger_id[0]))
        conn.commit()
        await interaction.response.send_message(
            f"The trigger '{trigger_word}' isn't blacklisted anymore for this guild. <:yellow:1313941466862587997>",
            ephemeral=True
        )
        logger.info(f"Trigger '{trigger_word}' isn't blacklisted anymore for guild {guild_id}.")

    else:
        cursor.execute("INSERT INTO triggers_blacklist (guild_id, trigger_id) VALUES (?, ?)", (guild_id, trigger_id[0]))
        conn.commit()
        await interaction.response.send_message(
            f"The trigger '{trigger_word}' has been successfully blacklisted for this guild. <a:bigCry:1313925251108835348>",
            ephemeral=True
        )
        logger.info(f"Trigger '{trigger_word}' has been blacklisted for guild {guild_id}.")

    conn.close()

@tree.command(name="show_blacklisted_triggers", description="Show the trigger blacklist for this server")
@app_commands.default_permissions()
async def show_blacklisted_triggers(interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command. Only administrators can blacklist triggers. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    triggers_list = blacklisted_triggers_list(guild_id=interaction.guild_id)

    if not triggers_list:
        await interaction.response.send_message(
            "There are no blacklisted triggers for this server. Great to see y'all using my free smileys <:yellow:1313941466862587997>",
        )
        return
    else:
        message = "## List of blacklisted triggers\n"
        message += "\n".join(f"> - {trigger}" for trigger in triggers_list)

        await interaction.response.send_message(message)


# timezone command - server_settings[5]
timezones = [
    "UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8", "UTC-7", "UTC-6", "UTC-5",
    "UTC-4", "UTC-3", "UTC-2", "UTC-1", "UTC+0", "UTC+1", "UTC+2", "UTC+3",
    "UTC+4", "UTC+5", "UTC+6", "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12"
]

class TimezoneAutocomplete(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> str:
        if value in timezones:
            return value
        raise ValueError("Invalid timezone")

    async def autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=tz, value=tz)
            for tz in timezones if current.lower() in tz.lower()
        ]

@tree.command(name="set_timezone", description="Set the timezone for the server")
@app_commands.describe(timezone="The timezone to set")
@app_commands.default_permissions()
async def set_timezone(interaction, timezone: TimezoneAutocomplete):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command. Only administrators can set the timezone. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    guild_id = interaction.guild_id
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT timezone FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()

    if not result:
        cursor.execute("INSERT INTO server_settings (guild_id, timezone) VALUES (?, ?)", (guild_id, timezone))
        conn.commit()
        await interaction.response.send_message(f"Timezone set to {timezone}. <:yellow:1313941466862587997>")
        logger.info(f"Timezone set to {timezone} for guild {guild_id}.")
    else:
        cursor.execute("UPDATE server_settings SET timezone = ? WHERE guild_id = ?", (timezone, guild_id))
        conn.commit()
        await interaction.response.send_message(f"Timezone updated to {timezone}. <:yellow:1313941466862587997>")
        logger.info(f"Timezone updated to {timezone} for guild {guild_id}.")

    conn.close()


# pause command - server_settings[6]
@tree.command(name="pause_bot", description="Pause the bot in the server")
@app_commands.describe(enable="True to pause the bot, False to unpause it")
@app_commands.default_permissions()
async def pause(interaction, enable: bool):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command. Only administrators can pause the bot. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    guild_id = interaction.guild_id
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT is_paused FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()

    if not result:
        cursor.execute("INSERT INTO server_settings (guild_id, is_paused) VALUES (?, ?)", (guild_id, int(enable)))
        conn.commit()
        status_message = "paused" if enable else "unpaused"
        await interaction.response.send_message(f"The bot has been {status_message}. <:yellow:1313941466862587997>")
    else:
        cursor.execute("UPDATE server_settings SET is_paused = ? WHERE guild_id = ?", (int(enable), guild_id))
        conn.commit()
        status_message = "paused" if enable else "unpaused"
        await interaction.response.send_message(f"The bot has been {status_message}. <:yellow:1313941466862587997>")

    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()
    logger.info(f"Bot paused status modified for guild {guild_id}. Current status: {result[6]}")

    conn.close()


@tree.command(name="set_chat", description="Enable or disable chat sessions in the server")
@app_commands.describe(enable="True to enable chat sessions, False to disable them")
@app_commands.default_permissions()
async def set_chat(interaction, enable: bool):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command. Only administrators can toggle chat sessions. <:redAngry:1313876421227057193>",
            ephemeral=True
        )
        return

    guild_id = interaction.guild_id
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()

    if not result:
        cursor.execute("INSERT INTO server_settings (guild_id, chat_enabled) VALUES (?, ?)", (guild_id, int(enable)))
        conn.commit()
        status_message = "enabled" if enable else "disabled"
        await interaction.response.send_message(f"Chat sessions {status_message}. <:yellow:1313941466862587997>")
    else:
        cursor.execute("UPDATE server_settings SET chat_enabled = ? WHERE guild_id = ?", (int(enable), guild_id))
        conn.commit()
        status_message = "enabled" if enable else "disabled"
        await interaction.response.send_message(f"Chat sessions {status_message}. <:yellow:1313941466862587997>")

    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()
    logger.info(f"Chat sessions settings modified for guild {guild_id}. Current status: {result[7]}")

    conn.close()



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
                f"Trigger '{trigger}' successfully removed from the database. <:yellow:1313941466862587997>"            )
            logger.info(f"Trigger '{trigger}' successfully removed from the database.")
        else:
            raise Exception("Deletion failed")

    except Exception as e:
        await interaction.response.send_message(
            f"Error removing trigger '{trigger}' from the database: {e}. <:redAngry:1313876421227057193>"        )
        logger.error(f"Error removing trigger '{trigger}' from the database: {e}")

    finally:
        conn.close()



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


@tasks.loop(minutes=5)
async def cleanup_followed_users():
    """
    Periodically removes users who have been followed for more than 24 hours on a per-server basis.
    """
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT followed_user_id, server_id, channel_id FROM followed_users WHERE start_time <= DATETIME('now', '-1 day')")
    expired_users = cursor.fetchall()
    conn.close()

    for user_id, server_id, channel_id in expired_users:
        await stop_following(user_id, server_id, channel_id, "auto")



@tasks.loop(minutes=1)
async def cleanup_expired_chat_sessions():
    """
    Vérifie toutes les minutes les sessions de chat en cours et supprime celles qui ont dépassé 5 minutes.
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT server_id, channel_id FROM chat_sessions WHERE start_time <= ?",
                   (now - datetime.timedelta(seconds=900),))
    expired_sessions = cursor.fetchall()

    cursor.execute("DELETE FROM chat_sessions WHERE start_time <= ?",
                   (now - datetime.timedelta(seconds=900),))
    conn.commit()
    conn.close()

    for server_id, channel_id in expired_sessions:
        guild = bot.get_guild(server_id)
        if guild:
            channel = guild.get_channel(channel_id)
            if channel:
                response = ("its been 15 minutes, i had to end the session. <:yellow:1313941466862587997>\n"
                            "-# use `/chat_start` again in 4 hours to start a new one")
                await channel.send(response)

##################### DISCORD BOT FUNCTIONS #####################

async def update_activity_status():
        activity = discord.Activity(type=discord.ActivityType.competing,
                                    name=f" {len(bot.guilds)} servers to use free smileys")
        await bot.change_presence(status=discord.Status.online, activity=activity)



async def stop_following(user_id, server_id, channel_id, reason, interaction=None):
    """
    Stops tracking a followed user on a specific server and sends a summary message.
    If called manually via `/follow`, interaction is required.
    If called automatically, interaction is None and the channel is fetched from the DB.
    """
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute(
        "SELECT follower_id, emoji_count, smiley_count, channel_id FROM followed_users WHERE followed_user_id = ? AND server_id = ?",
        (user_id, server_id)
    )
    followed = cursor.fetchone()

    if not followed:
        conn.close()
        return

    follower_id, emoji_count, smiley_count, channel_id = followed

    cursor.execute("DELETE FROM followed_users WHERE followed_user_id = ? AND server_id = ?", (user_id, server_id))
    conn.commit()
    conn.close()

    logger.info(f"Stopped following {user_id} in server {server_id}.")

    message = (
        f"> ## i've followed <@{user_id}>\n"
        f"> - **{emoji_count}** paid smileys sent <:redAngry:1313876421227057193>\n"
        f"> - **{smiley_count}** free smileys received <a:angel:1313891911219679283>"
    )

    # selecting the right channel
    if reason == "manual":
        await interaction.response.send_message(message, ephemeral=False)
    elif reason == "auto":
        guild = bot.get_guild(server_id)
        if guild:
            channel = guild.get_channel(channel_id)
            if channel:
                await channel.send(message)
            else:
                logger.error(f"Channel {channel_id} not found in guild {server_id}.")
        else:
            logger.error(f"Guild {server_id} not found.")





##################### DISCORD BOT EVENTS #####################

## Tree event
@tree.error
async def on_app_command_error(interaction, error: app_commands.AppCommandError):
    """Global error handler for app commands"""
    if isinstance(error, app_commands.errors.CommandOnCooldown):
        retry_after = round(error.retry_after) // 60
        await interaction.response.send_message(
            f"chill bro this command is on cooldown! try again in **{max(0, retry_after)}** minutes <:yawning_face:1313941450144223242>",
            ephemeral=True
        )
    else:
        await interaction.response.send_message("bruh an error occurred while executing the command. <:redAngry:1313876421227057193>", ephemeral=True)
        logger.error(f"Unhandled command error: {error}")



## Bot events
@bot.event
async def on_ready():
    ## create the server settings database if it don't exist
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='server_settings';")
    if not cursor.fetchone():
        logger.critical("The server_settings table does not exist in the database.")

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

    cleanup_followed_users.start()
    cleanup_expired_chat_sessions.start()



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
    if (message.author.bot or
            is_channel_blacklisted(message.guild.id, message.channel.id) or
            is_user_blacklisted(message.author.id)
    ):
        return


    # get server settings
    guild_id = message.guild.id if message.guild else None
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT smiley_messages, smiley_reactions, friday_messages, timezone, is_paused FROM server_settings WHERE guild_id = ?", (guild_id,))
    settings = cursor.fetchone()
    conn.close()

    # if there's no config we apply default settings -- should not happen, but just in case
    if not settings:
        smiley_messages_enabled = True
        friday_messages_enabled = True
        smiley_reactions_enabled = False
        timezone = "UTC+0"
        is_paused = False
    else:
        smiley_messages_enabled, smiley_reactions_enabled, friday_messages_enabled, timezone, is_paused = settings


    # if the bot is paused, we don't do anything
    if is_paused:
        return

    if is_in_chat_session(message.guild.id, message.channel.id):
        gemini_message = await process_gemini_message(message)
        if gemini_message:
            await message.reply(gemini_message)
            return
        else:
            return

    if friday_messages_enabled:
        if is_friday_ask_message(message.content):
            await message.reply(process_friday_ask_message(timezone))
            return


    smileys = await process_message_for_smiley(message)
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
                    logger.warning(f"Failed to add reaction {smiley} to message -> might be because it's a special trigger, or an animated smiley. if it is, all good.")
        add_experience(smileys, message.author.id, message.created_at)


bot.run(TOKEN)
