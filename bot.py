import discord
import asyncio
import os
import io
from datetime import datetime, timezone, timedelta
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1491033880491196588
SUPPORT_ROLE_ID = 1491787311472574654
LOG_CHANNEL_ID = 1497651927679500398
TICKET_LOG_CHANNEL_ID = 1497645297021485146

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

ticket_store: dict[int, dict] = {}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True

class MainBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Slash commands synchronisées.")

bot = MainBot()

# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════

async def send_log(guild: discord.Guild, embed: discord.Embed, channel_id: int = LOG_CHANNEL_ID, file: discord.File = None):
    ch = guild.get_channel(channel_id)
    if ch:
        await ch.send(embed=embed, file=file)

def log_embed(title: str, fields: list, staff: discord.Member, color: int = 0x3b82f6) -> discord.Embed:
    embed = discord.Embed(title=title, color=color, timestamp=datetime.now(timezone.utc))
    for name, value, inline in fields:
        embed.add_field(name=name, value=value, inline=inline)
    embed.set_footer(
        text=f"Effectué par {staff.display_name} • ID : {staff.id}",
        icon_url=staff.display_avatar.url
    )
    return embed

def parse_duration(s: str):
    units = {"s": ("seconde(s)", 1), "m": ("minute(s)", 60), "h": ("heure(s)", 3600), "d": ("jour(s)", 86400), "j": ("jour(s)", 86400)}
    s = s.strip().lower()
    unit = s[-1] if s else ""
    if unit not in units:
        return None, None
    try:
        amount = int(s[:-1])
    except ValueError:
        return None, None
    if amount <= 0:
        return None, None
    label, mul = units[unit]
    return timedelta(seconds=amount * mul), f"{amount} {label}"

# ══════════════════════════════════════════════════════════════════════════════
# MODÉRATION
# ══════════════════════════════════════════════════════════════════════════════

@bot.tree.command(name="clear", description="Supprimer un nombre de messages dans ce salon")
@app_commands.describe(nombre="Nombre de messages à supprimer (max 100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, nombre: int):
    if nombre < 1 or nombre > 100:
        await interaction.response.send_message("Le nombre doit être compris entre 1 et 100.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=nombre)
    count = len(deleted)
    await interaction.followup.send(f"{count} message(s) supprimé(s).", ephemeral=True)
    embed = log_embed(
        title="Messages supprimés — /clear",
        fields=[
            ("Salon", f"{interaction.channel.mention} (`{interaction.channel.id}`)", False),
            ("Nombre demandé", str(nombre), True),
            ("Nombre supprimé", str(count), True),
            ("Date", f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>", False),
        ],
        staff=interaction.user
    )
    await send_log(interaction.guild, embed)

@bot.tree.command(name="mute", description="Muter un membre pendant une durée définie")
@app_commands.describe(membre="Le membre à muter", duree="Durée (ex: 10m, 2h, 1d)", raison="Raison du mute")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, membre: discord.Member, duree: str, raison: str = "Aucune raison fournie"):
    await interaction.response.defer(ephemeral=True)
    if membre.top_role >= interaction.user.top_role:
        await interaction.followup.send("Tu ne peux pas muter un membre avec un rôle supérieur ou égal au tien.", ephemeral=True)
        return
    delta, duree_label = parse_duration(duree)
    if delta is None:
        await interaction.followup.send("Durée invalide. Exemples : `10s`, `5m`, `2h`, `1d`", ephemeral=True)
        return
    if delta > timedelta(days=28):
        await interaction.followup.send("La durée maximale est de 28 jours.", ephemeral=True)
        return
    until = datetime.now(timezone.utc) + delta
    try:
        await membre.timeout(until, reason=raison)
    except discord.Forbidden:
        await interaction.followup.send("Je n'ai pas la permission de muter ce membre.", ephemeral=True)
        return
    try:
        dm = discord.Embed(
            title="Tu as été mis en sourdine",
            description=(
                f"Tu as été mis en sourdine sur **{interaction.guild.name}**.\n\n"
                f"**Durée :** {duree_label}\n"
                f"**Raison :** {raison}\n\n"
                f"Tu pourras de nouveau écrire <t:{int(until.timestamp())}:R>."
            ),
            color=0xed4245, timestamp=datetime.now(timezone.utc)
        )
        dm.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        await membre.send(embed=dm)
        dm_sent = True
    except discord.Forbidden:
        dm_sent = False
    await interaction.followup.send(f"{membre.mention} a été mute pendant **{duree_label}**.", ephemeral=True)
    embed = log_embed(
        title="Membre mute — /mute",
        fields=[
            ("Membre ciblé", f"{membre.mention}\n`{membre.name}` • ID : `{membre.id}`", True),
            ("Durée", duree_label, True),
            ("Expire", f"<t:{int(until.timestamp())}:F>", True),
            ("Raison", raison, False),
            ("Salon", f"{interaction.channel.mention}", True),
            ("MP envoyé", "Oui" if dm_sent else "Non (MP fermés)", True),
            ("Date", f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>", False),
        ],
        staff=interaction.user
    )
    embed.set_thumbnail(url=membre.display_avatar.url)
    await send_log(interaction.guild, embed)

@bot.tree.command(name="ban", description="Bannir un membre du serveur")
@app_commands.describe(membre="Le membre à bannir", raison="Raison du ban", supprimer_messages="Supprimer les messages des X derniers jours (0-7)")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison fournie", supprimer_messages: int = 0):
    await interaction.response.defer(ephemeral=True)
    if membre.top_role >= interaction.user.top_role:
        await interaction.followup.send("Tu ne peux pas bannir un membre avec un rôle supérieur ou égal au tien.", ephemeral=True)
        return
    if membre.id == interaction.guild.me.id:
        await interaction.followup.send("Je ne peux pas me bannir moi-même.", ephemeral=True)
        return
    supprimer_messages = max(0, min(7, supprimer_messages))
    # MP avant le ban
    try:
        dm = discord.Embed(
            title="Tu as été banni",
            description=(
                f"Tu as été banni de **{interaction.guild.name}**.\n\n"
                f"**Raison :** {raison}"
            ),
            color=0xed4245, timestamp=datetime.now(timezone.utc)
        )
        dm.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        await membre.send(embed=dm)
        dm_sent = True
    except discord.Forbidden:
        dm_sent = False
    try:
        await membre.ban(reason=raison, delete_message_days=supprimer_messages)
    except discord.Forbidden:
        await interaction.followup.send("Je n'ai pas la permission de bannir ce membre.", ephemeral=True)
        return
    except discord.HTTPException as e:
        await interaction.followup.send(f"Erreur : {e}", ephemeral=True)
        return
    await interaction.followup.send(f"**{membre.name}** a été banni.", ephemeral=True)
    embed = log_embed(
        title="Membre banni — /ban",
        fields=[
            ("Membre banni", f"{membre.mention}\n`{membre.name}` • ID : `{membre.id}`", True),
            ("Compte créé le", membre.created_at.strftime("%d/%m/%Y à %H:%M UTC"), True),
            ("Raison", raison, False),
            ("Messages supprimés", f"{supprimer_messages} jour(s)", True),
            ("Salon", f"{interaction.channel.mention}", True),
            ("MP envoyé", "Oui" if dm_sent else "Non (MP fermés)", True),
            ("Date", f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>", False),
        ],
        staff=interaction.user,
        color=0xed4245
    )
    embed.set_thumbnail(url=membre.display_avatar.url)
    await send_log(interaction.guild, embed)

# ══════════════════════════════════════════════════════════════════════════════
# TICKETS
# ══════════════════════════════════════════════════════════════════════════════

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
        lines.append("  Pris en charge par : Personne")
    lines.append("")
    lines.append("── FERMETURE ───────────────────────────────────────────────────────")
    lines.append(f"  Fermé par          : {closed_by.display_name} ({closed_by.id})")
    lines.append(f"  Fermé le           : {now.strftime('%d/%m/%Y à %H:%M:%S UTC')}")
    opened_at = ticket_info.get("opened_at")
    if opened_at:
        lines.append(f"  Ouvert le          : {opened_at.strftime('%d/%m/%Y à %H:%M:%S UTC')}")
        total_seconds = int((now - opened_at).total_seconds())
        h, r = divmod(total_seconds, 3600)
        m, s = divmod(r, 60)
        lines.append(f"  Durée du ticket    : {h}h {m}m {s}s")
    lines.append("")
    lines.append("=" * 70)
    lines.append("                          MESSAGES DU TICKET")
    lines.append("=" * 70)
    lines.append("")
    messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
    if not messages:
        lines.append("  (Aucun message)")
    else:
        for msg in messages:
            ts = msg.created_at.strftime("%d/%m/%Y %H:%M:%S UTC")
            lines.append(f"[{ts}] {msg.author.display_name} ({msg.author.id})")
            if msg.content:
                lines.append(f"  {msg.content}")
            for att in msg.attachments:
                lines.append(f"  [Pièce jointe] {att.filename} → {att.url}")
            for emb in msg.embeds:
                title = emb.title or "(sans titre)"
                lines.append(f"  [Embed] {title}")
                if emb.description:
                    preview = emb.description[:100].replace("\n", " ")
                    lines.append(f"    {preview}{'...' if len(emb.description) > 100 else ''}")
            lines.append("")
    lines.append("=" * 70)
    lines.append(f"  Fin du transcript — généré le {now.strftime('%d/%m/%Y à %H:%M:%S UTC')}")
    lines.append("=" * 70)
    return io.BytesIO("\n".join(lines).encode("utf-8"))

class TicketSelectMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=data["label"], description=data["description"], emoji=data["emoji"], value=key)
            for key, data in TICKET_TYPES.items()
        ]
        super().__init__(placeholder="Sélectionner le type de ticket...", min_values=1, max_values=1, options=options, custom_id="ticket_select")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user
        ticket_type = self.values[0]
        data = TICKET_TYPES[ticket_type]

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
            name=f"{data['channel_prefix']}-{member.name.lower()}",
            category=category, overwrites=overwrites,
            topic=f"Ticket de {member} | Type : {data['label']}"
        )

        ticket_store[channel.id] = {
            "opener": member, "type_label": data["label"],
            "category": data["category"], "opened_at": datetime.now(timezone.utc),
            "claimed_by": None, "claimed_at": None,
        }

        if support_role:
            ghost = await channel.send(f"{support_role.mention} {member.mention}")
            await ghost.delete()

        embed = discord.Embed(title=data["embed_title"], description=data["embed_description"].format(mention=member.mention), color=data["color"])
        embed.set_footer(text=f"Ticket ouvert par {member}", icon_url=member.display_avatar.url)
        await channel.send(embed=embed, view=TicketControlView())
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
        if not (support_role and support_role in interaction.user.roles):
            await interaction.response.send_message("Seul le rôle Support Ticket peut prendre en charge un ticket.", ephemeral=True)
            return
        button.disabled = True
        button.label = f"Pris en charge par {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        if interaction.channel.id in ticket_store:
            ticket_store[interaction.channel.id]["claimed_by"] = interaction.user
            ticket_store[interaction.channel.id]["claimed_at"] = datetime.now(timezone.utc)
        embed = discord.Embed(description=f"Ticket pris en charge par {interaction.user.mention}.", color=0x57f287)
        await interaction.channel.send(embed=embed)

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="ticket_close", emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        support_role = interaction.guild.get_role(SUPPORT_ROLE_ID)
        if not (support_role and support_role in interaction.user.roles):
            await interaction.response.send_message("Seul le rôle Support Ticket peut fermer un ticket.", ephemeral=True)
            return
        embed = discord.Embed(description=f"Ticket fermé par {interaction.user.mention}. Suppression dans 5 secondes...", color=0xed4245)
        await interaction.response.send_message(embed=embed)
        ticket_info = ticket_store.get(interaction.channel.id, {})

        # Log + transcript
        now = datetime.now(timezone.utc)
        opener = ticket_info.get("opener")
        claimed_by = ticket_info.get("claimed_by")
        opened_at = ticket_info.get("opened_at")
        duration_str = "Inconnue"
        if opened_at:
            total = int((now - opened_at).total_seconds())
            h, r = divmod(total, 3600)
            m, s = divmod(r, 60)
            duration_str = f"{h}h {m}m {s}s"

        log_emb = discord.Embed(title=f"Ticket fermé — {ticket_info.get('type_label', 'Inconnu')}", color=0xed4245, timestamp=now)
        log_emb.add_field(name="Salon", value=f"`#{interaction.channel.name}` (`{interaction.channel.id}`)", inline=False)
        if opener:
            log_emb.add_field(name="Ouvert par", value=f"{opener.mention}\n`{opener.name}` • ID : `{opener.id}`", inline=True)
        log_emb.add_field(name="Fermé par", value=f"{interaction.user.mention}\n`{interaction.user.name}` • ID : `{interaction.user.id}`", inline=True)
        log_emb.add_field(name="\u200b", value="\u200b", inline=True)
        log_emb.add_field(name="Pris en charge par", value=f"{claimed_by.mention} (`{claimed_by.id}`)" if claimed_by else "Personne", inline=True)
        log_emb.add_field(name="Ouvert le", value=opened_at.strftime("%d/%m/%Y à %H:%M:%S UTC") if opened_at else "Inconnu", inline=True)
        log_emb.add_field(name="Durée", value=duration_str, inline=True)
        log_emb.set_footer(text=f"Ticket ID : {interaction.channel.id}")

        transcript_buf = await generate_transcript(interaction.channel, ticket_info, interaction.user)
        file = discord.File(transcript_buf, filename=f"transcript-{interaction.channel.name}.txt")
        await send_log(interaction.guild, log_emb, TICKET_LOG_CHANNEL_ID, file=file)

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
    await interaction.channel.send(embed=embed, view=TicketPanelView())
    await interaction.response.send_message("Panel créé.", ephemeral=True)

# ══════════════════════════════════════════════════════════════════════════════
# ON READY
# ══════════════════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())
    print(f"Connecté : {bot.user} (ID: {bot.user.id})")
    print("Commandes : /clear, /mute, /ban, /panel-ticket")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN manquant !")
    bot.run(TOKEN)
