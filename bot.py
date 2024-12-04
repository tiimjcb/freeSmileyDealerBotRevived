import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
import emoji
from smiley_map import unicode_to_custom_smiley

# logger configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)



def process_message_for_smiley(message, emoji_map):
    """
    return the smiley of the last emoji in a string that has an occurence in the dictionnary.
    if no emoji is in the string, or if none of the emojis in the string have an occurence, it returns None.
    """
    # grad the guild and the username -- logging purposes
    guild_id = message.guild.id if message.guild else "DM"
    user_name = message.author.name

    emojis_found = emoji.emoji_list(message.content)

    # first breakpoint : there is no emojis in the message
    if not emojis_found:
        logger.error(
            f"[GUILD : {guild_id}] - [USER : {user_name}] - No emojis found in the message."
        )
        return None

    # we go through all the emojis in the message - in a reverse way
    for emoji_entry in reversed(emojis_found):
        unicode_emoji = emoji_entry['emoji']
        if unicode_emoji in emoji_map:
            logger.info(
                f"[GUILD : {guild_id}] - [USER : {user_name}] - "
                f"Emoji '{unicode_emoji}' detected. Matching smiley sent."
            )
            return emoji_map[unicode_emoji]

    # last breakpoint : no matches detected
    logger.warning(
        f"[GUILD : {guild_id}] - [USER : {user_name}] - "
        f"Emoji(s) detected but none matched the database."
    )
    return None



# get the token
load_dotenv("token.env")
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("There is no token!")



# basic bot configuration
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix=">", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot loaded and connected as {bot.user} !")



# main program
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    free_smiley = process_message_for_smiley(message, unicode_to_custom_smiley)
    if free_smiley:
        await message.channel.send(free_smiley)


bot.run(TOKEN)
