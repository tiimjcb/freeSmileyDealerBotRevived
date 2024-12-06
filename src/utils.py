import datetime
import random
import sqlite3
import logging
import re
from logger import logger

friday_hours = []


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
    conn = sqlite3.connect('../databases/bot.db')
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
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()
    if not result:
        logger.info(f"\nAdding guild {guild_id} to the server settings database.")
        cursor.execute("INSERT INTO server_settings (guild_id) VALUES (?)", (guild_id,))
        conn.commit()
        logger.info(f"Guild {guild_id} added to the server settings database.")
        conn.close()


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
    friday_hours.append((23, 59))


def is_friday_random_time():
    """
    check if the current time matches one of the pre-generated Friday times.
    """
    now = datetime.datetime.now()
    return now.weekday() == 4 and (now.hour, now.minute) in friday_hours