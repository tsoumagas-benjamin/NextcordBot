import stoat
from random import shuffle
from asyncio import sleep
from stoat.ext import commands
from utilities import ChaosBot


class TriviaQuestion:
    def __init__(self, content: str, wrong: list[str], right: str, score: dict):
        self.content = content
        self.wrong = wrong
        self.right = right
        self.score = score
        self.options = shuffle(wrong.append(right))
        self.choices = ["🇦", "🇧", "🇨", "🇩"]
        self.correct = ""
        self.message = None
        self.responders = []

    def generate_embed(self) -> stoat.SendableEmbed:
        # Add in a prompt for players and options
        embed_description = "Type the number for your choice!\n"
        for x in range(len(self.options)):
            if self.options[x] == self.right:
                self.correct = self.choices[x]
            embed_description += f"{self.choices[x]}: {self.options[x]}\n"

        embed = stoat.SendableEmbed(title=self.content, description=embed_description)

        return embed

    # Function to react to embed message with 1-4 emojis
    def generate_choices(self, message: stoat.Message):
        self.message = message
        self.message.react("🇦")
        self.message.react("🇧")
        self.message.react("🇨")
        self.message.react("🇩")

    @commands.Gear.listener()
    async def handle_response(self, to: stoat.MessageReactEvent):
        # TODO: If someone responds to a trivia question, update their score accordingly
        if to.user_id in self.responders or to.message is not self.message:
            return
        else:
            if to.emoji in self.choices:
                self.responders.append(to.user_id)
                if to.emoji == self.correct:
                    if to.user_id in self.score:
                        self.score[to.user_id] += 1
                    else:
                        self.score[to.user_id] = 1
        return self.correct


# Class to handle trivia setup and initialization
class TriviaSetup:
    def __init__(self):
        self.url = "https://the-trivia-api.com/api/questions/"
        self.categories: list[str] = []
        self.corrects: list[str] = []
        self.incorrects: list[str] = []
        self.questions: list[str] = []
        self.difficulties: list[str] = []
        self.score: dict = dict()
        self.embed: stoat.SendableEmbed = stoat.SendableEmbed(
            title="Trivia Results", color=stoat.Colour.from_rgb(0, 128, 255)
        )

    def get_score(self):
        return self.score

    def set_score(self, user: stoat.User):
        if user in self.score:
            self.score[user.display_name] += 1
        else:
            self.score[user.display_name] = 1
        return None

    def display_score(self, server: stoat.Server):
        # Sort player scores in descending order and convert back to dictionary
        sorted_score = sorted(self.score.items(), key=lambda x: x[1], reverse=True)
        sorted_dict = dict(sorted_score)
        # Add each player and their score to game results embed
        score_fields = ""
        for name, score in sorted_dict.items():
            total = str(score) + "pts"
            score_fields += f"{name}\t{total}\n"
        # Send game results embed
        score_embed = stoat.SendableEmbed(
            title=f"Trivia Results for {server.name}",
            description=score_fields,
            color="purple",
            icon_url=server.icon.url,
        )
        return score_embed


# Create a gear for image manipulation
class Trivia(commands.Gear, name="Trivia"):
    """Commands related to trivia."""

    GEAR_EMOJI = "🎲"

    # Initialize all the default variables we need for trivia
    def __init__(self, bot: ChaosBot) -> None:
        self.bot = bot

    @commands.command()
    async def trivia(self, ctx: commands.Context):
        """Play 10 rounds of trivia with friends"""
        # Instantiate a TriviaSetup object
        ts = TriviaSetup()

        # Get trivia content from the API
        res = await self.bot.client.get_json(ts.url)
        for question in range(0, 10):
            ts.categories.append(res[question]["category"])
            ts.corrects.append(res[question]["correctAnswer"])
            ts.incorrects.append(res[question]["incorrectAnswers"])
            ts.questions.append(res[question]["question"])
            ts.difficulties.append(res[question]["difficulty"])

        await ctx.channel.send("Trivia Time!")
        # Each round takes 10 seconds with each trivia question having it's own embed
        for x in range(0, 10):
            content = f"**{ts.questions[x]}**\n> {ts.categories[x]} - {ts.difficulties[x].title()}"
            trivia_question = TriviaQuestion(
                content, ts.incorrects[x], ts.corrects[x], ts.score
            )
            trivia_embed: stoat.SendableEmbed = trivia_question.generate_embed()
            question_message: stoat.Message = await ctx.channel.send(
                embeds=[trivia_embed]
            )
            trivia_question.generate_choices(question_message)
            await sleep(10)
        # Send game results embed
        score_embed = ts.display_score(ctx.server)
        await ctx.channel.send(embeds=[score_embed])


# Add the gear to the bot
def setup(bot: ChaosBot):
    bot.add_gear(Trivia(bot))
