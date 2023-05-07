# Credit to https://github.com/seyo00/music_bot for the Music Player code
# Credit to https://github.com/ooliver1/mafic/blob/master/examples/simple.py for boilerplate
import nextcord
import mafic
import traceback
from nextcord import Interaction
from nextcord.ext import commands

class MyPlayer(mafic.Player[commands.Bot]):
    def __init__(self, client: commands.Bot, channel: nextcord.abc.Connectable) -> None:
        super().__init__(client, channel)

        self.queue: list[mafic.Track] = []

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
        player: MyPlayer = (interaction.guild.voice_client)
        if player.paused:
            await player.resume()
            return await interaction.response.send_message(f"**{player.current.title}** is now playing!", ephemeral=True)
        await player.pause()
        await interaction.response.send_message(f"**{player.current.title}** is now paused!", ephemeral=True)

    @nextcord.ui.button(label="⏭️ Skip", style=nextcord.ButtonStyle.blurple)
    async def skip(self, button: nextcord.ui.Button, interaction:Interaction):
        try:
            if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
                return await interaction.response.send_message("We must be in the same voice channel!", ephemeral=True)
        except:
            return await interaction.response.send_message("You or I am not in the voice channel!", ephemeral=True)
        player: MyPlayer = (interaction.guild.voice_client)
        try:
            next_song = player.queue.get()
            await player.play(next_song)
            return await interaction.response.send_message(f"**{player.current.title}** was skipped! Now playing: {next_song}", ephemeral=True)
        except:
            return await interaction.response.send_message(f"Queue is empty!", ephemeral=True)
    
    @nextcord.ui.button(label = "🔁 Queue", style = nextcord.ButtonStyle.green)
    async def queue(self, button : nextcord.ui.Button, interaction : Interaction):
        try:
            if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
                return await interaction.response.send_message("We must be in the same voice channel!", ephemeral=True)
        except:
            return await interaction.response.send_message("You or I am not in the voice channel!", ephemeral=True)
        player: MyPlayer = (interaction.guild.voice_client)
        if player.queue.is_empty:
            return await interaction.send("Queue is empty!")
        queue = player.queue.copy()
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
        player: MyPlayer = (interaction.guild.voice_client)
        if not player.loop:
            player.loop ^= True
            await interaction.response.send_message(f"**{player.current.title}** is now looping!", ephemeral=True)
        else:
            setattr(player, "loop", False)
            player.loop ^= True
            await interaction.response.send_message(f"**{player.current.title}** is no longer looping!", ephemeral=True)
        
        self.value = True
    
    @nextcord.ui.button(label = "⏹️ Stop", style = nextcord.ButtonStyle.red)
    async def disconnect(self, button : nextcord.ui.Button, interaction : Interaction):
        try:
            if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
                return await interaction.response.send_message("We must be in the same voice channel!", ephemeral=True)
        except:
            return await interaction.response.send_message("You or I am not in the voice channel!", ephemeral=True)
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message(f"I have left the voice channel!", ephemeral=True)
        self.value = True

async def join(interaction: Interaction):
    """Join your voice channel"""
    assert isinstance(interaction.user, nextcord.Member)

    if not interaction.user.voice or not interaction.user.voice.channel:
        return await interaction.response.send_message("You are not in a voice channel.")

    channel = interaction.user.voice.channel

    await channel.connect(cls=MyPlayer)
    await interaction.send(f"Joined {channel.mention}.")

class Music(commands.Cog, name="Music"):
    """Commands for playing music in voice channels"""

    COG_EMOJI = "🎵"

    def __init__(self, bot):
        self.bot = bot
        self.pool = mafic.NodePool(self)
        self.ready_ran = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self.ready_ran:
            return
        
        await self.pool.create_node(
            host="lavalink.sneakynodes.com",
            port=2333,
            label="MAIN",
            password="sneakynodes.com"
        )

        self.ready_ran = True

    @nextcord.slash_command()
    async def play(self, interaction: Interaction, song: str):
        """Play a song"""
        assert interaction.guild is not None

        if not interaction.guild.voice_client:
            await join(interaction)

        view = Music_Buttons()

        player: MyPlayer = (
            interaction.guild.voice_client
        )

        tracks = await player.fetch_tracks(song)

        if not tracks:
            return await interaction.send("No tracks found.")

        if isinstance(tracks, mafic.Playlist):
            tracks = tracks.tracks
            if len(tracks) > 1:
                player.queue.extend(tracks[1:])

        track = tracks[0]
        await player.play(track)
        embed = nextcord.Embed(title=f"Added {track} to the queue!",
            color=nextcord.Colour.from_rgb(214, 60, 26))
        await interaction.send(embed=embed, view=view)
        await view.wait()

    @commands.Cog.listener()
    async def on_track_end(event: mafic.TrackEndEvent):
        assert isinstance(event.player, MyPlayer)

        if event.player.queue:
            await event.player.play(event.player.queue.pop(0))

    @commands.Cog.listener()
    async def on_application_command_error(inter: Interaction[commands.Bot], error: Exception):
        traceback.print_exception(type(error), error, error.__traceback__)
        await inter.send(f"An error occurred: {error}")
  
def setup(bot):
    bot.add_cog(Music(bot))
