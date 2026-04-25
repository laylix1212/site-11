import discord
import asyncio
import os
from datetime import datetime, timezone, timedelta
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1491033880491196588
LOG_CHANNEL_ID = 1497651927679500398

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True

class ModBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Slash commands synchronisées.")

bot = ModBot()

# ── Utilitaire log ────────────────────────────────────────────────────────────
async def send_log(guild: discord.Guild, embed: discord.Embed):
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(embed=embed)

def log_embed(title: str, fields: list, staff: discord.Member) -> discord.Embed:
    embed = discord.Embed(title=title, color=0x3b82f6, timestamp=datetime.now(timezone.utc))
    for name, value, inline in fields:
        embed.add_field(name=name, value=value, inline=inline)
    embed.set_footer(
        text=f"Effectué par {staff.display_name} • ID : {staff.id}",
        icon_url=staff.display_avatar.url
    )
    return embed

# ── Parsing durée ─────────────────────────────────────────────────────────────
def parse_duration(duration_str: str) -> tuple:
    units = {
        "s": ("seconde(s)", 1),
        "m": ("minute(s)", 60),
        "h": ("heure(s)", 3600),
        "d": ("jour(s)", 86400),
        "j": ("jour(s)", 86400),
    }
    duration_str = duration_str.strip().lower()
    unit = duration_str[-1] if duration_str else ""
    if unit not in units:
        return None, None
    try:
        amount = int(duration_str[:-1])
    except ValueError:
        return None, None
    if amount <= 0:
        return None, None
    label, multiplier = units[unit]
    return timedelta(seconds=amount * multiplier), f"{amount} {label}"

# ── /clear ────────────────────────────────────────────────────────────────────
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

@clear.error
async def clear_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Tu n'as pas la permission de supprimer des messages.", ephemeral=True)

# ── /mute ─────────────────────────────────────────────────────────────────────
@bot.tree.command(name="mute", description="Muter un membre pendant une durée définie")
@app_commands.describe(
    membre="Le membre à muter",
    duree="Durée du mute (ex: 10m, 2h, 1d)",
    raison="Raison du mute"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, membre: discord.Member, duree: str, raison: str = "Aucune raison fournie"):
    await interaction.response.defer(ephemeral=True)

    if membre.top_role >= interaction.user.top_role:
        await interaction.followup.send("Tu ne peux pas muter un membre avec un rôle supérieur ou égal au tien.", ephemeral=True)
        return
    if membre.id == interaction.guild.me.id:
        await interaction.followup.send("Je ne peux pas me muter moi-même.", ephemeral=True)
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
    except discord.HTTPException as e:
        await interaction.followup.send(f"Erreur : {e}", ephemeral=True)
        return

    # MP au membre — sans révéler le modérateur
    try:
        dm_embed = discord.Embed(
            title="Tu as été mis en sourdine",
            description=(
                f"Tu as été mis en sourdine sur **{interaction.guild.name}**.\n\n"
                f"**Durée :** {duree_label}\n"
                f"**Raison :** {raison}\n\n"
                f"Tu pourras de nouveau écrire <t:{int(until.timestamp())}:R>."
            ),
            color=0xed4245,
            timestamp=datetime.now(timezone.utc)
        )
        dm_embed.set_footer(
            text=interaction.guild.name,
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        await membre.send(embed=dm_embed)
        dm_sent = True
    except discord.Forbidden:
        dm_sent = False

    await interaction.followup.send(
        f"{membre.mention} a été mute pendant **{duree_label}**.",
        ephemeral=True
    )

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

@mute.error
async def mute_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Tu n'as pas la permission de muter des membres.", ephemeral=True)

# ── On ready ──────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"Connecté : {bot.user} (ID: {bot.user.id})")
    print("Commandes : /clear, /mute")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN manquant !")
    bot.run(TOKEN)
