import os
import discord
from discord.ext import commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import requests
from functools import lru_cache

# Load environment variables
load_dotenv()

# Variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GOOGLE_CREDENTIALS_FILE = '/home/jsm177y/ODLBot/odlbot-421819-5192c6bbcd6c.json'

# Set up Discord intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

# Discord Bot setup
bot = commands.Bot(command_prefix='!', intents=intents)

# Google Sheets setup
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open("Oshawott Draft League").worksheet('Standings')

# Caching functions
@lru_cache(maxsize=128)
def get_pokeapi_data(endpoint: str):
    """Cached function to get data from the PokéAPI."""
    url = f"https://pokeapi.co/api/v2/{endpoint}/"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

# Caching functions
@lru_cache(maxsize=128)
def get_pokeapi_data(endpoint: str):
    """Cached function to get data from the PokéAPI."""
    url = f"https://pokeapi.co/api/v2/{endpoint}/"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

@bot.command(name='type')
async def type_info(ctx, *, poke_type: str):
    data = get_pokeapi_data(f'type/{poke_type.lower()}')
    if data:
        double_damage_to = [type_info['name'] for type_info in data['damage_relations']['double_damage_to']]
        half_damage_to = [type_info['name'] for type_info in data['damage_relations']['half_damage_to']]
        no_damage_to = [type_info['name'] for type_info in data['damage_relations']['no_damage_to']]
        double_damage_from = [type_info['name'] for type_info in data['damage_relations']['double_damage_from']]
        half_damage_from = [type_info['name'] for type_info in data['damage_relations']['half_damage_from']]
        no_damage_from = [type_info['name'] for type_info in data['damage_relations']['no_damage_from']]

        embed = discord.Embed(title=f"{poke_type.title()} Type Interactions", color=discord.Color.blue())
        embed.add_field(name="Super Effective Against", value=', '.join(double_damage_to).title() or "None", inline=False)
        embed.add_field(name="--------------------------------", value="\u200b", inline=False)  # Divider
        embed.add_field(name="Not Very Effective Against", value=', '.join(half_damage_to).title() or "None", inline=False)
        embed.add_field(name="--------------------------------", value="\u200b", inline=False)  # Divider
        embed.add_field(name="No Effect Against", value=', '.join(no_damage_to).title() or "None", inline=False)
        embed.add_field(name="--------------------------------", value="\u200b", inline=False)  # Divider
        embed.add_field(name="Vulnerable To", value=', '.join(double_damage_from).title() or "None", inline=False)
        embed.add_field(name="--------------------------------", value="\u200b", inline=False)  # Divider
        embed.add_field(name="Resistant To", value=', '.join(half_damage_from).title() or "None", inline=False)
        embed.add_field(name="--------------------------------", value="\u200b", inline=False)  # Divider
        embed.add_field(name="Immune To", value=', '.join(no_damage_from).title() or "None", inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("Type not found. Please check the type and try again.")

@bot.command(name='move')
async def move_info(ctx, *, move_name: str):
    data = get_pokeapi_data(f'move/{move_name.lower().replace(" ", "-")}')
    if data:
        # Basic move information
        name = data['name'].replace('-', ' ').title()
        description = next((entry['flavor_text'] for entry in data['flavor_text_entries'] if entry['language']['name'] == 'en'), "No description available.")
        power = data.get('power', 'N/A')
        pp = data.get('pp', 'N/A')
        accuracy = data.get('accuracy', 'N/A')
        
        # Move category (special, physical, status)
        category = data['damage_class']['name'].title()

        # Fetching additional effect text
        effect = next((entry['effect'] for entry in data['effect_entries'] if entry['language']['name'] == 'en'), "No additional effects.")

        embed = discord.Embed(title=f"Move: {name}", color=discord.Color.gold())
        embed.add_field(name="Description", value=description, inline=False)
        embed.add_field(name="Category", value=category, inline=True)
        embed.add_field(name="Power", value=power if power is not None else "N/A", inline=True)
        embed.add_field(name="PP", value=pp, inline=True)
        embed.add_field(name="Accuracy", value=f"{accuracy}%" if accuracy is not None else "N/A", inline=True)
        embed.add_field(name="Effect", value=effect, inline=False)
        
        await ctx.send(embed=embed)
    else:
        await ctx.send("Move not found. Please check the spelling and try again.")

@bot.command(name='pokemon')
async def pokemon_info(ctx, *, name: str):
    data = get_pokeapi_data(f'pokemon/{name.lower()}')
    if data:
        # Basic Pokémon information
        types = [t['type']['name'] for t in data['types']]
        abilities = [a['ability']['name'] for a in data['abilities']]
        stats = '\n'.join([f"{s['stat']['name'].title()}: {s['base_stat']}" for s in data['stats']])
        base_experience = data.get('base_experience', 'N/A')
        habitat = data.get('habitat', {'name': 'N/A'})['name'] if data.get('habitat') else "N/A"

        # Evolution information (requires fetching from another endpoint)
        species_url = data['species']['url']
        species_data = get_pokeapi_data(species_url.replace("https://pokeapi.co/api/v2/", ""))
        evolution_chain_url = species_data['evolution_chain']['url']
        evolution_data = get_pokeapi_data(evolution_chain_url.replace("https://pokeapi.co/api/v2/", ""))
        evolution_details = process_evolution_chain(evolution_data)

        description = f"**{data['name'].title()}**\n"
        description += f"**Types**: {', '.join(types)}\n"
        description += f"**Abilities**: {', '.join(abilities)}\n"
        description += f"**Base Experience**: {base_experience}\n"
        description += f"**Habitat**: {habitat}\n"
        description += f"**Stats**:\n{stats}\n"
        description += f"**Evolution Details**:\n{evolution_details}"

        embed = discord.Embed(description=description, color=discord.Color.green())
        embed.set_thumbnail(url=data['sprites']['front_default'])
        await ctx.send(embed=embed)
    else:
        await ctx.send("Pokémon not found. Please check the spelling and try again.")

def process_evolution_chain(data):
    """Processes the evolution chain data to format it as a readable string."""
    evolution_chain = ""
    current = data['chain']
    while current:
        species_name = current['species']['name'].title()  # Capitalize the Pokémon name
        if current['evolves_to']:
            details_list = current['evolves_to'][0]['evolution_details']
            conditions = []
            for details in details_list:
                trigger = details['trigger']['name']

                if trigger == 'level-up':
                    level = details.get('min_level')
                    condition = f"Level {level}" if level else "Level up"
                    if details.get('time_of_day'):
                        condition += f" during {details['time_of_day']} time"
                    if details.get('held_item'):
                        item = details['held_item']['name']
                        condition += f" while holding {item}"
                    if details.get('location'):
                        location = details['location']['name']
                        condition += f" at {location}"
                    if details.get('gender'):
                        condition += f" if gender is {details['gender']}"
                    if details.get('min_happiness'):
                        condition += f" with high friendship ({details['min_happiness']})"
                    conditions.append(condition)

                elif trigger == 'use-item':
                    item = details['item']['name']
                    conditions.append(f"Use {item}")

                elif trigger == 'trade':
                    if details.get('held_item'):
                        item = details['held_item']['name']
                        conditions.append(f"Trade while holding {item}")
                    else:
                        conditions.append("Trade")

                elif trigger == 'other':
                    conditions.append("Special condition")  # Can be detailed further as needed

                elif trigger == 'friendship':
                    condition = "With high friendship"
                    if details.get('time_of_day'):
                        condition += f" during {details['time_of_day']} time"
                    conditions.append(condition)

            evolution_details = " or ".join(conditions)
            evolution_chain += f"{species_name} -> ({evolution_details}) "
        else:
            evolution_chain += species_name
            break
        current = current['evolves_to'][0]
    return evolution_chain

@bot.command(name='game')
async def game_info(ctx, *, pokemon_name: str):
    """Provides the games in which the specified Pokémon can be found."""
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        encounters = data.get('location_area_encounters')
        if encounters:
            encounter_response = requests.get(encounters)
            if encounter_response.status_code == 200:
                encounter_data = encounter_response.json()
                games = set()
                for encounter in encounter_data:
                    for version_detail in encounter['version_details']:
                        games.add(version_detail['version']['name'].title())
                if games:
                    games_list = ", ".join(sorted(games))
                    await ctx.send(f"**{pokemon_name.title()}** can be found in the following games: {games_list}")
                else:
                    await ctx.send(f"**{pokemon_name.title()}** does not appear to be available in any game through regular encounters.")
            else:
                await ctx.send("Could not retrieve encounter information. Please try again later.")
        else:
            await ctx.send(f"No encounter data available for **{pokemon_name.title()}**.")
    else:
        await ctx.send(f"**{pokemon_name.title()}** not found. Please check the spelling and try again.")

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

@bot.command(name='standings')
async def standings(ctx):
    all_values = sheet.get_all_values()
    data_rows = all_values[3:]  # This skips the first three rows which are assumed to be headers or empty
    response = "**Standings:**\n"
    for row in data_rows:
        if all(cell.strip() == '' for cell in row):
            continue
        rank = row[2].strip('#')
        team_name = row[4]
        coach_name = row[5]
        record = row[6]
        response += f"{rank}: {team_name} - {coach_name}, {record}\n"
    await ctx.send(response)

@bot.command(name='mvp')
async def mvp(ctx):
    mvp_sheet = client.open("Oshawott Draft League").worksheet('MVP Race')
    all_values = mvp_sheet.get_all_values()
    data_rows = all_values[3:]  # Assumes the first three rows are headers or empty
    response = "**MVP Race - Top 15:**\n"

    # Debugging: Check the structure of the first data row
    print(data_rows[0])  # Remove or comment this line after debugging

    try:
        # Sorting rows by the 'Diff.' column
        sorted_rows = sorted(data_rows, key=lambda x: int(x[9].strip() or 0), reverse=True)
    except IndexError as e:
        await ctx.send("Error processing data: " + str(e))
        return

    for row in sorted_rows[:16]:  # Only include the top 20
        if all(cell.strip() == '' for cell in row):
            continue
        rank = row[2].strip('#')
        pokemon = row[4]
        coach_name = row[5]
        kills = row[7]
        deaths = row[8]
        diff = row[9]
        response += f"{rank}: {pokemon} - {coach_name}, Kills: {kills}, Deaths: {deaths}, Diff: {diff}\n"

    await ctx.send(response)

@bot.command(name='team')
async def team(ctx, *, query: str):
    draft_sheet = client.open("Oshawott Draft League").worksheet('Draft But Simple')
    draft_values = draft_sheet.get_all_values()
    query_lower = query.lower()
    response = ""
    found = False

    for index, col in enumerate(draft_values[0]):
        if col.lower() == query_lower or (draft_values[1][index].lower() == query_lower if len(draft_values) > 1 else False):
            team_name = col
            coach_name = draft_values[1][index] if len(draft_values) > 1 else "Not specified"
            pokemon_formatted = []

            for i in range(2, len(draft_values)):
                if index < len(draft_values[i]):
                    pokemon_name = draft_values[i][index]
                    types = draft_values[i][index+1:index+4]
                    types = [t.strip() for t in types if t.strip()]
                    pokemon_info = f"{pokemon_name} - {', '.join(types)}" if types else pokemon_name
                    pokemon_formatted.append(pokemon_info)

            response = f"**Team Name:** {team_name}\n**Coach Name:** {coach_name}\n**Pokémon:**\n - " + "\n - ".join(pokemon_formatted)
            found = True
            break

    if found:
        await ctx.send(response)
    else:
        await ctx.send("No team or coach found with that name.")

# Define team identifiers
teams = {
    1: "Scalchop Samurai",
    2: "Eevee Elite",
    3: "Gooning Gamblers",
    4: "Medali Mausholds",
    5: "Wixom Wakes",
    6: "Striking Talons",
    7: "Shell Shocks",
    8: "Fregigigas"
}
# Define the matchups for each week
week_matchups = {
    1: [
        (1,5),
        (2,6),
        (3,7),
        (4,8)
    ],
    2: [
        (1,3),
        (2,4),
        (5,7),
        (6,8)
    ],
    3: [
        (1,4),
        (2,3),
        (4,8),
        (6,7)
    ],
    4: [
        (1,2),
        (3,4),
        (5,6),
        (7,8)
    ],
    5: [
        (1,6),
        (2,5),
        (3,8),
        (4,7)
    ],
    6: [
        (1,7),
        (2,8),
        (3,5),
        (4,6)
    ],
    7: [
        (1,8),
        (2,7),
        (3,6),
        (4,5)
    ]
}
@bot.command(name='week')
async def week(ctx, week_number: int):
    if week_number in week_matchups:
        matchups = week_matchups[week_number]
        # Convert team identifiers to names
        formatted_matchups = [f"{teams[match[0]]} vs {teams[match[1]]}" for match in matchups]
        response = f"**Matchups for Week {week_number}:**\n" + "\n".join(formatted_matchups)
    else:
        response = "Invalid week number. Please enter a number between 1 and 7."
    
    await ctx.send(response)

@bot.command(name='tera')
async def tera(ctx):
    # Prepare the message
    response = """
**Terastalisation Rules**
1. Teams will have 15 points to spend on Tera Captains.
2. Captaining a Pokemon costs the same as the price you drafted it for.
3. A Tera Captain will have access to 3 Tera Crystals. One has to be of the same type as the user (1 of 2 STAB's if it is dual type), and then any 2 types, this includes Stellar.
4. Teams can assign 2 or 3 Tera Captains and must stay within the 15 point budget.
5. You can only Tera captain Pokemon 9 points and under, with some exceptions...

**Banned from being Tera Captains:**
- Alcremie
- Araquanid
- Basculegion-Female
- Basculegion-Male
- Blaziken
- Cetitan
- Chandelure
- Comfey
- Delphox
- Diancie
- Emboar
- Fezandipiti
- Floatzel
- Frosmoth
- Hisuian Braviary
- Hitmonlee
- Hoopa
- Iron Thorns
- Kilowattrel
- Lucario
- Meloetta
- Oricorio
- Paldean Tauros Aqua
- Paldean Tauros Blaze
- Polteageist
- Porygon2
- Regieleki
- Registeel
- Sinistcha
- Staraptor
- Torterra
- Venomoth
    """
    
    await ctx.send(response)

@bot.command(name='banned')
async def banned(ctx):
    # Prepare the message
    response = """
**Banned Abilities, Items, Moves, and Conditions**
**Abilities Banned:**
- Moody
- Sand Veil
- Snow Cloak
- Speed Boost (on Blaziken only)
- Sheer Force (on Landorus only)

**Items Banned:**
- Bright Powder
- Lax Incense
- King's Rock
- Focus Band
- Razor Fang
- Quick Claw

**Moves Banned:**
- Accupressure
- Confuse Ray
- Flatter
- Supersonic
- Swagger
- Sweet Kiss
- Shed Tail
- Last Respects
- Revival Blessing
- Take Heart (banned on Manaphy)

**Specific Rules:**
- Baton Pass is allowed but cannot be used to pass stats or Substitute.
- If more than 1 Pokémon gets slept due to Effect Spore, Relic Song, or Dire Claw then it will not result in a loss, otherwise sleep clause is in effect.
    """
    
    await ctx.send(response)

@bot.command(name='ability')
async def ability_info(ctx, *, ability_name: str):
    data = get_pokeapi_data(f'ability/{ability_name.lower().replace(" ", "-")}')
    if data:
        name = data['name'].replace('-', ' ').title()
        effect_entries = data['effect_entries']
        effect = next((entry['effect'] for entry in effect_entries if entry['language']['name'] == 'en'), "No description available.")
        short_effect = next((entry['short_effect'] for entry in effect_entries if entry['language']['name'] == 'en'), "No description available.")

        embed = discord.Embed(title=f"Ability: {name}", description=f"**Effect**: {effect}\n**Short Effect**: {short_effect}", color=discord.Color.dark_blue())
        await ctx.send(embed=embed)
    else:
        await ctx.send("Ability not found. Please check the spelling and try again.")

@bot.command(name='avatar')
async def avatar(ctx, *, member: discord.Member = None):
    member = member or ctx.author  # if no member is specified, use the message author
    avatar_url = member.display_avatar.url
    embed = discord.Embed(title=f"{member.name}'s avatar", color=discord.Color.blue())
    embed.set_image(url=avatar_url)
    await ctx.send(embed=embed)

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('Pong!')

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
