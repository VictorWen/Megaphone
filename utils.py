import asyncio
import discord
import time
import dataAccess as data
import pafy


PLAYTIME = 10
FALLOFF = 10

connection_queue = {}
play_ids = {}

audio_cache = {}
cache_expire = {}


async def play_audio(member: discord.User, channel: discord.VoiceChannel):
  play_id = str(time.time())

  # Connect the voice client
  try:
    vc = member.guild.voice_client
    if not vc:
      print(f"{play_id}: Connecting...")
      vc = await channel.connect(timeout = 5)
      print(f"{play_id}: Connected to {channel.id} in {member.guild.id}")
    elif vc.channel.id != channel.id:
      print(f"{play_id}: Moving to {channel.id} in {member.guild.id}")
      await vc.move_to(channel)
  except Exception as e:
    # connection_queue[member.guild.id].remove(connect_id)
    print(f"{play_id}: Failed to conncect to {channel.id} in {member.guild.id}")
    raise e
    return

  # Use the time as an id for synchronization
  play_ids[member.guild.id] = play_id

  # Stream the audio from the youtube video as an audio player
  try:
    print(f"{play_id}: Loading audio")
    audio, ffmpeg_options, length = await get_user_audio(member.guild, member)
    print(f"{play_id}: Successfully finished loading audio")
  except Exception as e:
    print(f"{play_id}: Failed to load audio")
    if play_ids[member.guild.id] == play_id:
      # await member.send(embed = discord.Embed(title = "Failed to load your fanfare audio", description = "Something went wrong. Please try again later.", color = 0xff0000))
      await vc.disconnect()
      print(f"{play_id}: Successfully disconnected")
    raise e
    return

  # Ensure proper connection before continuing
  timeout = 0
  while not vc.is_connected() or vc.channel.id != channel.id:
    timeout += 1
    print(f"{play_id}: Waiting for Voice Client connection, attempt #{timeout}")
    await asyncio.sleep(1)
    if play_ids[member.guild.id] != play_id:
      print(f"{play_id}: Aborting connection attempt")
      return
    if (timeout >= 10):
      print(f"{play_id}: Failed to conncect to Voice Client")
      if play_ids[member.guild.id] == play_id:
        await member.send(embed = discord.Embed(title = "Failed to connect properly", description = "I could not connect to the voice channel properly. Please try again later.", color = 0xff0000))
        await vc.disconnect(force = True)
        print(f"{play_id}: Successfully disconnected")
      return

  # Play the audio
  if play_ids[member.guild.id] == play_id:
    if vc.is_playing():
      vc.stop()
      await asyncio.sleep(0.1)
    print(f"{play_id}: Playing audio")
    try:
      audio_player = discord.FFmpegPCMAudio(audio, **ffmpeg_options)
      audio_player = discord.PCMVolumeTransformer(audio_player)
      vc.play(audio_player)
    except Exception as e:
      print(f"{play_id}: Failed to play audio")
      if play_ids[member.guild.id] == play_id:
        await member.send(embed = discord.Embed(title = "Error when playing your fanfare", description = "There was an error when trying to play your fanfare. Please try again later.", color = 0xff0000))
        await vc.disconnect(force = True)
        print(f"{play_id}: Successfully disconnected")
      raise e
      return
    
    # Update start time
    start_time = time.time()
    play_length = min(PLAYTIME, length)

    # normal play
    while time.time() - start_time < play_length:
      await asyncio.sleep(0.05)
      if play_ids[member.guild.id] != play_id:
        # If the play id has changed, stop playing
        vc.stop()
        return

    # volume falloff
    falloff_time = length - play_length
    delta = time.time()
    while delta - start_time - play_length < falloff_time:
      audio_player.volume -= (time.time() - delta) / FALLOFF
      delta = time.time()
      await asyncio.sleep(0.05)
      if play_ids[member.guild.id] != play_id:
          # If the play id has changed, stop falloff
          vc.stop()
          return
      
    # Finish playing
    audio_player.volume = 0
    print(f"{play_id}: Finished playing audio")
    print(f"{play_id}: Played for {time.time() - start_time:.2f}/{length}")
    await asyncio.sleep(0.5)
    
    # If the same play id, disconnect
    if play_ids[member.guild.id] == play_id:
      vc.stop()
      #vc.cleanup()
      await asyncio.sleep(0.1)
      await vc.disconnect()
      print(f"{play_id}: Successfully disconnected")
  else:
    print(f"{play_id}: Audio aborted")


async def get_user_audio(guild: discord.Guild, member: discord.User):
  # Grab youtube link from user data
  yt_url = data.get_userdata(guild, member, "url")
  guild_fanfare = False
  if not yt_url and data.get_guilddata(member.guild, "url"):
    guild_fanfare = True
    yt_url = data.get_guilddata(member.guild, "url")
  elif not yt_url:
    yt_url = "https://www.youtube.com/watch?v=x_XVntliea0"
  
  # Set up timings
  start = data.get_userdata(member.guild, member, "start") if not guild_fanfare else data.get_guilddata(member.guild, "start")
  length = data.get_userdata(member.guild, member, "length") if not guild_fanfare else data.get_guilddata(member.guild, "length")
  length = min(float(length), PLAYTIME + FALLOFF) if length else PLAYTIME + FALLOFF
  
  # If the link is already cached, grab the cached audio
  # If the cached audio is expired, renew it
  # Otherwise cache the link's audio
  if yt_url not in audio_cache or time.time() > cache_expire[yt_url]:
    audio_data = await asyncio.get_event_loop().run_in_executor(None, lambda: pafy.new(yt_url))
    duration = audio_data.length
    if duration < float(length):
      if not guild_fanfare: data.set_userdata(guild, member, "length", str(duration))
      else: data.set_guilddata(guild, "length", str(duration))
      length = duration
    audio = audio_data.getbestaudio().url_https
    expire = audio.find("expire=")
    try:
      expire = float(audio[expire+7:expire+17])
    except Exception as e:
      print(f"DEBUG: AUDIO URL: {audio}")
      expire = 0
      raise e
    audio_cache[yt_url] = audio
    cache_expire[yt_url] = expire
  else:
    audio = audio_cache[yt_url]
  
  # Setup FFMPEG options
  ffmpeg_options = {'before_options': '-probesize 5M', 'options': '-vn'}
  if start:
    ffmpeg_options["options"] += " -ss " + start
  ffmpeg_options["options"] += " -t " + str(length)
  length += 0.5

  return audio, ffmpeg_options, length


def is_in_blacklist(guild: discord.Guild, member: discord.User):
  blacklist = data.get_guilddata(guild, "blacklist")
  return blacklist and str(member.id) in blacklist


async def send_embed(context: discord.ext.commands.Context, text: str, title: str = None, color: int = 0x0066cc):
  embed = discord.Embed(description = text, color = color)
  if title:
    embed.title = title
  try:
    await context.send(embed = embed)
  except discord.errors.Forbidden:
    print(f"Missing embedded links permission for {context.channel.id} in {context.guild.id}")
    await context.author.send(embed = discord.Embed(title="Missing Permissions", description = f"I do not have permissions to embed links in \"{context.channel}\"!", color = 0xff0000))
