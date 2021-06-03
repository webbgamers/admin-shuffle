from discord.ext import commands
import discord
import json
import os
import asyncio
import time
import random
import traceback
import sys
import ast


# Check to test if invoker is guild owner
def isGuildOwner():
	def predicate(ctx):
		return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id
	return commands.check(predicate)


class Shuffle(commands.Cog):
	def __init__(self, bot, configFolder="./data"):
		self.bot = bot
		self._configFolder = configFolder
		self._loadConfigs()

	# Load all configs from file
	def _loadConfigs(self):
		self._configs = {}
		try:
			servers = os.listdir(self._configFolder)
			for server in servers:
				if server[-5:] != ".json":
					continue
				config = self._loadConfig(server)
				self._configs[config["id"]] = config
		except FileNotFoundError:
			os.mkdir("./data")

	# Load single config from file
	def _loadConfig(self, configFilePath):
		with open("{}/{}".format(self._configFolder, configFilePath)) as configFile:
			config = json.load(configFile)
			print("Loaded config for {}.".format(config["id"]))
			return config

	async def _updateLoop(self):
		print("Starting update loop.")
		while True:
			try:
				# Extract all configs for enabled servers
				enabledConfigs = []
				for config in self._configs:
					config = self._configs[config]
					if config["enabled"]:
						enabledConfigs.append(config)
				for config in enabledConfigs:
					# Warn current admins if there is less than an hour left
					if config["nextSwap"] - time.time() <= 3600 and not config["warned"]:
						server = self.bot.get_guild(int(config["id"]))
						await self.warnAdmins(server)
					# Swap admins if time is up
					if time.time() > config["nextSwap"]:
						server = self.bot.get_guild(int(config["id"]))
						await self.swapAdmins(server)
			except:
				print('Ignoring exception in shuffle update loop:', file=sys.stderr)
				traceback.print_exc()
			await asyncio.sleep(10)

	async def warnAdmins(self, server):
		config = self.getConfig(server)
		adminRole = server.get_role(int(config["adminRole"]))
		members = server.members
		for member in members:
			if adminRole in member.roles:
				try:
					await member.send("You have less than one hour remaining of time as admin, time is ticking!")
				except:
					print("Failed to send message to {}.".format(member.id))
		self.setConfigValue(server, "warned", True)

	async def swapAdmins(self, server):
		print("Swapping admins on {}!".format(server.id))
		config = self.getConfig(server)
		# Remove extra permissions from roles
		await self.stripRoles(server)
		adminRole = server.get_role(int(config["adminRole"]))
		members = server.members
		potentialAdmins = []
		# Remove current admin and get list of potential admins
		for member in members:
			roleIds = []
			for role in member.roles:
				roleIds.append(str(role.id))
			# Ignore members with role in ignore list or who are bots
			if any(role in roleIds for role in config["ignoreRoles"]) or member.bot:
				continue
			# Remove admin from members and prevent someone from getting it twice in a row
			if adminRole in member.roles:
				await member.remove_roles(adminRole, reason="End of admin time.")
				try:
					await member.send("Unfortunately your time as admin has ended. Your can't get admin twice in a row but after that you are fair game so be ready!")
				except:
					print("Failed to send message to {}.".format(member.id))
				continue
			potentialAdmins.append(member)
		adminCount = self.getAdminCount(server)
		# Select and apply new admins
		newAdmins = random.sample(potentialAdmins, adminCount)
		for newAdmin in newAdmins:
			await newAdmin.add_roles(adminRole, reason="Admin swap choice!")
			config = self.getConfig(server)
			try:
				await newAdmin.send("You were randomly selected to be the next admin! You have {} hours, make it count!".format(config["swapTime"]))
			except:
					print("Failed to send message to {}.".format(newAdmin.id))
		# Reset swap time
		nextSwap = time.time() + (int(config["swapTime"])*3600)
		self.setConfigValue(server, "nextSwap", nextSwap)
		# Reset warned flag
		self.setConfigValue(server, "warned", False)

	# Calculate number of admins with current settings
	def getAdminCount(self, server):
		config = self._configs[str(server.id)]
		return min(int(config["maxAdmins"]), max(int(config["minAdmins"]), int(len(server.members)/int(config["adminRatio"]))))

	# Remove permissions from non admin/ignored roles
	async def stripRoles(self, server):
		config = self.getConfig(server)
		standardPermissions = discord.Permissions(view_channel=True, view_audit_log=True, create_instant_invite=True, change_nickname=True, send_messages=True, embed_links=True, attach_files=True, add_reactions=True, use_external_emojis=True, read_message_history=True, use_slash_commands=True, connect=True, speak=True, stream=True, use_voice_activation=True)
		server = self.bot.get_guild(int(server.id))
		roles = server.roles
		for role in roles:
			if str(role.id) in config["ignoreRoles"] or str(role.id) == config["adminRole"]:
				continue
			if role.permissions != standardPermissions:
				await role.edit(permissions=standardPermissions, reason="Permissions reset at end of admin swap.")

	def getConfig(self, server):
		id = str(server.id)
		# Attempt to find config in loaded config list
		try:
			config = self._configs[id]
			return config
		except KeyError:
			# Attempt to load config from file 
			try:
				config = self._loadConfig("{}.json".format(id))
				return config
			except FileNotFoundError:
				# Initialize config file from defaults
				config = self.initConfig(server)
				return config

	def setConfigValue(self, server, key, value):
		# Update loaded configs
		config = self.getConfig(server)
		config[key] = value
		self._configs[str(server.id)] = config
		# Update saved configs
		with open("{}/{}.json".format(self._configFolder, str(server.id)), "w") as configFile:
			json.dump(config, configFile, indent=4)

	# Create config from default settings
	def initConfig(self, server):
		with open("./src/default_config.json") as defaultFile:
			default = json.load(defaultFile)
			id = str(server.id)
			default["id"] = id
			self._configs[id] = default
			with open("{}/{}.json".format(self._configFolder, id), "x") as configFile:
				json.dump(default, configFile, indent=4)
			return default
	
	# Start update loop on initial bot connection
	@commands.Cog.listener()
	async def on_ready(self):
		self.bot.remove_listener(self.on_ready)
		await self._updateLoop()

	# Config commands
	# Enable/disable swapping
	@isGuildOwner()
	@commands.command()
	async def toggle(self, ctx):
		config = self.getConfig(ctx.guild)
		self.setConfigValue(ctx.guild, "enabled", not config["enabled"])
		config = self.getConfig(ctx.guild)
		await ctx.send("Admin swapping is now {}".format("enabled. Swaps will happen every {} hours.".format(config["swapTime"]) if config["enabled"] else "disabled."))

	# Set minimum admins
	@isGuildOwner()
	@commands.command()
	async def setmin(self, ctx, minimum:int):
		self.setConfigValue(ctx.guild, "minAdmins", minimum)
		await ctx.send("Minimum admin number is now {}. With these settings there will be {} admins next swap.".format(minimum, self.getAdminCount(ctx.guild)))

	# Set maximum admins
	@isGuildOwner()
	@commands.command()
	async def setmax(self, ctx, maximum:int):
		self.setConfigValue(ctx.guild, "maxAdmins", maximum)
		await ctx.send("Maximum admin number is now {}. With these settings there will be {} admins next swap.".format(maximum, self.getAdminCount(ctx.guild)))

	# Set set admin-member ratio
	@isGuildOwner()
	@commands.command()
	async def setratio(self, ctx, ratio:int):
		self.setConfigValue(ctx.guild, "adminRatio", ratio)
		await ctx.send("The admin-member ratio is now 1:{}. With these settings there will be {} admins next swap.".format(ratio, self.getAdminCount(ctx.guild)))

	# Set admin role
	@isGuildOwner()
	@commands.command()
	async def setadmin(self, ctx, role:discord.Role):
		self.setConfigValue(ctx.guild, "adminRole", str(role.id))
		await ctx.send("The admin role is now {}. These settings will be applied next swap.".format(role.mention), allowed_mentions=discord.AllowedMentions.none())

	# Set time between swaps
	@isGuildOwner()
	@commands.command()
	async def settime(self, ctx, hours:int):
		self.setConfigValue(ctx.guild, "swapTime", hours)
		await ctx.send("After the next swap, the swap delay will be {} hours.".format(hours))

	# List ignored roles
	@isGuildOwner()
	@commands.command()
	async def ignoredroles(self, ctx):
		config = self.getConfig(ctx.guild)
		ignoreList = config["ignoreRoles"]
		await ctx.send("Here are the ignored roles:\n{}\nThese roles will not be reset at the end of each swap and anyone with them cannot be chosen for admin.".format(", ".join("<@&{}>".format(role) for role in ignoreList) or None), allowed_mentions=discord.AllowedMentions.none())

	# Add role to ignore list
	@isGuildOwner()
	@commands.command()
	async def ignore(self, ctx, role:discord.Role):
		config = self.getConfig(ctx.guild)
		if config["ignoreRoles"] is None:
			config["ignoreRoles"] = []
		config["ignoreRoles"].append(str(role.id))
		self.setConfigValue(ctx.guild, "ignoreRoles", config["ignoreRoles"])
		await ctx.send("{} has been added to the ignore list. Ignored roles will not be reset at the end of each swap and anyone with them cannot be chosen for admin.".format(role.mention), allowed_mentions=discord.AllowedMentions.none())

	# Remove role from ignore list
	@isGuildOwner()
	@commands.command()
	async def unignore(self, ctx, role:discord.Role):
		config = self.getConfig(ctx.guild)
		config["ignoreRoles"].remove(str(role.id))
		self.setConfigValue(ctx.guild, "ignoreRoles", config["ignoreRoles"])
		await ctx.send("{} has been removed from the ignore list.".format(role.mention), allowed_mentions=discord.AllowedMentions.none())

	# Manualy set config value (string)
	@isGuildOwner()
	@commands.command()
	async def setstr(self, ctx, key:str, value:str):
		self.setConfigValue(ctx.guild, key, value)
		await ctx.send("Set {} to {} in config. It is not reccomended to use this command unless necessary.".format(key, value))

	# Manualy set config value (boolean)
	@isGuildOwner()
	@commands.command()
	async def setbool(self, ctx, key:str, value:bool):
		self.setConfigValue(ctx.guild, key, value)
		await ctx.send("Set {} to {} in config. It is not reccomended to use this command unless necessary.".format(key, value))

	# Manualy set config value (integer)
	@isGuildOwner()
	@commands.command()
	async def setint(self, ctx, key:str, value:int):
		self.setConfigValue(ctx.guild, key, value)
		await ctx.send("Set {} to {} in config. It is not reccomended to use this command unless necessary.".format(key, value))

	# Manually get config value
	@isGuildOwner()
	@commands.command()
	async def getval(self, ctx, key:str):
		config = self.getConfig(ctx.guild)
		await ctx.send("Value for {} is {} in config.".format(key, config[key]))

	# Reload configs from disk
	@isGuildOwner()
	@commands.command()
	async def reloadconf(self, ctx):
		self._loadConfigs()
		await ctx.send("Reloaded configs!")

	# Manually do swap
	@isGuildOwner()
	@commands.command()
	async def swap(self, ctx):
		await self.swapAdmins(ctx.guild)

	# Info commands
	# Get time remaining on current swap
	@commands.command()
	async def timeleft(self, ctx):
		config = self.getConfig(ctx.guild)
		timeUntilSwap = config["nextSwap"] - time.time()
		hours = int(timeUntilSwap / 3600)
		minutes = int(timeUntilSwap % 3600 / 60)
		await ctx.send("The next swap will occur in {} hours and {} minutes.".format(hours, minutes))

	# Help command
	@commands.command()
	async def help(self, ctx):
		isOwner = ctx.guild.owner_id == ctx.author.id
		embed = discord.Embed(title="Admin Swap Help", description="Basic usage is `$command`.", color=0x7289da)
		embed.add_field(name="General Commands", value="`ping` - Tests the latency between the bot and discord.\n" + 
		"`timeleft` - Get the time until the next swap.\n" +
		"`help` - How to use this bot.", inline=False)
		if isOwner:
			embed.add_field(name="Config Commands", value="`toggle` - Enable/disable admin swapping.\n" + 
			"`setmin <minimum>` - Set the minimum number of admins.\n" +
			"`setmax <maximum>` - Set the maximum number of admins.\n" +
			"`setratio <members per admin>` - Set the member-admin ratio.\n" +
			"`setadmin <role>` - Set the role to use as the admin role.\n" +
			"`settime <hours>` - Set the time between swaps.\n" +
			"`ignore <role>` - Add a role to the list of ignored roles.\n" +
			"`unignore <role>` - Remove a role from the list of ignored roles.\n" +
			"`ignoredroles` - Get the list of ignored roles.\n" +
			"`swap` - Manually initiate a swap.", inline=False)
		await ctx.send(embed=embed)

	# Ping command
	@commands.command()
	async def ping(self, ctx):
		before = time.monotonic()
		message = await ctx.send("Pinging...")
		ping = round((time.monotonic() - before) * 1000, 1)
		await message.edit(content=":ping_pong: **Pong!**\nLatency: {}\nAPI Latency: {}".format(ping, round(self.bot.latency * 1000, 1)))

	# Exec command
	# VERY BUGGY
	@commands.is_owner()
	@commands.command()
	async def exec(self, ctx, *, code):
		before = time.monotonic()
		try:
			print("attemting as normal code")
			eval(compile(code, "<string>", mode="exec"))
		except SyntaxError:
			try:
				print("attempting as async code")
				await eval(compile(code, "<string>", mode="exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT))
			except:
				await ctx.send("Error: {}".format(sys.exc_info[0]))
		except:
			await ctx.send("Error: {}".format(sys.exc_info[0]))
				
		exec_time = before - time.monotonic()