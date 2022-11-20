import nextcord, pymongo, os, re, wavelink, datetime, random, asyncio
from nextcord import Interaction
from nextcord.ext import commands, application_checks
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


# TODO: Fix music quiz functionality
class Music(commands.Cog, name="Music"):
    """Commands for playing music in voice channels"""

    COG_EMOJI = "🎵"

    def __init__(self, bot):
        self.bot = bot
        self.mq_status = False
        self.mq_interaction = None
        self.song_indices = []
        self.player_dict = {}
        bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Connect to our lavalink nodes"""
        await self.bot.wait_until_ready()
        await wavelink.NodePool.create_node(
            bot=self.bot,
            host="lavalink.oops.wtf",
            port=443,
            password="www.freelavalink.ga",
            https=True,
        )

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        """Event fired when a node has finished connecting"""
        print(f"Node: {node.identifier} is ready!")

    @commands.Cog.listener()
    async def on_wavelink_track_end(
        self, player: wavelink.Player, track: wavelink.YouTubeTrack, reason
    ):
        interaction = player.interaction
        vc: player = interaction.guild.voice_client

        if vc.loop:
            return await vc.play(track)

        # If queue finishes and is empty
        if vc.queue.is_empty:
            await asyncio.sleep(120)  # Disconnect after 2 minutes of inactivity
            while vc.is_playing():
                break
            else:
                return await vc.disconnect()

        next_song = vc.queue.get()
        await vc.play(next_song)
        await interaction.send(f"Now playing: {next_song.title}")

    @nextcord.slash_command()
    async def disconnect(self, interaction: Interaction):
        """Disconnects the bot from the voice channel."""
        if not interaction.guild.voice_client:
            return await interaction.send("Nothing is playing.")
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first.")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        await vc.disconnect()
        await interaction.send("Left the voice channel.")

    @nextcord.slash_command()
    async def loop(self, interaction: Interaction):
        """Loops current song."""
        if not interaction.guild.voice_client:
            return await interaction.send("I am not in a voice channel.")
        elif not interaction.user.voice:
            return await interaction.send("Join a voice channel first.")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        try:
            vc.loop ^= True
        except Exception:
            setattr(vc, "loop", False)

        if vc.loop:
            return await interaction.send("Now looping the current song.")
        else:
            return await interaction.send("No longer looping the current song.")

    @nextcord.slash_command()
    async def music_quiz(self, interaction: Interaction):
        """Starts music quiz."""
        # Start of game message
        await interaction.send(
            f"Music quiz, {mq_rounds} rounds, {mq_duration} seconds each."
        )
        # Join user's voice channel
        if not interaction.guild.voice_client:
            vc: wavelink.Player = await interaction.user.voice.channel.connect(
                cls=wavelink.Player
            )
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        await vc.set_volume(default_volume)

        vc.interaction = interaction
        try:
            if vc.loop:
                return
        except Exception:
            setattr(vc, "loop", False)

        # Clear dictionary that stores player score
        self.player_dict = {}
        # Setup the embed to store game results
        score_embed.set_footer(
            icon_url=interaction.guild.icon.url, text=interaction.guild.name
        )
        # Make a list from available titles and artists
        titles = song_list.find({}, {"title": 1, "_id": 0})
        artists = song_list.find({}, {"artist": 1, "_id": 0})
        title_list, artist_list = [], []
        for t in titles:
            title_list.append(t["title"])
        for a in artists:
            artist_list.append(a["artist"])
        print(title_list)
        print(artist_list)
        # Randomize songs for as many rounds as needed
        index_list = range(0, int(song_list.count_documents({})) + 1)
        self.song_indices = random.sample(index_list, mq_rounds)

        # Enable music quiz responses to be read in the channel and declare start interaction
        self.mq_status = True
        self.mq_interaction = interaction

    @commands.Cog.listener("on_message")
    async def mq(self, message):
        # If the message is from a bot or music quiz is inactive, don't react
        if message.author.bot or self.mq_status == False:
            return

        channel = message.channel
        ctx = await self.bot.get_context(message)
        title_flag = ""
        artist_flag = ""

        # Check if user response matches the correct title
        def title_check(m):
            s1 = "".join(e for e in m.content.lower() if e.isalnum())
            s2 = "".join(e for e in correct_title.lower() if e.isalnum())
            percent_correct = fuzz.token_set_ratio(s1, s2)
            if percent_correct >= mq_leniency:
                increment_score(m.author.name)
                return str(m.author.name)
            return ""

        # Check if user response matches the correct artist
        def artist_check(m):
            s1 = "".join(e for e in m.content.lower() if e.isalnum())
            s2 = "".join(e for e in correct_artist.lower() if e.isalnum())
            percent_correct = fuzz.token_set_ratio(s1, s2)
            if percent_correct >= mq_leniency:
                increment_score(m.author.name)
                return str(m.author.name)
            return ""

        # Check if title and artist have been guessed
        def mq_check(m):
            return (title_flag != "") and (artist_flag != "")

        async def mq_disconnect(self, interaction: Interaction):
            """Disconnects the bot from the voice channel."""
            if not interaction.guild.voice_client:
                return await interaction.send("Nothing is playing.")
            elif not getattr(interaction.user.voice, "channel", None):
                return await interaction.send("Join a voice channel first.")
            elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
                return await interaction.send(
                    "We have to be in the same voice channel."
                )
            else:
                vc: wavelink.Player = interaction.guild.voice_client

            await vc.disconnect()
            await interaction.send("Music quiz has ended.")

        async def mq_play(self, interaction: Interaction, search: str):
            """Plays a song in a voice channel."""
            search = await wavelink.YouTubeTrack.search(query=search, return_first=True)
            if not interaction.guild.voice_client:
                vc: wavelink.Player = await interaction.user.voice.channel.connect(
                    cls=wavelink.Player
                )
            elif not getattr(interaction.user.voice, "channel", None):
                return await interaction.send("Join a voice channel first")
            elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
                return await interaction.send(
                    "We have to be in the same voice channel."
                )
            else:
                vc: wavelink.Player = interaction.guild.voice_client

            if vc.queue.is_empty and not vc.is_playing():
                await vc.set_volume(default_volume)
                await vc.play(search)
            else:
                await vc.queue.put_wait(search)

            vc.interaction = interaction
            try:
                if vc.loop:
                    return
            except Exception:
                setattr(vc, "loop", False)

        async def mq_stop(self, interaction: Interaction):
            """Stops the current song."""
            if not interaction.guild.voice_client:
                return await interaction.send("Nothing is playing.")
            elif not getattr(interaction.user.voice, "channel", None):
                return await interaction.send("Join a voice channel first.")
            elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
                return await interaction.send(
                    "We have to be in the same voice channel."
                )
            else:
                vc: wavelink.Player = interaction.guild.voice_client

            await vc.stop()
            await interaction.send("Music stopped.")

        for i in range(mq_rounds):
            # Start of round
            await asyncio.sleep(3)
            await channel.send(f"Starting round {i+1}")
            # Set guess flags to false at round start
            title_flag = ""
            artist_flag = ""
            # Make the correct song the first one from our random list
            index = self.song_indices[i]
            correct_title = title_list[index]
            correct_artist = artist_list[index]
            # Play the song at volume
            print("Playing " + title_list[index] + " by " + artist_list[index])
            await mq_play(
                self.mq_interaction, title_list[index] + " by " + artist_list[index]
            )
            try:
                # If title isn't guessed compare guess to the title
                if title_flag == "":
                    title_flag = await client.wait_for("message", check=title_check)
                # If artist isn't guessed compare guess to the artist
                if artist_flag == "":
                    artist_flag = await client.wait_for("message", check=artist_check)
                # End round when title and artist are guessed
                await client.wait_for("message", check=mq_check, timeout=mq_duration)
            except asyncio.TimeoutError:
                # Stop the round if users don't guess in time
                await mq_stop(self.mq_interaction)
                await channel.send(
                    f"Round over.\n Title: {title_case(correct_title)}\nArtist: {title_case(correct_artist)}."
                )
            else:
                # Stop the round and announce the round winner
                await mq_stop(self.mq_interaction)
                await channel.send(
                    f"Successfully guessed {title_case(correct_title)} by {title_case(correct_artist)}"
                )
                # Sort player score dictionary from highest to lowest
                sorted_list = sorted(
                    player_score.items(), key=lambda x: x[1], reverse=True
                )
                sorted_dict = dict(sorted_list)
                # Add each player and their score to game results embed
                for key, value in sorted_dict.items():
                    score = str(value) + " pts"
                    score_embed.add_field(name=key, value=score)
                # Send game results embed
                await ctx.send(embed=score_embed)
                for key, value in sorted_dict.items():
                    score_embed.remove_field(0)
        # Announce end of the game
        await channel.send("Music quiz is done.")
        # Sort player score dictionary from highest to lowest
        sorted_list = sorted(player_score.items(), key=lambda x: x[1], reverse=True)
        sorted_dict = dict(sorted_list)
        # Add each player and their score to game results embed
        for key, value in sorted_dict.items():
            score = str(value) + " pts"
            score_embed.add_field(name=key, value=score)
        # Send game results embed and leave voice channel
        await ctx.send(embed=score_embed)
        await mq_disconnect(self.mq_interaction)
        self.mq_status = False
        return

    @nextcord.slash_command()
    async def mq_swap(self, interaction: Interaction):
        """Debugging command to manually switch music quiz status"""
        self.mq_status = not self.mq_status
        await interaction.send(f"Status is {self.mq_status}")

    @nextcord.slash_command()
    async def nowplaying(self, interaction: Interaction):
        """Returns the currently playing song"""
        if not interaction.guild.voice_client:
            return await interaction.send("I am not in a voice channel.")
        elif not interaction.user.voice:
            return await interaction.send("Join a voice channel first.")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        if not vc.is_playing():
            return await interaction.send("Nothing is playing.")

        embed = nextcord.Embed(
            title=f"Now playing {vc.track.title}",
            description=f"Artist {vc.track.author}",
            color=nextcord.Colour.from_rgb(225, 0, 255),
        )
        full_time = str(datetime.timedelta(seconds=vc.position))
        timestamp = full_time.split(".", 1)[0]
        embed.add_field(name="Timestamp", value=f"{str(timestamp)}")
        embed.add_field(
            name="Duration", value=f"{str(datetime.timedelta(seconds=vc.track.length))}"
        )
        embed.add_field(name="Song URL", value=f"[Click Here]({str(vc.track.uri)})")

        return await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def pause(self, interaction: Interaction):
        """Pauses the current song."""
        if not interaction.guild.voice_client:
            return await interaction.send("Nothing is playing.")
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        await vc.pause()
        await interaction.send("Music paused.")

    @nextcord.slash_command()
    async def play(self, interaction: Interaction, search: str):
        """Plays a song in a voice channel."""
        if not interaction.guild.voice_client:
            vc: wavelink.Player = await interaction.user.voice.channel.connect(
                cls=wavelink.Player
            )
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        if search.startswith("https://"):
            if "list" in search:
                playlist = await wavelink.YouTubePlaylist.search(query=search)
                for track in playlist.tracks:
                    await interaction.send(f"Added {playlist.name.title}.")
                    await vc.queue.put_wait(track)
                if not vc.is_playing():
                    track = await vc.queue.get_wait()
                    await interaction.send(f"Now playing: {track.title}.")
                    return await vc.play(track)
            else:
                track = await vc.node.get_tracks(query=search, cls=wavelink.Track)
        else:
            track = await wavelink.YouTubeTrack.search(search)
        
        if vc.queue.is_empty and not vc.is_playing():
            await vc.set_volume(15)
            await interaction.send(f"Now playing: {track.title}.")
            await vc.play(track[0])
        else:
            await interaction.send(f"Added {track.title} to the queue.")
            await vc.queue.put_wait(track[0])

        vc.interaction = interaction
        try:
            if vc.loop:
                return
        except Exception:
            setattr(vc, "loop", False)

    @nextcord.slash_command()
    async def queue(self, interaction: Interaction):
        """Returns songs in the queue."""
        if not interaction.guild.voice_client:
            return await interaction.send("I am not in a voice channel.")
        elif not interaction.user.voice:
            return await interaction.send("Join a voice channel first.")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        if vc.queue.is_empty:
            return await interaction.send("Queue is empty")

        embed = nextcord.Embed(
            title="Queue", color=nextcord.Colour.from_rgb(225, 0, 255)
        )
        queue = vc.queue.copy()
        song_count = 0
        for song in queue:
            song_count += 1
            embed.add_field(name=f"{song_count}.", value=f"`{song.title}`")

        return await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def resume(self, interaction: Interaction):
        """Resumes the current song."""
        if not interaction.guild.voice_client:
            return await interaction.send("Nothing is playing.")
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        await vc.resume()
        await interaction.send("Music resumed.")

    @nextcord.slash_command()
    async def stop(self, interaction: Interaction):
        """Stops the current song."""
        if not interaction.guild.voice_client:
            return await interaction.send("Nothing is playing.")
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first.")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        await vc.stop()
        await interaction.send("Music stopped.")

    @nextcord.slash_command()
    async def volume(self, interaction: Interaction, volume: int):
        """Changes the music volume."""
        if not interaction.guild.voice_client:
            return await interaction.send("I am not in a voice channel.")
        elif not interaction.user.voice:
            return await interaction.send("Join a voice channel first.")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        if volume < 0 or volume > 100:
            return await interaction.send("Volume must be between 0 and 100.")
        await interaction.send(f"Set the volume to {volume}%.")
        return await vc.set_volume(volume)


def setup(bot):
    bot.add_cog(Music(bot))
