from typing import List, Tuple
import nextcord
from nextcord.ext import commands, menus

# Template for Paginated Help Command Cog from
# https://menus.docs.nextcord.dev/en/stable/ext/menus/pagination_examples/#paginated-help-command-cog


class HelpPageSource(menus.ListPageSource):
    """Page source for dividing the list of tuples into pages and displaying them in embeds"""

    def __init__(self, help_command: "CustomHelpCommand", data: List[Tuple[str, str]]):
        self._help_command = help_command
        # Initialize items displayed per page here
        super().__init__(data, per_page=2)

    async def format_page(
        self, menu: menus.ButtonMenuPages, entries: List[Tuple[str, str]]
    ):
        """
        Returns an embed containing the entries for the current page
        """
        prefix = self._help_command.context.clean_prefix
        invoked_with = self._help_command.invoked_with
        # Create embed for the help page
        embed = nextcord.Embed(
            title="Chaos Bot Commands", colour=self._help_command.COLOUR
        )
        embed.description = (
            f'Use "{prefix}{invoked_with} command" for more info on a command.\n'
            f'Use "{prefix}{invoked_with} category" for more info on a category.'
        )
        # Add entries to the embed
        for entry in entries:
            embed.add_field(name=entry[0], value=entry[1], inline=True)
        # Set the footer to display the page number
        embed.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
        return embed


class HelpButtonMenuPages(menus.ButtonMenuPages):
    """Subclass of ButtonMenuPages to add an interaction_check"""

    def __init__(self, ctx: commands.Context, **kwargs):
        super().__init__(**kwargs)
        self._ctx = ctx

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        """Ensure that the user of the button is the one who called the help command"""
        return self._ctx.author == interaction.user


class CustomHelpCommand(commands.MinimalHelpCommand):
    """Custom help command override using embeds and button pagination"""

    # Set the embed colour
    COLOUR = nextcord.Colour.from_rgb(0, 128, 255)

    def get_command_signature(self, command: commands.core.Command):
        """Retrieves the signature portion of the help page."""
        return (
            f"{self.context.clean_prefix}{command.qualified_name} {command.signature}"
        )

    async def send_bot_help(self, mapping: dict):
        """Implements bot command help page"""
        prefix = self.context.clean_prefix
        invoked_with = self.invoked_with
        embed = nextcord.Embed(title="Chaos Bot Commands", colour=self.COLOUR)
        embed.description = (
            f'Use "{prefix}{invoked_with} command" for more info on a command.\n'
            f'Use "{prefix}{invoked_with} category" for more info on a category.'
        )

        # Create a list of tuples for the page source
        embed_fields = []
        for cog, commands in mapping.items():
            name = "No Category" if cog is None else cog.qualified_name
            filtered = await self.filter_commands(commands, sort=True)
            if filtered:
                # \u2002 = en space
                value = "\u2002".join(f"`{prefix}{c.name}`" for c in filtered)
                if cog and cog.description:
                    value = f"{cog.description}\n{value}"
                # Add (name, value) pair to the list of fields
                embed_fields.append((name, value))

        # Create a pagination menu that paginates the fields
        pages = HelpButtonMenuPages(
            ctx=self.context,
            source=HelpPageSource(self, embed_fields),
            disable_buttons_after=True,
        )
        await pages.start(self.context)

    async def send_cog_help(self, cog: commands.Cog):
        """Implements cog help page"""
        embed = nextcord.Embed(
            title=f"{cog.qualified_name} Commands",
            colour=self.COLOUR,
        )
        if cog.description:
            embed.description = cog.description

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(
                name=self.get_command_signature(command),
                value=command.short_doc or "...",
                inline=False,
            )
        embed.set_footer(
            text=f"Use {self.context.clean_prefix}help [command] for more info on a command."
        )
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group: commands.Group):
        """Implements group help page and command help page"""
        embed = nextcord.Embed(title=group.qualified_name, colour=self.COLOUR)
        if group.help:
            embed.description = group.help

        if isinstance(group, commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                embed.add_field(
                    name=self.get_command_signature(command),
                    value=command.short_doc or "...",
                    inline=False,
                )

        await self.get_destination().send(embed=embed)

    # Use the same function as group help for command help
    send_command_help = send_group_help


class HelpCog(commands.Cog, name="Help"):
    """Displays help information for commands and cogs"""

    def __init__(self, bot: commands.AutoShardedBot):
        self.__bot = bot
        self.__original_help_command = bot.help_command
        bot.help_command = CustomHelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        self.__bot.help_command = self.__original_help_command


def setup(bot: commands.AutoShardedBot):
    bot.add_cog(HelpCog(bot))
