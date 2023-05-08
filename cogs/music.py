# Credit to https://github.com/chand1012/BeatBot for the Music Player code
# Credit to https://github.com/ooliver1/mafic/blob/master/examples/simple.py for boilerplate
import nextcord
import asyncio
import youtube_dl
from nextcord import Interaction
from nextcord.ext import commands

class MyQueue:
    def __init__(self):
        self.items = []
    
    def isEmpty(self):
        return self.items == []
    
    def push(self, item):
        self.items.insert(0, item)

    def pop(self):
        if self.isEmpty():
            return None
        return self.items.pop()
    
    def size(self):
        return len(self.items)
    
    def clear(self):
        self.items = []

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

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
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(nextcord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(nextcord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Music(commands.Cog, name="Music"):
    """Commands for playing music in voice channels"""

    COG_EMOJI = "🎵"

    def __init__(self, bot):
        self.bot = bot
        self.queue = MyQueue()
        self.bg_task = None
        self.vc: nextcord.VoiceClient = None

    @nextcord.slash_command()
    async def join(self, interaction: Interaction):
        """Join your voice channel"""
        if not interaction.user.voice.channel:
            return await interaction.response.send_message("You are not in a voice channel.")

        vc: nextcord.VoiceChannel = interaction.user.voice.channel

        await interaction.send(f"Joining {vc.mention}.")
        self.vc = await vc.connect()

    @nextcord.slash_command()
    async def play(self, interaction: Interaction, *, song: str):
        """Plays a song"""

        async with interaction.channel.typing():
            self.queue.push(song)
            if not self.vc.is_playing():
                self.play_songs(interaction)
        
        await interaction.send(f'Added to queue!')
    
    @nextcord.slash_command()
    async def skip(self, interaction: Interaction):
        """Skips the current song"""

        if self.vc.is_playing():
            self.vc.stop()
            await interaction.send('Skipped!')
            self.play_songs(interaction)

    @nextcord.slash_command()
    async def volume(self, interaction: Interaction, volume: int):
        """Changes the player's volume"""

        if self.vc is None:
            return await interaction.send("Not connected to a voice channel.")

        self.vc.source.volume = volume / 100
        await interaction.send(f"Changed volume to {volume}%")

    @nextcord.slash_command()
    async def stop(self, interaction: Interaction):
        """Stops and disconnects the bot from voice"""

        self.queue.clear()
        await self.vc.disconnect()
        self.vc = None

    @play.before_invoke
    async def ensure_voice(self, interaction: Interaction):
        if self.vc is None:
            if interaction.user.voice:
                await interaction.user.voice.channel.connect()
            else:
                await interaction.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")

    def play_songs(self, interaction: Interaction):
        self.bg_task = self.bot.loop.create_task(self.play_songs_task(interaction))
    
    async def play_songs_task(self, interaction: Interaction):
        if not self.queue.isEmpty():
            try:
                url = self.queue.pop()
                print(url)
                if self.vc.is_playing() or url is None:
                    return
                player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                print(f'[{player.title}] playing...')
                self.vc.play(player, after=lambda e: print(f'Player error: {e}') if e else self.play_songs(interaction))
                await interaction.send(f'Now playing: {player.title}')
            except Exception as e:
                print(e)
                await interaction.send(f'An error occured: {e}')
        else:
            print('Queue empty, stopping...')
            await interaction.send('Queue empty, goodbye!')
            await self.vc.disconnect()
            self.vc = None
  
def setup(bot):
    bot.add_cog(Music(bot))
