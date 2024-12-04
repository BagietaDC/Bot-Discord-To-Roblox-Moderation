import nextcord
import asyncio
from nextcord.ext import commands
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz

# Połączenie z MongoDB
MONGO_URI = "mongodb+srv://<nazwa>:<haslo>@<nazwaclustera>.uyah9.mongodb.net/?retryWrites=true&w=majority&appName=<nazwaclustera>"
client = MongoClient(MONGO_URI)
db = client['bans_db']
bans_collection = db['bans']

# Inicjalizacja bota
intents = nextcord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# Komenda /ban
@bot.slash_command(description="Banuj gracza Roblox")
async def ban(
    interaction: nextcord.Interaction,
    roblox_id: str,
    hours: int,
    reason: str,
    perm: bool
):
    # Sprawdź, czy gracz jest już zbanowany
    existing_ban = bans_collection.find_one({"roblox_id": roblox_id})
    if existing_ban:
        await interaction.response.send_message(f"Gracz {roblox_id} jest już zbanowany.", ephemeral=True)
        return

    # Oblicz czas zakończenia bana
    end_time = None if perm else datetime.now(pytz.utc) + timedelta(hours=hours)
    ban_data = {
        "roblox_id": roblox_id,
        "reason": reason,
        "end_time": end_time.isoformat() if end_time else None,
        "permanent": perm,
        "banned_by": str(interaction.user)
    }
    bans_collection.insert_one(ban_data)
    await interaction.response.send_message(f"Gracz {roblox_id} został zbanowany za '{reason}'.")

# Komenda /unban
@bot.slash_command(description="Usuń bana gracza Roblox")
async def unban(interaction: nextcord.Interaction, roblox_id: str):
    result = bans_collection.delete_one({"roblox_id": roblox_id})
    if result.deleted_count > 0:
        await interaction.response.send_message(f"Gracz {roblox_id} został odbanowany.")
    else:
        await interaction.response.send_message(f"Gracz {roblox_id} nie miał aktywnego bana.", ephemeral=True)

# Komenda /bans
@bot.slash_command(description="Pokaż aktywne bany")
async def bans(interaction: nextcord.Interaction):
    active_bans = bans_collection.find()
    if active_bans.count_documents({}) == 0:
        await interaction.response.send_message("Nie ma aktywnych banów.")
        return

    ban_list = []
    for ban in active_bans:
        end_time_str = ban["end_time"] if ban["end_time"] else "Permanent"
        ban_list.append(f"ID: {ban['roblox_id']} | Powód: {ban['reason']} | Koniec: {end_time_str}")
    ban_message = "\n".join(ban_list)
    await interaction.response.send_message(f"**Aktualne bany:**\n{ban_message}")

# Logika unbanowania po czasie
async def unban_expired_bans():
    while True:
        now = datetime.now(pytz.utc)
        expired_bans = bans_collection.find({"end_time": {"$lte": now.isoformat()}})
        for ban in expired_bans:
            bans_collection.delete_one({"_id": ban["_id"]})
        await asyncio.sleep(60)  # Sprawdzaj co minutę

# Start bota
@bot.event
async def on_ready():
    print(f"Bot {bot.user} jest online.")
    bot.loop.create_task(unban_expired_bans())

bot.run("TOKEN DISCORD BOT")