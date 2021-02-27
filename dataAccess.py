from replit import db
import discord
import json
import pafy


def get_guilddata(guild: discord.Guild, key: str):
  if str(guild.id) in db and key in db[str(guild.id)]:
    return db[str(guild.id)][key]
  else:
    return None


def set_guilddata(guild: discord.Guild, key: str, datum):
  if str(guild.id) not in db:
    db[str(guild.id)] = {}
  grab = db[str(guild.id)]
  grab[key] = datum
  db[str(guild.id)] = grab


def get_userdata(guild: discord.Guild, member: discord.User, key: str):
  userdata_dict = get_guilddata(guild, "users")
  if userdata_dict and str(member.id) in userdata_dict and key in userdata_dict[str(member.id)]:
    return userdata_dict[str(member.id)][key]
  else:
    return None


def set_userdata(guild: discord.Guild, member: discord.User, key: str, datum):
  userdata_dict = get_guilddata(guild, "users")
  if not userdata_dict:
    userdata_dict = {}
  if str(member.id) not in userdata_dict:
    userdata_dict[str(member.id)] = {}
  userdata_dict[str(member.id)][key] = datum
  set_guilddata(guild, "users", userdata_dict)


def convertOldData(json_string: str):
  data = json.loads(json_string)
  for guild in data:
    guilddata = data[guild]
    new_guilddata = {"users" : {}}
    for guild_key in guilddata:
      keywords = ["blacklist", "start", "length", "enabled", "url"]
      if guild_key in keywords:
        new_guilddata[guild_key] = guilddata[guild_key]
      else:
        new_guilddata["users"][guild_key] = guilddata[guild_key]
    db[guild] = new_guilddata
  return new_guilddata