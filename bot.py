import discord
import asyncio
import os
import io
from datetime import datetime, timezone, timedelta
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1491033880491196588
LOG_CHANNEL_ID = 1497651927679500398
TICKET_LOG_CHANNEL_ID = 1497645297021485146

# ── Rôles ─────────────────────────────────────────────────────────────────────
SUPPORT_ROLE_ID        = 1491787311472574654   # Support Ticket (pour question/report joueur/dev)
STAFF_REPORT_ROLE_ID   = 1491711237615255572   # Rôle mentionné pour report staff
ANIM_REPORT_ROLE_ID    = 1491711226907197540   # Rôle mentionné pour report animation
DEV_ROLE_ID            = 1500538990091309066   # Rôle mentionné pour report développement

# ── Catégories tickets (IDs Discord) ─────────────────────────────────────────
CAT_QUESTION_ID        = 1491789900222169098
CAT_REPORT_JOUEUR_ID   = 1491789966437515444
CAT_REPORT_PERSO_ID    = 1502229379592224798
CAT_REPORT_DEV_ID      = 1491789942399959070

# ── Config tickets ────────────────────────────────────────────────────────────
TICKET_CONFIG = {
    "question": {
        "category_id":    CAT_QUESTION_ID,
        "label":          "Ticket Question",
        "emoji":          "❓",
        "menu_desc":      "Une question sur le serveur ou les règles ?",
        "channel_prefix": "question",
        "mention_role_id": SUPPORT_ROLE_ID,
        "embed_title":    "Ticket Question",
        "embed_desc": (
            "Bonjour {mention},\n\n"
            "**À quoi sert ce ticket ?**\n"
            "Ce ticket est destiné à toute question générale que tu souhaites poser à l'équipe.\n"
            "Que ce soit une question sur le serveur, les règles, ou autre chose, nous sommes là pour t'aider.\n\n"
            "**Comment procéder ?**\n"
            "Explique ta question de manière claire et un membre du support te répondra dès que possible."
        ),
    },
    "report_joueur": {
        "category_id":    CAT_REPORT_JOUEUR_ID,
        "label":          "Report Joueur",
        "emoji":          "🎮",
        "menu_desc":      "Signaler un joueur pour comportement inapproprié ?",
        "channel_prefix": "report-joueur",
        "mention_role_id": SUPPORT_ROLE_ID,
        "embed_title":    "Report Joueur",
        "embed_desc": (
            "Bonjour {mention},\n\n"
            "**À quoi sert ce ticket ?**\n"
            "Ce ticket te permet de signaler un joueur pour un comportement inapproprié, du harcèlement ou une tricherie.\n\n"
            "**Comment procéder ?**\n"
            "Indique le pseudo du joueur, la date, et une description précise des faits.\n"
            "Des preuves (captures d'écran) sont fortement recommandées.\n"
            "Ton signalement sera traité en toute confidentialité."
        ),
    },
    "report_staff": {
        "category_id":    CAT_REPORT_PERSO_ID,
        "label":          "Report Staff",
        "emoji":          "🛡️",
        "menu_desc":      "Signaler un membre du staff ?",
        "channel_prefix": "report-staff",
        "mention_role_id": STAFF_REPORT_ROLE_ID,
        "embed_title":    "Report Staff",
        "embed_desc": (
            "Bonjour {mention},\n\n"
            "**À quoi sert ce ticket ?**\n"
            "Ce ticket te permet de signaler un membre du staff pour un comportement inapproprié ou un abus de pouvoir.\n\n"
            "**Comment procéder ?**\n"
            "Indique le pseudo du staff concerné, la date, et une description précise des faits.\n"
            "Des preuves (captures d'écran) sont fortement recommandées.\n"
            "Ton signalement sera traité en toute confidentialité."
        ),
    },
    "report_animation": {
        "category_id":    CAT_REPORT_PERSO_ID,
        "label":          "Report Animation",
        "emoji":          "🎭",
        "menu_desc":      "Signaler un membre de l'équipe animation ?",
        "channel_prefix": "report-anim",
        "mention_role_id": ANIM_REPORT_ROLE_ID,
        "embed_title":    "Report Animation",
        "embed_desc": (
            "Bonjour {mention},\n\n"
            "**À quoi sert ce ticket ?**\n"
            "Ce ticket te permet de signaler un membre de l'équipe animation pour un comportement inapproprié.\n\n"
            "**Comment procéder ?**\n"
            "Indique le pseudo du membre concerné, la date, et une description précise des faits.\n"
            "Des preuves (captures d'écran) sont fortement recommandées.\n"
            "Ton signalement sera traité en toute confidentialité."
        ),
    },
    "report_dev": {
        "category_id":    CAT_REPORT_DEV_ID,
        "label":          "Report Développement",
        "emoji":          "💻",
        "menu_desc":      "Signaler un bug ou un problème technique ?",
        "channel_prefix": "report-dev",
        "mention_role_id": DEV_ROLE_ID,
        "embed_title":    "Report Développement",
        "embed_desc": (
            "Bonjour {mention},\n\n"
            "**À quoi sert ce ticket ?**\n"
            "Ce ticket est réservé aux signalements de bugs, problèmes techniques ou suggestions de développement.\n\n"
            "**Comment procéder ?**\n"
            "Décris le problème de façon détaillée (captures d'écran, étapes pour reproduire le bug).\n"
            "Un développeur prendra en charge ton ticket rapidement."
        ),
    },
}

ticket_store: dict[int, dict] = {}

# ══════════════════════════════════════════════════════════════════════════════
# BOT SETUP
# ══════════════════════════════════════════════════════════════════════════════

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True
intents.presences = True

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
    embed.set_footer(text=f"Effectué par {staff.display_name} • ID : {staff.id}", icon_url=staff.display_avatar.url)
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

async def generate_transcript(channel: discord.TextChannel, ticket_info: dict, closed_by: discord.Member) -> io.BytesIO:
    now = datetime.now(timezone.utc)
    lines = []
    lines.append("=" * 70)
    lines.append("                        TRANSCRIPT DU TICKET")
    lines.append("=" * 70)
    lines.append(f"  Salon              : #{channel.name} ({channel.id})")
    lines.append(f"  Type               : {ticket_info.get('type_label', 'Inconnu')}")
    opener = ticket_info.get("opener")
    if opener:
        lines.append(f"  Ouvert par         : {opener.name} ({opener.id})")
        lines.append(f"  Compte créé le     : {opener.created_at.strftime('%d/%m/%Y %H:%M:%S UTC')}")
        if isinstance(opener, discord.Member) and opener.joined_at:
            lines.append(f"  A rejoint le       : {opener.joined_at.strftime('%d/%m/%Y %H:%M:%S UTC')}")
        roles = [r.name for r in opener.roles if r.name != "@everyone"] if isinstance(opener, discord.Member) else []
        lines.append(f"  Rôles              : {', '.join(roles) if roles else 'Aucun'}")
    claimed_by = ticket_info.get("claimed_by")
    lines.append(f"  Réclamé par        : {claimed_by.display_name} ({claimed_by.id})" if claimed_by else "  Réclamé par        : Personne")
    lines.append(f"  Fermé par          : {closed_by.display_name} ({closed_by.id})")
    opened_at = ticket_info.get("opened_at")
    if opened_at:
        lines.append(f"  Ouvert le          : {opened_at.strftime('%d/%m/%Y %H:%M:%S UTC')}")
        lines.append(f"  Fermé le           : {now.strftime('%d/%m/%Y %H:%M:%S UTC')}")
        total = int((now - opened_at).total_seconds())
        h, r = divmod(total, 3600)
        m, s = divmod(r, 60)
        lines.append(f"  Durée              : {h}h {m}m {s}s")
    lines.append("")
    lines.append("=" * 70)
    lines.append("                          MESSAGES")
    lines.append("=" * 70)
    lines.append("")
    messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
    for msg in messages:
        ts = msg.created_at.strftime("%d/%m/%Y %H:%M:%S UTC")
        lines.append(f"[{ts}] {msg.author.display_name} ({msg.author.id})")
        if msg.content:
            lines.append(f"  {msg.content}")
        for att in msg.attachments:
            lines.append(f"  [Fichier] {att.filename} → {att.url}")
        for emb in msg.embeds:
            lines.append(f"  [Embed] {emb.title or '(sans titre)'}")
        lines.append("")
    lines.append("=" * 70)
    lines.append(f"  Transcript généré le {now.strftime('%d/%m/%Y %H:%M:%S UTC')}")
    lines.append("=" * 70)
    return io.BytesIO("\n".join(lines).encode("utf-8"))

# ══════════════════════════════════════════════════════════════════════════════
# CRÉATION D'UN TICKET
# ══════════════════════════════════════════════════════════════════════════════

async def create_ticket(interaction: discord.Interaction, ticket_key: str):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    member = interaction.user
    config = TICKET_CONFIG[ticket_key]

    # Vérifie ticket existant (tous types)
    for key, cfg in TICKET_CONFIG.items():
        existing = discord.utils.get(guild.text_channels, name=f"{cfg['channel_prefix']}-{member.name.lower()}")
        if existing:
            await interaction.followup.send(f"Tu as déjà un ticket ouvert : {existing.mention}", ephemeral=True)
            return

    category = guild.get_channel(config["category_id"])
    mention_role = guild.get_role(config["mention_role_id"])
    support_role = guild.get_role(SUPPORT_ROLE_ID)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
    }
    # Donne accès à tous les rôles liés au support
    for role_id in {SUPPORT_ROLE_ID, STAFF_REPORT_ROLE_ID, ANIM_REPORT_ROLE_ID, DEV_ROLE_ID}:
        role = guild.get_role(role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    channel = await guild.create_text_channel(
        name=f"{config['channel_prefix']}-{member.name.lower()}",
        category=category,
        overwrites=overwrites,
        topic=f"Ticket de {member} | Type : {config['label']}"
    )

    ticket_store[channel.id] = {
        "opener": member,
        "type_label": config["label"],
        "ticket_key": ticket_key,
        "opened_at": datetime.now(timezone.utc),
        "claimed_by": None,
        "claimed_at": None,
    }

    # Mention permanente du rôle + membre (ne se supprime PAS)
    await channel.send(f"{mention_role.mention if mention_role else ''} {member.mention}")

    # Embed du ticket
    embed = discord.Embed(
        title=config["embed_title"],
        description=config["embed_desc"].format(mention=member.mention),
        color=0x2b2d31
    )
    embed.set_footer(text=f"Ticket ouvert par {member}", icon_url=member.display_avatar.url)
    await channel.send(embed=embed, view=TicketControlView())

    await interaction.followup.send(f"Ton ticket a été créé : {channel.mention}", ephemeral=True)

# ══════════════════════════════════════════════════════════════════════════════
# VUE CONTRÔLE TICKET (menu déroulant)
# ══════════════════════════════════════════════════════════════════════════════

class TicketControlSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Réclamer le ticket",    emoji="✋", value="claim",    description="Prendre en charge ce ticket"),
            discord.SelectOption(label="Relâcher le ticket",    emoji="🔓", value="unclaim",  description="Libérer la prise en charge"),
            discord.SelectOption(label="Transférer le ticket",  emoji="🔁", value="transfer", description="Transférer à un autre membre du support"),
            discord.SelectOption(label="Rappel au membre",      emoji="🔔", value="remind",   description="Ghost ping le membre pour lui rappeler son ticket"),
            discord.SelectOption(label="Fermer le ticket",      emoji="🔒", value="close",    description="Fermer et supprimer ce ticket"),
        ]
        super().__init__(
            placeholder="Gérer le ticket...",
            min_values=1, max_values=1,
            options=options,
            custom_id="ticket_control_select"
        )

    async def callback(self, interaction: discord.Interaction):
        support_role = interaction.guild.get_role(SUPPORT_ROLE_ID)
        # Vérifie que c'est bien un membre du support (ou admin)
        is_support = (support_role and support_role in interaction.user.roles) or interaction.user.guild_permissions.administrator

        action = self.values[0]

        # ── Réclamer ──────────────────────────────────────────────────────────
        if action == "claim":
            if not is_support:
                await interaction.response.send_message("Seul le Support Ticket peut réclamer un ticket.", ephemeral=True)
                return
            info = ticket_store.get(interaction.channel.id, {})
            if info.get("claimed_by"):
                await interaction.response.send_message(f"Ce ticket est déjà réclamé par {info['claimed_by'].mention}.", ephemeral=True)
                return
            ticket_store.setdefault(interaction.channel.id, {})
            ticket_store[interaction.channel.id]["claimed_by"] = interaction.user
            ticket_store[interaction.channel.id]["claimed_at"] = datetime.now(timezone.utc)
            embed = discord.Embed(description=f"Ticket réclamé par {interaction.user.mention}.", color=0x57f287)
            await interaction.response.send_message(embed=embed)

        # ── Relâcher ──────────────────────────────────────────────────────────
        elif action == "unclaim":
            if not is_support:
                await interaction.response.send_message("Seul le Support Ticket peut relâcher un ticket.", ephemeral=True)
                return
            info = ticket_store.get(interaction.channel.id, {})
            claimer = info.get("claimed_by")
            if not claimer:
                await interaction.response.send_message("Ce ticket n'est pas encore réclamé.", ephemeral=True)
                return
            if claimer.id != interaction.user.id and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("Seul la personne ayant réclamé le ticket (ou un admin) peut le relâcher.", ephemeral=True)
                return
            ticket_store[interaction.channel.id]["claimed_by"] = None
            ticket_store[interaction.channel.id]["claimed_at"] = None
            embed = discord.Embed(description=f"Ticket relâché par {interaction.user.mention}. Il est de nouveau disponible.", color=0xfee75c)
            await interaction.response.send_message(embed=embed)

        # ── Transférer ────────────────────────────────────────────────────────
        elif action == "transfer":
            if not is_support:
                await interaction.response.send_message("Seul le Support Ticket peut transférer un ticket.", ephemeral=True)
                return
            await interaction.response.send_modal(TransferModal())

        # ── Rappel ────────────────────────────────────────────────────────────
        elif action == "remind":
            if not is_support:
                await interaction.response.send_message("Seul le Support Ticket peut envoyer un rappel.", ephemeral=True)
                return
            info = ticket_store.get(interaction.channel.id, {})
            opener = info.get("opener")
            if opener:
                ghost = await interaction.channel.send(opener.mention)
                await ghost.delete()
                embed = discord.Embed(description=f"Rappel envoyé au membre.", color=0xfee75c)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("Impossible de trouver le membre ayant ouvert ce ticket.", ephemeral=True)

        # ── Fermer ────────────────────────────────────────────────────────────
        elif action == "close":
            if not is_support:
                await interaction.response.send_message("Seul le Support Ticket peut fermer un ticket.", ephemeral=True)
                return
            embed = discord.Embed(description=f"Ticket fermé par {interaction.user.mention}. Suppression dans 5 secondes...", color=0xed4245)
            await interaction.response.send_message(embed=embed)

            ticket_info = ticket_store.get(interaction.channel.id, {})
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
            log_emb.add_field(name="Réclamé par", value=f"{claimed_by.mention} (`{claimed_by.id}`)" if claimed_by else "Personne", inline=True)
            log_emb.add_field(name="Ouvert le", value=opened_at.strftime("%d/%m/%Y à %H:%M:%S UTC") if opened_at else "Inconnu", inline=True)
            log_emb.add_field(name="Durée", value=duration_str, inline=True)
            log_emb.set_footer(text=f"Ticket ID : {interaction.channel.id}")

            transcript_buf = await generate_transcript(interaction.channel, ticket_info, interaction.user)
            file = discord.File(transcript_buf, filename=f"transcript-{interaction.channel.name}.txt")
            await send_log(interaction.guild, log_emb, TICKET_LOG_CHANNEL_ID, file=file)

            await asyncio.sleep(5)
            ticket_store.pop(interaction.channel.id, None)
            await interaction.channel.delete()

class TransferModal(discord.ui.Modal, title="Transférer le ticket"):
    membre = discord.ui.TextInput(
        label="ID ou pseudo du membre du support",
        placeholder="Ex: 123456789012345678",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        target = None
        val = self.membre.value.strip()
        # Cherche par ID
        if val.isdigit():
            target = guild.get_member(int(val))
        # Sinon par pseudo
        if target is None:
            target = discord.utils.find(lambda m: m.name.lower() == val.lower() or m.display_name.lower() == val.lower(), guild.members)

        if target is None:
            await interaction.response.send_message("Membre introuvable.", ephemeral=True)
            return

        support_role = guild.get_role(SUPPORT_ROLE_ID)
        is_target_support = support_role and support_role in target.roles
        if not is_target_support and not target.guild_permissions.administrator:
            await interaction.response.send_message("Ce membre ne fait pas partie du Support Ticket.", ephemeral=True)
            return

        # Donne accès au nouveau membre
        await interaction.channel.set_permissions(target, read_messages=True, send_messages=True)

        # Met à jour le claimed_by
        if interaction.channel.id in ticket_store:
            ticket_store[interaction.channel.id]["claimed_by"] = target

        embed = discord.Embed(description=f"Ticket transféré à {target.mention} par {interaction.user.mention}.", color=0x5865f2)
        await interaction.response.send_message(embed=embed)

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketControlSelect())

# ══════════════════════════════════════════════════════════════════════════════
# PANEL TICKET — SELECT MENU PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class MainTicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Ticket Question",       emoji="❓", value="question",         description="Une question sur le serveur ou les règles ?"),
            discord.SelectOption(label="Report Joueur",         emoji="🎮", value="report_joueur",     description="Signaler un joueur pour comportement inapproprié ?"),
            discord.SelectOption(label="Report Personnel",      emoji="👥", value="report_personnel",  description="Signaler un staff ou un membre de l'animation ?"),
            discord.SelectOption(label="Report Développement",  emoji="💻", value="report_dev",        description="Signaler un bug ou un problème technique ?"),
        ]
        super().__init__(placeholder="Sélectionner le type de ticket...", min_values=1, max_values=1, options=options, custom_id="main_ticket_select")

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        if value == "report_personnel":
            # Sous-menu pour choisir staff ou animation
            await interaction.response.send_message(
                embed=discord.Embed(description="Choisis le type de report :", color=0x2b2d31),
                view=ReportPersonnelView(),
                ephemeral=True
            )
        else:
            await create_ticket(interaction, value)

class ReportPersonnelSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Report Staff",      emoji="🛡️", value="report_staff",     description="Signaler un membre du staff ?"),
            discord.SelectOption(label="Report Animation",  emoji="🎭", value="report_animation", description="Signaler un membre de l'équipe animation ?"),
        ]
        super().__init__(placeholder="Staff ou Animation ?", min_values=1, max_values=1, options=options, custom_id="report_personnel_sub")

    async def callback(self, interaction: discord.Interaction):
        await create_ticket(interaction, self.values[0])

class ReportPersonnelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(ReportPersonnelSelect())

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MainTicketSelect())

# ══════════════════════════════════════════════════════════════════════════════
# COMMANDE /panel-ticket
# ══════════════════════════════════════════════════════════════════════════════

@bot.tree.command(name="panel-ticket", description="Créer le panel de tickets dans ce salon")
@app_commands.checks.has_permissions(administrator=True)
async def panel_ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Support",
        description=(
            "Tu as besoin d'aide ? Sélectionne le type de ticket ci-dessous.\n\n"
            "❓ **Ticket Question**\nUne question sur le serveur, les règles ou autre chose.\n\n"
            "🎮 **Report Joueur**\nSignaler un joueur pour comportement inapproprié.\n\n"
            "👥 **Report Personnel**\nSignaler un staff ou un membre de l'animation.\n\n"
            "💻 **Report Développement**\nSignaler un bug ou un problème technique."
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
        dm = discord.Embed(title="Tu as été mis en sourdine", description=(f"Tu as été mis en sourdine sur **{interaction.guild.name}**.\n\n**Durée :** {duree_label}\n**Raison :** {raison}\n\nTu pourras de nouveau écrire <t:{int(until.timestamp())}:R>."), color=0xed4245, timestamp=datetime.now(timezone.utc))
        dm.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        await membre.send(embed=dm)
        dm_sent = True
    except discord.Forbidden:
        dm_sent = False
    await interaction.followup.send(f"{membre.mention} a été mute pendant **{duree_label}**.", ephemeral=True)
    embed = log_embed(title="Membre mute — /mute", fields=[("Membre ciblé", f"{membre.mention}\n`{membre.name}` • ID : `{membre.id}`", True), ("Durée", duree_label, True), ("Expire", f"<t:{int(until.timestamp())}:F>", True), ("Raison", raison, False), ("Salon", f"{interaction.channel.mention}", True), ("MP envoyé", "Oui" if dm_sent else "Non (MP fermés)", True), ("Date", f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>", False)], staff=interaction.user)
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
    supprimer_messages = max(0, min(7, supprimer_messages))
    try:
        dm = discord.Embed(title="Tu as été banni", description=f"Tu as été banni de **{interaction.guild.name}**.\n\n**Raison :** {raison}", color=0xed4245, timestamp=datetime.now(timezone.utc))
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
    await interaction.followup.send(f"**{membre.name}** a été banni.", ephemeral=True)
    embed = log_embed(title="Membre banni — /ban", fields=[("Membre banni", f"{membre.mention}\n`{membre.name}` • ID : `{membre.id}`", True), ("Compte créé le", membre.created_at.strftime("%d/%m/%Y à %H:%M UTC"), True), ("Raison", raison, False), ("Messages supprimés", f"{supprimer_messages} jour(s)", True), ("Salon", f"{interaction.channel.mention}", True), ("MP envoyé", "Oui" if dm_sent else "Non (MP fermés)", True), ("Date", f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>", False)], staff=interaction.user, color=0xed4245)
    embed.set_thumbnail(url=membre.display_avatar.url)
    await send_log(interaction.guild, embed)

# ══════════════════════════════════════════════════════════════════════════════
# SYSTÈME VOCAL STAFF
# ══════════════════════════════════════════════════════════════════════════════

STAFF_TRIGGER_CHANNEL_ID = 1500546745682235482
STAFF_ROOMS_CATEGORY_ID  = 1500550167772921968
WAITING_CHANNEL_ID       = 1500550504269479947

staff_rooms: dict[int, dict] = {}

class StaffRoomView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="Rendre Privé", style=discord.ButtonStyle.secondary, custom_id="staff_private_toggle", emoji="🔒")
    async def toggle_private(self, interaction: discord.Interaction, button: discord.ui.Button):
        room = staff_rooms.get(self.channel_id)
        if room is None:
            await interaction.response.send_message("Ce salon n'est plus actif.", ephemeral=True)
            return
        if interaction.user.id != room["staff"].id:
            await interaction.response.send_message("Seul le staff propriétaire peut changer ce paramètre.", ephemeral=True)
            return
        room["private"] = not room["private"]
        is_private = room["private"]
        if is_private:
            button.label = "Rendre Disponible"
            button.emoji = "✅"
            button.style = discord.ButtonStyle.danger
        else:
            button.label = "Rendre Privé"
            button.emoji = "🔒"
            button.style = discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)
        status = "privé" if is_private else "disponible"
        await interaction.channel.send(f"Salon désormais **{status}**.", delete_after=8)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    guild = member.guild

    if after.channel and after.channel.id == STAFF_TRIGGER_CHANNEL_ID:
        for ch_id, room in staff_rooms.items():
            if room["staff"].id == member.id:
                existing_ch = guild.get_channel(ch_id)
                if existing_ch:
                    await member.move_to(existing_ch)
                    return
        category = guild.get_channel(STAFF_ROOMS_CATEGORY_ID)
        if category is None:
            return
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=False),
            member: discord.PermissionOverwrite(connect=True, view_channel=True, manage_channels=True),
            guild.me: discord.PermissionOverwrite(connect=True, view_channel=True, manage_channels=True),
        }
        voice_channel = await guild.create_voice_channel(name=f"〔🎙〕{member.display_name}", category=category, overwrites=overwrites)
        staff_rooms[voice_channel.id] = {"staff": member, "private": False}
        await member.move_to(voice_channel)
        await asyncio.sleep(1)
        text_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        text_channel = await guild.create_text_channel(name=f"chat-{member.display_name.lower().replace(' ', '-')}", category=category, overwrites=text_overwrites)
        staff_rooms[voice_channel.id]["text_channel_id"] = text_channel.id
        view = StaffRoomView(voice_channel.id)
        embed = discord.Embed(title="Salon Staff", description=(f"Bienvenue {member.mention} dans ton salon privé.\n\n**Statut actuel :** ✅ Disponible\n\nClique sur **Rendre Privé** pour passer en mode Ne Pas Déranger."), color=0x57f287)
        embed.set_footer(text=f"Salon de {member.display_name}")
        await text_channel.send(embed=embed, view=view)

    if before.channel and before.channel.id in staff_rooms:
        room = staff_rooms[before.channel.id]
        if room["staff"].id == member.id:
            channel = guild.get_channel(before.channel.id)
            if channel and len(channel.members) == 0:
                text_ch_id = room.get("text_channel_id")
                if text_ch_id:
                    text_ch = guild.get_channel(text_ch_id)
                    if text_ch:
                        await text_ch.delete()
                await channel.delete()
                staff_rooms.pop(before.channel.id, None)

    if after.channel and after.channel.id == WAITING_CHANNEL_ID:
        for ch_id, room in staff_rooms.items():
            if room["staff"].id == member.id:
                return
        available_room = None
        for ch_id, room in staff_rooms.items():
            if room["private"]:
                continue
            staff_member = room["staff"]
            if hasattr(staff_member, "status") and staff_member.status == discord.Status.dnd:
                continue
            voice_ch = guild.get_channel(ch_id)
            if voice_ch and staff_member in voice_ch.members:
                available_room = voice_ch
                break
        if available_room:
            try:
                await member.move_to(available_room)
            except (discord.Forbidden, discord.HTTPException):
                pass

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
