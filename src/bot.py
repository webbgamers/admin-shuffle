from discord.ext import commands
import discord
from shuffle import Shuffle

print("Connecting...")

commandPrefix = "$"
intents = discord.Intents(guild_messages=True, guilds=True, members=True, messages=True)
bot = commands.Bot(command_prefix=commandPrefix, intents=intents)
bot.RED = 0xff0000
bot.GREEN = 0x00ff00
bot.YELLOW = 0xffff00

bot.remove_command("help")
bot.add_cog(Shuffle(bot, "./data"))

@bot.event
async def on_ready():
	print("Connected to Discord!")

with open("./token") as tokenFile:
	tokenFile.seek(0)
	token = tokenFile.read()
	bot.run(token)
