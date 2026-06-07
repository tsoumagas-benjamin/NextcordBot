import stoat
from stoat.ext import commands
from datetime import datetime
from utilities import db, send_embed

# TODO: Switch from MongoDB


# Create a gear for audit log functionality
class Audit(commands.Gear, name="Audit"):
    """Commands for managing server event logs"""

    GEAR_EMOJI = "📋"

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # Function to format
    def date_format(self, time: datetime):
        return time.strftime("%m/%d/%Y %H:%M:%S")

    # Function to set audit log channel for this server
    @commands.command()
    @commands.has_permissions(manage_server=True)
    async def set_audit_log(self, ctx: commands.Context, channel_link: str):
        """Takes in a channel link and sets it as the automated audit log channel for this server."""

        # Get the channel ID
        channel_id: str = channel_link.split("/")[-1]

        # Prepares the new server & channel combination for this server
        new_channel = {"server": ctx.server.id, "channel": channel_id}

        # Updates the daily channel for the server or inserts it if one doesn't exist currently
        db.audit_logs.replace_one({"server": ctx.server.id}, new_channel, upsert=True)

        # Let users know where the updated channel is
        updated_channel = self.bot.get_channel(channel_id)
        if updated_channel is None:
            updated_channel = await self.bot.fetch_channel(channel_id)
        await ctx.channel.send(
            f"Audit logs for this server will go to {updated_channel.name}."
        )

    # Function to remove audit log channel for this server
    @commands.command()
    @commands.has_permissions(manage_server=True)
    async def remove_audit_log(self, ctx: commands.Context):
        """Removes the automated audit log channel for this server, if it exists."""

        # Removes the daily channel for the server if it exists
        if db.audit_logs.find_one({"server": ctx.server.id}):
            db.audit_logs.delete_one({"server": ctx.server.id})
            await ctx.channel.send("Audit logs for this server are stopped.")

        # Lets the user know if there is no existing audit log channel
        else:
            await ctx.channel.send("There is no audit log channel for this server.")

    # Record when a server channel is created
    @commands.Gear.listener()
    async def on_server_channel_create(self, to: stoat.ServerChannelCreateEvent):
        # Get the created server channel
        target_channel: stoat.ServerChannel = to.channel

        # If there is no assigned audit log channel for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"server": target_channel.server_id})
        if not server_audit_log:
            return

        embed_footer = (
            f"Channel ID: {target_channel.id} | {self.date_format(datetime.now())}"
        )

        # Check if channel is a text or voice channel, create the embed for each
        if target_channel.voice is None:
            create_channel = stoat.SendableEmbed(
                title="Text Channel Created",
                description=f"Name {target_channel.name}\nCategory {target_channel.category.title}\n{embed_footer}",
                color="green",
            )
        else:
            create_channel = stoat.SendableEmbed(
                title="Voice Channel Created",
                description=f"Name {target_channel.name}\nCategory {target_channel.category.title}\n{embed_footer}",
                color="green",
            )

        # Send the embed to the designated channel
        await send_embed(self.bot, server_audit_log["channel"], create_channel)

    # Record when a server channel is deleted
    @commands.Gear.listener()
    async def on_server_channel_delete(self, to: stoat.ChannelDeleteEvent):
        # Get the deleted server channel
        if isinstance(to.channel, stoat.TextChannel):
            target_channel: stoat.TextChannel = to.channel
        else:
            return

        # If there is no assigned audit log channel for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"server": target_channel.server_id})
        if not server_audit_log:
            return

        embed_footer = (
            f"Channel ID: {target_channel.id} | {self.date_format(datetime.now())}"
        )

        # Check if channel is a text or voice channel, create the embed for each
        if target_channel.voice is None:
            delete_channel = stoat.SendableEmbed(
                title="Text Channel Deleted",
                description=f"Name {target_channel.name}\nCategory {target_channel.category.title}\n{embed_footer}"
                + embed_footer,
                color="red",
            )
        else:
            delete_channel = stoat.SendableEmbed(
                title="Voice Channel Deleted",
                description=f"Name {target_channel.name}\nCategory {target_channel.category.title}\n{embed_footer}",
                color="red",
            )

        # Send the embed to the designated channel
        await send_embed(self.bot, server_audit_log["channel"], delete_channel)

    # Record when a server channel is updated
    @commands.Gear.listener()
    async def on_server_channel_update(self, to: stoat.ChannelUpdateEvent):

        # Get the updated server channel
        if isinstance(to.before, stoat.TextChannel):
            target_channel: stoat.TextChannel = to.after
        else:
            return

        # If there is no assigned audit log channel for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"server": to.after.server_id})
        if not server_audit_log:
            return

        # Compare specific attributes of the channel before and after the update
        targeted_attributes = {
            "Category": (to.before.category, to.after.category),
            "Default Permissions": (
                to.before.default_permissions,
                to.after.default_permissions,
            ),
            "Description": (to.before.description, to.after.description),
            "Icon": (to.before.icon, to.after.icon),
            "Name": (to.before.name, to.after.name),
            "NSFW": (to.before.nsfw, to.after.nsfw),
            "Role Permissions": (to.before.role_permissions, to.after.role_permissions),
        }

        attribute_changes: str = ""

        for attribute in targeted_attributes:
            if attribute.value[0] != attribute.value[1]:
                attribute_changes += (
                    f"{attribute.key}:\t{attribute.value[0]} -> {attribute.value[1]}\n"
                )

        # If all targeted attributes are unchanged, return before sending embed
        if attribute_changes == "":
            return

        embed_footer = (
            f"Channel ID: {target_channel.id} | {self.date_format(datetime.now())}"
        )

        # Check if channel is a text or voice channel, create the embed for each
        if target_channel.voice is None:
            update_channel = stoat.SendableEmbed(
                title="Text Channel Updated",
                description=f"Name {target_channel.name}\nCategory {target_channel.category.title}\n{attribute_changes}\n{embed_footer}",
                color="purple",
            )
        else:
            update_channel = stoat.SendableEmbed(
                title="Voice Channel Updated",
                description=f"Name {target_channel.name}\nCategory {target_channel.category.title}\n{attribute_changes}\n{embed_footer}",
                color="purple",
            )

        # Send the embed to the designated channel
        await send_embed(self.bot, server_audit_log["channel"], update_channel)

    # Record when a server role is deleted
    @commands.Gear.listener()
    async def on_server_role_delete(self, on: stoat.ServerRoleDeleteEvent):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"server": on.server_id})
        if not server_audit_log:
            return

        delete_role = stoat.SendableEmbed(
            title="Role Deleted",
            description=f"Name {on.role.name}\tColour {on.role.color}\nRole ID: {on.role_id} | {self.date_format(datetime.now())}",
            color="red",
        )

        # Send the embed to the designated channel
        await send_embed(self.bot, server_audit_log["channel"], delete_role)

    # Record when a server role is updated
    @commands.Gear.listener()
    async def on_server_role_update(self, on: stoat.RawServerRoleUpdateEvent):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"server": on.server.id})
        if not server_audit_log:
            return

        embed_footer = f"Role ID: {on.new_role.id} | {self.date_format(datetime.now())}"

        # Check if role is being created
        if on.old_role is None:
            create_role = stoat.SendableEmbed(
                title="Role Created",
                description=f"Name: {on.new_role.name}\tColour: {on.new_role.color}\tHoist: {on.new_role.hoist}\tRank: {on.new_role.rank}\n{embed_footer}",
                color="green",
            )

            # Send the embed to the designated channel
            await send_embed(self.bot, server_audit_log["channel"], create_role)

        else:
            # Compare specific attributes of the role before and after the update
            targeted_attributes = {
                "Name": (on.old_role.name, on.new_role.name),
                "Colour": (on.old_role.color, on.new_role.color),
                "Hoist": (on.old_role.hoist, on.new_role.hoist),
                "Rank": (on.old_role.rank, on.new_role.rank),
            }

            attribute_changes: str = ""

            for attribute in targeted_attributes:
                if attribute.value[0] != attribute.value[1]:
                    attribute_changes += f"{attribute.key}:\t{attribute.value[0]} -> {attribute.value[1]}\n"

            # If all targeted attributes are unchanged, return before sending embed
            if attribute_changes == "":
                return

            update_role = stoat.SendableEmbed(
                title=" Updated",
                description=f"Name {on.new_role.name}\n{attribute_changes}\n{embed_footer}",
                color="purple",
            )

            # Send the embed to the designated channel
            await send_embed(self.bot, server_audit_log["channel"], update_role)

    # Record when a server updates
    @commands.Gear.listener()
    async def on_server_update(self, on: stoat.ServerUpdateEvent):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"server": on.before.id})
        if not server_audit_log:
            return

        # Compare specific attributes of the role before and after the update
        targeted_attributes = {
            "Name": (on.before.name, on.after.name),
            "Banner": (on.before.banner.url, on.after.banner.url),
            "Description": (on.before.description, on.after.description),
            "Discoverable": (on.before.discoverable, on.after.discoverable),
            "Icon": (on.before.icon.url, on.after.icon.url),
            "NSFW": (on.before.nsfw, on.after.nsfw),
            "Owner": (on.before.owner.display_name, on.after.owner.display_name),
        }

        attribute_changes: str = ""

        for attribute in targeted_attributes:
            if attribute.value[0] != attribute.value[1]:
                attribute_changes += (
                    f"{attribute.key}:\t{attribute.value[0]} -> {attribute.value[1]}\n"
                )

        # Compare changes in categories
        if set(on.before.categories) - set(on.after.categories):
            removed = set(on.before.categories) - set(on.after.categories)
            removed_categories = [category.title for category in removed]
            attribute_changes += f"Categories Removed:\t{removed_categories}\n"
        elif set(on.after.categories) - set(on.before.categories):
            added = set(on.after.categories) - set(on.before.categories)
            added_categories = [category.title for category in added]
            attribute_changes += f"Categories Added:\t{added_categories}\n"

        # Compare changes in default permissions and flags
        if on.before.default_permissions != on.after.default_permissions:
            attribute_changes += "Default Permissions Changed\n"
        if on.before.flags.verified != on.after.flags.verified:
            if on.after.flags.verified:
                attribute_changes += "Server is now verified\n"
            else:
                attribute_changes += "Server is no longer verified\n"
        if on.before.flags.official != on.after.flags.official:
            if on.after.flags.official:
                attribute_changes += "Server is now official"
            else:
                attribute_changes += "Server is no longer official"

        # If all targeted attributes are unchanged, return before sending embed
        if attribute_changes == "":
            return

        update_server = stoat.SendableEmbed(
            title="Server Updated",
            description=f"Name {on.new_role.name}\n{attribute_changes}\nRole ID: {on.after.id} | {self.date_format(datetime.now())}",
            color="purple",
        )

        # Send the embed to the designated channel
        await send_embed(self.bot, server_audit_log["channel"], update_server)

    # Record when an emoji is removed, added, or updated
    @commands.Gear.listener()
    async def on_server_emojis_update(self, on: stoat.ServerUpdateEvent):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"server": on.after.id})
        if (not server_audit_log) or (on.server.emojis is stoat.UNDEFINED):
            return

        emoji_changes: str = ""

        # Check if an emoji was removed
        if len(on.before.emojis) > len(on.after.emojis):
            removed = {
                emoji.id: emoji
                for emoji in on.before.emojis
                if emoji not in on.after.emojis
            }
            for emoji in removed.values():
                emoji_changes += f"Old Name: {emoji.name}\nCreated by: {emoji.creator.name}\nEmoji ID: {emoji.id} | {self.date_format(datetime.now())}"
            emoji_update = stoat.SendableEmbed(
                title="Emoji Removed", description=emoji_changes, color="red"
            )

        # Check if an emoji was added
        elif len(on.before.emojis) < len(on.after.emojis):
            added = {
                emoji.id: emoji
                for emoji in on.after.emojis
                if emoji not in on.before.emojis
            }
            for emoji in added.values():
                emoji_changes += f"New Name: {emoji.name}\nCreated by: {emoji.creator.name}\nEmoji ID: {emoji.id} | {self.date_format(datetime.now())}"
            emoji_update = stoat.SendableEmbed(
                title="Emoji Added", description=emoji_changes, color="green"
            )

        # Check if an emoji was updated
        else:
            removed = {
                emoji.id: emoji
                for emoji in on.before.emojis
                if emoji not in on.after.emojis
            }
            added = {
                emoji.id: emoji
                for emoji in on.after.emojis
                if emoji not in on.before.emojis
            }
            updated = {emoji.id: emoji for emoji in on.server.emojis}
            print(updated)
            for emoji in removed.values():
                emoji_changes += f"{emoji.name} -> "
            for emoji in added.values():
                emoji_changes += f"{emoji.name}\nCreated by: {emoji.creator.name}\nEmoji ID: {emoji.id} | {self.date_format(datetime.now())}"
            emoji_update = stoat.SendableEmbed(
                title="Emoji Updated", description=emoji_changes, color="purple"
            )

        await send_embed(self.bot, server_audit_log["channel"], emoji_update)

    # Record when a member's roles, display name, or server avatar are updated
    @commands.Gear.listener()
    async def on_member_update(self, on: stoat.ServerMemberUpdateEvent):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"server": on.after.server_id})
        if not server_audit_log or on.before.bot or on.after.bot:
            return

        # Return early if there is no changes to the member's roles, display name, or server avatar
        if (
            (on.member.roles is stoat.UNDEFINED)
            or (on.member.display_name is stoat.UNDEFINED)
            or (on.member.server_avatar is stoat.UNDEFINED)
        ):
            return

        embed_footer = f"Member ID: {on.after.id} | {self.date_format(datetime.now())}"

        # Check if a role has been added
        if len(on.before.roles) < len(on.after.roles):
            new_role = [role for role in on.after.roles if role not in on.before.roles]
            update_description = (
                f"{on.after.display_name} +{new_role[0].name}\n{embed_footer}"
            )
            member_update = stoat.SendableEmbed(
                title="Role Added",
                description=update_description,
                icon_url=on.after.server_avatar.url(),
                color="green",
            )

        # Check if a role has been removed
        elif len(on.before.roles) > len(on.after.roles):
            old_role = [role for role in on.before.roles if role not in on.after.roles]
            update_description = (
                f"{on.after.display_name} -{old_role[0].name}\n{embed_footer}"
            )
            member_update = stoat.SendableEmbed(
                title="Role Removed",
                description=update_description,
                icon_url=on.after.server_avatar.url(),
                color="red",
            )

        # Check if the user's username has changed
        elif on.before.display_name != on.after.display_name:
            update_description = f"{on.after.mention}\n{on.before.display_name} -> {on.after.display_name}\n{embed_footer}"
            member_update = stoat.SendableEmbed(
                title="Display Name Update",
                description=update_description,
                icon_url=on.after.server_avatar.url(),
                color="purple",
            )

        # Check if the user's server avatar has changed
        elif on.before.server_avatar != on.after.server_avatar:
            update_description = f"Old Avatar [View]({on.before.server_avatar.url()}) -> New Avatar [View]({on.after.server_avatar.url()})\n{embed_footer}"
            member_update = stoat.SendableEmbed(
                title="Server Avatar Update",
                description=update_description,
                icon_url=on.after.server_avatar.url(),
                color="purple",
            )

        # Send the embed to the designated channel
        await send_embed(self.bot, server_audit_log["channel"], member_update)

    # Records when a member is banned
    @commands.Gear.listener()
    async def on_member_ban(self, on: stoat.UserBannedSystemEvent):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one(
            {"server": on.user_as_member.server_id}
        )
        if not server_audit_log or on.user.bot:
            return

        embed_footer = f"Member ID: {on.user.id} | {self.date_format(datetime.now())}"

        member_ban = stoat.SendableEmbed(
            title="Member Banned",
            description=f"{on.user_as_member.display_name}\n{on.user_as_member.mention}\n{embed_footer}",
            icon_url=on.user_as_member.server_avatar.url(),
            color="red",
        )

        # Send the embed to the designated channel
        await send_embed(self.bot, server_audit_log["channel"], member_ban)

    # Records when a member is unbanned
    @commands.Gear.listener()
    async def on_member_unban(self, on: stoat.UserBannedSystemEvent):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one(
            {"server": on.user_as_member.server_id}
        )
        if not server_audit_log or on.user.bot:
            return

        embed_footer = f"Member ID: {on.user.id} | {self.date_format(datetime.now())}"

        member_unban = stoat.SendableEmbed(
            title="Member Unbanned",
            description=f"{on.user_as_member.display_name}\n{on.user_as_member.mention}\n{embed_footer}",
            icon_url=on.user_as_member.server_avatar.url(),
            color="green",
        )

        # Send the embed to the designated channel
        await send_embed(self.bot, server_audit_log["channel"], member_unban)

    # Records when a message is deleted
    @commands.Gear.listener()
    async def on_message_delete(self, on: stoat.MessageDeleteEvent):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"server": on.message.server.id})
        if not server_audit_log or on.message.author.bot:
            return

        embed_footer = (
            f"Message ID: {on.message.id} | {self.date_format(datetime.now())}"
        )
        embed_contents = ""

        # If there are attachments, mention them and the deleted filenames
        if on.message.attachments:
            attachment_urls = [
                attachment.url() for attachment in on.message.attachments
            ]
            embed_contents += "\n".join(attachment_urls)

        # If there is content, add content of the deleted message
        if on.message.content:
            embed_contents += f"{on.message.content}\nDeleted message from {on.message.author.mention}"

        message_delete = stoat.SendableEmbed(
            title=f"Message Deleted in #{on.message.channel.name}",
            description=embed_contents + embed_footer,
            icon_url=on.message.author.server_avatar.url(),
            color="red",
        )

        # Send the embed to the designated channel
        await send_embed(self.bot, server_audit_log["channel"], message_delete)

    # Records when a message is edited
    @commands.Gear.listener()
    async def on_message_edit(self, on: stoat.MessageUpdateEvent):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"server": on.message.server.id})
        if not server_audit_log or on.before.author.bot or on.after.author.bot:
            return

        embed_footer = (
            f"Message ID: {on.message.id} | {self.date_format(datetime.now())}"
        )
        embed_contents = ""

        # If attachments are removed, mention them and the deleted filenames
        if len(on.before.attachments) > len(on.after.attachments):
            removed_attachments = [
                attachment
                for attachment in on.before.attachments
                if attachment not in on.after.attachments
            ]
            attachment_urls = [attachment.url() for attachment in removed_attachments]
            embed_contents += "Removed Attachments" + "\n".join(attachment_urls)

        # If attachments are added, mention them and the added filenames
        elif len(on.before.attachments) < len(on.after.attachments):
            added_attachments = [
                attachment
                for attachment in on.after.attachments
                if attachment not in on.before.attachments
            ]
            attachment_urls = [attachment.url() for attachment in added_attachments]
            embed_contents += "Added Attachments" + "\n".join(attachment_urls)

        # If message content has changed, record it
        if on.before.content is not on.after.content:
            embed_contents += f"{on.before.content} -> {on.after.content}\nEdited by {on.after.author.mention}"

        message_edit = stoat.SendableEmbed(
            title=f"Message Edited in #{on.after.channel.name}",
            description=embed_contents + embed_footer,
            icon_url=on.after.author.server_avatar.url(),
            color="purple",
        )

        # Send the embed to the designated channel
        await send_embed(self.bot, server_audit_log["channel"], message_edit)

    # Records when a member joins
    @commands.Gear.listener()
    async def on_member_join(self, on: stoat.ServerMemberJoinEvent):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"server": on.member.server_id})
        if not server_audit_log:
            return

        embed_footer = (
            f"Message ID: {on.member.id} | {self.date_format(datetime.now())}"
        )
        embed_contents = ""

        embed_contents += (
            f"{on.member.display_name} #{len(on.member.get_server().members)}\n"
            + f"Joined at: {self.date_format(on.member.joined_at)}"
        )

        member_join = stoat.SendableEmbed(
            title="Member Joined",
            description=embed_contents + embed_footer,
            icon_url=on.member.server_avatar.url(),
            color="green",
        )

        # Send the embed to the designated channel
        await send_embed(self.bot, server_audit_log["channel"], member_join)

    # Records when a member leaves
    @commands.Gear.listener()
    async def on_member_remove(self, on: stoat.ServerMemberRemoveEvent):
        # If there is no assigned audit log role for this server, return before creating an embed
        server_audit_log = db.audit_logs.find_one({"server": on.member.server_id})
        if not server_audit_log:
            return

        embed_footer = (
            f"Message ID: {on.member.id} | {self.date_format(datetime.now())}"
        )
        embed_contents = ""

        embed_contents += (
            f"{on.member.display_name}\n"
            + f"Joined at: {self.date_format(on.member.joined_at)}"
        )

        # Get a list of role names
        role_names = []
        for role in on.member.roles:
            if role.name != "Default Permissions":
                role_names.append(role.mention)
            role_names.reverse()

        embed_contents += "Roles\n" + f"{', '.join(role_names)}"

        member_remove = stoat.SendableEmbed(
            title="Member Left",
            description=embed_contents + embed_footer,
            icon_url=on.member.server_avatar.url(),
            color="red",
        )

        # Send the embed to the designated channel
        await send_embed(self.bot, server_audit_log["channel"], member_remove)


async def setup(bot: commands.Bot):
    bot.add_gear(Audit(bot))
