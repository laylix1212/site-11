import discord
import asyncio
import os
from discord.ext import commands

# ─── Configuration ───────────────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1491033880491196588
VOICE_CHANNEL_ID = 1497624020823183522

# ─── Intents ─────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ─── Events ──────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user} (ID: {bot.user.id})")
    print(f"📡 Tentative de connexion au salon vocal {VOICE_CHANNEL_ID}...")
    await join_voice()

async def join_voice():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print(f"❌ Serveur introuvable (ID: {GUILD_ID})")
        return

    channel = guild.get_channel(VOICE_CHANNEL_ID)
    if channel is None:
        print(f"❌ Salon vocal introuvable (ID: {VOICE_CHANNEL_ID})")
        return

    if not isinstance(channel, discord.VoiceChannel):
        print(f"❌ Le salon {channel.name} n'est pas un salon vocal")
        return

    # Vérifie si déjà connecté
    if guild.voice_client is not None:
        if guild.voice_client.channel.id == VOICE_CHANNEL_ID:
            print(f"✅ Déjà connecté à #{channel.name}")
            return
        await guild.voice_client.disconnect()

    # Connexion : self_mute=True (sourdine), self_deaf=False (PAS muet)
    vc = await channel.connect(self_deaf=False, self_mute=True)

    print(f"🎙️  Connecté à #{channel.name}")
    print(f"   🔇 Sourdine (self_mute) : OUI  → le bot n'envoie pas d'audio")
    print(f"   👂 Muet    (self_deaf)  : NON  → le bot ENTEND les autres")

# ─── Commandes (optionnel) ────────────────────────────────────────────────────
@bot.command(name="join")
@commands.has_permissions(administrator=True)
async def join(ctx):
    """Force le bot à rejoindre le salon vocal configuré."""
    await join_voice()
    await ctx.send("✅ Connexion au salon vocal effectuée.")

@bot.command(name="leave")
@commands.has_permissions(administrator=True)
async def leave(ctx):
    """Déconnecte le bot du salon vocal."""
    guild = ctx.guild
    if guild.voice_client:
        await guild.voice_client.disconnect()
        await ctx.send("👋 Déconnecté du salon vocal.")
    else:
        await ctx.send("❌ Le bot n'est pas dans un salon vocal.")

@bot.command(name="status")
async def status(ctx):
    """Affiche le statut de connexion du bot."""
    guild = ctx.guild
    if guild.voice_client and guild.voice_client.is_connected():
        vc = guild.voice_client
        await ctx.send(
            f"✅ Connecté à **#{vc.channel.name}**\n"
            f"🔇 Sourdine : `{vc.self_mute}` | 👂 Muet : `{vc.self_deaf}`"
        )
    else:
        await ctx.send("❌ Non connecté à un salon vocal.")

# ─── Reconnexion automatique si éjecté ───────────────────────────────────────
@bot.event
async def on_voice_state_update(member, before, after):
    if member.id != bot.user.id:
        return
    # Si le bot a été déconnecté
    if before.channel is not None and after.channel is None:
        print("⚠️  Bot déconnecté du vocal, tentative de reconnexion dans 5s...")
        await asyncio.sleep(5)
        await join_voice()

# ─── Lancement ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("❌ DISCORD_TOKEN manquant ! Ajoute-le dans les variables d'environnement.")
    bot.run(TOKEN)
