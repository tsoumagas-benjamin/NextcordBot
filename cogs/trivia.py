import nextcord
import aiohttp
import random
import asyncio
from nextcord import Interaction
from nextcord.ext import commands

# Dropdown classes for Trivia
class Answers(nextcord.ui.Select): 
    def __init__(self, wrong: list[str], right: str, score: dict):
        self.wrong = wrong
        self.right = right
        self.score = score
        # Get list of right and wrong options
        selects: list[nextcord.SelectOption] = []
        for w in self.wrong:
            selects.append(nextcord.SelectOption(label = w))
        selects.append(nextcord.SlashOption(label = right))
        # Shuffle options so the last one is not always the correct one
        selects = random.shuffle(selects)
        super().__init__(
            placeholder="Select an answer", 
            max_values=1, 
            min_values=1, 
            options=selects
            )
    # Let the user know if they were correct or not and update score
    async def callback(self, interaction: nextcord.Interaction):
        if self.values[0] == self.right:
            if interaction.user in self.score:
                self.score[interaction.user] += 1
            else:
                self.score[interaction.user] = 0
            await interaction.response.send_message(f"{self.values[0]} is correct!", ephemeral=True)
        else:
            await interaction.response.send_message(f"{self.values[0]} is incorrect!", ephemeral=True)

class TriviaView(nextcord.ui.View):
    def __init__(self, *, wrong: list[str], right: str, score: dict, timeout = 10):
        super().__init__(timeout=timeout)
        self.add_item(Trivia.Answers(wrong, right, score))

#Create a cog for image manipulation
class Trivia(commands.Cog, name="Trivia"):
    """Commands related to trivia."""

    COG_EMOJI = "🎲"

    # Initialize all the default variables we need for trivia
    def __init__(self) -> None:
        self.bot = bot
        self.url = f'https://the-trivia-api.com/api/questions/'
        self.categories: list[str] = []
        self.corrects: list[str] = []
        self.incorrects: list[str] = []
        self.questions: list[str] = []
        self.difficulties: list[str] = []
        self.score: dict = dict()
        self.embed: nextcord.Embed = nextcord.Embed(
            title = "Trivia Results", 
            color=nextcord.Colour.from_rgb(214, 60, 26)
            )
    
    @nextcord.slash_command()
    async def trivia(self, interaction: Interaction):
        """Play 10 rounds of trivia with friends"""
        # Instantiate a Trivia object
        t = Trivia()

        # Get trivia content from the API
        async with aiohttp.ClientSession() as cs:
            async with cs.get(t.url) as r:
                res = await r.json()
                for question in range(0,10):
                    t.categories.append(res[question]['category'])
                    t.corrects.append(res[question]['correctAnswer'])
                    t.incorrects.append(res[question]['incorrectAnswers'])
                    t.questions.append(res[question]['questions'])
                    t.difficulties.append(res[question]['difficulty'])
                await cs.close()
        
        await interaction.send("Trivia Time!")
        msg = await interaction.original_message()
        # Each round takes 10 seconds
        for x in range(0,10):
            content = f"**{t.questions[x]}**\n> {t.categories[x]} - {t.difficulties[x].title()}"
            await msg.edit(content=content, view=TriviaView(t.incorrects[x], t.corrects[x], t.score))
            await asyncio.sleep(10)
        # Sort player scores in descending order and convert back to dictionary
        sorted_score = sorted(t.score.items(), key=lambda x:x[1], reverse=True)
        sorted_dict = dict(sorted_score)
        # Add each player and their score to game results embed
        for k, v in sorted_dict.items():
            score = str(v) + "pts"
            self.embed.add_field(name=k, value=score)
        # Send game results embed
        self.embed.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon.url)
        await msg.edit(embed=self.embed)


#Add the cog to the bot
def setup(bot):
    bot.add_cog(Trivia(bot))