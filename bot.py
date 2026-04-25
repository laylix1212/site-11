import discord
import asyncio
import os
from datetime import datetime, timezone, timedelta
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1491033880491196588
LOG_CHANNEL_ID = 1497651927679500398

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True

bot = commands.Bot(command_prefix="+", intents=intents)
bot.remove_command("help")

# ── Utilitaire log ────────────────────────────────────────────────────────────
async def send_log(guild: discord.Guild, embed: discord.Embed):
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(embed=embed)
    else:
        print(f"Salon de logs introuvable (ID: {LOG_CHANNEL_ID})")

def log_embed(title: str, fields: list[tuple], staff: discord.Member) -> discord.Embed:
    embed = discord.Embed(title=title, color=0x3b82f6, timestamp=datetime.now(timezone.utc))
    for name, value, inline in fields:
        embed.add_field(name=name, value=value, inline=inline)
    embed.set_footer(
        text=f"Effectué par {staff.display_name} • ID : {staff.id}",
        icon_url=staff.display_avatar.url
    )
    return embed

# ── Parsing durée ─────────────────────────────────────────────────────────────
def parse_duration(duration_str: str) -> tuple[timedelta | None, str | None]:
    """
    Accepte : 10s, 10m, 10h, 1d, 1j
    Retourne (timedelta, texte lisible) ou (None, None) si invalide
    """
    units = {
        "s": ("seconde(s)", 1),
        "m": ("minute(s)", 60),
        "h": ("heure(s)", 3600),
        "d": ("jour(s)", 86400),
        "j": ("jour(s)", 86400),
    }
    duration_str = duration_str.strip().lower()
    if not duration_str:
        return None, None
    unit = duration_str[-1]
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

# ── +clear ─────────────────────────────────────────────────────────────────────
@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
@commands.guild_only()
async def clear(ctx: commands.Context, nombre: int):
    if nombre < 1 or nombre > 100:
        await ctx.send("Le nombre doit être compris entre 1 et 100.", delete_after=5)
        return

    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=nombre)
    count = len(deleted)

    await ctx.send(f"{count} message(s) supprimé(s).", delete_after=5, silent=True)

    embed = log_embed(
        title="Messages supprimés — +clear",
        fields=[
            ("Salon", f"{ctx.channel.mention} (`#{ctx.channel.name}` • `{ctx.channel.id}`)", False),
            ("Nombre demandé", str(nombre), True),
            ("Nombre supprimé", str(count), True),
            ("Date", f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>", False),
        ],
        staff=ctx.author
    )
    await send_log(ctx.guild, embed)

@clear.error
async def clear_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Tu n'as pas la permission de supprimer des messages.", delete_after=5)
    elif isinstance(error, commands.BadArgument) or isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Utilisation : `+clear <nombre>` (max 100)", delete_after=5)

# ── +mute ──────────────────────────────────────────────────────────────────────
@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
@commands.guild_only()
async def mute(ctx: commands.Context, membre: discord.Member, duree: str, *, raison: str = "Aucune raison fournie"):
    await ctx.message.delete()

    # Vérifications
    if membre.top_role >= ctx.author.top_role:
        await ctx.send("Tu ne peux pas mute un membre avec un rôle supérieur ou égal au tien.", delete_after=5)
        return
    if membre.id == ctx.guild.me.id:
        await ctx.send("Je ne peux pas me muter moi-même.", delete_after=5)
        return

    delta, duree_label = parse_duration(duree)
    if delta is None:
        await ctx.send("Durée invalide. Exemples : `10m`, `1h`, `2d` (s/m/h/d/j)", delete_after=5)
        return

    # Discord limite le timeout à 28 jours max
    max_delta = timedelta(days=28)
    if delta > max_delta:
        await ctx.send("La durée maximale est de 28 jours.", delete_after=5)
        return

    until = datetime.now(timezone.utc) + delta

    try:
        await membre.timeout(until, reason=raison)
    except discord.Forbidden:
        await ctx.send("Je n'ai pas la permission de muter ce membre.", delete_after=5)
        return
    except discord.HTTPException as e:
        await ctx.send(f"Erreur lors du mute : {e}", delete_after=5)
        return

    # Message privé au membre (sans afficher le modérateur)
    try:
        dm_embed = discord.Embed(
            title="Tu as été mis en sourdine",
            description=(
                f"Tu as été mis en sourdine sur **{ctx.guild.name}**.\n\n"
                f"**Durée :** {duree_label}\n"
                f"**Raison :** {raison}\n\n"
                f"Tu pourras de nouveau écrire <t:{int(until.timestamp())}:R>."
            ),
            color=0xed4245,
            timestamp=datetime.now(timezone.utc)
        )
        dm_embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        await membre.send(embed=dm_embed)
        dm_sent = True
    except discord.Forbidden:
        dm_sent = False

    await ctx.send(
        f"{membre.mention} a été mute pendant **{duree_label}**.",
        delete_after=8,
        silent=True
    )

    embed = log_embed(
        title="Membre mute — +mute",
        fields=[
            ("Membre ciblé", f"{membre.mention}\n`{membre.name}` • ID : `{membre.id}`", True),
            ("Durée", duree_label, True),
            ("Expire", f"<t:{int(until.timestamp())}:F>", True),
            ("Raison", raison, False),
            ("Salon", f"{ctx.channel.mention}", True),
            ("MP envoyé", "Oui" if dm_sent else "Non (MP fermés)", True),
            ("Date", f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>", False),
        ],
        staff=ctx.author
    )
    embed.set_thumbnail(url=membre.display_avatar.url)
    await send_log(ctx.guild, embed)

@mute.error
async def mute_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Tu n'as pas la permission de muter des membres.", delete_after=5)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Membre introuvable.", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Utilisation : `+mute <@membre> <durée> [raison]`\nExemple : `+mute @pseudo 10m Spam`", delete_after=8)
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Membre introuvable.", delete_after=5)

# ── On ready ──────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"Connecté : {bot.user} (ID: {bot.user.id})")
    print("Commandes disponibles : +clear, +mute")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN manquant !")
    bot.run(TOKEN)
