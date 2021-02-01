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


class Fanfare(commands.Cog):
  
  @commands.command()
  async def fanfare(self, ctx, yt_url, start = None, length = None):
    '''
    Sets the fanfare for the user.
    Parameters:
      yt_url: a valid URL to a Youtube video.
      start: the starting time of the fanfare in seconds.
      length: the duration of the fanfare in seconds.
    '''
    msg = ""
    # check if url is a valid URL
    if validators.url(yt_url):
      msg += "Successfully added new fanfare for {0.mention}"
      await utils.set_data(ctx.guild, ctx.author, "url", yt_url)
      # Check if start can be converted to a float and greater than zero
      if start and (start.isnumeric() or start.replace('.', '', 1).isdigit()) and float(start) >= 0:
        await utils.set_data(ctx.guild, ctx.author, "start", start)
        msg += " starting at " + start + " seconds"

        # Check if length can be converted to a float and greater than zero
        if length and (length.isnumeric() or length.replace('.', '', 1).isdigit()) and float(length) >= 0:
          await utils.set_data(ctx.guild, ctx.author, "length", length)
          msg += " and lasting " + length + " seconds"
        else:
          await utils.set_data(ctx.guild, ctx.author, "length", None)
      else:
        await utils.set_data(ctx.guild, ctx.author, "start", None)
        await utils.set_data(ctx.guild, ctx.author, "length", None)

      # embed = discord.Embed(description = )
      msg += "."
      await utils.send_embed(ctx, msg.format(ctx.author), color = 0x009900)
      print("Added new fanfare for: {0.name}".format(ctx.author))
    else:
      await utils.send_embed(ctx, f"{yt_url} is not a valid URL!", color = 0xff0000) 
      return         


  @commands.command()
  async def play(self, ctx):
    '''
    Plays the fanfare of the user.
    Requires that the user be in a voice channel.
    '''
    if not ctx.author.voice:
      await utils.send_embed(ctx, "You are not in a voice channel!", color = 0xff0000)
      return
    # if utils.get_data(context.guild, context.author, "enabled") == "false":
    #   await utils.send_embed(context,"You do not have fanfare enabled! Use \'*enable\' to enable it.", color = 0xff0000)
    #   return
    if str(ctx.author.id) not in utils.get_blacklist(ctx.guild):
      await utils.send_embed(ctx, "Playing {0}'s fanfare.".format(ctx.author.mention))
      await utils.play_audio(ctx.author, ctx.author.voice.channel)
    else:
      await utils.send_embed(ctx, "You are blacklisted and cannot play fanfare.", color = 0)


class AdminSettings(commands.Cog):

  @commands.command()
  async def blacklist(self, ctx):
    '''
    Blacklists any mentioned members.
    This prevents them from playing their fanfare.
    The user must either have server mute permissions or be an administrator.
    The user must also not be blacklisted.
    '''
    if str(ctx.author.id) in utils.get_blacklist(ctx.guild):
      await utils.send_embed(ctx, "You are blacklisted and cannot change the blacklist.", color = 0)
      return
    permissions = ctx.author.guild_permissions
    if permissions.mute_members or permissions.administrator:
      guild_blacklist = utils.get_blacklist(ctx.guild)
      if len(ctx.message.mentions) == 0:
        await utils.send_embed(ctx, "There is no one mentioned. Use @ to mention someone.", color = 0xff0000)
        return
      for user in ctx.message.mentions:
        if str(user.id) not in guild_blacklist:
          guild_blacklist.append(str(user.id))
          await utils.send_embed(ctx, "Added {0} to the blacklist.".format(user.mention), color = 0)
      await utils.save_data()
    else:
      await utils.send_embed(ctx, "You do not have permission to blacklist members.", color = 0xff0000)


  @commands.command()
  async def whitelist(self, ctx):
    '''
    Whitelists any mentioned members.
    This allows them to play their fanfare.
    The user must either have server mute permissions or be an administrator.
    The user must also not be blacklisted.
    '''
    if str(ctx.author.id) in utils.get_blacklist(ctx.guild):
      await utils.send_embed(ctx, "You are blacklisted and cannot change the blacklist.", color = 0)
      return
    permissions = ctx.author.guild_permissions
    if permissions.mute_members or permissions.administrator:
        guild_blacklist = utils.get_blacklist(ctx.guild)
        if len(ctx.message.mentions) == 0:
          await utils.send_embed(ctx, "There is no one mentioned. Use @ to mention someone.", color = 0xff0000)
          return
        for user in ctx.message.mentions:
          if str(user.id) in guild_blacklist:
            guild_blacklist.remove(str(user.id))
            await utils.send_embed(ctx, "Removed {0} to the blacklist.".format(user.mention), color = 0xffffff)
        await utils.save_data()
    else:
      await utils.send_embed(ctx, "You do not have permission to whitelist members.", color = 0xff0000)     


class UserSettings(commands.Cog):
  
  @commands.command()
  async def disable(self, ctx):
    '''
    Disables the user's fanfare.
    Makes it so that fanfare will not play when they join a voice channel.
    '''
    if utils.get_data(ctx.guild, ctx.author, "enabled") != "false":
      await utils.set_data(ctx.guild, ctx.author, "enabled", "false")
      print("Disabling for {0}".format(ctx.author))
      await utils.send_embed(ctx, "Disabled fanfare for {0}.".format(ctx.author.mention))


  @commands.command()
  async def enable(self, ctx):
    '''
    Enables the user's fanfare.
    Makes it so that fanfare will play when they join a voice channel.
    '''
    if utils.get_data(ctx.guild, ctx.author, "enabled") == "false":
      await utils.set_data(ctx.guild, ctx.author, "enabled", "true")
      print("Enabling for {0}".format(ctx.author))
      await utils.send_embed(ctx,"Enabled fanfare for {0}.".format(ctx.author.mention))


keep_alive()
client.add_cog(Fanfare())
client.add_cog(UserSettings())
client.add_cog(AdminSettings())
client.run(config('TOKEN'))
