import discord
import asyncio
import os
import io
from datetime import datetime, timezone
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1491033880491196588
SUPPORT_ROLE_ID = 1491787311472574654
LOG_CHANNEL_ID = 1497645297021485146

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

# Stockage en mémoire : channel_id -> infos du ticket
ticket_store: dict[int, dict] = {}

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

# ── Génération du transcript ──────────────────────────────────────────────────
async def generate_transcript(channel: discord.TextChannel, ticket_info: dict, closed_by: discord.Member) -> io.BytesIO:
    now = datetime.now(timezone.utc)
    lines = []

    lines.append("=" * 70)
    lines.append("                        TRANSCRIPT DU TICKET")
    lines.append("=" * 70)
    lines.append("")
    lines.append("── INFORMATIONS GÉNÉRALES ──────────────────────────────────────────")
    lines.append(f"  Salon              : #{channel.name}")
    lines.append(f"  ID du salon        : {channel.id}")
    lines.append(f"  Type de ticket     : {ticket_info.get('type_label', 'Inconnu')}")
    lines.append(f"  Catégorie          : {ticket_info.get('category', 'Inconnue')}")
    lines.append("")
    lines.append("── MEMBRE AYANT OUVERT LE TICKET ───────────────────────────────────")
    opener = ticket_info.get("opener")
    if opener:
        lines.append(f"  Pseudo             : {opener.name}")
        lines.append(f"  Nom affiché        : {opener.display_name}")
        lines.append(f"  ID                 : {opener.id}")
        lines.append(f"  Tag complet        : {str(opener)}")
        lines.append(f"  Compte créé le     : {opener.created_at.strftime('%d/%m/%Y à %H:%M:%S UTC')}")
        if isinstance(opener, discord.Member) and opener.joined_at:
            lines.append(f"  A rejoint le       : {opener.joined_at.strftime('%d/%m/%Y à %H:%M:%S UTC')}")
        roles = [r.name for r in opener.roles if r.name != "@everyone"] if isinstance(opener, discord.Member) else []
        lines.append(f"  Rôles              : {', '.join(roles) if roles else 'Aucun'}")
    lines.append("")
    lines.append("── PRISE EN CHARGE ─────────────────────────────────────────────────")
    claimed_by = ticket_info.get("claimed_by")
    if claimed_by:
        lines.append(f"  Pris en charge par : {claimed_by.display_name} ({claimed_by.id})")
        claimed_at = ticket_info.get("claimed_at")
        if claimed_at:
            lines.append(f"  Pris en charge le  : {claimed_at.strftime('%d/%m/%Y à %H:%M:%S UTC')}")
    else:
        lines.append(f"  Pris en charge par : Personne")
    lines.append("")
    lines.append("── FERMETURE ───────────────────────────────────────────────────────")
    lines.append(f"  Fermé par          : {closed_by.display_name} ({closed_by.id})")
    lines.append(f"  Fermé le           : {now.strftime('%d/%m/%Y à %H:%M:%S UTC')}")
    opened_at = ticket_info.get("opened_at")
    if opened_at:
        lines.append(f"  Ouvert le          : {opened_at.strftime('%d/%m/%Y à %H:%M:%S UTC')}")
        duration = now - opened_at
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        lines.append(f"  Durée du ticket    : {hours}h {minutes}m {seconds}s")
    lines.append("")
    lines.append("=" * 70)
    lines.append("                          MESSAGES DU TICKET")
    lines.append("=" * 70)
    lines.append("")

    messages = []
    async for msg in channel.history(limit=None, oldest_first=True):
        messages.append(msg)

    if not messages:
        lines.append("  (Aucun message)")
    else:
        for msg in messages:
            timestamp = msg.created_at.strftime("%d/%m/%Y %H:%M:%S UTC")
            author = f"{msg.author.display_name} ({msg.author.id})"
            lines.append(f"[{timestamp}] {author}")
            if msg.content:
                lines.append(f"  {msg.content}")
            if msg.attachments:
                for att in msg.attachments:
                    lines.append(f"  [Pièce jointe] {att.filename} → {att.url}")
            if msg.embeds:
                for embed in msg.embeds:
                    title = embed.title or "(sans titre)"
                    lines.append(f"  [Embed] {title}")
                    if embed.description:
                        preview = embed.description[:100].replace("\n", " ")
                        lines.append(f"    {preview}{'...' if len(embed.description) > 100 else ''}")
            lines.append("")

    lines.append("=" * 70)
    lines.append(f"  Fin du transcript — généré le {now.strftime('%d/%m/%Y à %H:%M:%S UTC')}")
    lines.append("=" * 70)

    content = "\n".join(lines)
    return io.BytesIO(content.encode("utf-8"))

# ── Envoi du log ──────────────────────────────────────────────────────────────
async def send_log(guild: discord.Guild, channel: discord.TextChannel, ticket_info: dict, closed_by: discord.Member):
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel is None:
        print(f"Salon de logs introuvable (ID: {LOG_CHANNEL_ID})")
        return

    now = datetime.now(timezone.utc)
    opener = ticket_info.get("opener")
    claimed_by = ticket_info.get("claimed_by")
    opened_at = ticket_info.get("opened_at")

    duration_str = "Inconnue"
    if opened_at:
        total_seconds = int((now - opened_at).total_seconds())
        h, r = divmod(total_seconds, 3600)
        m, s = divmod(r, 60)
        duration_str = f"{h}h {m}m {s}s"

    embed = discord.Embed(
        title=f"Ticket fermé — {ticket_info.get('type_label', 'Inconnu')}",
        color=0xed4245,
        timestamp=now
    )
    embed.add_field(name="Salon", value=f"`#{channel.name}` (`{channel.id}`)", inline=False)
    if opener:
        embed.add_field(
            name="Ouvert par",
            value=f"{opener.mention}\n`{opener.name}` • ID : `{opener.id}`",
            inline=True
        )
    embed.add_field(
        name="Fermé par",
        value=f"{closed_by.mention}\n`{closed_by.name}` • ID : `{closed_by.id}`",
        inline=True
    )
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(
        name="Pris en charge par",
        value=f"{claimed_by.mention} (`{claimed_by.id}`)" if claimed_by else "Personne",
        inline=True
    )
    embed.add_field(
        name="Ouvert le",
        value=opened_at.strftime("%d/%m/%Y à %H:%M:%S UTC") if opened_at else "Inconnu",
        inline=True
    )
    embed.add_field(name="Durée", value=duration_str, inline=True)
    embed.set_footer(text=f"Ticket ID : {channel.id}")

    transcript_buf = await generate_transcript(channel, ticket_info, closed_by)
    file = discord.File(transcript_buf, filename=f"transcript-{channel.name}.txt")

    await log_channel.send(embed=embed, file=file)

# ── Select menu ───────────────────────────────────────────────────────────────
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

        # Enregistrement dans le store
        ticket_store[channel.id] = {
            "opener": member,
            "type_label": data["label"],
            "category": data["category"],
            "opened_at": datetime.now(timezone.utc),
            "claimed_by": None,
            "claimed_at": None,
        }

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

        # Mise à jour du store
        if interaction.channel.id in ticket_store:
            ticket_store[interaction.channel.id]["claimed_by"] = interaction.user
            ticket_store[interaction.channel.id]["claimed_at"] = datetime.now(timezone.utc)

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

        ticket_info = ticket_store.get(interaction.channel.id, {})

        # Envoi du log + transcript avant suppression
        await send_log(interaction.guild, interaction.channel, ticket_info, interaction.user)

        await asyncio.sleep(5)

        ticket_store.pop(interaction.channel.id, None)
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
