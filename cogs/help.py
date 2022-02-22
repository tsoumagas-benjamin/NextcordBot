from typing import Set
from nextcord.ext import commands
import nextcord

class HelpDropdown(nextcord.ui.Select):
    def __init__(self, help_command: "MyHelpCommand", options):
        super().__init__(placeholder="Choose a category...", min_values=1, max_values=1, options=options)
        self.help_command = help_command

    async def callback(self, interaction: nextcord.Interaction):
        embed = (
            await self.help_command.cog_help_embed(self.help_command.context.bot.get_cog(self.values[0]))
            if self.values[0] != self.options[0].value
            else await self.help_command.bot_help_embed(self.help_command.get_bot_mapping())
        )
        await interaction.response.edit_message(embed=embed)


class HelpView(nextcord.ui.View):
    def __init__(self, help_command: "MyHelpCommand", options, *, timeout: float = 120.0):
        super().__init__(timeout=timeout)
        self.add_item(HelpDropdown(help_command, options))
        self.help_command = help_command

    async def on_timeout(self):
        # remove dropdown from message on timeout
        self.clear_items()
        await self.help_command.response.edit(view=self)

    async def interaction_check(self, interaction: nextcord.Interaction):
        return self.help_command.context.author == interaction.user


class MyHelpCommand(commands.MinimalHelpCommand):
    def get_command_signature(self, command):
        return f"{self.context.clean_prefix}{command.qualified_name} {command.signature}"

    async def cog_select_options(self):
        options = []
        options.append(nextcord.SelectOption(
            label="Home",
            emoji="🏠",
            description="Go back to the main menu.",
        ))

        for cog, command_set in self.get_bot_mapping().items():
            filtered = await self.filter_commands(command_set, sort=True)
            if not filtered:
                continue
            emoji = getattr(cog, "COG_EMOJI", None)
            options.append(nextcord.SelectOption(
                label=cog.qualified_name.title() if cog else "No Category",
                emoji=emoji,
                description=cog.description[:100] if cog and cog.description else None
            ))

        return options

    async def help_embed(
        self, title: str, description: str = None, mapping: str = None,
        command_set: Set[commands.Command] = None, set_author: bool = False
    ):
        embed = nextcord.Embed(title=title, color=nextcord.Colour.blurple())
        if description:
            embed.description = description
        if set_author:
            avatar = self.context.bot.user.avatar or self.context.bot.user.default_avatar
            embed.set_author(name=self.context.bot.user.name, icon_url=avatar)
        if command_set:
            # show help about all commands in the set
            filtered = await self.filter_commands(command_set, sort=True)
            for command in filtered:
                embed.add_field(
                    name=self.get_command_signature(command),
                    value=command.short_doc or "...",
                    inline=True
                )
        elif mapping:
            # add a short description of commands in each cog
            for cog, command_set in mapping.items():
                filtered = await self.filter_commands(command_set, sort=True)
                if not filtered:
                    continue
                name = cog.qualified_name.title() if cog else "No category"
                emoji = getattr(cog, "COG_EMOJI", None)
                cog_label = f"{emoji} {name}" if emoji else name
                # \u2002 is an en-space
                cmd_list = "\u2002".join(
                    f"`{self.context.clean_prefix}{cmd.name}`" for cmd in filtered
                )
                value = (
                    f"{cog.description}\n\n{cmd_list}"
                    if cog and cog.description
                    else cmd_list
                )
                embed.add_field(name=cog_label, value=value)
                embed.set_footer(text=f"Type `{self.context.clean_prefix}help <category>` for more information on a category.\nType `{self.context.clean_prefix}help <command>` for more information on a command.")
        return embed

    async def bot_help_embed(self, mapping: dict):
        return await self.help_embed(
            title="PersonalDiscordBot Commands",
            description=self.context.bot.description,
            mapping=mapping,
            set_author=True
        )
    
    async def send_bot_help(self, mapping: dict):
        embed = await self.bot_help_embed(mapping)
        options = await self.cog_select_options()
        self.response = await self.get_destination().send(embed=embed, view=HelpView(self, options))

    async def send_command_help(self, command: commands.Command):
        emoji = getattr(command.cog, "COG_EMOJI", None)
        embed = await self.help_embed(
            title=f"{emoji} {command.qualified_name.title()}" if emoji else command.qualified_name,
            description=command.help,
            command_set=command.commands if isinstance(command, commands.Group) else None
        )
        await self.get_destination().send(embed=embed)

    async def cog_help_embed(self, cog: commands.Cog = None):
        if cog is None:
            return await self.help_embed(
                title=f"No category",
                command_set=self.get_bot_mapping()
            )
        emoji = getattr(cog, "COG_EMOJI", None)
        return await self.help_embed(
            title=f"{emoji} {cog.qualified_name.title()}" if emoji else cog.qualified_name.title(),
            description=cog.description,
            command_set=cog.get_commands()
        )

    async def send_cog_help(self, cog: commands.Cog):
        embed = await self.cog_help_embed(cog)
        await self.get_destination().send(embed=embed)

    # Use the same function as command help for group help
    send_group_help = send_command_help

class HelpCog(commands.Cog, name="Help"):
    """Shows help info for commands and cogs"""

    COG_EMOJI = "❔"

    def __init__(self, bot):
        self.original_help_command = bot.help_command
        bot.help_command = MyHelpCommand()
        bot.help_command.cog = self

def setup(bot):
    bot.add_cog(HelpCog(bot))