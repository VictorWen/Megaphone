import asyncio
import discord
import youtube_dl
import json
import time

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
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

ffmpeg_options = {
    'options': '-vn'
}

PLAYTIME = 15

connection_queue = {}
play_starts = {}

read_file = open("./data", "r")
json_str = read_file.read()
if json_str != "":
    data = json.loads(json_str)
else:
    data = {}
read_file.close()


async def play_audio(member, channel):

    # Connect to the voice client
    if member.guild.id not in connection_queue:
        connection_queue[member.guild.id] = []
    connect_id = str(time.time())
    connection_queue[member.guild.id].append(connect_id)
    while connection_queue[member.guild.id][0] != connect_id:
        await asyncio.sleep(1)
    vc = member.guild.voice_client
    if not vc or not vc.is_connected():
        vc = await channel.connect()
    elif vc.channel != channel:
        await vc.move_to(channel)
    print("Joined {0}".format(channel))
    await asyncio.sleep(1)
    connection_queue[member.guild.id].pop(0)

    # Obtain the URL for the youtube video audio
    print("Loading Audio...")

    url = get_data(member.guild, member.id)
    url = url if url else "https://www.youtube.com/watch?v=x_XVntliea0"  # default URL

    # Stream the audio from the youtube video as an audio player
    # IDK what this really does
    audio_data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
    filename = audio_data['url']
    audio = discord.FFmpegPCMAudio(filename, **ffmpeg_options)
    audio_player = discord.PCMVolumeTransformer(audio)

    # Play the audio
    if vc and vc.is_connected():
        if vc.is_playing():
            vc.stop()
        print("Playing audio")
        vc.play(audio_player)
        play_starts[member.guild.id] = str(time.time())
        await asyncio.sleep(PLAYTIME)
        if time.time() - float(play_starts[member.guild.id]) >= PLAYTIME - 0.5:
            print("Finished playing audio")
            vc.stop()
            await asyncio.sleep(1)
            await vc.disconnect()
            vc.cleanup()


def get_data(guild, tag: str):
    if str(guild.id) in data and str(tag) in data[str(guild.id)]:
        return data[str(guild.id)][str(tag)]
    else:
        return None


def set_data(guild, tag: str, datum: str):
    if str(guild.id) not in data:
        data[str(guild.id)] = {}
    data[str(guild.id)][str(tag)] = datum
    save_data()


def get_blacklist(guild):
    if str(guild.id) not in data:
        data[str(guild.id)] = {}
    if "blacklist" not in data[str(guild.id)]:
        data[str(guild.id)]["blacklist"] = []
    return data[str(guild.id)]["blacklist"]


def save_data():
    write_file = open("./data", "w")
    write_json_str = json.dumps(data)
    write_file.write(write_json_str)
    write_file.close()
