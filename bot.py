import os
import discord
from discord.ext import commands
from discord import app_commands
import random
from dotenv import load_dotenv
import json

# Ładowanie tokenu z pliku .env
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Ustawienia bota
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Większa lista emotek do wyboru (około 20)
emotki = ['✅', '❌', '😀', '🚀', '🎉', '💡', '🔒', '🍎', '🍇', '🏆', 
          '🔥', '🌈', '⚽', '🎮', '🚗', '🎯', '🛠️', '🌍', '🌟', '🍕',
          '🍔', '🍟', '🎃', '🚁', '🦄', '🐍', '🐶']

# Słownik do przechowywania postępów użytkowników
users_progress = {}

# Plik do zapisywania ról weryfikacyjnych dla serwerów
roles_file = "verification_roles.json"

# Funkcja do zapisu ról do pliku
def save_roles_to_file(roles_data):
    with open(roles_file, "w") as file:
        json.dump(roles_data, file)

# Funkcja do ładowania ról z pliku
def load_roles_from_file():
    if os.path.exists(roles_file):
        with open(roles_file, "r") as file:
            try:
                data = json.load(file)
                if not data:
                    return {}
                return data
            except json.JSONDecodeError:
                # Jeśli plik jest pusty lub uszkodzony, zainicjuj pusty słownik
                return {}
    return {}

# Ładowanie ról na starcie
verification_roles = load_roles_from_file()

# Funkcja odpowiedzialna za aktualizację CAPTCHA po weryfikacji
async def update_captcha_message(message, guild_id):
    # Wylosowanie 3 poprawnych emotek (unikalne)
    correct_emojis = random.sample(emotki, 3)
    
    # Wylosowanie dodatkowych 6 unikalnych emotek, które nie są poprawnymi emotkami
    remaining_emotki = [emoji for emoji in emotki if emoji not in correct_emojis]
    wrong_emojis = random.sample(remaining_emotki, 6)

    # Łącznie 9 unikalnych emotek
    all_emojis = correct_emojis + wrong_emojis
    random.shuffle(all_emojis)

    # Tworzenie embedowanej wiadomości z instrukcjami
    embed = discord.Embed(
        title="Weryfikacja CAPTCHA",
        description=f"Zapamiętaj te emotki: {', '.join(correct_emojis)}\nKliknij 3 poprawne emotki z poniższej tabeli.",
        color=discord.Color.blue()
    )

    # Tworzenie widoku z przyciskami
    view = discord.ui.View(timeout=None)  # Timeout ustawiony na None, aby wiadomość była "trwała"

    # Funkcja wywoływana po kliknięciu każdego przycisku
    async def button_callback(interaction_button, emoji):
        user = interaction_button.user

        if user not in users_progress:
            users_progress[user] = []

        users_progress[user].append(emoji)
        await interaction_button.response.defer()

        # Sprawdzenie, czy użytkownik wybrał 3 emotki
        if len(users_progress[user]) == 3:
            if set(users_progress[user]) == set(correct_emojis):
                # Nadanie roli dla danego serwera
                role_id = verification_roles.get(str(guild_id))
                if role_id:
                    role = discord.utils.get(interaction_button.guild.roles, id=int(role_id))
                    if role:
                        await user.add_roles(role)
                        await interaction_button.followup.send(f'{user.mention}, zostałeś zweryfikowany i nadano ci rolę!', ephemeral=True)
                    else:
                        await interaction_button.followup.send(f'Rola z ID {role_id} nie istnieje na tym serwerze.', ephemeral=True)
                else:
                    await interaction_button.followup.send('Nie ustawiono roli weryfikacji dla tego serwera.', ephemeral=True)
            else:
                await interaction_button.followup.send(f'{user.mention}, błędny wybór emotek! Spróbuj ponownie.', ephemeral=True)

            # Czyszczenie postępu po ukończeniu i aktualizacja CAPTCHA
            users_progress[user] = []
            await update_captcha_message(message, guild_id)

    # Dodanie przycisków do widoku
    for emoji in all_emojis:
        button = discord.ui.Button(label=emoji, style=discord.ButtonStyle.primary)
        button.callback = lambda interaction_button, emoji=emoji: button_callback(interaction_button, emoji)
        view.add_item(button)

    # Edytowanie wiadomości z nowymi emotkami
    await message.edit(embed=embed, view=view)

# Komenda do ustawienia roli weryfikacyjnej dla serwera
@bot.tree.command(name="setrole", description="Ustawia rolę weryfikacyjną dla tego serwera")
@app_commands.describe(role="Rola, którą chcesz ustawić jako weryfikacyjną")
async def set_role(interaction: discord.Interaction, role: discord.Role):
    verification_roles[str(interaction.guild_id)] = str(role.id)
    save_roles_to_file(verification_roles)
    await interaction.response.send_message(f'Rola {role.name} została ustawiona jako weryfikacyjna dla tego serwera.', ephemeral=True)

# Komenda do spawnowania wiadomości z CAPTCHA
@bot.tree.command(name="captcha", description="Spawnuje wiadomość CAPTCHA na kanale lub dla użytkownika")
@app_commands.describe(user="Opcjonalny użytkownik do weryfikacji")
async def captcha(interaction: discord.Interaction, user: discord.Member = None):
    # Wysłanie nowej wiadomości CAPTCHA
    channel = interaction.channel
    if user:
        message = await channel.send(f"Weryfikacja dla {user.mention}...")  # Placeholder wiadomości dla użytkownika
    else:
        message = await channel.send("Trwa ładowanie CAPTCHA...")  # Placeholder wiadomości ogólnej
    await update_captcha_message(message, interaction.guild_id)  # Aktualizacja z CAPTCHA
    await interaction.response.send_message("Wiadomość CAPTCHA została wysłana.", ephemeral=True)

# Uruchom bota
bot.run(TOKEN)
