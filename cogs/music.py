# Credit to https://github.com/seyo00/music_bot for the Music Buttons code
import nextcord
import wavelink
from nextcord import Interaction
from nextcord.ext import commands, application_checks

class Music_Buttons(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @nextcord.ui.button(label = "⏯️ Play/Pause", style = nextcord.ButtonStyle.blurple)
    async def pause(self, button : nextcord.ui.Button, interaction : Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("Please join the voice channel!", ephemeral=True)
        elif not interaction.user.voice:
            return await interaction.response.send_message("Please join the voice channel!", ephemeral=True)
        try:
            if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
                return await interaction.response.send_message("We must be in the same voice channel!", ephemeral=True)
        except:
            return await interaction.response.send_message("I am not connected to voice!", ephemeral=True)
        vc: wavelink.Player = interaction.guild.voice_client
        if vc.is_paused():
            await vc.resume()
            return await interaction.response.send_message(f"**{vc.current.title}** is now playing!", ephemeral=True)
        await vc.pause()
        await interaction.response.send_message(f"**{vc.current.title}** is now paused!", ephemeral=True)

    @nextcord.ui.button(label="⏭️ Skip", style=nextcord.ButtonStyle.blurple)
    async def skip(self, button: nextcord.ui.Button, interaction:Interaction):
        try:
            if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
                return await interaction.response.send_message("We must be in the same voice channel!", ephemeral=True)
        except:
            return await interaction.response.send_message("You or I am not in the voice channel!", ephemeral=True)
        vc: wavelink.Player = interaction.guild.voice_client
        try:
            next_song = vc.queue.get()
            await vc.play(next_song)
            return await interaction.response.send_message(f"**{vc.current.title}** was skipped! Now playing: {next_song}", ephemeral=True)
        except:
            return await interaction.response.send_message(f"Queue is empty!", ephemeral=True)
    
    @nextcord.ui.button(label = "🔁 Queue", style = nextcord.ButtonStyle.green)
    async def queue(self, button : nextcord.ui.Button, interaction : Interaction):
        try:
            if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
                return await interaction.response.send_message("We must be in the same voice channel!", ephemeral=True)
        except:
            return await interaction.response.send_message("You or I am not in the voice channel!", ephemeral=True)
        vc: wavelink.Player = interaction.guild.voice_client
        if vc.queue.is_empty:
            return await interaction.send("Queue is empty!")
        queue = vc.queue.copy()
        song_count = 0
        msg = ""
        for song in queue:
            song_count += 1
            msg += f"**{song_count}**: **{song.title}**\n"
        return await interaction.response.send_message(f"__Queue__\n{msg}", ephemeral=True)

    @nextcord.ui.button(label = "🔁 Loop", style = nextcord.ButtonStyle.green)
    async def loop(self, button : nextcord.ui.Button, interaction : Interaction):
        try:
            if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
                return await interaction.response.send_message("We must be in the same voice channel!", ephemeral=True)
        except:
            return await interaction.response.send_message("You or I am not in the voice channel!", ephemeral=True)
        vc: wavelink.Player = interaction.guild.voice_client
        if not vc.queue.loop:
            vc.queue.loop = True
            await interaction.response.send_message(f"**{vc.current.title}** is now looping!", ephemeral=True)
        else:
            vc.queue.loop = False
            await interaction.response.send_message(f"**{vc.current.title}** is no longer looping!", ephemeral=True)
        
        self.value = True
    
    @nextcord.ui.button(label = "⏹️ Stop", style = nextcord.ButtonStyle.red)
    async def disconnect(self, button : nextcord.ui.Button, interaction : Interaction):
        try:
            if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
                return await interaction.response.send_message("We must be in the same voice channel!", ephemeral=True)
        except:
            return await interaction.response.send_message("You or I am not in the voice channel!", ephemeral=True)
        vc: wavelink.Player = interaction.guild.voice_client
        await vc.disconnect()
        await interaction.response.send_message(f"I have left the voice channel!", ephemeral=True)
        self.value = True

class Music(commands.Cog, name="Music"):
    """Commands for playing music in voice channels"""

    COG_EMOJI = "🎵"

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener('on_ready')
    async def node_connect(self):   
        node_list: list[wavelink.Node] = [
            wavelink.Node(uri='http://lavalink.sneakynodes.com:2333', password = 'sneakynodes.com'),
            wavelink.Node(uri='http://narco.buses.rocks:2269', password = 'glasshost1984'),
            wavelink.Node(uri='http://lavalink.alexanderof.xyz:2333', password = 'lavalink'),
            wavelink.Node(uri='http://lavalink2.devamop.in:8830', password = 'DevamOP'),
            wavelink.Node(uri='http://lavalink1.albinhakanson.se:1141', password = 'albinhakanson.se')
            ]
        await wavelink.NodePool.connect(client=self, nodes=[node_list])

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
        if member.id == self.bot.user.id and before.channel is not None and after.channel is None:
            vc: wavelink.Player = member.guild.voice_client
            vc.queue.clear()
            await vc.disconnect()
    
    @commands.Cog.listener() 
    async def on_wavelink_track_end(self, payload: wavelink.TrackEventPayload):
        vc: wavelink.Player = payload.player
        if vc.queue.loop:
            return await vc.play(payload.track)
        elif vc.queue.is_empty:
            return await vc.disconnect()
        next_song = vc.queue.get()
        await vc.play(next_song)
    
    @nextcord.slash_command()
    async def play(self, interaction: Interaction, *, song: str):
        """Play a song"""
        # Ensure bot can connect to voice channel
        if not interaction.user.voice:
            return await interaction.send("Please enter a voice channel!")
        elif not interaction.guild.voice_client:
            vc : wavelink.Player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        view = Music_Buttons()
        search = await wavelink.YouTubeTrack.search(song, return_first=True)

        if vc.queue.is_empty and not vc.is_playing():
            await vc.play(search)
            embed = nextcord.Embed(title=f"Started playing {vc.current.title}!",
            color = nextcord.Colour.from_rgb(214, 60, 26))
            await interaction.send(embed=embed, view=view)
            await view.wait()
        else:
            await vc.queue.put_wait(search)
            embed = nextcord.Embed(title=f"Added {song.title()} to the queue!",
            color = nextcord.Colour.from_rgb(214, 60, 26))
            await interaction.send(embed=embed, delete_after=10.0)

def setup(bot):
    bot.add_cog(Music(bot))