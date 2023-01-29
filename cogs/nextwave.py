import nextcord, nextwave
from nextcord import Interaction
from nextcord.ext import commands


class Nextwave(commands.Cog):
    """Music cog to hold Nextwave related commands and listeners."""

    def __init__(self, bot):
        self.bot = bot

        bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Connect to our Lavalink nodes."""
        await self.bot.wait_until_ready()

        await nextwave.NodePool.create_node(bot=self.bot,
                                            host='lavalink.botsuniversity.ml',
                                            port=443,
                                            password='mathiscool')

    @commands.Cog.listener()
    async def on_nextwave_node_ready(self, node: nextwave.Node):
        """Event fired when a node has finished connecting."""
        print(f'Node: <{node.identifier}> is ready!')
    
    @nextcord.slash_command()
    async def leave(self, interaction: Interaction):
        """Disconnect from the voice channel."""
        if not interaction.guild.voice_client:
            return await interaction.send("Not currently in a voice channel.")
        else:
            vc: nextwave.Player = interaction.guild.voice_client

        await vc.disconnect()
        await interaction.send(f"Disconnected from voice.")
    
    @nextcord.slash_command()
    async def now_playing(self, interaction: Interaction):
        """Returns the current song."""
        if not interaction.guild.voice_client:
            vc: nextwave.Player = await interaction.user.voice.channel.connect(cls=nextwave.Player)
        else:
            vc: nextwave.Player = interaction.guild.voice_client

        await interaction.send(f"Now playing {vc.track.title}")

    @nextcord.slash_command()
    async def pause(self, interaction: Interaction):
        """Pause currently playing song."""
        if not interaction.guild.voice_client:
            return await interaction.send("Not currently playing anything.")
        elif vc.is_paused():
            return await interaction.send("Already paused.")
        else:
            vc: nextwave.Player = interaction.guild.voice_client

        await vc.pause()
        await interaction.send(f"Paused {vc.track.title}")

    @nextcord.slash_command()
    async def play(self, interaction: Interaction, *, search: nextwave.YouTubeTrack):
        """Play a song with the given search query.
        If not connected, connect to our voice channel."""
        if not interaction.guild.voice_client:
            vc: nextwave.Player = await interaction.user.voice.channel.connect(cls=nextwave.Player)
        else:
            vc: nextwave.Player = interaction.guild.voice_client

        await vc.play(search)
        await interaction.send(f"Playing {vc.track.title}")
    
    @nextcord.slash_command()
    async def queue(self, interaction: Interaction):
        """Returns the song queue."""
        if not interaction.guild.voice_client:
            vc: nextwave.Player = await interaction.user.voice.channel.connect(cls=nextwave.Player)
        else:
            vc: nextwave.Player = interaction.guild.voice_client

        queue = nextwave.Queue.copy()
        print(queue)
        queue_list = ','.join(queue)
        await interaction.send(f"{queue_list}")
    
    @nextcord.slash_command()
    async def resume(self, interaction: Interaction):
        """Resume currently playing song."""
        if not interaction.guild.voice_client:
            return await interaction.send("Not currently playing anything.")
        elif not vc.is_paused():
            return await interaction.send("Not currently paused.")
        else:
            vc: nextwave.Player = interaction.guild.voice_client

        await vc.resume()
        await interaction.send(f"Resumed {vc.track.title}")
    
    @nextcord.slash_command()
    async def stop(self, interaction: Interaction):
        """Stop currently playing song."""
        if not interaction.guild.voice_client:
            return await interaction.send("Not currently playing anything.")
        else:
            vc: nextwave.Player = interaction.guild.voice_client

        await vc.stop()
        await interaction.send(f"Stopped {vc.track.title}")
    
    @nextcord.slash_command()
    async def volume(self, interaction: Interaction, volume: int):
        """Sets music volume between 1 - 100%."""
        if not interaction.guild.voice_client:
            return await interaction.send("Not currently playing anything.")
        elif volume not in range(1, 101):
            return await interaction.send("Please keep the volume between 1-100")
        else:
            vc: nextwave.Player = interaction.guild.voice_client

        await vc.set_volume(volume, True)
        await interaction.send(f"Resumed {vc.track.title}")

def setup(bot):
    bot.add_cog(Nextwave(bot))