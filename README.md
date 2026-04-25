# Discord Voice Bot 🎙️

Bot Discord qui rejoint un salon vocal en **sourdine** (il n'envoie pas d'audio) mais **pas muet** (il entend les autres).

## Différence sourdine / muet

| État | Icône Discord | Ce que ça fait |
|------|--------------|----------------|
| **Sourdine** (`self_mute=True`) | 🔇 Micro barré | Le bot **n'envoie pas** de son |
| **Muet** (`self_deaf=True`) | 🔈 Casque barré | Le bot **n'entend pas** les autres |

> Ce bot est en **sourdine uniquement** → il entend tout mais ne parle pas.

## Configuration Railway

### 1. Variables d'environnement
Dans Railway → ton projet → **Variables**, ajoute :
```
DISCORD_TOKEN=ton_token_ici
```

### 2. Déploiement
1. Push ce repo sur GitHub
2. Dans Railway : **New Project → Deploy from GitHub repo**
3. Sélectionne ton repo
4. Railway détecte automatiquement le `Procfile`

## Obtenir un token Discord

1. Va sur https://discord.com/developers/applications
2. **New Application** → donne un nom
3. **Bot** → **Add Bot** → copie le token
4. **Bot** → active les intents :
   - ✅ `SERVER MEMBERS INTENT`
   - ✅ `MESSAGE CONTENT INTENT`
5. **OAuth2 → URL Generator** :
   - Scopes : `bot`
   - Permissions : `Connect`, `Speak`, `View Channels`
6. Utilise l'URL générée pour inviter le bot sur ton serveur

## Commandes disponibles

| Commande | Description |
|---------|-------------|
| `!join` | Force la connexion au salon vocal (admin) |
| `!leave` | Déconnecte le bot du vocal (admin) |
| `!status` | Affiche l'état de connexion |
