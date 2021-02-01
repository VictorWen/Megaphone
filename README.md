# Megaphone
Discord bot to play fanfare whenever someone joins a voice channel.

[Add to your Discord server](https://discord.com/api/oauth2/authorize?client_id=803491378326667285&permissions=3164160&scope=bot)

## Commands

### *fanfare <yt_url> [start] [length]
Sets the fanfare for the user.

Parameters:

    yt_url: a valid URL to a Youtube video.
  
    start: the starting time of the fanfare in seconds.
  
    length: the duration of the fanfare in seconds.
  

### *play
Plays the fanfare of the user.
Requires that the user be in a voice channel.

### *enable
Enables the user's fanfare.
Makes it so that fanfare will play when they join a voice channel.

### *disable
Disables the user's fanfare.
Makes it so that fanfare will not play when they join a voice channel.

### *blacklist
Blacklists any mentioned members.
This prevents them from playing their fanfare.
The user must either have server mute permissions or be an administrator.
The user must also not be blacklisted.

### *whitelist
Whitelists any mentioned members.
This allows them to play their fanfare.
The user must either have server mute permissions or be an administrator.
The user must also not be blacklisted.
