# import nextcord, NextcordUtils, pymongo, os, re, random, asyncio
# from nextcord.ext import commands
# from fuzzywuzzy import fuzz

# #Name our access to the music library
# music = NextcordUtils.Music()

# #Set up our mongodb client
# client = pymongo.MongoClient(os.getenv('CONN_STRING'))

# #Name our access to our client database
# db = client.NextcordBot

# #Get all the existing collections
# collections = db.list_collection_names()

# #Get access to the songs collection
# song_list = db['songs']

# #Music Quiz Variables
# mq_rounds = 10
# mq_duration = 30
# mq_vol = 25
# mq_leniency = 90

# def title_case(s):
#   return re.sub(r"[A-Za-z]+('[A-Za-z]+)?", lambda mo: mo.group(0)[0].upper() + mo.group(0)[1:].lower(),s)

# # Modified version of play for music quiz
# async def mq_play(ctx, *, url):
#     player = music.get_player(guild_id=ctx.guild.id)
#     if not player:
#         player = music.create_player(ctx, ffmpeg_error_betterfix=True)
#     if not ctx.voice_client.is_playing():
#         await player.queue(url, search=True)
#         await player.play()
#     else:
#         await player.queue(url, search=True)   

# # Modified version of skip for music quiz
# async def mq_skip(ctx):
#     player = music.get_player(guild_id=ctx.guild.id)
#     await player.skip(force=True)

# # Modified version of volume for music quiz
# async def mq_volume(ctx, vol):
#     player = music.get_player(guild_id=ctx.guild.id)
#     await player.change_volume(float(vol) / 100) # volume should be a float between 0 to 1

# # Modified version of pause for music quiz
# async def mq_pause(ctx):
#     player = music.get_player(guild_id=ctx.guild.id)
#     await player.pause()
    
# # Modified version of stop for music quiz
# async def mq_stop(ctx):
#     player = music.get_player(guild_id=ctx.guild.id)
#     await player.stop()


# class Music(commands.Cog, name="Music"):
#     """Commands for playing music in voice channels"""

#     COG_EMOJI = "🎵"

#     def __init__(self, bot):
#         self.bot = bot
        
#     @commands.command(aliases=['as'])
#     async def addsong(self, ctx, *, song):
#         """Adds a song to the music quiz playlist
        
#         Example: `$addsong Africa, Toto`"""
#         title, artist = song.split(", ",2)
#         title = title_case(title)
#         artist = title_case(artist)
#         input = {"title":title, "artist":artist}
#         song_list.insert_one(input)
#         await ctx.send(f"Added {title} by {artist}")

#     @commands.command(aliases=['ds'])
#     async def deletesong(self, ctx, *, song):
#         """Deletes a song from the music quiz playlist
        
#         Example: `$deletesong Africa, Toto`"""
#         title, artist = song.split(", ",2)
#         title = title_case(title)
#         artist = title_case(artist)
#         input = {"title":title, "artist":artist}
#         song_list.delete_one(input)
#         await ctx.send(f"Deleted {title} by {artist}")

#     @commands.command()
#     async def songs(self, ctx):
#         """Gets all songs available for music quiz
        
#         Example: `$songs`"""
#         embed = nextcord.Embed(title="Songs", description="Songs that will appear in music quiz.", color=nextcord.Colour.blurple())
#         song_cursor = song_list.find({}, {"_id":0, "title":1, "artist":1})
#         for song in song_cursor:
#             embed.add_field(name=f"{song['title']}", value=f"{song['artist']}")
#         await ctx.send(embed=embed)

#     @commands.command(aliases=['rs'])
#     async def randomsong(self, ctx):
#         """Gets a random song from the music quiz playlist
        
#         Example: `$randomsong`"""
#         object = song_list.aggregate([{ "$sample": { "size": 1 }}])
#         for x in object:
#             title, artist = x['title'], x['artist']
#         await ctx.send(f"{title} by {artist}")
        
#     @commands.command()
#     async def join(self, ctx):
#         """Get the bot to join a voice channel
        
#         Example: `$join`"""
#         await ctx.author.voice.channel.connect() #Joins author's voice channel
        
#     @commands.command()
#     async def leave(self, ctx):
#         """Get the bot to leave a voice channel
        
#         Example: `$leave`"""
#         await ctx.voice_client.disconnect()
        
#     @commands.command()
#     async def play(self, ctx, *, url):
#         """Get the bot to play a song from a url
        
#         Example: `$play https://youtu.be/dQw4w9WgXcQ"""
#         player = music.get_player(guild_id=ctx.guild.id)
#         if not player:
#             player = music.create_player(ctx, ffmpeg_error_betterfix=True)
#         if not ctx.voice_client.is_playing():
#             await player.queue(url, search=True)
#             song = await player.play()
#             await ctx.send(f"Playing {song.name}")
#         else:
#             song = await player.queue(url, search=True)
#             await ctx.send(f"Queued {song.name}")     
#     @commands.command()
#     async def pause(self, ctx):
#         """Get the bot to pause the music
        
#         Example: `$pause`"""
#         player = music.get_player(guild_id=ctx.guild.id)
#         song = await player.pause()
#         await ctx.send(f"Paused {song.name}")
        
#     @commands.command()
#     async def resume(self, ctx):
#         """Get the bot to resume the music
        
#         Example: `$resume`"""
#         player = music.get_player(guild_id=ctx.guild.id)
#         song = await player.resume()
#         await ctx.send(f"Resumed {song.name}")
        
#     @commands.command()
#     async def stop(self, ctx):
#         """Get the bot to stop the music and leave the voice channel
        
#         Example: `$stop`"""
#         player = music.get_player(guild_id=ctx.guild.id)
#         await player.stop()
#         await ctx.send("Stopped")
        
#     @commands.command()
#     async def loop(self, ctx):
#         """Get the bot to loop the current song
        
#         Example: `$loop`"""
#         player = music.get_player(guild_id=ctx.guild.id)
#         song = await player.toggle_song_loop()
#         if song.is_looping:
#             await ctx.send(f"Enabled loop for {song.name}")
#         else:
#             await ctx.send(f"Disabled loop for {song.name}")
        
#     @commands.command()
#     async def queue(self, ctx):
#         """Show all the songs currently queued to play in open
        
#         Example: `$queue`"""
#         player = music.get_player(guild_id=ctx.guild.id)
#         await ctx.send(f"{', '.join([song.name for song in player.current_queue()])}")
        
#     @commands.command()
#     async def np(self, ctx):
#         """Get information on the song currently Playing
        
#         Example: `$np`"""
#         player = music.get_player(guild_id=ctx.guild.id)
#         song = player.now_playing()
#         await ctx.send(song.name)
        
#     @commands.command()
#     async def skip(self, ctx):
#         """Skip the currently playing song
        
#         Example: `$skip`"""
#         player = music.get_player(guild_id=ctx.guild.id)
#         data = await player.skip(force=True)
#         if len(data) == 2:
#             await ctx.send(f"Skipped from {data[0].name} to {data[1].name}")
#         else:
#             await ctx.send(f"Skipped {data[0].name}")

#     @commands.command()
#     async def volume(self, ctx, vol):
#         """Changes the bot's volume (0-100)
        
#         Example: `$volume 25`"""
#         player = music.get_player(guild_id=ctx.guild.id)
#         song, volume = await player.change_volume(float(vol) / 100) # volume should be a float between 0 to 1
#         await ctx.send(f"Changed volume for {song.name} to {volume*100}%")
        
#     @commands.command()
#     async def remove(self, ctx, index):
#         """Removes a song at a specified index
        
#         Example: `$remove 3`"""
#         player = music.get_player(guild_id=ctx.guild.id)
#         song = await player.remove_from_queue(int(index))
#         await ctx.send(f"Removed {song.name} from queue")
    
#     #TODO: Implement music quiz functionality
#     @commands.listen('on_message')
#     async def mq(self, message):
#         # If the message is from a bot, don't react
#         if message.author.bot:
#             return

#         prefix = str(db.guilds.find_one({"_id": message.guild.id})['prefix'] + "mq")
#         if message.content == prefix:
#             # Initialize variables
#             channel = message.channel
#             ctx = await self.bot.get_context(message)
#             title_flag = ''
#             artist_flag = ''
#             # Game start
#             await channel.send(f"Music quiz, {mq_rounds} rounds, {mq_duration} each.")
#             #If bot isn't in a voice channel, join the user's
#             if self.bot.voice_clients == []:
#                 await ctx.author.voice.channel.connect()
#             #Initialize dictionary to store player score
#             player_dict = {}
#             #Setup the embed to store game results
#             embed = nextcord.Embed(title = "Music Quiz", description = "Results", color = nextcord.Colour.blurple())
#             embed.set_footer(icon_url = ctx.guild.icon_url, text = ctx.guild.name)
#             #Make a list from available titles and artists
#             title_list = []
#             artist_list = []
#             song_cursor = song_list.find({}, {"_id":0, "title":1, "artist":1})
#             for song in song_cursor:
#                 title_list.append(song['title'])
#                 artist_list.append(song['artist'])
#             #Randomize songs for as many rounds as needed
#             index_list = range(0,len(title_list))
#             randomized_indices = random.sample(index_list,mq_rounds)

#             #Function to increment player score
#             def increment_score(name):
#                 if name in player_dict:
#                     player_dict[str(name)] += 1
#                 else:
#                     player_dict[str(name)] = 1

#             #Check if user response matches the correct title
#             def title_check(m, ans):
#                 s1 = ''.join(e for e in m.content.lower() if e.isalnum())
#                 s2 = ''.join(e for e in ans.lower() if e.isalnum())
#                 percent_correct = fuzz.token_set_ratio(s1,s2)
#                 if percent_correct >= mq_leniency:
#                     increment_score(m.author.name)
#                     return str(m.author.name)
#                 return ''
            
#             #Check if user response matches the correct artist
#             def artist_check(m, ans):
#                 s1 = ''.join(e for e in m.content.lower() if e.isalnum())
#                 s2 = ''.join(e for e in ans.lower() if e.isalnum())
#                 percent_correct = fuzz.token_set_ratio(s1,s2)
#                 if percent_correct >= mq_leniency:
#                     increment_score(m.author.name)
#                     return str(m.author.name)
#                 return ''
            
#             #Check if title and artist have been guessed
#             def mq_check(m):
#                 return ((title_flag != '') and (artist_flag != ''))
            
#             for i in range(mq_rounds):
#                 #Start of round
#                 await asyncio.sleep(3)
#                 await channel.send(f"Starting round {i+1}")
#                 #Set guess flags to false at round start
#                 title_flag = ''
#                 artist_flag = ''
#                 #Make the correct song the first one from our random list
#                 index = randomized_indices[i]
#                 correct_title = title_list[index]
#                 correct_artist = artist_list[index]
#                 #Play the song at volume
#                 print("Playing " + title_list[index] + " by " + artist_list[index])
#                 await mq_play(ctx,title_list[index]+" by "+artist_list[index])
#                 await mq_volume(ctx, mq_vol)
#                 try:
#                     #If title isn't guessed compare guess to the title
#                     if title_flag == '':
#                         title_flag = await client.wait_for('message',check=title_check)
#                     #If artist isn't guessed compare guess to the artist
#                     if artist_flag == '':
#                         artist_flag = await client.wait_for('message',check=artist_check)
#                     #End round when title and artist are guessed
#                     guess = await client.wait_for('message',check=mq_check,timeout=mq_duration)
#                 except asyncio.TimeoutError:
#                     #Stop the round if users don't guess in time
#                     await mq_skip(ctx)
#                     await mq_pause(ctx)
#                     await channel.send(f"Round over.\n Title: {title_case(correct_title)}\nArtist: {title_case(correct_artist)}.")
#                 else:
#                     #Stop the round and announce the round winner
#                     await mq_skip(ctx)
#                     await mq_pause(ctx)
#                     await channel.send(f"Successfully guessed {title_case(correct_title)} by {title_case(correct_artist)}")
#                 #Sort player score dictionary from highest to lowest
#                 sorted_list = sorted(player_dict.items(), key = lambda x:x[1], reverse=True)
#                 sorted_dict = dict(sorted_list)
#                 #Add each player and their score to game results embed
#                 for key, value in sorted_dict.items():
#                     score = str(value) + " pts"
#                     embed.add_field(name=key, value=score)
#                 #Send game results embed
#                 await ctx.send(embed=embed)
#                 for key, value in sorted_dict.items():
#                     embed.remove_field(0)
#             #Announce end of the game
#             await channel.send("Music quiz is done.")
#             #Sort player score dictionary from highest to lowest
#             sorted_list = sorted(player_dict.items(), key = lambda x:x[1], reverse=True)
#             sorted_dict = dict(sorted_list)
#             #Add each player and their score to game results embed
#             for key, value in sorted_dict.items():
#                 score = str(value) + " pts"
#                 embed.add_field(name=key, value=score)
#             #Send game results embed and leave voice channel
#             await ctx.send(embed=embed)
#             await mq_stop(ctx)
#             return
    

# def setup(bot):
#     bot.add_cog(Music(bot))