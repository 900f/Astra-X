import discord
import functools
from utils.Tools import *
import re


class Dropdown(discord.ui.Select):
    def __init__(self, ctx, options):
        super().__init__(
            placeholder="Choose a Category for Help",
            min_values=1,
            max_values=1,
            options=options
        )
        self.invoker = ctx.author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.invoker:
            return await interaction.response.send_message(
                "You must run this command to interact with it.", ephemeral=True
            )

        selected = self.values[0]
        if selected == "Home":
            await self.view.set_page(0, interaction)
            return

        # FIXED: Proper index matching for dropdown
        for i, option in enumerate(self.view.options):
            if option.label == selected:
                await self.view.set_page(i, interaction)
                return


class Button(discord.ui.Button):
    def __init__(self, command, ctx, label, style: discord.ButtonStyle, emoji=None, args=None):
        disabled = False
        super().__init__(label=label, style=style, emoji=emoji, disabled=disabled)
        self.command = command
        self.invoker = ctx.author
        self.args = args

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.invoker:
            return await interaction.response.send_message(
                "You must run this command to interact with it.", ephemeral=True
            )

        if self.args is not None:
            func = functools.partial(self.command, self.args, interaction)
            await func()
        else:
            await self.command(interaction)


class View(discord.ui.View):
    def __init__(self, mapping: dict, ctx: discord.ext.commands.Context, homeembed: discord.Embed, ui: int):
        super().__init__(timeout=180)
        self.mapping, self.ctx, self.home = mapping, ctx, homeembed
        self.current_page = 0
        self.buttons = None

        self.options, self.embeds, self.total_pages = self.gen_embeds()

        if ui in (0, 2):
            self.add_item(Dropdown(ctx=self.ctx, options=self.options))
        if ui in (1, 2):
            self.buttons = self.add_buttons()

    def add_buttons(self):
        # FIXED: Proper emoji IDs from your bot + correct commands/args
        self.homeB = Button(
            label="", style=discord.ButtonStyle.secondary, 
            emoji="<:rewind1:1329360839874056225>", 
            command=self.set_page, args=0, ctx=self.ctx
        )
        self.backB = Button(
            label="", style=discord.ButtonStyle.secondary, 
            emoji="<:next:1327829548426854522>",  # Your original back emoji
            command=self.change_page, args=-1, ctx=self.ctx
        )
        self.quitB = Button(
            label="", style=discord.ButtonStyle.danger, 
            emoji="<:delete:1327842168693461022>", 
            command=self.quit, ctx=self.ctx
        )
        self.nextB = Button(
            label="", style=discord.ButtonStyle.secondary, 
            emoji="<:icons_next:1327829470027055184>", 
            command=self.change_page, args=1, ctx=self.ctx
        )
        self.lastB = Button(
            label="", style=discord.ButtonStyle.secondary, 
            emoji="<:forward:1329361532999569439>", 
            command=self.set_page, args=-1, ctx=self.ctx
        )

        buttons = [self.homeB, self.backB, self.quitB, self.nextB, self.lastB]
        for button in buttons:
            self.add_item(button)
        return buttons

    def get_cogs(self):
        return list(self.mapping.keys())

    def parse_emoji(self, emoji_str):
        """FIXED: Convert :voice: → actual Discord emoji"""
        if emoji_str.startswith('<:') and emoji_str.endswith('>'):
            return emoji_str  # Already custom emoji
        elif emoji_str.startswith(':') and emoji_str.endswith(':'):
            # Try to find emoji by name
            try:
                return discord.utils.find(lambda e: str(e.name) == emoji_str[1:-1], self.ctx.guild.emojis)
            except:
                pass
        return "📋"  # Default fallback

    def gen_embeds(self):
        options, embeds = [], []
        total_pages = 0

        # Home page
        options.append(discord.SelectOption(label="Home", emoji='<:home:1332569722801225749>', description=""))
        embeds.append(self.home)
        total_pages += 1

        # FIXED: Proper cog processing with emoji parsing
        for i, cog in enumerate(self.get_cogs()):
            if "help_custom" in dir(cog):
                raw_emoji, label, description = cog.help_custom()
                
                # Parse emoji properly
                emoji_obj = self.parse_emoji(raw_emoji)
                
                options.append(discord.SelectOption(label=label, emoji=emoji_obj, description=description))
                
                embed = discord.Embed(title=f"{emoji_obj} {label}", color=0x000000)

                for command in cog.get_commands():
                    params = " ".join([f"[{list(p.keys())[0]}]" for p in command.clean_params])
                    embed.add_field(
                        name=f"`{command.name}{params}`", 
                        value=f"{command.help or 'No description'}\n\u200b", 
                        inline=False
                    )

                embeds.append(embed)
                total_pages += 1

        # Update home footer
        self.home.set_footer(
            text=f"• Help page 1/{total_pages} | Requested by: {self.ctx.author.display_name}",
            icon_url=self.ctx.bot.user.avatar.url if self.ctx.bot.user.avatar else None
        )

        return options, embeds, total_pages

    async def quit(self, interaction: discord.Interaction):
        try:
            await interaction.message.delete()
        except:
            try:
                await interaction.response.defer()
            except:
                pass

    async def change_page(self, delta: int, interaction: discord.Interaction):
        """FIXED: Proper relative page change"""
        new_page = self.current_page + delta
        new_page = max(0, min(new_page, self.total_pages - 1))
        
        if new_page == self.current_page:
            return await interaction.response.defer()

        self.current_page = new_page
        await self.update_display(interaction)

    async def set_page(self, page: int, interaction: discord.Interaction):
        """FIXED: Home (0) and Last (-1) work properly"""
        if page == -1:  # Last page
            page = self.total_pages - 1
        elif page == 0:  # Home
            page = 0

        page = max(0, min(page, self.total_pages - 1))
        
        if page == self.current_page:
            return await interaction.response.defer()

        self.current_page = page
        await self.update_display(interaction)

    async def update_display(self, interaction: discord.Interaction):
        """FIXED: Updates embed + button states correctly"""
        embed = self.embeds[self.current_page].copy()  # Copy to avoid modifying original
        embed.set_footer(
            text=f"• Help page {self.current_page + 1}/{self.total_pages} | Requested by: {self.ctx.author.display_name}",
            icon_url=self.ctx.bot.user.avatar.url if self.ctx.bot.user.avatar else None
        )

        # FIXED: Proper button disabling
        if self.buttons:
            self.homeB.disabled = self.current_page == 0
            self.backB.disabled = self.current_page == 0
            self.nextB.disabled = self.current_page == self.total_pages - 1
            self.lastB.disabled = self.current_page == self.total_pages - 1

        await interaction.response.edit_message(embed=embed, view=self)