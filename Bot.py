from discord.ext import commands
import discord
import time
from Shuffle import Shuffle
import os

print("Connecting...")

commandPrefix = "$"
intents = discord.Intents(guild_messages=True, guilds=True, members=True, messages=True)
bot = commands.Bot(command_prefix=commandPrefix, intents=intents)
bot.RED = 0xff0000
bot.GREEN = 0x00ff00
bot.YELLOW = 0xffff00

bot.add_cog(Shuffle(bot, "./data"))

@bot.event
async def on_ready():
	print("Connected to Discord!")

@bot.command()
async def ping(ctx):
	embed1 = discord.Embed(title="Pinging...", description="You should only see this message for a moment.", color=bot.YELLOW)
	embed1.set_footer(text="Requested by {}.".format(ctx.message.author), icon_url=ctx.message.author.avatar_url)
	before = time.monotonic()
	message = await ctx.send(embed=embed1)
	ping = round((time.monotonic() - before) * 1000, 1)
	embed2 = discord.Embed(title=":ping_pong: Pong!", description="Latency: {0}ms\nAPI Latency: {1}ms".format(ping, round(bot.latency * 1000, 1)), color=bot.GREEN)
	embed2.set_footer(text="Requested by {}.".format(ctx.message.author), icon_url=ctx.message.author.avatar_url)
	await message.edit(embed=embed2)

with open("./token") as tokenFile:
	tokenFile.seek(0)
	token = tokenFile.read()
	bot.run(token)
