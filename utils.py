import asyncio
import discord
import youtube_dl
import json
import time
from aiofile import async_open

# Constants
ytdl_format_options = {
  'format': 'bestaudio/best',
  'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
  'restrictfilenames': True,
  'noplaylist': True,
  'nocheckcertificate': True,
  'ignoreerrors': False,
  'logtostderr': False,
  'quiet': True,
  'no_warnings': True,
  'default_search': 'auto',
  'skip_download': True,
  'simulate': True,
  'source_address':
  '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

PLAYTIME = 10
FALLOFF = 10

connection_queue = {}
play_ids = {}

read_file = open("./data", "r")
json_str = read_file.read()
if json_str != "":
  data = json.loads(json_str)
else:
  data = {}
read_file.close()


async def play_audio(member: discord.User, channel: discord.VoiceChannel):  
  # Use the time as an id for synchronization
  play_id = str(time.time())
  play_ids[member.guild.id] = play_id

  await asyncio.sleep(0.5)
  if (play_ids[member.guild.id] != play_id):
    print(f"{play_id}: Connection to {channel} in {member.guild} aborted")
    return

  # Connect the voice client
  try:
    vc = member.guild.voice_client
    if not vc:
      print(f"{play_id}: Connecting...")
      vc = await channel.connect(timeout = 5)
      print(f"{play_id}: Connected to {channel} in {member.guild}")
    elif vc.channel != channel:
      print(f"{play_id}: Moving to {channel} in {member.guild}")
      await vc.move_to(channel)
  except Exception as e:
    # connection_queue[member.guild.id].remove(connect_id)
    print(f"{play_id}: Failed to conncect to {channel} in {member.guild}")
    raise e
    return

  # Ensure proper connection before continuing
  timeout = 0
  while not vc.is_connected():
    timeout += 1
    print(f"{play_id}: Waiting for Voice Client connection, attempt #{timeout}")
    await asyncio.sleep(1)
    if (timeout > 5):
      print(f"{play_id}: Failed to conncect to Voice Client")
      if play_ids[member.guild.id] == play_id:
        await vc.disconnect(force = True)
        print(f"{play_id}: Successfully disconnected")
      return

  # Obtain the URL for the youtube video audio
  print(f"{play_id}: Loading Audio...")
  url = get_data(member.guild, member, "url")
  url = url if url else "https://www.youtube.com/watch?v=x_XVntliea0"  # default URL

  # Stream the audio from the youtube video as an audio player
  try:
    # Load the audio from Youtube-DL
    audio_data = await asyncio.get_event_loop().run_in_executor(
      None, lambda: ytdl.extract_info(url, download=False))
    filename = audio_data['url']
    duration = float(audio_data['duration'])

    # Set options for start time and length
    ffmpeg_options = {'options': '-vn'}
    start = get_data(member.guild, member, "start")
    if start:
      ffmpeg_options["options"] += " -ss " + start
      duration -= float(start)
    length = get_data(member.guild, member, "length")
    length = min(float(length), PLAYTIME + FALLOFF) if length else PLAYTIME + FALLOFF
    if length < duration:
      ffmpeg_options["options"] += " -t " + str(length)
    else:
      length = duration
    length += 0.5

    # Create discord audio player
    audio = discord.FFmpegPCMAudio(filename, **ffmpeg_options)
    audio_player = discord.PCMVolumeTransformer(audio)
  except Exception as e:
    print(f"{play_id}: Failed to load audio")
    await member.send(embed = discord.Embed(title = "Failed to load your fanfare audio", description = f"Check if there is something wrong with your youtube link: {url}. Otherwise try again later.", color = 0xff0000))
    if play_ids[member.guild.id] == play_id:
      await vc.disconnect()
      print(f"{play_id}: Successfully disconnected")
    raise e
    return

  print(f"{play_id}: Successfully finished loading audio")

  # Play the audio
  if play_ids[member.guild.id] == play_id:
    if vc.is_playing():
      vc.stop()
    print(f"{play_id}: Playing audio")
    try:
      vc.play(audio_player)
    except Exception as e:
      print(f"{play_id}: Failed to play audio")
      if play_ids[member.guild.id] == play_id:
        await vc.disconnect(force = True)
        print(f"{play_id}: Successfully disconnected")
      raise e
      return
    
    # Update start time
    start_time = time.time()
    play_length = min(PLAYTIME, length)

    # normal play
    while time.time() - start_time < play_length:
      await asyncio.sleep(0.01)
      if play_ids[member.guild.id] != play_id:
        # If the play id has changed, stop playing
        vc.stop()
        return

    # volume falloff
    falloff_time = length - play_length
    delta = time.time()
    while delta - start_time - play_length < falloff_time:
      audio_player.volume -= (time.time() - delta) / FALLOFF
      await asyncio.sleep(0.01)
      if play_ids[member.guild.id] != play_id:
          # If the play id has changed, stop falloff
          vc.stop()
          return
      delta = time.time()
      
    # Finish playing
    audio_player.volume = 0
    print(f"{play_id}: Finished playing audio")
    await asyncio.sleep(0.5)
    
    # If the same play id, disconnect
    if play_ids[member.guild.id] == play_id:
      vc.stop()
      await asyncio.sleep(0.01)
      await vc.disconnect()
      print(f"{play_id}: Successfully disconnected")
      vc.cleanup()
  else:
    print(f"{play_id}: Audio aborted")


def get_data(guild: discord.Guild, member: discord.User, tag: str):
  if str(guild.id) in data and \
  str(member.id) in data[str(guild.id)] and \
  str(tag) in data[str(guild.id)][str(member.id)]:
    return data[str(guild.id)][str(member.id)][str(tag)]
  else:
    return None


async def set_data(guild: discord.Guild, member: discord.User, tag: str, datum: str):
  if str(guild.id) not in data:
    data[str(guild.id)] = {}
  if str(member.id) not in data[str(guild.id)]:
    data[str(guild.id)][str(member.id)] = {}
  data[str(guild.id)][str(member.id)][str(tag)] = datum
  await save_data()


def get_blacklist(guild: discord.Guild):
  if str(guild.id) not in data:
    data[str(guild.id)] = {}
  if "blacklist" not in data[str(guild.id)]:
    data[str(guild.id)]["blacklist"] = []
  return data[str(guild.id)]["blacklist"]


async def save_data():
  async with async_open("./data", "w") as write_file:
  # write_file = open()
    write_json_str = json.dumps(data)
    await write_file.write(write_json_str)


async def send_embed(context: discord.ext.commands.Context, text: str, title: str = None, color: int = 0x0066cc):
  embed = discord.Embed(description = text, color = color)
  if title:
    embed.title = title
  try:
    await context.send(embed = embed)
  except discord.errors.Forbidden:
    print(f"Missing embedded links permission for {context.channel} in {context.guild}")
    await context.author.send(embed = discord.Embed(title="Missing Permissions", description = f"I do not have permissions to embed links in \"{context.channel}\"!", color = 0xff0000))
