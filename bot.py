import discord
from discord.ext import commands
from dotenv import load_dotenv
import emoji
import os
import logging
from smiley_map import get_custom_smiley


### Logger configuration


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)




def return_last_emoji(text):
    """
    Return the last emoji of a string. If there is no emoji, it returns None
    """
    emojis_found = emoji.emoji_list(text)
    return emojis_found[-1]['emoji'] if emojis_found else None


# get the token
load_dotenv("token.env")
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("There is no token!")


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix=">", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot loaded and connected as {bot.user} !")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    last_emoji = return_last_emoji(message.content)
    if last_emoji:
        guild_id = message.guild.id if message.guild else "DM"
        user_name = message.author.name

        try:
            free_smiley = get_custom_smiley(last_emoji)
            await message.channel.send(free_smiley)

            logger.info(
                f"[GUILD : {guild_id}] - [USER : {user_name}] - "
                f"The emoji {last_emoji} has been detected -- matching smiley sent."
            )
        except ValueError:
            logger.warning(
                f"[GUILD : {guild_id}] - [USER : {user_name}] - "
                f"The emoji {last_emoji} has been detected, but it is not referenced in the database :("
            )


bot.run(TOKEN)
