print("Starting up")

import nacl #upm package(pynacl)
from discord.ext import commands
from decouple import config
import utils
import dataAccess as data
import validators
from keep_alive import keep_alive

client = commands.Bot(command_prefix='*')

@client.event
async def on_ready():
  print('Logged in as {0.user}'.format(client))


@client.event
async def on_voice_state_update(member, before, after):
  # Check if not a bot, is not in blacklist, has fanfare enabled, and has moved to a channel
  if not member.bot and not utils.is_in_blacklist(member.guild, member) and data.get_userdata(member.guild, member, "enabled") != "false" and after.channel is not None and before.channel != after.channel and after.channel.permissions_for(member.guild.me).view_channel and (after.channel.user_limit == 0 or len(after.channel.members) < after.channel.user_limit):
    print("Detected {0} joined {1} in {2}".format(member.id, after.channel.id, member.guild.id))
    await utils.play_audio(member, after.channel)


class Fanfare(commands.Cog):
  
  @commands.command()
  async def fanfare(self, ctx, yt_url, start = None, length = None):
    '''
    Sets the fanfare for the user.
    Parameters:
      yt_url: a valid URL to a Youtube video.
      start: the starting time of the fanfare in seconds.
      length: the duration of the fanfare in seconds. (Maxes out at 20 secs)
    '''
    msg = ""
    # check if url is a valid URL
    if validators.url(yt_url):
      msg += "Successfully added new fanfare for {0.mention}"
      data.set_userdata(ctx.guild, ctx.author, "url", yt_url)
      # Check if start can be converted to a float and greater than zero
      if start and (start.isnumeric() or start.replace('.', '', 1).isdigit()) and float(start) >= 0:
        data.set_userdata(ctx.guild, ctx.author, "start", start)
        msg += " starting at " + start + " seconds"

        # Check if length can be converted to a float and greater than zero
        if length and (length.isnumeric() or length.replace('.', '', 1).isdigit()) and float(length) >= 0:
          data.set_userdata(ctx.guild, ctx.author, "length", length)
          msg += " and lasting " + length + " seconds"
        else:
          data.set_userdata(ctx.guild, ctx.author, "length", None)
      else:
        data.set_userdata(ctx.guild, ctx.author, "start", None)
        data.set_userdata(ctx.guild, ctx.author, "length", None)

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
    if not ctx.author.voice.channel.permissions_for(ctx.guild.me).view_channel or (ctx.author.voice.channel.user_limit > 0 and len(ctx.author.voice.channel.members) >= ctx.author.voice.channel.user_limit):
      await utils.send_embed(ctx, "I cannot join that channel!", color = 0xff0000)
      return
    if not utils.is_in_blacklist(ctx.guild, ctx.author):
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
    if utils.is_in_blacklist(ctx.guild, ctx.author):
      await utils.send_embed(ctx, "You are blacklisted and cannot change the blacklist.", color = 0)
      return
    permissions = ctx.author.guild_permissions
    if permissions.mute_members or permissions.administrator:
      guild_blacklist = data.get_guilddata(ctx.guild, "blacklist")
      if not guild_blacklist:
        guild_blacklist = []
      if len(ctx.message.mentions) == 0:
        await utils.send_embed(ctx, "There is no one mentioned. Use @ to mention someone.", color = 0xff0000)
        return
      for user in ctx.message.mentions:
        if (user.id == ctx.author.id):
          await utils.send_embed(ctx, "You cannot blacklist yourself", color = 0xff0000)
          continue
        if str(user.id) not in guild_blacklist:
          guild_blacklist.append(str(user.id))
          await utils.send_embed(ctx, "Added {0} to the blacklist.".format(user.mention), color = 0)
      data.set_guilddata(ctx.guild, "blacklist", guild_blacklist)
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
    if utils.is_in_blacklist(ctx.guild, ctx.author):
      await utils.send_embed(ctx, "You are blacklisted and cannot change the blacklist.", color = 0)
      return
    permissions = ctx.author.guild_permissions
    if permissions.mute_members or permissions.administrator:
      guild_blacklist = data.get_guilddata(ctx.guild, "blacklist")
      if not guild_blacklist:
        guild_blacklist = []
      if len(ctx.message.mentions) == 0:
        await utils.send_embed(ctx, "There is no one mentioned. Use @ to mention someone.", color = 0xff0000)
        return
      for user in ctx.message.mentions:
        if guild_blacklist and str(user.id) in guild_blacklist:
          guild_blacklist.remove(str(user.id))
          await utils.send_embed(ctx, "Removed {0} to the blacklist.".format(user.mention), color = 0xffffff)
      data.set_guilddata(ctx.guild, "blacklist", guild_blacklist)
    else:
      await utils.send_embed(ctx, "You do not have permission to whitelist members.", color = 0xff0000)


  @commands.command()
  async def default(self, ctx, yt_url = None, start = None, length = None):
    '''
    Sets the default fanfare url.
    Requires administrator permissions.
    Parameters:
      yt_url: a valid URL to a youtube video. (leave blank to restore to factory default)
      start: the starting time of the fanfare in seconds.
      length: the duration of the fanfare in seconds. 
    '''
    if utils.is_in_blacklist(ctx.guild, ctx.author):
      await utils.send_embed(ctx, "You are blacklisted and cannot change the default fanfare.", color = 0)
      return
    permissions = ctx.author.guild_permissions
    if permissions.administrator:
      # Adapted fanfare command
      msg = ""
      # check if url is a valid URL
      if not yt_url or validators.url(yt_url):
        msg += "Successfully changed default fanfare for {0}"
        data.set_guilddata(ctx.guild, "url", yt_url)
        # Check if start can be converted to a float and greater than zero
        if start and (start.isnumeric() or start.replace('.', '', 1).isdigit()) and float(start) >= 0:
          data.set_guilddata(ctx.guild, "start", start)
          msg += " starting at " + start + " seconds"

          # Check if length can be converted to a float and greater than zero
          if length and (length.isnumeric() or length.replace('.', '', 1).isdigit()) and float(length) >= 0:
            data.set_guilddata(ctx.guild, "length", length)
            msg += " and lasting " + length + " seconds"
          else:
            data.set_guilddata(ctx.guild, "length", None)
        else:
          data.set_guilddata(ctx.guild, "start", None)
          data.set_guilddata(ctx.guild, "length", None)

        msg += "."
        await utils.send_embed(ctx, msg.format(ctx.guild), color = 0x009900)
        print("Changed default fanfare for: {0}".format(ctx.guild))
      else:
        await utils.send_embed(ctx, f"{yt_url} is not a valid URL!", color = 0xff0000) 
        return
    else:
      await utils.send_embed(ctx, "You do not have permission to change the default fanfare.", color = 0xff0000)


class UserSettings(commands.Cog):
  
  @commands.command()
  async def disable(self, ctx):
    '''
    Disables the user's fanfare.
    Makes it so that fanfare will not play when they join a voice channel.
    '''
    if data.get_userdata(ctx.guild, ctx.author, "enabled") != "false":
      data.set_userdata(ctx.guild, ctx.author, "enabled", "false")
      print("Disabling for {0}".format(ctx.author))
      await utils.send_embed(ctx, "Disabled fanfare for {0}.".format(ctx.author.mention))


  @commands.command()
  async def enable(self, ctx):
    '''
    Enables the user's fanfare.
    Makes it so that fanfare will play when they join a voice channel.
    '''
    if data.get_userdata(ctx.guild, ctx.author, "enabled") == "false":
      data.set_userdata(ctx.guild, ctx.author, "enabled", "true")
      print("Enabling for {0}".format(ctx.author))
      await utils.send_embed(ctx, "Enabled fanfare for {0}.".format(ctx.author.mention))
  

  @commands.command()
  async def reset(self, ctx):
    '''
    Resets the user's user settings to factory defaults.
    This includes the user's fanfare and whether it disabled or not.
    '''
    data.set_userdata(ctx.guild, ctx.author, "url", None)
    data.set_userdata(ctx.guild, ctx.author, "start", None)
    data.set_userdata(ctx.guild, ctx.author, "length", None)
    data.set_userdata(ctx.guild, ctx.author, "enabled", True)
    await utils.send_embed(ctx, f"Successfully reset user settings for {ctx.author.mention}")


keep_alive()
client.add_cog(Fanfare())
client.add_cog(UserSettings())
client.add_cog(AdminSettings())
client.run(config('TOKEN'))
