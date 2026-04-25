import discord
import asyncio
import os
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1491033880491196588
SUPPORT_ROLE_ID = 1491787311472574654
TICKET_CATEGORY_NAME = "→ TICKET QUESTION"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class TicketBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Slash commands synchronisees.")

bot = TicketBot()

class TicketSelectMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Question",
                description="Poser une question au support",
                emoji="❓",
                value="question"
            ),
        ]
        super().__init__(
            placeholder="Selectionner le type de ticket...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{member.name.lower()}")
        if existing:
            await interaction.followup.send(f"Tu as deja un ticket ouvert : {existing.mention}", ephemeral=True)
            return

        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if category is None:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        support_role = guild.get_role(SUPPORT_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{member.name.lower()}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket de {member} | Type : Question"
        )

        if support_role:
            ghost = await channel.send(f"{support_role.mention} {member.mention}")
            await ghost.delete()

        embed = discord.Embed(
            title="Ticket Question",
            description=f"Bonjour {member.mention},\n\nExplique ta question et un membre du support te repondra rapidement.\n\nUtilise les boutons ci-dessous pour gerer ce ticket.",
            color=0x2b2d31
        )
        embed.set_footer(text=f"Ticket ouvert par {member}", icon_url=member.display_avatar.url)

        view = TicketControlView()
        await channel.send(embed=embed, view=view)
        await interaction.followup.send(f"Ton ticket a ete cree : {channel.mention}", ephemeral=True)

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelectMenu())

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Prendre en charge", style=discord.ButtonStyle.success, custom_id="ticket_claim", emoji="✋")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        support_role = interaction.guild.get_role(SUPPORT_ROLE_ID)
        is_support = support_role and support_role in interaction.user.roles
        is_admin = interaction.user.guild_permissions.administrator

        if not is_support and not is_admin:
            await interaction.response.send_message("Seul le support peut prendre en charge un ticket.", ephemeral=True)
            return

        button.disabled = True
        button.label = f"Pris en charge par {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)

        embed = discord.Embed(description=f"Ticket pris en charge par {interaction.user.mention}.", color=0x57f287)
        await interaction.channel.send(embed=embed)

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="ticket_close", emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        support_role = interaction.guild.get_role(SUPPORT_ROLE_ID)
        is_support = support_role and support_role in interaction.user.roles
        is_admin = interaction.user.guild_permissions.administrator
        opener_name = interaction.channel.name.replace("ticket-", "")
        is_opener = interaction.user.name.lower() == opener_name

        if not is_support and not is_admin and not is_opener:
            await interaction.response.send_message("Tu n'as pas la permission de fermer ce ticket.", ephemeral=True)
            return

        embed = discord.Embed(description=f"Ticket ferme par {interaction.user.mention}. Suppression dans 5 secondes...", color=0xed4245)
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        await interaction.channel.delete()

@bot.tree.command(name="panel-ticket", description="Creer le panel de tickets dans ce salon")
@app_commands.checks.has_permissions(administrator=True)
async def panel_ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Support",
        description="Tu as besoin d'aide ?\nSelectionne le type de ticket dans le menu ci-dessous et un membre du support te repondra.",
        color=0x2b2d31
    )
    if interaction.guild.icon:
        embed.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon.url)
    else:
        embed.set_footer(text=interaction.guild.name)

    view = TicketPanelView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("Panel cree.", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())
    print(f"Connecte : {bot.user} (ID: {bot.user.id})")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN manquant !")
    bot.run(TOKEN)
