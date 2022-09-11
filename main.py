import nextcord, os, pymongo, random, config
from nextcord.ext import commands
from log import log

def main():
    # Allows privileged intents for monitoring members joining, roles editing, and role assignments
    # These need to be enabled in the developer portal as well
    intents = nextcord.Intents.all()    

    # Database config
    client = pymongo.MongoClient(os.getenv('CONN_STRING'))

    # Name our access to our client database
    db = client.NextcordBot    

    # Subclass our bot instance
    class NextcordBot(commands.AutoShardedBot):
        def __init__(self, **kwargs):
            super().__init__()

    # Instantiate the bot
    bot = NextcordBot(intents=intents)

    # Define bot behaviour on start up
    @bot.event
    async def on_ready():
        """When discord is connected"""
        collections = db.list_collection_names()
        for c in ['birthdays', 'rules', 'keywords', 'songs', 'velkoz']:
            if c not in collections:
                db.create_collection(c)

        await bot.change_presence(activity = nextcord.Activity(
        type=nextcord.ActivityType.listening, 
        name="commands, @ me for help!"
        ))
        print(f"Collections: {collections}")
        print(f"Intents: {intents}")
        print(f'We have logged in as {bot.user}')
    
    # Define bot behaviour on joining server
    @bot.event
    async def on_guild_join(guild):
        # Add an entry for starter keywords
        if db.keywords.find_one({"_id": guild.id}) == None:
            db.keywords.insert_one({
                "_id": guild.id, 
                "sad": config.sad_words, 
                "filter": config.filter_words, 
                "encouragements": config.encouragements,
                "status": False})
    
    # Defining bot behaviour on leaving server
    @bot.event
    async def on_guild_remove(guild):
        for collection in db.list_collection_names():
            mycol = db[collection]
            mycol.delete_many({"_id": guild.id})
    
    # Defining bot behaviour when a message is sent
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

        if bot.user.mentioned_in(message) and not message.mention_everyone:
            commands_list = bot.get_application_commands()
            cmds = []
            for cmd in commands_list:
                cmds.append(cmd.qualified_name)
            cmds.sort()
            bot_commands = ", ".join(cmds)
            embed = nextcord.Embed(
                title=f"{bot.user.name} Commands",
                description=bot_commands,
                color=nextcord.Colour.from_rgb(225, 0, 255))
            await message.channel.send(embed=embed)

    # Add functionality from cogs
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            bot.load_extension(f'cogs.{filename[:-3]}')

    # Tell the bot to store logs in nextcord.log
    log()

    # Run Discord bot
    bot.run(os.getenv('DISCORD_TOKEN'))


if __name__ == "__main__":
    main()
