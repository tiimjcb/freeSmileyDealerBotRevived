import datetime
import difflib
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

    # import the blacklisted triggers
    blacklisted_triggers = blacklisted_triggers_list(guild_id)

    # break the message into words -> we use the normalize_emoji() function to remove skin tone modifiers
    words = [normalize_emoji(word) for word in re.findall(r'\w+|[^\w\s]', message.content)]
    #logger.debug(f"Words: {words}")                # commented because it's useful for debugging. disabled on host.
    words = [word for word in merge_regional_indicators(words) if word.lower() not in blacklisted_triggers]
    #logger.debug(f"Processed words: {words}")      # idem
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
            logger.info(f"{user_name} in {guild_name} said the word '{word}' -> proper response sent (special trigger)")
            logger.debug(
                f"Special trigger found - ID: '{result[0]}', Trigger: '{result[1]}', Response: '{result[2]}', Is Emoji: '{result[3]}'")
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
            logger.info(f"{user_name} in {guild_name} said the word '{word}' -> Smiley sent")
            logger.debug(
                f"Regular trigger found - ID: '{result[0]}', Trigger: '{result[1]}', Response: '{result[2]}', Is Emoji: '{result[3]}'")
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


def process_friday_ask_message():
    """
    returns a message depending on the current day.
    :return: the message to send
    """

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
            "negative, we're not tuesday today. <a:thumbs_down:1313939628826431568>"
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
            "no <:fish:1313927965519773818>"
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
            "YES YES YES YES YES YES YES YES <:poggers:1313935895975563343>"
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
            "sunday's here. at least it's not monday. yet. <:expressionless_1:1313927857172647986>"]
    }

    current_day = datetime.datetime.now().weekday()
    messages = day_messages.get(current_day, [])
    return random.choice(messages)



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
