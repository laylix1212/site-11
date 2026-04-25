import discord
import asyncio
import os
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1491033880491196588
SUPPORT_ROLE_ID = 1491787311472574654

TICKET_TYPES = {
    "question": {
        "category": "→ TICKET QUESTION",
        "label": "Ticket Question",
        "emoji": "❓",
        "description": "Une question sur le serveur ou les règles ?",
        "channel_prefix": "question",
        "embed_title": "Ticket Question",
        "embed_description": (
            "Bonjour {mention},\n\n"
            "**À quoi sert ce ticket ?**\n"
            "Ce ticket est destiné à toute question générale que tu souhaites poser à l'équipe.\n"
            "Que ce soit une question sur le serveur, les règles, ou autre chose, nous sommes là pour t'aider.\n\n"
            "**Comment procéder ?**\n"
            "Explique ta question de manière claire et un membre du support te répondra dès que possible.\n\n"
            "Utilise les boutons ci-dessous pour gérer ce ticket."
        ),
        "color": 0x2b2d31,
    },
    "developpement": {
        "category": "→ TICKET DÉVELOPPEMENT",
        "label": "Ticket Développement",
        "emoji": "💻",
        "description": "Un bug à signaler ou une fonctionnalité à proposer ?",
        "channel_prefix": "développement",
        "embed_title": "Ticket Développement",
        "embed_description": (
            "Bonjour {mention},\n\n"
            "**À quoi sert ce ticket ?**\n"
            "Ce ticket est réservé aux sujets liés au développement : signaler un bug, proposer une nouvelle fonctionnalité, "
            "ou discuter d'améliorations techniques.\n\n"
            "**Comment procéder ?**\n"
            "Décris le problème ou ta suggestion de façon détaillée (captures d'écran bienvenues).\n"
            "Un développeur prendra en charge ton ticket rapidement.\n\n"
            "Utilise les boutons ci-dessous pour gérer ce ticket."
        ),
        "color": 0x2b2d31,
    },
    "report": {
        "category": "→ TICKET REPORT",
        "label": "Ticket Report",
        "emoji": "⚠️",
        "description": "Signaler un membre pour un comportement inapproprié ?",
        "channel_prefix": "report",
        "embed_title": "Ticket Report",
        "embed_description": (
            "Bonjour {mention},\n\n"
            "**À quoi sert ce ticket ?**\n"
            "Ce ticket te permet de signaler un membre pour un comportement inapproprié, du harcèlement, "
            "une tricherie, ou toute autre infraction aux règles du serveur.\n\n"
            "**Comment procéder ?**\n"
            "Indique le pseudo de la personne concernée, la date et une description précise des faits. "
            "Des preuves (captures d'écran) sont fortement recommandées.\n"
            "Ton signalement sera traité en toute confidentialité.\n\n"
            "Utilise les boutons ci-dessous pour gérer ce ticket."
        ),
        "color": 0x2b2d31,
    },
}

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
        print("Slash commands synchronisées.")

bot = TicketBot()

class TicketSelectMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=data["label"],
                description=data["description"],
                emoji=data["emoji"],
                value=key
            )
            for key, data in TICKET_TYPES.items()
        ]
        super().__init__(
            placeholder="Sélectionner le type de ticket...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user
        ticket_type = self.values[0]
        data = TICKET_TYPES[ticket_type]
        prefix = data["channel_prefix"]

        # Vérifie si le membre a déjà un ticket ouvert (tous types confondus)
        for key, d in TICKET_TYPES.items():
            existing = discord.utils.get(guild.text_channels, name=f"{d['channel_prefix']}-{member.name.lower()}")
            if existing:
                await interaction.followup.send(f"Tu as déjà un ticket ouvert : {existing.mention}", ephemeral=True)
                return

        category = discord.utils.get(guild.categories, name=data["category"])
        if category is None:
            category = await guild.create_category(data["category"])

        support_role = guild.get_role(SUPPORT_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"{prefix}-{member.name.lower()}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket de {member} | Type : {data['label']}"
        )

        # Ghost ping
        if support_role:
            ghost = await channel.send(f"{support_role.mention} {member.mention}")
            await ghost.delete()

        embed = discord.Embed(
            title=data["embed_title"],
            description=data["embed_description"].format(mention=member.mention),
            color=data["color"]
        )
        embed.set_footer(text=f"Ticket ouvert par {member}", icon_url=member.display_avatar.url)

        view = TicketControlView()
        await channel.send(embed=embed, view=view)
        await interaction.followup.send(f"Ton ticket a été créé : {channel.mention}", ephemeral=True)

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

        if not is_support:
            await interaction.response.send_message("Seul le rôle Support Ticket peut prendre en charge un ticket.", ephemeral=True)
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

        if not is_support:
            await interaction.response.send_message("Seul le rôle Support Ticket peut fermer un ticket.", ephemeral=True)
            return

        embed = discord.Embed(
            description=f"Ticket fermé par {interaction.user.mention}. Suppression dans 5 secondes...",
            color=0xed4245
        )
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        await interaction.channel.delete()

@bot.tree.command(name="panel-ticket", description="Créer le panel de tickets dans ce salon")
@app_commands.checks.has_permissions(administrator=True)
async def panel_ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Support",
        description=(
            "Tu as besoin d'aide ? Sélectionne le type de ticket ci-dessous.\n\n"
            "❓ **Ticket Question**\nUne question sur le serveur, les règles ou autre chose.\n\n"
            "💻 **Ticket Développement**\nSignaler un bug ou proposer une fonctionnalité.\n\n"
            "⚠️ **Ticket Report**\nSignaler un membre pour comportement inapproprié."
        ),
        color=0x2b2d31
    )
    if interaction.guild.icon:
        embed.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon.url)
    else:
        embed.set_footer(text=interaction.guild.name)

    view = TicketPanelView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("Panel créé.", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())
    print(f"Connecté : {bot.user} (ID: {bot.user.id})")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN manquant !")
    bot.run(TOKEN)
