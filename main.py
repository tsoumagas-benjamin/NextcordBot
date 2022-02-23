import nextcord, os, pymongo, random, config
from nextcord.ext import commands
from log import log

def main():
    # Allows privileged intents for monitoring members joining, roles editing, and role assignments
    # These need to be enabled in the developer portal as well
    intents = nextcord.Intents.default()

    # To enable member intents:
    intents.members = True
    
    # Set custom status to "Listening to ?help"
    activity = nextcord.Activity(
        type=nextcord.ActivityType.listening, name="@ me for help!"
    )

    # Set bot description
    description = '''An example bot to showcase the nextcord.ext.commands extension
    module.
    There are a number of utility commands being showcased here.'''

    # Database config
    client = pymongo.MongoClient(os.getenv('CONN_STRING'))

    #Name our access to our client database
    db = client.NextcordBot

    # Subclass our bot instance
    class NextcordBot(commands.AutoShardedBot):
        def __init__(self, **kwargs):
            super().__init__(
                self.get_prefix,
                description=description,
                intents=intents,
                activity=activity,
            )

        # Overrides bot.get_prefix
        async def get_prefix(self, message: nextcord.Message):
            if db.guilds.find_one({"_id": message.guild.id}) != None:
                output = db.guilds.find_one({"_id": message.guild.id})
                return output['prefix']
            else:
                output = db.guilds.insert_one({"_id": message.guild.id, "prefix": "$"})
                return output['prefix']

    bot = NextcordBot()

    @bot.event
    async def on_ready():
        """When discord is connected"""
        collections = db.list_collection_names()
        for c in ['guilds', 'rules', 'keywords', 'songs']:
            if c not in collections:
                db.create_collection(c)

        print(f"Collections: {collections}")
        print(f'We have logged in as {bot.user}')
    
    @bot.event
    async def on_guild_join(guild):
        # Add an entry for starter keywords
        if db.keywords.find_one({"_id": guild.id}) == None:
            db.keywords.insert_one({"_id": guild.id, "sad": config.sad_words, "filter": config.filter_words, "encouragements": config.encouragements, "status": True})
        # Add an entry for starter guild prefix
        if db.guilds.find_one({"_id": guild.id}) == None:
            db.guilds.insert_one({"_id": guild.id, "prefix": ">"})
    
    @bot.event
    async def on_guild_remove(guild):
        for collection in db.list_collection_names():
            mycol = db[collection]
            mycol.delete_many({"_id": guild.id})
    

    @bot.event
    async def on_message(message):
        # If the message is from a bot, don't react
        if message.author.bot:
            return

        # Tells the bot to also look for commands in messages
        await bot.process_commands(message)

        # Check bot responsiveness for inspiration commands
        respond = db.keywords.find_one({"_id": message.guild.id})
        if respond["status"]:
            options = respond["encouragements"]
            sad_words = respond["sad"]
            filter_words = respond["filter"]

            for word in filter_words:
                if word.lower() in message.content.lower(): 
                    await message.delete()
                    break

            for word in sad_words:
                if word.lower() in message.content.lower():
                    await message.channel.send(random.choice(options))
                    break

        if bot.user.mentioned_in(message):
            curr_channel = message.channel
            if db.guilds.find_one({"_id": message.guild.id}) != None:
                output = db.guilds.find_one({"_id": message.guild.id})
                await curr_channel.send(f"My prefix in this server is {output['prefix']}")
            else:
                await curr_channel.send("My prefix in this server is $")

    # Add functionality from cogs
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            bot.load_extension(f'cogs.{filename[:-3]}')

    # Tell the bot to store logs in nextcord.log
    log()

    # Run Discord bot
    bot.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
