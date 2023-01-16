import nextcord, pymongo, os, json, lavaplayer, re, datetime, random, asyncio
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

lavalink = lavaplayer.Lavalink(
    host="lavalink.botsuniversity.ml",  # Lavalink host
    port=443,  # Lavalink port
    password="mathiscool",  # Lavalink password
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

    @commands.Cog.listener()
    async def on_ready(self):
        lavalink.set_user_id(self.bot.user.id)
        lavalink.set_event_loop(self.bot.loop)
        lavalink.connect()
    
    @commands.Cog.listener()
    async def on_socket_raw_receive(msg):
        data = json.loads(msg)

        if not data or not data["t"]:
            return
        if data["t"] == "VOICE_SERVER_UPDATE":
            guild_id = int(data["d"]["guild_id"])
            endpoint = data["d"]["endpoint"]
            token = data["d"]["token"]

            await lavalink.raw_voice_server_update(guild_id, endpoint, token)

        elif data["t"] == "VOICE_STATE_UPDATE":
            if not data["d"]["channel_id"]:
                channel_id = None
            else:
                channel_id = int(data["d"]["channel_id"])

            guild_id = int(data["d"]["guild_id"])
            user_id = int(data["d"]["user_id"])
            session_id = data["d"]["session_id"]

            await lavalink.raw_voice_state_update(
                guild_id,
                user_id,
                session_id,
                channel_id,
            )

    @nextcord.slash_command(aliases=["join"])
    async def connect(self, interaction: Interaction):
        """Connects the bot to the voice channel."""
        if not interaction.user.voice:
            await interaction.response.send_message("You are not in a voice channel!")
            return
        await interaction.guild.change_voice_state(
            channel=interaction.user.voice.channel, self_deaf=True, self_mute=False
        )
        await lavalink.wait_for_connection(interaction.guild.id)
        await interaction.response.send_message("Joined the voice channel.")

    @nextcord.slash_command(aliases=["leave"])
    async def disconnect(self, interaction: Interaction):
        """Disconnects the bot from the voice channel."""
        await interaction.guild.change_voice_state(channel=None)
        await lavalink.wait_for_remove_connection(interaction.guild.id)
        await interaction.response.send_message("Left the voice channel.")

    @nextcord.slash_command()
    async def loop(self, interaction: Interaction, loop: bool, queue: bool = False):
        """Enable/Disable looping for the entire queue or a single song."""
        if queue:
            await lavalink.queue_repeat(interaction.guild.id, loop)
        else:
            await lavalink.repeat(interaction.guild.id, loop)
        await interaction.response.send_message("Looped the queue.")

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

    @nextcord.slash_command()
    async def nowplaying(self, interaction: Interaction):
        """Returns the currently playing song"""
        queue = await lavalink.queue(interaction.guild.id)
        current_song = queue[0]
        if not queue:
            return await interaction.response.send_message("No tracks in queue.")

        embed = nextcord.Embed(
            title=f"Now playing: {current_song.title}",
            description=f"Artist: {current_song.author}",
            color=nextcord.Colour.from_rgb(225, 0, 255),
        )
        embed.add_field(
            name="Duration", value=f"{str(datetime.timedelta(seconds=current_song.length))}"
        )
        embed.add_field(name="Song URL", value=f"[Click Here]({str(current_song.uri)})")

        return await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def pause(self, interaction: Interaction):
        """Pauses the current song."""
        await lavalink.pause(interaction.guild.id, True)
        await interaction.response.send_message("Paused the track.")

    @nextcord.slash_command()
    async def play(self, interaction: Interaction, *, search: str):
        """Plays a song in a voice channel."""
        tracks = await lavalink.auto_search_tracks(search)
        if not tracks:
            return await interaction.response.send_message("No results found.")
        elif isinstance(tracks, lavaplayer.TrackLoadFailed):
            await interaction.response.send_message(f"Error loading track, Try again later.\n```{tracks.message}```")
            return
        elif isinstance(tracks, lavaplayer.PlayList):
            await interaction.response.send_message(
                "Playlist found, Adding to queue, Please wait..."
            )
            await lavalink.add_to_queue(
                interaction.guild.id, tracks.tracks, interaction.user.id
            )
            await interaction.edit_original_message(
                content=f"Added to queue, tracks: {len(tracks.tracks)}, name: {tracks.name}"
            )
            return
        await lavalink.play(interaction.guild.id, tracks[0], interaction.user.id)
        await interaction.response.send_message(f"Now playing: {tracks[0].title}")

    @nextcord.slash_command()
    async def queue(self, interaction: Interaction):
        """Returns songs in the queue."""
        queue = await lavalink.queue(interaction.guild.id)
        if not queue:
            return await interaction.response.send_message("No tracks in queue.")
        tracks = [f"**{i + 1}.** {t.title}" for (i, t) in enumerate(queue)]
        await interaction.response.send_message("\n".join(tracks))

    @nextcord.slash_command()
    async def resume(self, interaction: Interaction):
        """Resumes the current song."""
        await lavalink.pause(interaction.guild.id, False)
        await interaction.response.send_message("Resumed the track.")

    @nextcord.slash_command()
    async def resume(self, interaction: Interaction):
        """Shuffles the current queue."""
        await lavalink.shuffle(interaction.guild.id)
        await interaction.response.send_message("Shuffled the queue.")

    @nextcord.slash_command()
    async def skip(self, interaction: Interaction):
        """Skips the current song."""
        await lavalink.skip(interaction.guild.id)
        await interaction.response.send_message("Skipped the track.")

    @nextcord.slash_command()
    async def stop(self, interaction: Interaction):
        await lavalink.stop(interaction.guild.id)
        await interaction.response.send_message("Stopped the track.")

    @nextcord.slash_command()
    async def volume(self, interaction: Interaction, volume: int):
        """Changes the music volume."""
        await lavalink.volume(interaction.guild.id, volume)
        await interaction.response.send_message(f"Set the volume to {volume}%.")

def setup(bot):
    bot.add_cog(Music(bot))
