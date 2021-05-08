from discord.ext import commands
import discord
import json
import os
import asyncio
import time
import random
import traceback
import sys


def isGuildOwner():
    def predicate(ctx):
        return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id
    return commands.check(predicate)


class Shuffle(commands.Cog):
	def __init__(self, bot, configFolder="./data"):
		self.bot = bot
		self._configFolder = configFolder
		self._configs = {}
		self._loadConfigs()

	def _loadConfigs(self):
		try:
			servers = os.listdir(self._configFolder)
			for server in servers:
				if server[-5:] != ".json":
					continue
				config = self._loadConfig(server)
				self._configs[config["id"]] = config
		except FileNotFoundError:
			os.mkdir("./data")

	def _loadConfig(self, configFilePath):
		with open("{}/{}".format(self._configFolder, configFilePath)) as configFile:
			config = json.load(configFile)
			print("Loaded config for {}.".format(config["id"]))
			return config

	async def _updateLoop(self):
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
				await member.send("You have less than one hour remaining of time as admin, time is ticking!")
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
			if adminRole in member.roles:
				await member.remove_roles(adminRole, reason="End of admin time.")
				await member.send("Unfortunately your time as admin has ended. Your chances of getting admin again are the same so be ready!")
			potentialAdmins.append(member)
		adminCount = self.getAdminCount(server)
		# Select and apply new admins
		newAdmins = random.sample(potentialAdmins, adminCount)
		for newAdmin in newAdmins:
			await newAdmin.add_roles(adminRole, reason="Admin swap choice!")
			config = self.getConfig(server)
			await newAdmin.send("You were randomly selected to be the next admin! You have {} hours, make it count!".format(config["swapTime"]))
		# Reset swap time
		nextSwap = time.time() + (int(config["swapTime"])*86400)
		self.setConfigValue(server, "nextSwap", nextSwap)
		# Reset warned flag
		self.setConfigValue(server, "warned", False)

	def getAdminCount(self, server):
		config = self._configs[str(server.id)]
		return min(int(config["maxAdmins"]), max(int(config["minAdmins"]), int(len(server.members)/int(config["adminRatio"]))))

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
		config = self.getConfig(server)
		config[key] = value
		self._configs[str(server)] = config
		with open("{}/{}.json".format(self._configFolder, str(server.id)), "w") as configFile:
			json.dump(config, configFile, indent=4)

	def initConfig(self, server):
		with open("./default_config.json") as defaultFile:
			default = json.load(defaultFile)
			id = str(server.id)
			default["id"] = id
			self._configs[id] = default
			with open("{}/{}.json".format(self._configFolder, id), "x") as configFile:
				json.dump(default, configFile, indent=4)
			return default
	
	@commands.Cog.listener()
	async def on_ready(self):
		await self._updateLoop()

	# Config commands
	@isGuildOwner()
	@commands.command()
	async def toggle(self, ctx):
		config = self.getConfig(ctx.guild)
		self.setConfigValue(ctx.guild, "enabled", not config["enabled"])
		config = self.getConfig(ctx.guild)
		await ctx.send("Admin swapping is now {}".format("enabled. Swaps will happen every {} hours.".format(config["swapTime"]) if config["enabled"] else "disabled."))

	@isGuildOwner()
	@commands.command()
	async def setmin(self, ctx, minimum:int):
		self.setConfigValue(ctx.guild, "minAdmins", minimum)
		await ctx.send("Minimum admin number is now {}. With these settings there will be {} admins next swap.".format(minimum, self.getAdminCount(ctx.guild)))

	@isGuildOwner()
	@commands.command()
	async def setmax(self, ctx, maximum:int):
		self.setConfigValue(ctx.guild, "maxAdmins", maximum)
		await ctx.send("Maximum admin number is now {}. With these settings there will be {} admins next swap.".format(maximum, self.getAdminCount(ctx.guild)))

	@isGuildOwner()
	@commands.command()
	async def setratio(self, ctx, ratio:int):
		self.setConfigValue(ctx.guild, "adminRatio", ratio)
		await ctx.send("The admin-member ratio is now 1:{}. With these settings there will be {} admins next swap.".format(ratio, self.getAdminCount(ctx.guild)))

	@isGuildOwner()
	@commands.command()
	async def setadmin(self, ctx, role:discord.Role):
		self.setConfigValue(ctx.guild, "adminRole", str(role.id))
		await ctx.send("The admin role is now {}. These settings will be applied next swap.".format(role.mention))

	@isGuildOwner()
	@commands.command()
	async def settime(self, ctx, hours:int):
		self.setConfigValue(ctx.guild, "swapTime", hours)
		await ctx.send("After the next swap, the swap delay will be {} hours.".format(hours))

	@isGuildOwner()
	@commands.command()
	async def ignoredroles(self, ctx):
		config = self.getConfig(ctx.guild)
		ignoreList = config["ignoreRoles"]
		await ctx.send("Here are the ignore roles:\n{}\nThese roles will not be reset at the end of each swap and anyone with them cannot be chosen for admin.".format(", ".join(ctx.guild.get_role(int(role)).mention for role in ignoreList) or None))

	@isGuildOwner()
	@commands.command()
	async def ignore(self, ctx, role:discord.Role):
		config = self.getConfig(ctx.guild)
		if config["ignoreRoles"] is None:
			config["ignoreRoles"] = []
		config["ignoreRoles"].append(str(role.id))
		self.setConfigValue(ctx.guild, "ignoreRoles", config["ignoreRoles"])
		await ctx.send("{} has been added to the ignore list. Ignored roles will not be reset at the end of each swap and anyone with them cannot be chosen for admin.".format(role.mention))

	@isGuildOwner()
	@commands.command()
	async def unignore(self, ctx, role:discord.Role):
		config = self.getConfig(ctx.guild)
		config["ignoreRoles"].remove(str(role.id))
		self.setConfigValue(ctx.guild, "ignoreRoles", config["ignoreRoles"])
		await ctx.send("{} has been removed from the ignore list.".format(role.mention))

	@isGuildOwner()
	@commands.command()
	async def setstr(self, ctx, key:str, value:str):
		self.setConfigValue(ctx.guild, key, value)
		await ctx.send("Set {} to {} in config. It is not reccomended to use this command unless necessary.".format(key, value))

	@isGuildOwner()
	@commands.command()
	async def setbool(self, ctx, key:str, value:bool):
		self.setConfigValue(ctx.guild, key, value)
		await ctx.send("Set {} to {} in config. It is not reccomended to use this command unless necessary.".format(key, value))

	@isGuildOwner()
	@commands.command()
	async def setint(self, ctx, key:str, value:int):
		self.setConfigValue(ctx.guild, key, value)
		await ctx.send("Set {} to {} in config. It is not reccomended to use this command unless necessary.".format(key, value))

	@isGuildOwner()
	@commands.command()
	async def getval(self, ctx, key:str):
		config = self.getConfig(ctx.guild)
		await ctx.send("Value for {} is {} in config.".format(config[key]))

	@isGuildOwner()
	@commands.command()
	async def reloadconf(self, ctx):
		self._loadConfigs()
		await ctx.send("Reloaded configs!")

	@isGuildOwner()
	@commands.command()
	async def swap(self, ctx):
		self.swapAdmins(ctx.guild)

	# Info commands
	@commands.command()
	async def timeleft(self, ctx):
		config = self.getConfig(ctx.guild)
		timeUntilSwap = config["nextSwap"] - time.time()
		hours = int(timeUntilSwap / 3600)
		minutes = int(timeUntilSwap % 3600 / 60)
		await ctx.send("The next swap will occur in {} hours and {} minutes.".format(hours, minutes))
