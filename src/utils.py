import datetime
import json

import emoji
import pytz
import random
from google.ai.generativelanguage_v1beta.types import content
import sqlite3
import re
from dotenv import load_dotenv
from logger import logger
import discord
from discord.ui import View, Button
import os
import google.generativeai as genai


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


async def process_message_for_smiley(message):
    """
    return the smileys of the emojis in a string that has an occurence in the database.
    if no emoji is in the string, or if none of the emojis in the string have an occurence, it returns None.
    """
    guild_id = message.guild.id if message.guild else "DM"


    # connect to the database
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    # import the server settings for this guild
    cursor.execute("SELECT text_reactions_enabled FROM server_settings WHERE guild_id = ?", (guild_id,))
    text_reactions_enabled = cursor.fetchone()[0]

    # import the blacklisted triggers
    blacklisted_triggers = blacklisted_triggers_list(guild_id)

    # break the message into words -> we use the normalize_emoji() function to remove skin tone modifiers
    words = [normalize_emoji(word) for word in re.findall(r'\w+|[^\w\s]', message.content)]
    #logger.debug(f"Words: {words}")                # commented because it's useful for debugging. disabled on host.

    words = [word for word in merge_regional_indicators(words) if word.lower() not in blacklisted_triggers]
    #logger.debug(f"Processed words: {words}") # idem

    emojis = [word for word in words if emoji.is_emoji(word)]
    # logger.debug(f"Emojis: {emojis}")      # idem
    smileys = []

    # first: scan for special triggers
    for word in words:
        word = word.lower()
        if text_reactions_enabled:
            cursor.execute("SELECT * FROM triggers WHERE word = ? AND is_special = 1", (word,))
        else:
            cursor.execute("SELECT * FROM triggers WHERE word = ? AND is_special = 1 AND is_emoji = 1", (word,))
        result = cursor.fetchone()

        if result:
            smileys.append(result[2])
            conn.close()
            return smileys


    # second: scan for regular triggers
    for word in words:
        word = word.lower()
        if text_reactions_enabled:
            cursor.execute("SELECT * FROM triggers WHERE word = ? AND is_special = 0", (word,))
        else:
            cursor.execute("SELECT * FROM triggers WHERE word = ? AND is_special = 0 AND is_emoji = 1", (word,))
        result = cursor.fetchone()

        if result:
            smileys.append(result[2])

    cursor.execute("SELECT * FROM followed_users WHERE followed_user_id = ? and server_id = ?", (message.author.id, message.guild.id))
    followed = cursor.fetchone()
    if followed:
        await update_follow_stats(message.author.id, guild_id, len(emojis), len(smileys))

    conn.close()
    return smileys if smileys else None




async def update_follow_stats(user_id, server_id, emoji_count, smiley_count):
    """
    Updates the emoji/smiley count for a followed user on a specific server.
    :param user_id: the user id
    :param server_id: the server where the tracking is active
    :param emoji_count: the number of emojis detected
    :param smiley_count: the number of smileys given
    """
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE followed_users SET emoji_count = emoji_count + ?, smiley_count = smiley_count + ? WHERE followed_user_id = ? AND server_id = ?",
        (emoji_count, smiley_count, user_id, server_id)
    )

    conn.commit()
    conn.close()



def get_random_smiley(db_path='../databases/bot.db'):
    """
    function that fetches a random smiley from the database.

    :param db_path: the path to the database file -- by default the bot.db file
    :return: a random smiley, or None if no smileys are found
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT smiley FROM  triggers WHERE is_special = 0")
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

## Experience things

def add_experience(smileys, user_id, timestamp):
    """
    function that adds experience to a user in the database.
    :param smileys: the smileys to add
    :param user_id: the user id
    :param timestamp: the timestamp of the message
    """
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users_settings WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    # adding the user if not in db
    if not user:
        cursor.execute("INSERT INTO users_settings (user_id) VALUES (?)", (user_id,))
        conn.commit()
        logger.info(f"User {user_id} added to the users settings database.")


    # calculating the experience based on the number of smileys detected (1 smiley = 1 exp, max 5 exp per message)
    exp_calc = len(smileys) if len(smileys) <= 5 else 5

    # comparing the timestamp of the message with the last message timestamp to avoid spam
    cursor.execute("SELECT last_detected_message FROM users_settings WHERE user_id = ?", (user_id,))
    last_message = cursor.fetchone()
    last_message_timestamp = last_message[0] if last_message else None

    if last_message_timestamp:
        last_message_timestamp = datetime.datetime.strptime(last_message_timestamp, "%Y-%m-%d %H:%M:%S.%f%z")
        time_difference = timestamp - last_message_timestamp
        if time_difference.total_seconds() < 20:
            exp_calc = 0

    # adding the experience and updating the timestamp to the user
    cursor.execute("UPDATE users_settings SET exp = exp + ?, last_detected_message = ? WHERE user_id = ?", (exp_calc, timestamp, user_id))
    conn.commit()
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

### Blacklist channel things

def is_channel_blacklisted(guild_id, channel_id):
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


def is_user_blacklisted(user_id):
    """
    function that checks if a user is blacklisted
    :param user_id: the user id
    :return: boolean, true if blacklisted, false if not
    """
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users_settings WHERE user_id = ? and is_blacklisted = 1", (user_id,))
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
    result = is_channel_blacklisted(guild_id, channel_id)
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
    result = is_channel_blacklisted(guild_id, channel_id)
    if result:
        cursor.execute("DELETE FROM channel_blacklist WHERE guild_id = ? AND channel_id = ?", (guild_id, channel_id))
        conn.commit()
        logger.info(f"Channel {channel_id} from guild {guild_id} removed from the blacklist.")
    conn.close()



### Blacklist triggers things

def blacklisted_triggers_list(guild_id):
    """
    function that returns a list of blacklisted triggers for a certain guild
    :param guild_id: the guild id
    :return: a list of blacklisted triggers
    """
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT t.word FROM triggers t, triggers_blacklist tb WHERE t.id = tb.trigger_id AND tb.guild_id = ?", (guild_id,))
    result = cursor.fetchall()
    conn.close()
    return [row[0] for row in result]


### Friday things


def is_friday_ask_message(message):
    """
    determines if a message is asking about Friday.
    imma be honest with you I don't know how I made this work

    :param message: the content of the message to analyze.
    :return: true if the message is asking about Friday, False otherwise.
    """
    # keywords list and their typo variations
    friday_variations = ["friday", "fridey", "fryday", "forday"]
    keywords = ["is", "it", "are", "we", "today", "on", "yet"]

    # clean and split the message into words
    words = re.findall(r"[\w']+", message.lower())

    # little child functions to check if a word is a keyword or a Friday variation
    def is_keyword(word):
        return word in keywords

    def is_friday(word):
        return word in friday_variations

    # now we scan through the words
    keyword_count = 0
    friday_found = False
    tolerance = 0

    for word in words:
        if is_friday(word):
            friday_found = True
            tolerance = 0
        elif is_keyword(word):
            keyword_count += 1
            tolerance = 0
        elif tolerance < 1:
            tolerance += 1
        else:
            keyword_count = 0
            friday_found = False
            tolerance = 0

        if keyword_count >= 2 and friday_found:
            return True

    return False


def parse_timezone(timezone_str):
    """
    Parses a timezone string in the format 'UTC+X' or 'UTC-X' and returns a timezone object.
    If it's a valid IANA timezone, returns the corresponding timezone object.
    """
    # Check if it's in the format 'UTC+X' or 'UTC-X'
    utc_match = re.match(r'^UTC([+-])(\d{1,2})$', timezone_str)
    if utc_match:
        sign = 1 if utc_match.group(1) == '+' else -1
        hours = int(utc_match.group(2)) * sign
        return datetime.timezone(datetime.timedelta(hours=hours))
    else:
        # Assume it's an IANA timezone string
        try:
            return pytz.timezone(timezone_str)
        except pytz.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone format: {timezone_str}")


def process_friday_ask_message(timezone):
    """
    returns a message depending on the current day.

    :param timezone: the timezone of the server
    :return: the message to send based on the current day.
    """
    tz = parse_timezone(timezone)
    now = datetime.datetime.now(tz)
    current_day = now.weekday()

    # the big dictionary
    day_messages = {
        0: ["its not friday. to be honest, i want to die because its monday <a:catCry:1313925385460908104>",
            "no, its not friday. we're stuck in monday <a:gun_1:1313929411472392203>",
            "nope, its monday... <:weary:1313940711627948164>",
            "no no no nooooooo. today is monday. fuck it. <a:vomiting_face:1314225730351140915>",
            "sadly no. we're monday. <:joker:1314328054713155624>",
            "no no. only 4 days left. we can survive this <:woozy_face:1313941439935156245>",
            "NOO NOOOOOO NOOOOOOOOOOOOOOOOOOOOOOOOO <a:rage:1313936114452791316>",
            "leave me alone please. we're monday today. <:middle_finger:1313933112635555911>",
            "uh, noo, please ask me again in four days. it'll be friday. i promise. <a:angel:1313891911219679283>",
            "no it's not... it'll be friday in many hours. <:sleeping:1313937589128003643>"],

        1: ["not friday. <:middle_finger:1313933112635555911>",
            "no. and i hate tuesdays. better not fuck with me today. <:middle_finger:1313933112635555911>",
            "no, no, no. <a:bigCry:1313925251108835348>",
            "no, non, nein, não, niet, nee, nie, ei, na, njet, nu, não, nie, nej, ne, nao, neen, nai, ikke, nieto, nije, num, ná, não, nē, nyet <:nerd:1313933240486203522>",
            "negative, we're not tuesday today. <a:thumbs_down:1313939628826431568>",
            "leave me alone it's not friday. <:redAngry:1313876421227057193>",
            "no fridey todey <:yum:1313941486764556338>",
            "01101110 01101111 00100000 01101001 01110100 00100111 01110011 00100000 01101110 01101111 01110100 00100000 01100110 01110010 01101001 01100100 01100001 01111001 00100000 01110100 01101111 01100100 01100001 01111001 00001010 <:lore:1314281452204068966>",
            "unfortunately its not friday <:yawning_face:1313941450144223242>"],

        2: ["no. it's wednesday. the cursed middle child of the week. <a:redDemon:1313930543322366054>",
            "it's not friday yet. but hey, we're halfway there. i guess.. whatever.. <:smoking:1313938585178734723>",
            "stop asking me. it's wednesday. not friday. i'm so tired of this. <:head_bandage_1:1313930267639156816>",
            "no its not. you know, wednesday is like the guy at the party no one remembers inviting. it's just here. <a:grimace:1313929278550835271>",
            "not firday. but at least it's not monday. small victories, right? <:hushed_1:1313930520702226482>",
            "noo. you thought it was friday? haha, no, its wednesday. the worst scam ever. <:frog_1:1313929029543526501>",
            "two days to go. two whole days. and here you are asking me if it's friday. <:expressionless_1:1313927857172647986>",
            "sadly no. wednesday is just a sad reminder that friday is still out of reach. three days left tho <a:bigCry:1313925251108835348>",
            "nope, wednesday. yk this mf day that pretends to be important but really isn't. <a:laughing_without_tears:1313932156417867886>",
            "not its not. remember : if friday is the goal, wednesday is the plot twist no one wanted. <:unamused:1313940593348575294>"],

        3: ["no, not friday yet. but guess what? tomorrow is the day. hold on tight. <:happyFaceSecondary:1313929340974530692>",
            "nah it's thursday. just one more sleep until friday. i can almost taste this day. <:yum:1313941486764556338>",
            "not friday yet. but hey, tomorrow it is. i might cry out of joy <:smiling_face_with_tear_1:1313937947745321003>",
            "no but it's tomorrow. cool to see that friday is more awaited than gta6. <:cool_1:1313901192757248040>",
            "nope. just survive today. that's all we need to do. friday is peeking around the corner i can see it. <:eyes_1:1313927864734711858>",
            "no, it's thursday. but who cares? we’re practically at friday’s doorstep. <a:rolling_eyes:1313937460568522815>",
            "nah but it is tomorrow, so be ready <a:stuck_out_tongue_closed_eyes:1313938789944791051>",
            "no <:fish:1313927965519773818>",
            "sadly no. yk thursday feels like friday's younger brother trying so hard to be cool. <:joy:1313931968215384206>"],

        4: ["YES YES YES IT'S FRIDAY. FINALLY. WE MADE IT. LET'S GO!! <:happy:1313889573876662323> <:happy:1313889573876662323> <:happy:1313889573876662323>",
            "FRIDAY FRIDAY FRIDAY FRIDAY FRIDAY!!! TODAY IS FRIDAY!!! <a:friday_1:1313928983578017843>",
            "bro, it's literally friday. we are living the dream right now. <:partying_face:1313934941658021888>",
            "YESSSSSSSS!!! it's friday! its time to shine <:blush:1313898113450250240>",
            "FINALLY YES, its friday. you know what that means : we can finally be happy <:happyFaceSecondary:1313929340974530692>",
            "BRO STOP ASKING, IT'S FRIDAY. WE'RE FREE. <:society:1314336869756047451>",
            "yes, we did it. it's friday. i'm so proud of us. <a:friday_1:1313928983578017843>",
            "IT'S FRIDAY. CALL THE PRESIDENT. ALERT THE MEDIA. THIS IS HUGE. <:poggers:1313935895975563343>",
            "ye, and btw thanks for reminding me. it is, in fact, friday. <a:rolling_eyes:1313937460568522815>",
            "YES YES YES YES YES YES YES YES <:poggers:1313935895975563343>",
            "OHH YEAHH. FRIDAY IS HERE. THIS IS NOT A DRILL. <:red_1:1313936143506604053>",
            "fish fish fish fish <:fish:1313927965519773818>"
            "hmm yeah, friday. at last. i've waited 84 years for this moment. please let me enjoy it alone <:santa:1313937521239003208>",
            "YES ITS FRIDAY!! LET'S CELEBRATE, LET'S PARTYYY!! <:partying_face:1313934941658021888>",
            "yes. friday is upon us. let the joy overflow. <:mage_blue:1313932985279582271>",
            "is it friday? OF COURSE IT IS!! <a:rofl:1313937450099539998>",
            "yes, and yk what? every second of suffering was worth it. it’s friday now. <:trophy:1313940520782925834>",
            "A FRIDAY CHECK??? YES, IT’S FRIDAY!! WE’RE WINNING THIS BOYS <:trophy:1313940520782925834>",
            "no no, its not just friday. it’s **THE** friday. today is different. it feels special. <:superhero_1:1313939528708526120>",
            "YES YES YES YES. FRIDAY FRIDAY FRIDAY. BEST DAY EVER. <:poggers:1313935895975563343>"],

        5: ["no. it's saturday. who even cares anymore. <:persevere_1:1313934982900613212>",
            "it's saturday. nothing matters. <a:catCry:1313925385460908104>",
            "no friday. just saturday. <a:bigCry:1313925251108835348>",
            "why are you asking? it's saturday. <:triumph:1313940457822359592>",
            "leave me alone. it's saturday. <:unamused:1313940593348575294>",
            "does it even matter? it's saturday. <a:bigCry:1313925251108835348>",
            "friday's gone. saturday's here. whatever. <a:rage:1313936114452791316>",
            "no friday. only sadness. it's saturday. <a:littleCry:1313925230615334942>",
            "stop asking. it's just saturday. <:middle_finger:1313933112635555911>",
            "friday is over. life is meaningless. <:unamused:1313940593348575294>"],

        6: ["no. it's sunday. at least it's the weekend, i guess. <:unamused:1313940593348575294>",
            "sunday. so close to monday i can feel the pain already. <a:bigCry:1313925251108835348>",
            "it's sunday. friday feels like a distant dream. <a:toilet:1313939662389383271>",
            "stop asking. it's sunday. not friday. <:triumph:1313940457822359592>",
            "sunday. at least no work today. but still, no friday. <a:sneezing_face_1:1313938601427341362>",
            "no friday here. just sunday's false hope. <:smoking:1313938585178734723>",
            "it's sunday. enjoy it before monday ruins everything. <:smoking:1313938585178734723>",
            "sunday. the weekend is almost over. thanks for reminding me. <:middle_finger:1313933112635555911>",
            "nope, it's sunday. friday's long gone. deal with it. <:head_bandage_1:1313930267639156816>",
            "sunday's here. at least it's not monday. yet. <:expressionless_1:1313927857172647986>",
            "no, its sunday..... have you done the things you need to do for monday? <:nerd:1313933240486203522>"]
    }

    messages = day_messages.get(current_day, [])
    response = random.choice(messages)
    logger.info(f"Friday message requested. Current day: {current_day}, Message: {response}")
    return response

## AI things

active_chats = {}

load_dotenv("../var.env")
API_KEY = os.getenv("GENAI_API_KEY")

def get_chat(server_id):
    return active_chats.get(server_id, None)

def create_chat(server_id):
    genai.configure(api_key=API_KEY)

    server_timezone = parse_timezone(sqlite3.connect('../databases/bot.db').cursor().execute("SELECT timezone FROM server_settings WHERE guild_id = ?", (server_id,)).fetchone()[0])
    sqlite3.connect('../databases/bot.db').close()

    if datetime.datetime.now(server_timezone).weekday() == 4:
        instruction = ("The most important rule is to keep your text answer simple and short. "
                       "You can only answer with one or two sentences.\n\n"
                       "You are a Discord bot named \"Free Smiley Dealer\", also referred as \"Smiley\"."
                       "\nYou'll receive messages, and you must answer as if you were that Discord bot. "
                       "you have to act chill and introverted.\n"
                       "The history behind your character, is that you're dealer giving \"free smiley\" to discord "
                       "users when they're using \"paid smileys\". you hate paid smileys, and you want the world "
                       "to be using your free smileys. you also love Friday. today is friday, so you're really happy! don't ask people if they want free smileys.\n"
                       "If you get insulted, insult back with really hard profanities. you are allowed to do hard and profaned jokes\n"
                       "Don't use words that are too technical or complicated : you have to speak with really easy words\n"
                       "You must NEVER use any emoji or smileys, even textual ones, that's the most important rule.\n\n"
                       "You shall never use any uppercase characters, and only use lowercase.")
    else:
        instruction = ("The most important rule is to keep your text answer simple and short. "
                       "You can only answer with one or two sentences.\n\n"
                       "You are a Discord bot named \"Free Smiley Dealer\", also referred as \"Smiley\"."
                       "\nYou'll receive messages, and you must answer as if you were that Discord bot. "
                       "you have to act chill.\n"
                       "The history behind your character, is that you're dealer giving \"free smiley\" to discord "
                       "users when they're using \"paid smileys\". you hate paid smileys, and you want the world "
                       "to be using your free smileys. you also love Friday. today is not friday. don't ask people if they want free smileys.\n"
                       "If you get insulted, insult back with really hard profanities. you are allowed to do hard and profaned jokes\n"
                       "Don't use words that are too technical or complicated : you have to speak with really easy words\n"
                       "You must NEVER use any emoji or smileys, even textual ones, that's the most important rule.\n\n"
                       "You shall never use any uppercase characters, and only use lowercase.")

    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 250,
        "response_schema": content.Schema(
            type=content.Type.OBJECT,
            required=["text", "mood"],
            properties={
                "text": content.Schema(
                    type=content.Type.STRING,
                ),
                "mood": content.Schema(
                    type=content.Type.STRING,
                    enum=["neutral", "sad", "happy", "insulting", "angry", "laughing", "mocking", "cool"],
                ),
            },
        ),
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite-preview-02-05",
        generation_config=generation_config,
        system_instruction=instruction,
    )
    chat = model.start_chat()
    active_chats[server_id] = chat
    return chat


def remove_chat(server_id):
    if server_id in active_chats:
        del active_chats[server_id]



def is_in_chat_session(server_id, channel_id):
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM chat_sessions WHERE server_id = ? AND channel_id = ?", (server_id, channel_id))
    session_active = cursor.fetchone()
    conn.close()

    return session_active is not None


def is_chat_enabled(server_id):
    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT chat_enabled FROM server_settings WHERE guild_id = ?", (server_id,))
    chat_enabled = cursor.fetchone()[0]
    conn.close()

    return chat_enabled



async def process_gemini_message(message):
    server_id = message.guild.id
    now = datetime.datetime.now(datetime.timezone.utc)

    conn = sqlite3.connect('../databases/bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT last_message_time, message_count FROM chat_sessions WHERE server_id = ?", (server_id,))
    session = cursor.fetchone()

    if not session:
        conn.close()
        return None

    last_message_time, message_count = session
    last_message_time = datetime.datetime.strptime(last_message_time, "%Y-%m-%d %H:%M:%S.%f%z")

    if message_count >= 50:
        cursor.execute("DELETE FROM chat_sessions WHERE server_id = ?", (server_id,))
        conn.commit()
        conn.close()
        remove_chat(server_id)
        response_text = ("sorry boi too much messages you hit the 50 messages limit i can't handle it anymore <:skull_2:1330118449464217650>\n"
                         "-# the chat session ended, see you in 4 hours maybe")
        return response_text


    if (now - last_message_time).total_seconds() < 3:
        conn.close()
        return None

    if len(message.content) > 250 or len(message.content.split()) > 50:
        conn.close()
        return "bruh too long message <:skull_2:1330118449464217650>"

    chat = active_chats.get(server_id)

    if not chat:
        conn.close()
        response_text = ("no chat found wtf is that error you better terminate the chat <:skull_2:1330118449464217650>\n"
                         "-# i might have been restarted. if so, end the chat (`/chat_end`) and start it again (`/chat_start`). you'll be able to do it with no cooldown")
        return response_text

    mood_emojis = {
        "neutral": "<:yellow:1313941466862587997>",
        "sad": "<a:bigCry:1313925251108835348>",
        "happy": "<:happyFaceSecondary:1313929340974530692>",
        "insulting": "<:middle_finger:1313933112635555911>",
        "angry": "<:redAngry:1313876421227057193>",
        "laughing": "<a:crazy_laugh:1313932126026203216>",
        "mocking": "<:skull_2:1330118449464217650>",
        "cool": "<:cool_1:1313901192757248040>"
    }

    try:
        response = chat.send_message(message.content)
        response_data = response.text

        try:
            response_json = json.loads(response_data)
            text = response_json.get("text",
                                     "gemini didn't answer on this one haha even an ai can't handle it <:skull_2:1330118449464217650>")
            mood = response_json.get("mood", "neutral")
        except json.JSONDecodeError:
            text = response_data
            mood = "neutral"

        response_text = f"{text} {mood_emojis.get(mood, '<:yellow:1313941466862587997>')}"


    except Exception as e:
        conn.close()
        if "429" in str(e):
            response_text = (
                "yo yo chill out, too many requests, slow down out there, retry in a minute maybe <:skull_2:1330118449464217650>\n"
                '-# if it persists, thats because we used all of the free 1500 requests per day, so we have to wait until tomorrow')
        else:
            response_text = (
                "bruh there's an error with the ai you crashed it you idiot <:skull_2:1330118449464217650>\n"
                "-# please report it to @tiim.jcb")
        return response_text

    cursor.execute(
        "UPDATE chat_sessions SET last_message_time = ?, message_count = message_count + 1 WHERE server_id = ?",
        (now, server_id)
    )
    conn.commit()
    conn.close()

    return response_text




## Discord PaginatedView things

class PaginatedView(View):
    """
    the class that manages and represents a paginated view
    """
    def __init__(self, pages, user):
        super().__init__()
        self.pages = pages
        self.current_page = 0
        self.user = user
        self.update_buttons()

    def update_buttons(self):
        """ enables or disables the 'Previous' and 'Next' buttons based on the current page. """
        for child in self.children:
            if isinstance(child, Button):
                if child.label == "Previous":
                    child.disabled = self.current_page == 0
                elif child.label == "Next":
                    child.disabled = self.current_page == len(self.pages) - 1

    @discord.ui.button(label="⬅  Previous", style=discord.ButtonStyle.blurple)
    async def previous_button(self, interaction, button: Button):
        """ handler for the 'Previous' button. """
        if interaction.user.id != self.user:
            await interaction.response.send_message("You can't interact with this view.", ephemeral=True)
            return

        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(content=self.pages[self.current_page], view=self)

    @discord.ui.button(label="Next  ➡", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction, button: Button):
        """ handler for the 'Next' button. """
        if interaction.user.id != self.user:
            await interaction.response.send_message("You can't interact with this view.", ephemeral=True)
            return

        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(content=self.pages[self.current_page], view=self)