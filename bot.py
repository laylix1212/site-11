import discord
import asyncio
import os
from discord import app_commands
from discord.ext import commands

# ─── Configuration ───────────────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1491033880491196588
MUSIC_FILE = "music.mp3"

# ─── Intents ─────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

# ─── Bot setup ───────────────────────────────────────────────────────────────
class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("✅ Slash commands synchronisées !")

bot = MusicBot()

# ─── Lecture musique en boucle ───────────────────────────────────────────────
def play_music(vc: discord.VoiceClient):
    if not os.path.exists(MUSIC_FILE):
        print(f"❌ Fichier {MUSIC_FILE} introuvable !")
        return

    def after_play(error):
        if error:
            print(f"❌ Erreur lecture : {error}")
            return
        if vc.is_connected():
            play_music(vc)

    source = discord.FFmpegPCMAudio(MUSIC_FILE)
    source = discord.PCMVolumeTransformer(source, volume=0.5)
    vc.play(source, after=after_play)
    print(f"🎵 Lecture de {MUSIC_FILE} en boucle...")

# ─── Autocomplete : liste des salons vocaux ──────────────────────────────────
async def vocal_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    guild = interaction.guild
    if guild is None:
        return []
    choices = [
        app_commands.Choice(name=channel.name, value=str(channel.id))
        for channel in guild.voice_channels
        if current.lower() in channel.name.lower()
    ]
    return choices[:25]

# ─── Commande /connecter ─────────────────────────────────────────────────────
@bot.tree.command(
    name="connecter",
    description="Connecte le bot à un salon vocal et joue la musique 🎵"
)
@app_commands.describe(salon="Choisis un salon vocal")
@app_commands.autocomplete(salon=vocal_autocomplete)
async def connecter(interaction: discord.Interaction, salon: str):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    channel = guild.get_channel(int(salon))

    if channel is None or not isinstance(channel, discord.VoiceChannel):
        await interaction.followup.send("❌ Salon vocal introuvable.", ephemeral=True)
        return

    if guild.voice_client is not None:
        if guild.voice_client.is_playing():
            guild.voice_client.stop()
        await guild.voice_client.move_to(channel)
        vc = guild.voice_client
    else:
        vc = await channel.connect(self_deaf=False, self_mute=False)

    if not vc.is_playing():
        play_music(vc)

    await interaction.followup.send(
        f"✅ Connecté à **#{channel.name}** et musique lancée 🎵",
        ephemeral=True
    )

# ─── Commande /deconnecter ────────────────────────────────────────────────────
@bot.tree.command(
    name="deconnecter",
    description="Déconnecte le bot du salon vocal 👋"
)
async def deconnecter(interaction: discord.Interaction):
    guild = interaction.guild
    if guild.voice_client and guild.voice_client.is_connected():
        if guild.voice_client.is_playing():
            guild.voice_client.stop()
        await guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Déconnecté !", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Le bot n'est pas dans un salon vocal.", ephemeral=True)

# ─── Commande /pause ─────────────────────────────────────────────────────────
@bot.tree.command(name="pause", description="Met la musique en pause ⏸️")
async def pause(interaction: discord.Interaction):
    guild = interaction.guild
    if guild.voice_client and guild.voice_client.is_playing():
        guild.voice_client.pause()
        await interaction.response.send_message("⏸️ Musique en pause.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Aucune musique en cours.", ephemeral=True)

# ─── Commande /reprendre ──────────────────────────────────────────────────────
@bot.tree.command(name="reprendre", description="Reprend la musique ▶️")
async def reprendre(interaction: discord.Interaction):
    guild = interaction.guild
    if guild.voice_client and guild.voice_client.is_paused():
        guild.voice_client.resume()
        await interaction.response.send_message("▶️ Musique reprise !", ephemeral=True)
    else:
        await interaction.response.send_message("❌ La musique n'est pas en pause.", ephemeral=True)

# ─── On ready ────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user} (ID: {bot.user.id})")
    print(f"🎵 Fichier musique : {'✅ trouvé' if os.path.exists(MUSIC_FILE) else '❌ MANQUANT'}")
    print("📋 Commandes dispo : /connecter, /deconnecter, /pause, /reprendre")

# ─── Lancement ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("❌ DISCORD_TOKEN manquant !")
    bot.run(TOKEN)
