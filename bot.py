import discord
import asyncio
import os
import sys
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

    # Cherche ffmpeg dans plusieurs endroits possibles
    ffmpeg_path = "ffmpeg"
    for path in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/nix/store"]:
        if os.path.isfile(path):
            ffmpeg_path = path
            break
        if path == "/nix/store" and os.path.isdir(path):
            # cherche dans nix store
            for root, dirs, files in os.walk(path):
                if "ffmpeg" in files:
                    ffmpeg_path = os.path.join(root, "ffmpeg")
                    break

    print(f"Utilisation ffmpeg : {ffmpeg_path}")
    source = discord.FFmpegPCMAudio(MUSIC_FILE, executable=ffmpeg_path, options="-vn")
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

async def connect_voice(channel: discord.VoiceChannel) -> discord.VoiceClient:
    guild = channel.guild

    # Nettoyage complet
    if guild.voice_client is not None:
        try:
            guild.voice_client.stop()
        except Exception:
            pass
        try:
            await guild.voice_client.disconnect(force=True)
        except Exception:
            pass
        await asyncio.sleep(3)

    # Reconnexion du gateway principal pour reset la session voice
    try:
        await bot.ws.voice_state(guild.id, None)
        await asyncio.sleep(2)
    except Exception as e:
        print(f"Reset voice state: {e}")

    # Tentatives de connexion
    for attempt in range(1, 6):
        try:
            print(f"Tentative {attempt}/5...")
            vc = await asyncio.wait_for(
                channel.connect(reconnect=True, self_deaf=False, self_mute=False),
                timeout=30.0
            )
            print(f"Connexion reussie tentative {attempt}")
            return vc
        except asyncio.TimeoutError:
            print(f"Timeout tentative {attempt}")
        except discord.errors.ConnectionClosed as e:
            print(f"ConnectionClosed {e.code} tentative {attempt}")
            if guild.voice_client:
                try:
                    await guild.voice_client.disconnect(force=True)
                except Exception:
                    pass
            # Reset voice state entre les tentatives
            try:
                await bot.ws.voice_state(guild.id, None)
            except Exception:
                pass
        except Exception as e:
            print(f"Erreur tentative {attempt} : {e}")
        await asyncio.sleep(4)

    raise Exception("Impossible de se connecter au salon vocal apres 5 tentatives.")

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
        vc = await connect_voice(channel)
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
    ffmpeg_found = os.system("which ffmpeg > /dev/null 2>&1") == 0
    print(f"FFmpeg : {'ok' if ffmpeg_found else 'INTROUVABLE'}")
    print(f"music.mp3 : {'trouve' if os.path.exists(MUSIC_FILE) else 'INTROUVABLE'}")
    print(f"Python : {sys.version}")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN manquant !")
    bot.run(TOKEN)
