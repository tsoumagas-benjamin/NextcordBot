import nextcord, pymongo, os, json, re, youtube_dl, datetime, random, asyncio
from nextcord import Interaction
from nextcord.ext import commands
from fuzzywuzzy import fuzz

# Set up our mongodb client
client = pymongo.MongoClient(os.getenv("CONN_STRING"))

# Name our access to our client database
db = client.NextcordBot

# Get all the existing collections
collections = db.list_collection_names()

# Get access to the songs collection
song_list = db["songs"]

# Default player volume
default_volume = 5

# Music quiz variables
mq_rounds = 10
mq_duration = 30
mq_leniency = 90
player_score = {}
score_embed = nextcord.Embed(
    title="Music Quiz Results", color=nextcord.Colour.from_rgb(225, 0, 255)
)
song_indices = []
title_list = []
artist_list = []
# mq_interaction: Interaction
# mq_status = False

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    "format": "bestaudio/best",
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {"options": "-vn"}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(nextcord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if "entries" in data:
            data = data["entries"][0]
        
        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(nextcord.FFmpegAudio(filename, *ffmpeg_options), data=data)

def title_case(s):
    return re.sub(
        r"[A-Za-z]+('[A-Za-z]+)?",
        lambda mo: mo.group(0)[0].upper() + mo.group(0)[1:].lower(),
        s,
    )

# Function to increment player score
def increment_score(guess):
    if guess.author.name in player_score:
        player_score[str(guess.author.name)] += 1
    else:
        player_score[str(guess.author.name)] = 1


# Function to do fuzzy string matching
def fuzz_check(s1, s2):
    return (
        fuzz.token_set_ratio(
            "".join(e for e in s1.content.lower() if e.isalnum()),
            "".join(e for e in s2.lower() if e.isalnum()),
        )
        >= mq_leniency
    )

# TODO: Fix music quiz functionality
class Music(commands.Cog, name="Music"):
    """Commands for playing music in voice channels"""

    COG_EMOJI = "🎵"

    def __init__(self, bot):
        self.bot = bot
        self.mq_channel = None
        self.mq_interaction = None
        self.song_indices = []
        self.player_dict = {}
        self.player_score = {}
        self.title_list = []
        self.artist_list = []
        self.title_flag = None
        self.artist_flag = None
        self.correct_title = None
        self.correct_artist = None
        self.score_embed = nextcord.Embed(title = "Music Quiz Results", color = nextcord.Colour.from_rgb(225, 0, 255))    

    async def ensure_voice(self, interaction: Interaction):
        if interaction.guild.voice_client is None:
            if interaction.user.voice:
                await interaction.user.voice.channel.connect()
            else:
                await interaction.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()

    @nextcord.slash_command()
    async def join(self, interaction: Interaction):
        if interaction.user.voice.channel:
            await interaction.send(f"Joining {interaction.user.voice.channel.name}.")
            return await interaction.user.voice.channel.connect()
        else:
            interaction.send("You must be in a voice channel to use this command!")
        
    @nextcord.slash_command()
    @nextcord.SlashApplicationCommand.before_invoke(ensure_voice)
    async def play(self, interaction: Interaction, *, query):
        """Plays a file from the local filesystem"""

        source = nextcord.PCMVolumeTransformer(nextcord.FFmpegPCMAudio(query))
        interaction.guild.voice_client.play(source, after=lambda e: print(f"Player error: {e}") if e else None)

        await interaction.send(f"Now playing: {query}")

    @nextcord.slash_command()
    @nextcord.SlashApplicationCommand.before_invoke(ensure_voice)
    async def yt(self, interaction: Interaction, *, url):
        """Plays from a URL (almost anything youtube_dl supports)"""

        async with interaction.channel.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            interaction.guild.voice_client.play(
                player, after=lambda e: print(f"Player error: {e}") if e else None
            )

        await interaction.send(f"Now playing: {player.title}")

    @nextcord.slash_command()
    @nextcord.SlashApplicationCommand.before_invoke(ensure_voice)
    async def stream(self, interaction: Interaction, *, url):
        """Streams from a URL (same as yt, but doesn't predownload)"""

        async with interaction.channel.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            interaction.voice_client.play(
                player, after=lambda e: print(f"Player error: {e}") if e else None
            )

        await interaction.send(f"Now playing: {player.title}")

    @nextcord.slash_command()
    async def volume(self, interaction: Interaction, volume: int):
        """Changes the player's volume"""

        if interaction.guild.voice_client is None:
            return await interaction.send("Not connected to a voice channel.")

        interaction.guild.voice_client.source.volume = volume / 100
        await interaction.send(f"Changed volume to {volume}%")

    @nextcord.slash_command()
    async def stop(self, interaction: Interaction):
        """Stops and disconnects the bot from voice"""

        await interaction.send(f"Leaving voice.")
        await interaction.guild.voice_client.disconnect()

    # @nextcord.slash_command()
    # async def music_quiz(self, interaction: Interaction):
    #     """Starts music quiz."""
    #     # Start of game message
    #     await interaction.send(
    #         f"Music quiz, {mq_rounds} rounds, {mq_duration} seconds each."
    #     )
    #     # Join user's voice channel
    #     player = self.bot.lavalink.player_manager.get(interaction.guild.id)
    #     channel = interaction.user.voice.channel
    #     if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
    #         # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
    #         # may not disconnect the bot.
    #         return await interaction.send('You\'re not in my voicechannel!')
    #     await channel.connect()
    #     await player.set_volume(default_volume)

    #     # Clear dictionary that stores player score
    #     self.player_dict = {}
    #     # Setup the embed to store game results
    #     self.score_embed.set_footer(icon_url = interaction.guild.icon.url, text = interaction.guild.name)
    #     # Make a list from available titles and artists
    #     titles = song_list.find({}, {"title":1, "_id":0})
    #     artists = song_list.find({}, {"artist":1, "_id":0})
    #     self.title_list, self.artist_list = [], []
    #     for t in titles:
    #         self.title_list.append(t["title"])
    #     for a in artists:
    #         self.artist_list.append(a["artist"])
    #     print(self.title_list)
    #     print(self.artist_list)
    #     # Randomize songs for as many rounds as needed
    #     index_list = range(0,int(song_list.count_documents({}))+1)
    #     self.song_indices = random.sample(index_list, mq_rounds)
    #     # Enable music quiz responses to be read in the channel and store start interaction
    #     if self.mq_channel is None:
    #         self.mq_channel = interaction.channel
    #     else:
    #         return await interaction.send("Music quiz is already active in another channel! Please try again later.")
    #     self.mq_interaction = interaction
    #     # Added for testing purposes
    #     await interaction.send(self.player_dict)
    #     await interaction.send(self.score_embed)
    #     await interaction.send(self.title_list)
    #     await interaction.send(self.song_indices)

    #     channel = self.mq_channel

        
    #     async def mq_disconnect(self, interaction: Interaction):
    #         """Disconnects the bot from the voice channel."""
    #         if not interaction.voice_client:
    #             # We can't disconnect, if we're not connected.
    #             return await interaction.send('Not connected.')
    #         if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
    #             # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
    #             # may not disconnect the bot.
    #             return await interaction.send('You\'re not in my voicechannel!')

    #         # Clear the queue to ensure old tracks don't start playing
    #         # when someone else queues something.
    #         player.queue.clear()
    #         # Stop the current track so Lavalink consumes less resources.
    #         await player.stop()
    #         # Disconnect from the voice channel.
    #         await interaction.voice_client.disconnect(force=True)
    #         await interaction.send('*⃣ | Music Quiz has ended.')

    #     async def mq_play(self, interaction: Interaction, search: str):
    #         """Plays a song in a voice channel."""
    #         # Get the player for this guild from cache.
    #         player = self.bot.lavalink.player_manager.get(interaction.guild.id)
    #         # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
    #         query = query.strip('<>')

    #         # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
    #         # SoundCloud searching is possible by prefixing "scsearch:" instead.
    #         if not url_rx.match(query):
    #             query = f'ytsearch:{query}'

    #         # Get the results for the query from Lavalink.
    #         results = await player.node.get_tracks(query)

    #         # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
    #         # Alternatively, results.tracks could be an empty array if the query yielded no tracks.
    #         if not results or not results.tracks:
    #             return await interaction.send('Nothing found!')

    #         # Valid loadTypes are:
    #         #   TRACK_LOADED    - single video/direct URL)
    #         #   PLAYLIST_LOADED - direct URL to playlist)
    #         #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
    #         #   NO_MATCHES      - query yielded no results
    #         #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
    #         if results.load_type == 'PLAYLIST_LOADED':
    #             tracks = results.tracks
    #             for track in tracks:
    #                 # Add all of the tracks from the playlist to the queue.
    #                 player.add(track=track)
    #         else:
    #             track = results.tracks[0]
    #             player.add(track=track)

    #         # We don't want to call .play() if the player is playing as that will effectively skip
    #         # the current track.
    #         if not player.is_playing:
    #             await player.play()

    #     for i in range(mq_rounds):
    #         # Start of round
    #         await asyncio.sleep(3)
    #         await channel.send(f"Starting round {i+1}")
    #         # Reset guess flags for each round
    #         self.title_flag = ""
    #         self.artist_flag = ""
    #         # Make the correct song the first one from our random list
    #         index = self.song_indices[i]
    #         self.correct_title = self.title_list[index]
    #         self.correct_artist = self.artist_list[index]
    #         #Play the song at volume
    #         print("Playing " + self.title_list[index] + " by " + self.artist_list[index])
    #         await mq_play(self.mq_interaction, self.title_list[index]+" by "+ self.artist_list[index])
    #     #Announce end of the game
    #     await channel.send("Music quiz is done.")
    #     #Sort player score dictionary from highest to lowest
    #     sorted_list = sorted(self.player_score.items(), key = lambda x:x[1], reverse=True)
    #     sorted_dict = dict(sorted_list)
    #     # Add each player and their score to game results embed
    #     for key, value in sorted_dict.items():
    #         score = str(value) + " pts"
    #         self.score_embed.add_field(name=key, value=score)
    #     #Send game results embed and leave voice channel
    #     await interaction.send(embed=self.score_embed)
    #     await disconnect(self.mq_interaction)
    #     self.mq_channel = None
    #     return
        
    # @commands.Cog.listener("on_message")
    # async def mq(self, message):
    #     # If the message is from a bot or not in an active music quiz channel, don't react
    #     if message.author.bot or self.mq_channel != message.channel:
    #         return

    #     channel = message.channel
        
    #     async def mq_stop(self, interaction: Interaction):
    #         """Stops the current song."""
    #         player = self.bot.lavalink.player_manager.get(interaction.guild.id)

    #         if not interaction.voice_client:
    #             # We can't stop, if we're not connected.
    #             return await interaction.send('Not connected.')
    #         if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
    #             # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
    #             # may not stop the bot.
    #             return await interaction.send('You\'re not in my voicechannel!')

    #         # Stop the current track so Lavalink consumes less resources.
    #         await player.stop()
    #         await interaction.send('*⃣ | Stopped playing music.')

    #     # Check if user response matches the correct title
    #     def title_check(m):
    #         s1 = "".join(e for e in m.content.lower() if e.isalnum())
    #         s2 = "".join(e for e in self.correct_title.lower() if e.isalnum())
    #         percent_correct = fuzz.token_set_ratio(s1, s2)
    #         if percent_correct >= mq_leniency:
    #             increment_score(m.author.name)
    #             return str(m.author.name)
    #         return ""

    #     # Check if user response matches the correct artist
    #     def artist_check(m):
    #         s1 = "".join(e for e in m.content.lower() if e.isalnum())
    #         s2 = "".join(e for e in self.correct_artist.lower() if e.isalnum())
    #         percent_correct = fuzz.token_set_ratio(s1, s2)
    #         if percent_correct >= mq_leniency:
    #             increment_score(m.author.name)
    #             return str(m.author.name)
    #         return ""

    #     # Check if title and artist have been guessed
    #     def mq_check(m):
    #         if (self.title_flag != None) and (self.artist_flag != None):
    #             if self.title_flag == self.artist_flag:
    #                 increment_score(m.author.name)
    #             return True
           
    #     try:
    #         # If title isn't guessed compare guess to the title
    #         if self.title_flag == "":
    #             self.title_flag = await client.wait_for("message", check=title_check)
    #         # If artist isn't guessed compare guess to the artist
    #         if self.artist_flag == "":
    #             self.artist_flag = await client.wait_for("message", check=artist_check)
    #         # End round when title and artist are guessed
    #         await client.wait_for("message", check=mq_check, timeout=mq_duration)
    #     except asyncio.TimeoutError:
    #         # Stop the round if users don't guess in time
    #         await mq_stop(self.mq_interaction)
    #         await channel.send(
    #             f"Round over.\nTitle: {title_case(self.correct_title)}\nArtist: {title_case(self.correct_artist)}."
    #         )
    #     else:
    #         # Stop the round and announce the round winner
    #         await mq_stop(self.mq_interaction)
    #         await channel.send(f"Successfully guessed {title_case(self.correct_title)} by {title_case(self.correct_artist)}")
    #         #Sort player score dictionary from highest to lowest
    #         sorted_list = sorted(self.player_score.items(), key = lambda x:x[1], reverse=True)
    #         sorted_dict = dict(sorted_list)
    #         # Add each player and their score to game results embed
    #         for key, value in sorted_dict.items():
    #             score = str(value) + " pts"
    #             self.score_embed.add_field(name=key, value=score)
    #         #Send game results embed
    #         await self.mq_interaction.send(embed=self.score_embed)
    #         for key, value in sorted_dict.items():
    #             self.score_embed.remove_field(0)

    # @nextcord.slash_command()
    # async def mq_swap(self, interaction: Interaction):
    #     """Debugging command to manually switch music quiz channel"""
    #     self.mq_channel = None
    #     await interaction.send(f"Status is {self.mq_channel}")

    

def setup(bot):
    bot.add_cog(Music(bot))
