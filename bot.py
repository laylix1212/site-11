import discord
import asyncio
import os
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1491033880491196588
MUSIC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music.mp3")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Slash commands synchronisees.")

bot = MusicBot()

def play_music(vc: discord.VoiceClient):
    if not os.path.exists(MUSIC_FILE):
        print(f"music.mp3 introuvable : {MUSIC_FILE}")
        return

    def after_play(error):
        if error:
            print(f"Erreur lecture : {error}")
            return
        if vc.is_connected():
            play_music(vc)

    source = discord.FFmpegPCMAudio(MUSIC_FILE, options="-vn")
    source = discord.PCMVolumeTransformer(source, volume=0.5)
    vc.play(source, after=after_play)
    print("Musique lancee en boucle.")

async def vocal_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    guild = interaction.guild
    if guild is None:
        return []
    return [
        app_commands.Choice(name=channel.name, value=str(channel.id))
        for channel in guild.voice_channels
        if current.lower() in channel.name.lower()
    ][:25]

async def force_connect(channel: discord.VoiceChannel) -> discord.VoiceClient:
    guild = channel.guild

    # Nettoyage complet de toute connexion existante
    if guild.voice_client is not None:
        try:
            guild.voice_client.stop()
        except Exception:
            pass
        try:
            await guild.voice_client.disconnect(force=True)
        except Exception:
            pass
        # Attendre que Discord enregistre la déconnexion
        await asyncio.sleep(2)

    # Plusieurs tentatives de connexion
    last_error = None
    for attempt in range(1, 4):
        try:
            print(f"Tentative de connexion vocale {attempt}/3...")
            vc = await channel.connect(timeout=60.0, reconnect=True, self_deaf=False, self_mute=False)
            print(f"Connexion vocale reussie (tentative {attempt})")
            return vc
        except Exception as e:
            last_error = e
            print(f"Echec tentative {attempt} : {e}")
            # Forcer le nettoyage entre les tentatives
            if guild.voice_client is not None:
                try:
                    await guild.voice_client.disconnect(force=True)
                except Exception:
                    pass
            await asyncio.sleep(3)

    raise Exception(f"Impossible de se connecter apres 3 tentatives : {last_error}")

@bot.tree.command(name="connecter", description="Connecte le bot a un salon vocal et joue la musique")
@app_commands.describe(salon="Choisis un salon vocal")
@app_commands.autocomplete(salon=vocal_autocomplete)
async def connecter(interaction: discord.Interaction, salon: str):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    channel = guild.get_channel(int(salon))

    if channel is None or not isinstance(channel, discord.VoiceChannel):
        await interaction.followup.send("Salon vocal introuvable.", ephemeral=True)
        return

    try:
        vc = await force_connect(channel)
    except Exception as e:
        await interaction.followup.send(f"Erreur : {e}", ephemeral=True)
        return

    await asyncio.sleep(1)
    play_music(vc)

    await interaction.followup.send(f"Connecte a **#{channel.name}**.", ephemeral=True)

@bot.tree.command(name="deconnecter", description="Deconnecte le bot du salon vocal")
async def deconnecter(interaction: discord.Interaction):
    guild = interaction.guild
    if guild.voice_client and guild.voice_client.is_connected():
        guild.voice_client.stop()
        await guild.voice_client.disconnect(force=True)
        await interaction.response.send_message("Deconnecte.", ephemeral=True)
    else:
        await interaction.response.send_message("Le bot n'est pas dans un salon vocal.", ephemeral=True)

@bot.tree.command(name="pause", description="Met la musique en pause")
async def pause(interaction: discord.Interaction):
    guild = interaction.guild
    if guild.voice_client and guild.voice_client.is_playing():
        guild.voice_client.pause()
        await interaction.response.send_message("Musique en pause.", ephemeral=True)
    else:
        await interaction.response.send_message("Aucune musique en cours.", ephemeral=True)

@bot.tree.command(name="reprendre", description="Reprend la musique")
async def reprendre(interaction: discord.Interaction):
    guild = interaction.guild
    if guild.voice_client and guild.voice_client.is_paused():
        guild.voice_client.resume()
        await interaction.response.send_message("Musique reprise.", ephemeral=True)
    else:
        await interaction.response.send_message("La musique n'est pas en pause.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Connecte : {bot.user} (ID: {bot.user.id})")
    print(f"FFmpeg : {'ok' if os.system('which ffmpeg > /dev/null 2>&1') == 0 else 'INTROUVABLE'}")
    print(f"music.mp3 : {'trouve' if os.path.exists(MUSIC_FILE) else 'INTROUVABLE'}")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN manquant !")
    bot.run(TOKEN)
