import asyncio
import discord
import nacl #upm package(pynacl)
from discord.ext import commands
from decouple import config
import utils
import validators
from keep_alive import keep_alive

client = commands.Bot(command_prefix='*')


@client.event
async def on_ready():
  print('Logged in as {0.user}'.format(client))


@client.event
async def on_voice_state_update(member, before, after):
  # Check if not a bot, is not in blacklist, has fanfare enabled, and has moved to a channel
  if not member.bot and str(member.id) not in utils.get_blacklist(member.guild) and utils.get_data(member.guild, member, "enabled") != "false" and after.channel is not None and before.channel != after.channel:
    print("Detected {0} joined {1} in {2}".format(member, after.channel, member.guild))
    await utils.play_audio(member, after.channel)


@client.command()
async def fanfare(context, url, start = None, length = None):
  msg = ""
  # check if url is a valid URL
  if validators.url(url):
    msg += "Successfully added new fanfare for {0.mention}"
    utils.set_data(context.guild, context.author, "url", url)
    # Check if start can be converted to a float and greater than zero
    if start and (start.isnumeric() or start.replace('.', '', 1).isdigit()) and float(start) >= 0:
      utils.set_data(context.guild, context.author, "start", start)
      msg += " starting at " + start + " seconds"

      # Check if length can be converted to a float and greater than zero
      if length and (length.isnumeric() or length.replace('.', '', 1).isdigit()) and float(length) >= 0:
        utils.set_data(context.guild, context.author, "length", length)
        msg += " and lasting " + length + " seconds"
      else:
        utils.set_data(context.guild, context.author, "length", None)
    else:
      utils.set_data(context.guild, context.author, "start", None)
      utils.set_data(context.guild, context.author, "length", None)

    await context.send(msg.format(context.author))
    print("Added new fanfare for: {0.name}".format(context.author))
  else:
    await context.send("Not a valid URL")   
    return         


@client.command()
async def play(context):
  if not context.author.voice:
    await context.send("You are not in a voice channel")
    return
  if utils.get_data(context.guild, context.author, "enabled") == "false":
    await context.send("You do not have fanfare enabled, use \'*enable\' to enable it")
    return
  if str(context.author.id) not in utils.get_blacklist(context.guild):
    await context.send("Playing {0}'s fanfare".format(context.author.mention))
    await utils.play_audio(context.author, context.author.voice.channel)


@client.command()
async def blacklist(context):
  if str(context.author.id) in utils.get_blacklist(context.guild):
    return
  permissions = context.author.guild_permissions
  if permissions.mute_members or permissions.administrator:
    guild_blacklist = utils.get_blacklist(context.guild)
    for user in context.message.mentions:
      if str(user.id) not in guild_blacklist:
        guild_blacklist.append(str(user.id))
        await context.send("Added {0} to the blacklist".format(user.mention))
    utils.save_data()


@client.command()
async def whitelist(context):
  if str(context.author.id) in utils.get_blacklist(context.guild):
    return
  permissions = context.author.guild_permissions
  if permissions.mute_members or permissions.administrator:
      guild_blacklist = utils.get_blacklist(context.guild)
      for user in context.message.mentions:
        if str(user.id) in guild_blacklist:
          guild_blacklist.remove(str(user.id))
          await context.send("Removed {0} to the blacklist".format(user.mention))
      utils.save_data()


@client.command()
async def disable(context):
  if utils.get_data(context.guild, context.author, "enabled") != "false":
    utils.set_data(context.guild, context.author, "enabled", "false")
    print("Disabling for {0}".format(context.author))
    await context.send("Disabled fanfare for {0}".format(context.author.mention))


@client.command()
async def enable(context):
  if utils.get_data(context.guild, context.author, "enabled") == "false":
    utils.set_data(context.guild, context.author, "enabled", "true")
    print("Enabling for {0}".format(context.author))
    await context.send("Enabled fanfare for {0}".format(context.author.mention))


keep_alive()
client.run(config('TOKEN'))
