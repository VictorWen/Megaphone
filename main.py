import asyncio
import discord
import nacl
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
    if not member.bot and str(member.id) not in utils.get_blacklist(member.guild) and \
            after.channel is not None and before.channel != after.channel:
        print("Detected {0} joined a channel in {1}".format(member, member.guild))
        await utils.play_audio(member, after.channel)


@client.command()
async def fanfare(context, url, start = None, length = None):
    msg = ""
    if validators.url(url):
        msg += "Successfully added new fanfare for {0.mention}"
        utils.set_data(context.guild, context.author, "url", url)
        if start and start.isnumeric() and float(start) > 0:
            utils.set_data(context.guild, context.author, "start", start)
            msg += " starting at " + start + " seconds"
        else:
            utils.set_data(context.guild, context.author, "start", None)
        if length and length.isnumeric() and float(length) > 0:
            utils.set_data(context.guild, context.author, "length", length)
            msg += " and lasting " + length + " seconds"
        else:
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
    if str(context.author.id) not in utils.get_blacklist(context.guild):
        await context.send("Playing {0}'s fanfare".format(context.author.mention))
        await utils.play_audio(context.author, context.author.voice.channel)


@client.command()
async def blacklist(context):
    if str(context.author.id) in utils.get_blacklist(context.guild):
        return
    permissions = context.author.guild_permissions
    if permissions.mute_members or \
            permissions.administrator:
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
    if permissions.mute_members or \
            permissions.administrator:
        guild_blacklist = utils.get_blacklist(context.guild)
        for user in context.message.mentions:
            if str(user.id) in guild_blacklist:
                guild_blacklist.remove(str(user.id))
                await context.send("Removed {0} to the blacklist".format(user.mention))
        utils.save_data()


keep_alive()
client.run(config('TOKEN'))
