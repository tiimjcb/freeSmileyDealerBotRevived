import datetime
import random
import sqlite3
import re
import os
from logger import logger

friday_hours = []

## Smiley things

def normalize_emoji(emoji):
    """
    function that normalizes an emoji by removing skin tone modifiers.
    """
    skin_tone_modifiers = re.compile(r'[\U0001F3FB-\U0001F3FF]')
    return skin_tone_modifiers.sub('', emoji)


def is_regional_indicator(char):
    """
    checks if a character is a regional indicator symbol
    """
    return '\U0001F1E6' <= char <= '\U0001F1FF'


def merge_regional_indicators(words):
    """
    merge the regional indicator symbols in a list into a single emoji if they are adjacent while preserving all other elements in the list.
    """
    merged_words = []
    skip_next = False

    for i in range(len(words)):
        if skip_next:
            skip_next = False
            continue

        if is_regional_indicator(words[i]) and i + 1 < len(words) and is_regional_indicator(words[i + 1]):
            merged_words.append(words[i] + words[i + 1])
            skip_next = True
        else:
            merged_words.append(words[i])

    return merged_words



def process_message_for_smiley(message):
    """
    return the smileys of the emojis in a string that has an occurence in the database.
    if no emoji is in the string, or if none of the emojis in the string have an occurence, it returns None.
    """
    guild_id = message.guild.id if message.guild else "DM"
    guild_name = message.guild.name if message.guild else "DM"
    user_name = message.author.name

    # connect to the database
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    # import the server settings for this guild
    cursor.execute("SELECT text_reactions_enabled FROM server_settings WHERE guild_id = ?", (guild_id,))
    text_reactions_enabled = cursor.fetchone()[0]


    # break the message into words -> we use the normalize_emoji() function to remove skin tone modifiers
    words = [normalize_emoji(word) for word in re.findall(r'\w+|[^\w\s]', message.content)]
    #logger.debug(f"Words: {words}")                # commented because it's useful for debugging. disabled on host.
    words = merge_regional_indicators(words)
    #logger.debug(f"Processed words: {words}")      # idem
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
            logger.info(f"{user_name} in {guild_name} said the word '{word}' -> proper response sent (special trigger)")
            logger.debug(f"Special trigger word found - ID: '{result[0]}', Trigger : '{result[1]}', Response: '{result[2]}', isEmoji : '{result[3]}'")
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
            logger.info(f"{user_name} in {guild_name} said the word '{word}' -> Smiley sent")
            logger.debug(f"Trigger word found - ID: '{result[0]}', Trigger : '{result[1]}', Response: '{result[2]}', isEmoji : '{result[3]}'")
            smileys.append(result[2])

    conn.close()
    return smileys if smileys else None


def get_random_smiley(db_path='../databases/bot.db'):
    """
    function that fetches a random smiley from the database.

    :param db_path: the path to the database file -- by default the bot.db file
    :return: a random smiley, or None if no smileys are found
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT smiley FROM trigger_words")
        smileys = cursor.fetchall()

        if not smileys:
            logger.critical("No smileys found in the database for random selection.")
            return "CRIT_ERR"

        random_smiley = random.choice(smileys)[0]
        return random_smiley

    except Exception as e:
        logger.error(f"Error fetching a random smiley: {e}")
        return "ERR"

    finally:
        conn.close()

## Guild things

def add_guild_to_db(guild_id):
    """
    function that adds a guild to the server settings database
    """
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()
    if not result:
        logger.info(f"Adding guild {guild_id} to the server settings database.")
        cursor.execute("INSERT INTO server_settings (guild_id) VALUES (?)", (guild_id,))
        conn.commit()
        logger.info(f"Guild {guild_id} added to the server settings database.")
        conn.close()

def remove_guild_from_db(guild_id):
    """
    function that removes a guild from the server settings database
    """
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()
    if result:
        logger.info(f"Removing guild {guild_id} from the server settings database.")
        cursor.execute("DELETE FROM server_settings WHERE guild_id = ?", (guild_id,))
        conn.commit()
        logger.info(f"Guild {guild_id} removed from the server settings database.")
        conn.close()


### Blacklist things

def is_blacklisted(guild_id, channel_id):
    """
    function that checks if a channel in a certain guild is blacklisted
    :param guild_id: the guild id
    :param channel_id: the channel id
    :return: boolean, true if blacklisted, false if not
    """
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM channel_blacklist WHERE guild_id = ? AND channel_id = ?", (guild_id, channel_id))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_channel_to_blacklist(guild_id, channel_id):
    """
    function that adds a channel to the blacklist
    :param guild_id: the guild id
    :param channel_id: the channel id
    """
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()
    result = is_blacklisted(guild_id, channel_id)
    if not result:
        cursor.execute("INSERT INTO channel_blacklist (guild_id, channel_id) VALUES (?, ?)", (guild_id, channel_id))
        conn.commit()
        logger.info(f"Channel {channel_id} from guild {guild_id} added to the blacklist.")
    conn.close()

def remove_channel_from_blacklist(guild_id, channel_id):
    """
    function that removes a channel from the blacklist
    :param guild_id: the guild id
    :param channel_id: the channel id
    """
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()
    result = is_blacklisted(guild_id, channel_id)
    if result:
        cursor.execute("DELETE FROM channel_blacklist WHERE guild_id = ? AND channel_id = ?", (guild_id, channel_id))
        conn.commit()
        logger.info(f"Channel {channel_id} from guild {guild_id} removed from the blacklist.")
    conn.close()


### Friday things

def generate_friday_schedule():
    """
    Generate a random schedule for Friday messages.
    Between 5 and 12 times a day, at random hours and minutes.
    """
    friday_hours.clear()
    num_messages = random.randint(15, 22)
    for _ in range(num_messages):
        hour = random.choices(
            population=range(24),
            weights=[1] * 8 + [3] * 16,  # Weights: 1 for hours 0-7, 3 for hours 8-23
            k=1
        )[0]
        minute = random.randint(0, 59)
        friday_hours.append((hour, minute))


def is_friday_random_time():
    """
    check if the current time matches one of the pre-generated Friday times.
    """
    now = datetime.datetime.now()
    return now.weekday() == 4 and (now.hour, now.minute) in friday_hours


## Log things

def get_last_log_lines(n: int, log_dir: str):
    """
    Retrieves the last n lines from the most recently modified log file in the specified directory.
    """
    try:
        # get the last modified log file
        log_files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
        if not log_files:
            raise FileNotFoundError("No log files found in the specified directory.")

        log_files = sorted(log_files, key=lambda f: os.path.getmtime(os.path.join(log_dir, f)), reverse=True)
        latest_log_file = os.path.join(log_dir, log_files[0])

        # Read the last n lines
        with open(latest_log_file, "r") as log_file:
            lines = log_file.readlines()
            return "".join(lines[-n:]) if len(lines) >= n else "".join(lines)

    except Exception as e:
        logger.error("An error occurred while reading the logs.")
        return f"An error occurred while reading the logs: {e}"
