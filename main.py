import discord
from discord.ext import commands
import datetime
from datetime import timedelta
import json
import os
import asyncio
from discord.ui import View, Button, Modal, TextInput

TOKEN = "" #BOT TOKEN

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=",", intents=intents)

def load_interface_message_data():
    try:
        with open('interface_message_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_interface_message_data(data):
    with open('interface_message_data.json', 'w') as f:
        json.dump(data, f)

def load_temp_channels():
    if os.path.exists("temp_channels.json"):
        with open("temp_channels.json", "r") as file:
            data = json.load(file)
            return data.get("main_channels", []), data.get("temp_channels", {})
    else:
        return [], {}

def save_temp_channels(main_channels, temp_channels):
    with open("temp_channels.json", "w") as file:
        json.dump({"main_channels": main_channels, "temp_channels": temp_channels}, file, indent=4)

main_channels, temporary_channels = load_temp_channels()

@bot.event
async def on_ready():
    bot.last_channel_rename_time = {}
    bot.last_user_limit_change_time = {}

    interface_data = load_interface_message_data()
    for message_id, channel_id in interface_data.items():
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                message = await channel.fetch_message(message_id)
                view = VoiceChannelInterface()
                await message.edit(view=view)
                print(f"Reattached interface view to the message {message_id} in channel {channel_id}.")
                await asyncio.sleep(2)
            except discord.NotFound:
                print(f"The message {message_id} was not found.")

@bot.listen('on_voice_state_update')
async def on_voice_state_update(member, before, after):
    if after.channel and before.channel and before.channel.user_limit != after.channel.user_limit:
        bot.last_user_limit_change_time[after.channel.id] = datetime.datetime.utcnow()

    await create_temporary_channel(member, before, after)

    for channel_id, user_id in list(temporary_channels.items()):
        if user_id == member.id:
            channel = member.guild.get_channel(int(channel_id))
            if channel and not channel.members:
                await channel.delete()
                del temporary_channels[channel_id]
                save_temp_channels(main_channels, temporary_channels)

class RenameChannelModal(Modal):
    def __init__(self, channel, last_change_time):
        super().__init__(title="Rename Voice Channel")
        self.channel = channel
        self.last_change_time = last_change_time
        self.new_name = TextInput(label="New Channel Name", placeholder="Enter new name...", required=True)
        self.add_item(self.new_name)

    async def on_submit(self, interaction: discord.Interaction):
        now = datetime.datetime.utcnow()
        if self.last_change_time is None or now - self.last_change_time > timedelta(minutes=1):
            await self.channel.edit(name=self.new_name.value)
            await interaction.response.send_message(f'Voice channel renamed to {self.new_name.value}', ephemeral=True)
            bot.last_channel_rename_time[self.channel.id] = now
        else:
            await interaction.response.send_message("Please wait for the cooldown before renaming the channel again.", ephemeral=True)

class KickUserModal(Modal):
    def __init__(self, channel):
        super().__init__(title="Kick User from Voice Channel")
        self.channel = channel
        self.user_id = TextInput(label="User ID", placeholder="Enter the User ID to kick...", required=True)
        self.add_item(self.user_id)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = self.user_id.value
        user = interaction.guild.get_member(int(user_id))

        if user and user.voice and user.voice.channel == self.channel:
            await user.move_to(None)
            await interaction.response.send_message(f'User {user.display_name} has been kicked from the voice channel.', ephemeral=True)
        else:
            await interaction.response.send_message('User not found or not in the voice channel.', ephemeral=True)

class SetUserLimitModal(Modal):
    def __init__(self, channel, last_change_time):
        super().__init__(title="Set User Limit")
        self.channel = channel
        self.last_change_time = last_change_time
        self.user_limit = TextInput(label="New User Limit", placeholder="Enter new user limit...", required=True)
        self.add_item(self.user_limit)

    async def on_submit(self, interaction: discord.Interaction):
        now = datetime.datetime.utcnow()
        if self.last_change_time is None or now - self.last_change_time > timedelta(minutes=1):
            try:
                user_limit = int(self.user_limit.value)
                if user_limit < 0:
                    raise ValueError("User limit must be a positive number.")
                await self.channel.edit(user_limit=user_limit)
                await interaction.response.send_message(f'User limit set to {user_limit}', ephemeral=True)
                bot.last_user_limit_change_time[self.channel.id] = now
            except ValueError:
                await interaction.response.send_message('Invalid user limit.', ephemeral=True)
        else:
            await interaction.response.send_message("Please wait for the cooldown before setting the user limit again.", ephemeral=True)

class VoiceChannelInterface(View):
    def __init__(self):
        super().__init__()
        self.timeout = None

    async def ensure_creator(self, interaction: discord.Interaction):
        if interaction.user.voice and interaction.user.voice.channel:
            voice_channel = interaction.user.voice.channel
            creator_id = temporary_channels.get(str(voice_channel.id))
            if creator_id and int(creator_id) == interaction.user.id:
                return voice_channel
            else:
                await interaction.response.send_message('You are not the creator of this voice channel.', ephemeral=True)
        else:
            await interaction.response.send_message('You need to be in a voice channel to use this button.', ephemeral=True)
        return None

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='🔒')
    async def lock_button(self, interaction: discord.Interaction, button: Button):
        voice_channel = await self.ensure_creator(interaction)
        if voice_channel:
            await voice_channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message(f'🔒 {interaction.user.mention}: Voice channel locked.', ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='🔓')
    async def unlock_button(self, interaction: discord.Interaction, button: Button):
        voice_channel = await self.ensure_creator(interaction)
        if voice_channel:
            await voice_channel.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message(f'🔓 {interaction.user.mention}: Voice channel unlocked.', ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='✏️')
    async def rename_button(self, interaction: discord.Interaction, button: Button):
        voice_channel = await self.ensure_creator(interaction)
        if voice_channel:
            modal = RenameChannelModal(voice_channel, bot.last_channel_rename_time.get(voice_channel.id))
            await interaction.response.send_modal(modal)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='👁️')
    async def hide_button(self, interaction: discord.Interaction, button: Button):
        voice_channel = await self.ensure_creator(interaction)
        if voice_channel:
            await voice_channel.set_permissions(interaction.guild.default_role, view_channel=False)
        await interaction.response.send_message(f'👁️ {interaction.user.mention}: Voice channel hidden.', ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='👀')
    async def reveal_button(self, interaction: discord.Interaction, button: Button):
        voice_channel = await self.ensure_creator(interaction)
        if voice_channel:
            await voice_channel.set_permissions(interaction.guild.default_role, view_channel=True)
        await interaction.response.send_message(f'👀 {interaction.user.mention}: Voice channel revealed.', ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='👥')
    async def set_user_limit_button(self, interaction: discord.Interaction, button: Button):
        voice_channel = await self.ensure_creator(interaction)
        if voice_channel:
            modal = SetUserLimitModal(voice_channel, bot.last_user_limit_change_time.get(voice_channel.id))
            await interaction.response.send_modal(modal)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='ℹ️')
    async def info_button(self, interaction: discord.Interaction, button: Button):
        voice_channel = await self.ensure_creator(interaction)
        if voice_channel:
            owner_id = temporary_channels.get(voice_channel.id)
            owner = interaction.guild.get_member(owner_id) if owner_id else None

            embed = discord.Embed(
                title="Voice Channel Information",
                description=f"Members: **{len(voice_channel.members)}**\n"
                            f"Member Limit: **{voice_channel.user_limit if voice_channel.user_limit > 0 else 'No limit'}**",
                color=0x2d7d9f
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='🚪')
    async def leave_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.voice and interaction.user.voice.channel:
            await interaction.user.move_to(None)
            await interaction.response.send_message(f'🚪 {interaction.user.mention}: You have left the voice channel.', ephemeral=True)
        else:
            await interaction.response.send_message('You are not in a voice channel.', ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='❌')
    async def kick_button(self, interaction: discord.Interaction, button: Button):
        voice_channel = await self.ensure_creator(interaction)
        if voice_channel:
            modal = KickUserModal(voice_channel)
            await interaction.response.send_modal(modal)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='🗑️')
    async def delete_button(self, interaction: discord.Interaction, button: Button):
        voice_channel = await self.ensure_creator(interaction)
        if voice_channel:
            await voice_channel.delete()
            del temporary_channels[str(voice_channel.id)]
            save_temp_channels(main_channels, temporary_channels)
        await interaction.response.send_message(f'🗑️ {interaction.user.mention}: Voice channel deleted.', ephemeral=True)

@bot.group(invoke_without_command=True, aliases=["vm", "vc"])
async def voicemaster(ctx):
    embed = discord.Embed(
        title="ℹ️ - VoiceMaster",
        description="Commands related to voicemaster",
        color=0x2d7d9f
    )
    embed.add_field(name="📝 Syntax", value="`voicemaster [subcommand]`", inline=False)
    embed.add_field(name="🔧 Subcommands", value="`setup` - Setup voicemaster\n`interface` - Send the voicemaster interface", inline=False)
    await ctx.reply(embed=embed)

@voicemaster.command(name="setup")
@commands.has_permissions(manage_channels=True)
async def voice_setup(ctx):
    category = discord.utils.get(ctx.guild.categories, name="Voice Channels")
    if category is None:
        category = await ctx.guild.create_category("VC")

    main_channel = discord.utils.get(ctx.guild.voice_channels, name="Join 2 Create", category=category)
    
    if main_channel is None:
        main_channel = await ctx.guild.create_voice_channel("Join 2 Create", category=category)
    
    if main_channel.id not in main_channels:
        main_channels.append(main_channel.id)
        save_temp_channels(main_channels, temporary_channels)

    interface_channel = discord.utils.get(ctx.guild.text_channels, name="interface", category=category)
    if interface_channel is None:
        interface_channel = await ctx.guild.create_text_channel("interface", category=category)
    
    embed = discord.Embed(
        title="VoiceMaster Interface",
        description="Use the buttons below to control your voice channel.\n\n"
                    "🔒 — **Locks** the channel\n"
                    "🔓 — **Unlocks** the channel\n"
                    "✏️ — **Renames** the channel\n"
                    "👁️ — **Hides** the channel\n"
                    "👀 — **Reveals** the channel\n"
                    "👥 — Sets the **User Limit**\n"
                    "ℹ️ — **Information** on the channel\n"
                    "🚪 — **Leave** the channel\n"
                    "❌ — **Kick** a user from the channel\n"
                    "🗑️ — **Delete** the channel",
        color=0x2d7d9f
    )
    embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

    view = VoiceChannelInterface()
    message = await interface_channel.send(embed=embed, view=view)
    
    interface_data = load_interface_message_data()
    interface_data[message.id] = interface_channel.id
    save_interface_message_data(interface_data)

    confirmation_embed = discord.Embed(
        title="",
        description=f"✅ {ctx.author.mention}: Successfully setup voicemaster",
        color=0x2d7d9f
    )
    await ctx.send(embed=confirmation_embed)

@voice_setup.error
async def voice_setup_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="ℹ️ - Voicemaster setup",
            description="Setups voicemaster to your server",
            color=0x2d7d9f
        )
        embed.add_field(name="📝 Syntax", value="`voicemaster setup`", inline=False)
        embed.add_field(name="🔒 Permissions", value="`manage channels`", inline=False)
        await ctx.reply(embed=embed)

@voicemaster.command(name="interface")
@commands.has_permissions(manage_channels=True)
async def interface(ctx):
    view = VoiceChannelInterface()
    embed = discord.Embed(
        title="VoiceMaster Interface",
        description="Use the buttons below to control your voice channel.\n\n"
                    "🔒 — **Locks** the channel\n"
                    "🔓 — **Unlocks** the channel\n"
                    "✏️ — **Renames** the channel\n"
                    "👁️ — **Hides** the channel\n"
                    "👀 — **Reveals** the channel\n"
                    "👥 — Sets the **User Limit**\n"
                    "ℹ️ — **Information** on the channel\n"
                    "🚪 — **Leave** the channel\n"
                    "❌ — **Kick** a user from the channel\n"
                    "🗑️ — **Delete** the channel",
        color=0x2d7d9f
    )
    embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

    message = await ctx.send(embed=embed, view=view)
    interface_data = load_interface_message_data()
    interface_data[message.id] = ctx.channel.id
    save_interface_message_data(interface_data)

@interface.error
async def interface_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="ℹ️ - Interface",
            description="Sends the voicemaster interface.",
            color=0x2d7d9f
        )
        embed.add_field(name="📝 Syntax", value="`interface`", inline=False)
        embed.add_field(name="🔒 Permissions", value="`manage channels`", inline=False)
        await ctx.reply(embed=embed)

async def create_temporary_channel(member, before, after):
    for main_channel_id in main_channels:
        main_channel = bot.get_channel(main_channel_id)
        if main_channel is None:
            continue

        if before.channel is None and after.channel == main_channel:
            category = main_channel.category
            temp_channel = await member.guild.create_voice_channel(f"{member.display_name}'s Channel", category=category)
            temporary_channels[str(temp_channel.id)] = member.id
            await member.move_to(temp_channel)
            save_temp_channels(main_channels, temporary_channels)

        if before.channel and str(before.channel.id) in temporary_channels and len(before.channel.members) == 0:
            await before.channel.delete()
            del temporary_channels[str(before.channel.id)]
            save_temp_channels(main_channels, temporary_channels)

if TOKEN == "":
    print("Please add your bot token to the TOKEN variable in this file at line 10.")
else:
    bot.run(TOKEN)
