from collections.abc import Sequence
import nextcord
from os import getenv
from pymongo import MongoClient
from nextcord.ext import commands, application_checks
import datetime

client = MongoClient(getenv('CONN_STRING')) 
db = client.NextcordBot 

# Create a cog for audit log functionality
class Audit(commands.Cog, name="Audit Logs"):
    """Commands for managing server event logs"""

    COG_EMOJI = "📋"
    
    def __init__(self, bot) -> None:
      self.bot = bot

    # Function to format
    def date_format(self, time: datetime.datetime):
        return time.strftime("%m/%d/%Y %H:%M:%S")
    
    # Function to send embeds to the designated channel
    async def send_embed(self, audit_channel_id: int, target_embed: nextcord.Embed):
        audit_channel = self.bot.get_channel(audit_channel_id)
        if audit_channel is None:
            audit_channel = await self.bot.fetch_channel(audit_channel_id)
        await audit_channel.send(embed=target_embed)
    
    # Function to set audit log channel for this server
    @nextcord.slash_command()
    @application_checks.has_permissions(manage_guild=True)
    async def set_audit_log(self, interaction: nextcord.Interaction, channel: str):
        """Takes in a channel link/ID and sets it as the automated audit log channel for this server."""

        # Get the channel ID as an integer whether the user inputs a channel link or channel ID
        audit_log_id = int(channel.split("/")[-1])
        # Prepares the new guild & channel combination for this server
        new_channel = {"guild": interaction.guild_id, "channel": audit_log_id}
        # Updates the daily channel for the server or inserts it if one doesn't exist currently
        db.audit_logs.replace_one({"guild": interaction.guild_id}, new_channel, upsert=True)

        # Let users know where the updated channel is
        updated_channel = interaction.guild.get_channel(audit_log_id)
        if updated_channel is None:
            updated_channel = await self.bot.fetch_channel(audit_log_id)
        await interaction.send(f"Audit logs for this server will go to {updated_channel.name}.")
    
    # Function to remove audit log channel for this server
    @nextcord.slash_command()
    @application_checks.has_permissions(manage_guild=True)
    async def remove_audit_log(self, interaction: nextcord.Interaction):
        """Removes the automated audit log channel for this server, if it exists."""

        # Removes the daily channel for the server if it exists
        if db.audit_logs.find_one({"guild": interaction.guild_id}):
            db.audit_logs.delete_one({"guild": interaction.guild_id})
            await interaction.send("Audit logs for this server are stopped.")

        # Lets the user know if there is no existing audit log channel
        else:
            await interaction.send("There is no audit log channel for this server.")

    # Record when a server channel is created
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: nextcord.abc.GuildChannel):

        # If there is no assigned audit log channel for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": channel.guild.id})
        if not server_audit_log:
            return
       
        # Handle the different kind of channels that can be made and category if applicable
        if isinstance(channel, nextcord.TextChannel):
            create_channel = nextcord.Embed(title="Text Channel Created", color=nextcord.Colour.green())
            create_channel.add_field(name="Category", value=f"{channel.category}")
        elif isinstance(channel, nextcord.VoiceChannel):
            create_channel = nextcord.Embed(title="Voice Channel Created", color=nextcord.Colour.green())
            create_channel.add_field(name="Category", value=f"{channel.category}")
        elif isinstance(channel, nextcord.CategoryChannel):
            create_channel = nextcord.Embed(title="Category Channel Created", color=nextcord.Colour.green())
        elif isinstance(channel, nextcord.StageChannel):
            create_channel = nextcord.Embed(title="Stage Channel Created", color=nextcord.Colour.green())
            create_channel.add_field(name="Category", value=f"{channel.category}")
        else:
            create_channel = nextcord.Embed(title="Forum Channel Created", color=nextcord.Colour.green())
            create_channel.add_field(name="Category", value=f"{channel.category}")

        # Add channel name to the embed
        create_channel.add_field(name="Name", value=f"{channel.name}")

        # Format the time the channel was created at and the channel ID into the footer
        create_channel.set_footer(text=f"Channel ID: {channel.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], create_channel)

    # Record when a server channel is deleted
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: nextcord.abc.GuildChannel):

        # If there is no assigned audit log channel for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": channel.guild.id})
        if not server_audit_log:
            return
       
        # Handle the different kind of channels that can be made and their categories if applicable
        if isinstance(channel, nextcord.TextChannel):
            delete_channel = nextcord.Embed(title="Text Channel deleted", color=nextcord.Colour.red())
            delete_channel.add_field(name="Category", value=f"{channel.category}")
        elif isinstance(channel, nextcord.VoiceChannel):
            delete_channel = nextcord.Embed(title="Voice Channel deleted", color=nextcord.Colour.red())
            delete_channel.add_field(name="Category", value=f"{channel.category}")
        elif isinstance(channel, nextcord.CategoryChannel):
            delete_channel = nextcord.Embed(title="Category Channel deleted", color=nextcord.Colour.red())
        elif isinstance(channel, nextcord.StageChannel):
            delete_channel = nextcord.Embed(title="Stage Channel deleted", color=nextcord.Colour.red())
            delete_channel.add_field(name="Category", value=f"{channel.category}")
        else:
            delete_channel = nextcord.Embed(title="Forum Channel deleted", color=nextcord.Colour.red())
            delete_channel.add_field(name="Category", value=f"{channel.category}")

        # Add channel name to the embed
        delete_channel.add_field(name="Name", value=f"{channel.name}")

        # Format the time the channel was deleted at and the channel ID into the footer
        delete_channel.set_footer(text=f"Channel ID: {channel.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], delete_channel)

    # Record when a server channel is updated
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: nextcord.abc.GuildChannel, after: nextcord.abc.GuildChannel):

        # If there is no assigned audit log channel for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": before.guild.id})
        if not server_audit_log:
            return
       
        # Handle the different kind of channels that can be made
        if isinstance(before, nextcord.TextChannel):
            update_channel = nextcord.Embed(title="Text Channel updated", color=nextcord.Colour.blurple())
        elif isinstance(before, nextcord.VoiceChannel):
            update_channel = nextcord.Embed(title="Voice Channel updated", color=nextcord.Colour.blurple())
        elif isinstance(before, nextcord.CategoryChannel):
            update_channel = nextcord.Embed(title="Category Channel updated", color=nextcord.Colour.blurple())
        elif isinstance(before, nextcord.StageChannel):
            update_channel = nextcord.Embed(title="Stage Channel updated", color=nextcord.Colour.blurple())
        else:
            update_channel = nextcord.Embed(title="Forum Channel updated", color=nextcord.Colour.blurple())

        # Add channel name and category to the embed for before and after
        update_channel.add_field(name="Old Name", value=f"{before.name}")
        update_channel.add_field(name="Old Category", value=f"{before.category}")
        update_channel.add_field(name="New Name", value=f"{after.name}")
        update_channel.add_field(name="New Category", value=f"{after.category}")

        # Format the time the channel was updated at and the channel ID into the footer
        update_channel.set_footer(text=f"Channel ID: {before.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], update_channel)

    # Record when a server role is created
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: nextcord.Role):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": role.guild.id})
        if not server_audit_log:
            return
        
        create_role = nextcord.Embed(title="Role Created", color=nextcord.Colour.green())

        # Add role name and category to the embed
        create_role.add_field(name="Name", value=f"{role.name}")
        create_role.add_field(name="Hoisted", value=f"{role.hoist}")
        create_role.add_field(name="Integration Role", value=f"{role.managed}")
        create_role.add_field(name="Mentionable", value=f"{role.mentionable}")

        # Format the time the role was created at and the role ID into the footer
        create_role.set_footer(text=f"Role ID: {role.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], create_role)
    
    # Record when a server role is deleted
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: nextcord.Role):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": role.guild.id})
        if not server_audit_log:
            return
        
        delete_role = nextcord.Embed(title="Role Deleted", color=nextcord.Colour.red())

        # Add role name and category to the embed
        delete_role.add_field(name="Name", value=f"{role.name}")
        delete_role.add_field(name="Hoisted", value=f"{role.hoist}")
        delete_role.add_field(name="Integration Role", value=f"{role.managed}")
        delete_role.add_field(name="Mentionable", value=f"{role.mentionable}")

        # Format the time the role was created at and the role ID into the footer
        delete_role.set_footer(text=f"Role ID: {role.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], delete_role)

    # Record when a server role is updated
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: nextcord.Role, after: nextcord.Role):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": before.guild.id})
        if not server_audit_log:
            return
        
        # Only record if one of the following traits are updated
        if (
            (before.name == after.name) and 
            (before.hoist == after.hoist) and 
            (before.managed == after.managed) and 
            (before.mentionable == after.mentionable)):
            return
        
        update_role = nextcord.Embed(title="Role Updated", color=nextcord.Colour.blurple())

        # Add role name and category to the embed
        update_role.add_field(name="Name", value=f"{before.name} -> {after.name}")
        update_role.add_field(name="Hoisted", value=f"{before.hoist} -> {after.hoist}")
        update_role.add_field(name="Integration Role", value=f"{before.managed} -> {after.managed}")
        update_role.add_field(name="Mentionable", value=f"{before.mentionable} -> {after.mentionable}")

        # Format the time the role was created at and the role ID into the footer
        update_role.set_footer(text=f"Role ID: {before.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], update_role)

    # Record when a server updates
    @commands.Cog.listener()
    async def on_guild_update(self, before: nextcord.Guild, after: nextcord.Guild):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": before.id})
        if not server_audit_log:
            return

        update_server = nextcord.Embed(title="Server Updated", color=nextcord.Colour.blurple())

        # Add role name and category to the embed
        update_server.add_field(name="Before Name", value=f"{before.name}")
        update_server.add_field(name="After Name", value=f"{after.name}")

        # Format the time the role was created at and the role ID into the footer
        update_server.set_footer(text=f"Server ID: {before.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], update_server)

    # Record when an emoji is added or deleted
    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: nextcord.Guild, before: Sequence[nextcord.Emoji], after: Sequence[nextcord.Emoji]):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": guild.id})
        if not server_audit_log:
            return
        
        old_emoji = [emoji for emoji in before if emoji not in after]
        new_emoji = [emoji for emoji in after if emoji not in before]
        for emoji in old_emoji:
            print(emoji.name)
        for emoji in new_emoji:
            print(emoji.name)
        
        # Check if an emoji is removed, added, or updated
        if len(before) > len(after):
            emoji_update = nextcord.Embed(title="Emoji Deleted", color=nextcord.Colour.red())
            # Get emojis that used to exist but are deleted and add them to the embed
            deleted_emoji = [emoji for emoji in before if emoji not in after]
            emoji_update.add_field(name="Old Name", value=f"{deleted_emoji[0].name}")
            emoji_update.set_footer(text=f"Emoji ID: {deleted_emoji[0].id} | {self.date_format(datetime.datetime.now())}")

        elif len(before) < len(after):
            emoji_update = nextcord.Embed(title="Emoji Created", color=nextcord.Colour.green())
            # Get emojis that have been created and add them to the embed
            created_emoji = [emoji for emoji in after if emoji not in before]
            emoji_update.add_field(name="New Name", value=f"<:{created_emoji[0].name}:{created_emoji[0].id}> {created_emoji[0].name}")
            emoji_update.set_footer(text=f"Emoji ID: {created_emoji[0].id} | {self.date_format(datetime.datetime.now())}")

        else:
            emoji_update = nextcord.Embed(title="Emoji Updated", color=nextcord.Colour.blurple())
            # Get emojis that have been updated and add them to the embed
            old_emoji = [emoji for emoji in before if emoji not in after]
            new_emoji = [emoji for emoji in after if emoji not in before]
            for emoji in old_emoji:
                print(emoji.name)
            for emoji in new_emoji:
                print(emoji.name)
            emoji_update.add_field(name="Updated Name", value=f"{old_emoji[0].name} -> <:{new_emoji[0].name}:{new_emoji[0].id}> {new_emoji[0].name}")
            emoji_update.set_footer(text=f"Emoji ID: {new_emoji[0].id} | {self.date_format(datetime.datetime.now())}")
        
        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], emoji_update)

    # Record when a member's roles are updated
    @commands.Cog.listener()
    async def on_member_update(self, before: nextcord.Member, after: nextcord.Member):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": after.guild.id})
        if (not server_audit_log or before.bot or after.bot):
            return 
        
        # Check if a role has been added
        if len(before.roles) < len(after.roles):
            member_update = nextcord.Embed(title="Role Added", description=f"{after.display_name}", color=nextcord.Colour.green())
            new_role = [role for role in after.roles if role not in before.roles]
            member_update.add_field(name=new_role[0].name, value=new_role[0].mention)
        
        # Check if a role has been removed
        elif len(before.roles) > len(after.roles):
            member_update = nextcord.Embed(title="Role Removed", description=f"{after.display_name}", color=nextcord.Colour.red())
            removed_role = [role for role in before.roles if role not in after.roles]
            member_update.add_field(name=removed_role[0].name, value=removed_role[0].mention)

        # If none of the above conditions are met, do nothing
        else:
            return
        
        # Set the thumbnail and footer
        member_update.set_thumbnail(after.display_avatar.url)
        member_update.set_footer(text=f"Member ID: {after.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], member_update)

    # Records when a user's avatar is updated
    @commands.Cog.listener()
    async def on_user_update(self, before: nextcord.User, after: nextcord.User):
        # Get mutual guilds where the user and this bot is set up for audit logs
        mutuals = after.mutual_guilds

        for guild in mutuals:
            # If there is no assigned audit log role for this server, return before creating an embed
            server_audit_log = db.audit_logs.find_one({"guild": guild.id})
            if (not server_audit_log or before.bot or after.bot):
                continue
            
            # Check if the user's avatar is changed
            if before.display_avatar != after.display_avatar:
                user_update = nextcord.Embed(title="Avatar Update", description=f"{after.mention}", color=nextcord.Colour.blurple())
                user_update.add_field(name="Old Avatar", value=f"[View]({before.display_avatar.url})")
                user_update.add_field(name="New Avatar", value=f"[View]({after.display_avatar.url})")

            # Check if the user's username has changed
            elif (before.display_name != after.display_name):
                user_update = nextcord.Embed(title="Display Name Update", description=f"{after.mention}", colour=nextcord.Colour.blurple())
                user_update.add_field(name=f"{before.display_name} -> {after.display_name}", value=after.mention)
            
            # Set the thumbnail and footer
            user_update.set_thumbnail(after.display_avatar.url)
            user_update.set_footer(text=f"Member ID: {after.id} | {self.date_format(datetime.datetime.now())}")

            # Send the embed to the designated channel
            await self.send_embed(server_audit_log['channel'], user_update)


    # Records when a member is banned
    @commands.Cog.listener()
    async def on_member_ban(self, guild: nextcord.Guild,  user: nextcord.User):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": guild.id})
        if (not server_audit_log or user.bot):
            return 
        
        member_ban = nextcord.Embed(title="Member Banned", color=nextcord.Colour.red())
        member_ban.add_field(name=f"{user.display_name}", value=user.mention)

        # Set the thumbnail and footer
        member_ban.set_thumbnail(user.display_avatar.url)
        member_ban.set_footer(text=f"Member ID: {user.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], member_ban)

    # Records when a member is unbanned
    @commands.Cog.listener()
    async def on_member_unban(self, guild: nextcord.Guild,  user: nextcord.User):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": guild.id})
        if (not server_audit_log or user.bot):
            return 
        
        member_unban = nextcord.Embed(title="Member Unbanned", color=nextcord.Colour.green())
        member_unban.add_field(name=f"{user.display_name}", value=user.mention)

        # Set the thumbnail and footer
        member_unban.set_thumbnail(user.display_avatar.url)
        member_unban.set_footer(text=f"Member ID: {user.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], member_unban)
    
    # Records when a message is deleted
    @commands.Cog.listener()
    async def on_message_delete(self, message: nextcord.Message):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": message.guild.id})
        if (not server_audit_log or message.author.bot):
            return
        
        message_delete = nextcord.Embed(title=f"Message Deleted in #{message.channel.name}", color=nextcord.Colour.red())

        # If there are attachments, mention them and the deleted filenames
        if message.attachments:
            message_delete.add_field(name="Attachments", value="\n".join(message.attachments))
        
        # If there is content, add content of the deleted message
        if message.content:
            message_delete.add_field(name=f"{message.content}", value=f"Deleted by {message.author.mention}")

        # Set the thumbnail and footer
        message_delete.set_thumbnail(message.author.display_avatar.url)
        message_delete.set_footer(text=f"Message ID: {message.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], message_delete)
    
    # Records when a message is edited
    @commands.Cog.listener()
    async def on_message_edit(self, before: nextcord.Message, after: nextcord.Message):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": after.guild.id})
        if (not server_audit_log or before.author.bot or after.author.bot or (before.content == after.content)):
            return
        
        message_edit = nextcord.Embed(title=f"Message Edited in #{after.channel.name}", color=nextcord.Colour.blurple())

        # If attachments are removed, mention them and the deleted filenames
        if len(before.attachments) > len(after.attachments):
            removed_attachments = [attachment for attachment in before.attachments if attachment not in after.attachments]
            message_edit.add_field(name="Attachments", value="\n".join(removed_attachments))
        
        # If message content has changed, record it
        if before.content is not after.content:
            message_edit.add_field(name=f"{before.content} -> {after.content}", value=f"Edited by {after.author.mention}")
        
        # Set the thumbnail and footer
        message_edit.set_thumbnail(after.author.display_avatar.url)
        message_edit.set_footer(text=f"Message ID: {after.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], message_edit)
    
    # Records when a member joins
    @commands.Cog.listener()
    async def on_member_join(self, member: nextcord.Member):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": member.guild.id})
        if not server_audit_log:
            return

        member_join = nextcord.Embed(title="Member Joined", color=nextcord.Colour.green())
        member_join.add_field(name=f"{member.display_name} #{member.guild.member_count}", value=f"Created at: {member.created_at}")

        # Set the thumbnail and footer
        member_join.set_thumbnail(member.display_avatar.url)
        member_join.set_footer(text=f"Member ID: {member.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], member_join)

    # Records when a member leaves
    @commands.Cog.listener()
    async def on_member_remove(self, member: nextcord.Member):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"guild": member.guild.id})
        if not server_audit_log:
            return

        member_remove = nextcord.Embed(title="Member Left", color=nextcord.Colour.red())
        member_remove.add_field(name=f"{member.display_name}", value=f"Joined at: {self.date_format(member.joined_at)}")

        # Get a list of role names
        role_names = []
        for role in member.roles:
            if role.name != "@everyone":
                role_names.append(role.mention)
            role_names.reverse()

        member_remove.add_field(name="Roles", value=", ".join(role_names))

        # Set the thumbnail and footer
        member_remove.set_thumbnail(member.display_avatar.url)
        member_remove.set_footer(text=f"Member ID: {member.id} | {self.date_format(datetime.datetime.now())}")

        # Send the embed to the designated channel
        await self.send_embed(server_audit_log['channel'], member_remove)

def setup(bot):
    bot.add_cog(Audit(bot))