"""
This example aims to show the full capabilities of the library.
This is in the form of a drop-in cog you can use and modify to your liking.
This example aims to include everything you would need to make a fully functioning music bot,
from a queue system, advanced queue control and more.
"""

import nextcord
from nextcord import Interaction
from nextcord.ext import pomice, commands, application_checks

async def join(interaction: Interaction):
    if interaction.guild.voice_client is None:
        if interaction.user.voice:
            await interaction.user.voice.channel.connect()
            interaction.guild.voice_client.source.volume = 0.05
        else:
            await interaction.send("You are not connected to a voice channel.")
            raise commands.CommandError("Author not connected to a voice channel.")
        
class Pomice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
        # In order to initialize a node, or really do anything in this library,
        # you need to make a node pool
        self.pomice = pomice.NodePool()
    
    async def start_nodes(self):
        # You can pass in Spotify credentials to enable Spotify querying.
        # If you do not pass in valid Spotify credentials, Spotify querying will not work
        await self.pomice.create_node(
            bot=self.bot,
            host="ssl.freelavalink.ga",
            port="443",
            password="www.freelavalink.ga",
            identifier="MAIN",
            secure=True
        )
        print(f"Node is ready!")


    @nextcord.slash_command()
    async def leave(self, interaction: Interaction):
        if not interaction.guild.voice_client:
            return await interaction.send("Not connected.")

        player: pomice.Player = interaction.guild.voice_client

        await player.destroy()
        await interaction.send("Leaving the voice channel.")
    
    @application_checks.application_command_before_invoke(join)
    @commands.command(aliases=["p"])
    async def play(self, interaction: Interaction, *, search: str) -> None:
        player: pomice.Player = interaction.guild.voice_client   

        # If you search a keyword, Pomice will automagically search the result using YouTube
        # You can pass in "search_type=" as an argument to change the search type
        # i.e: player.get_tracks("query", search_type=SearchType.ytmsearch)
        # will search up any keyword results on YouTube Music
        results = await player.get_tracks(search)     
        
        if not results:
            raise commands.CommandError("No results were found for that search term.")
        
        if isinstance(results, pomice.Playlist):
            await player.play(track=results.tracks[0])
        else:
            await player.play(track=results[0])

    @commands.command()
    async def pause(self, interaction: Interaction):
        if not interaction.guild.voice_client:
            raise commands.CommandError("No player detected")

        player: pomice.Player = interaction.guild.voice_client

        if player.is_paused:
            return await interaction.send("Player is already paused!")

        await player.set_pause(pause=True)
        await interaction.send("Player has been paused")

    @commands.command()
    async def resume(self, interaction: Interaction):
        if not interaction.guild.voice_client:
            raise commands.CommandError("No player detected")

        player: pomice.Player = interaction.guild.voice_client

        if not player.is_paused:
            return await interaction.send("Player is already playing!")

        await player.set_pause(pause=False)
        await interaction.send("Player has been resumed")

    @commands.command()
    async def stop(self, interaction: Interaction):
        if not interaction.guild.voice_client:
            raise commands.CommandError("No player detected")

        player: pomice.Player = interaction.voice_client

        if not player.is_playing:
            return await interaction.send("Player is already stopped!")

        await player.stop()
        await interaction.send("Player has been stopped")

def setup(bot):
    bot.add_cog(Pomice(bot))