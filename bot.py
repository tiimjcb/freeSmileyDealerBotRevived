import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
import emoji
import re
from smiley_map import unicode_to_custom_smiley

# logger configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)




def normalize_emoji(emoji):
    """
    Supprime les modificateurs de couleur de peau d'un emoji.
    """
    # Regex pour détecter les modificateurs de couleur (U+1F3FB à U+1F3FF)
    skin_tone_modifiers = re.compile(r'[\U0001F3FB-\U0001F3FF]')
    return skin_tone_modifiers.sub('', emoji)


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
        return None

    # we go through all the emojis in the message - in a reverse way
    for emoji_entry in reversed(emojis_found):
        unicode_emoji = emoji_entry['emoji']
        normalized_emoji = normalize_emoji(unicode_emoji)  # Normaliser l'emoji

        if normalized_emoji in emoji_map:
            logger.info(
                f"[GUILD : {guild_id}] - [USER : {user_name}] - "
                f"Emoji '{unicode_emoji}' detected (normalized to '{normalized_emoji}'). Matching smiley sent."
            )
            return emoji_map[normalized_emoji]

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
