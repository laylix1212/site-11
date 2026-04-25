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
        "category": "\u2192 TICKET QUESTION",
        "label": "Ticket Question",
        "emoji": "\u2753",
        "description": "Poser une question au support",
        "embed_title": "Ticket Question",
        "embed_description": (
            "Bonjour {mention},\n\n"
            "**\u00c0 quoi sert ce ticket ?**\n"
            "Ce ticket est destin\u00e9 \u00e0 toute question g\u00e9n\u00e9rale que tu souhaites poser \u00e0 l'\u00e9quipe.\n"
            "Que ce soit une question sur le serveur, les r\u00e8gles, ou autre chose, nous sommes l\u00e0 pour t'aider.\n\n"
            "**Comment proc\u00e9der ?**\n"
            "Explique ta question de mani\u00e8re claire et un membre du support te r\u00e9pondra d\u00e8s que possible.\n\n"
            "Utilise les boutons ci-dessous pour g\u00e9rer ce ticket."
        ),
        "color": 0x5865f2,
    },
    "developpement": {
        "category": "\u2192 TICKET D\u00c9VELOPPEMENT",
        "label": "Ticket D\u00e9veloppement",
        "emoji": "\ud83d\udcbb",
        "description": "Signaler un bug ou demander une fonctionnalit\u00e9",
        "embed_title": "Ticket D\u00e9veloppement",
        "embed_description": (
            "Bonjour {mention},\n\n"
            "**\u00c0 quoi sert ce ticket ?**\n"
            "Ce ticket est r\u00e9serv\u00e9 aux sujets li\u00e9s au d\u00e9veloppement : signaler un bug, proposer une nouvelle fonctionnalit\u00e9, "
            "ou discuter d'am\u00e9liorations techniques.\n\n"
            "**Comment proc\u00e9der ?**\n"
            "D\u00e9cris le probl\u00e8me ou ta suggestion de fa\u00e7on d\u00e9taill\u00e9e (captures d'\u00e9cran bienvenues).\n"
            "Un d\u00e9veloppeur prendra en charge ton ticket rapidement.\n\n"
            "Utilise les boutons ci-dessous pour g\u00e9rer ce ticket."
        ),
        "color": 0xeb459e,
    },
    "report": {
        "category": "\u2192 TICKET REPORT",
        "label": "Ticket Report",
        "emoji": "\u26a0\ufe0f",
        "description": "Signaler un membre ou un comportement",
        "embed_title": "Ticket Report",
        "embed_description": (
            "Bonjour {mention},\n\n"
            "**\u00c0 quoi sert ce ticket ?**\n"
            "Ce ticket te permet de signaler un membre pour un comportement inappropri\u00e9, du harcel\u00e8lement, "
            "une tricherie, ou toute autre infraction aux r\u00e8gles du serveur.\n\n"
            "**Comment proc\u00e9der ?**\n"
            "Indique le pseudo de la personne concern\u00e9e, la date et une description pr\u00e9cise des faits. "
            "Des preuves (captures d'\u00e9cran) sont fortement recommand\u00e9es.\n"
            "Ton signalement sera trait\u00e9 en toute confidentialit\u00e9.\n\n"
            "Utilise les boutons ci-dessous pour g\u00e9rer ce ticket."
        ),
        "color": 0xed4245,
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

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{member.name.lower()}")
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
            name=f"ticket-{member.name.lower()}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket de {member} | Type : {data['label']}"
        )

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

        embed = discord.Embed(description=f"Ticket fermé par {interaction.user.mention}. Suppression dans 5 secondes...", color=0xed4245)
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        await interaction.channel.delete()

@bot.tree.command(name="panel-ticket", description="Créer le panel de tickets dans ce salon")
@app_commands.checks.has_permissions(administrator=True)
async def panel_ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Support",
        description="Tu as besoin d'aide ?\nSélectionne le type de ticket dans le menu ci-dessous et un membre du support te répondra.",
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
