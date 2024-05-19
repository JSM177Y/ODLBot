import os
import discord
from discord.ext import commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from functools import lru_cache
from thefuzz import fuzz, process  # Fuzzy string matching

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

# Fetch team names from the "Data" sheet
data_sheet = client.open("Oshawott Draft League").worksheet('Data')
team_names = data_sheet.get('D2:D9')

# Convert the fetched data to a dictionary
teams = {index + 1: team[0] for index, team in enumerate(team_names)}

# Fetch matchup data
matchup_data = data_sheet.get_all_values()
week_matchups = {}

# Process the matchup data
for row in matchup_data[1:]:  # Skip the header row
    try:
        week = int(row[7])  # Column H
        team1 = int(row[9])  # Column J
        team2 = int(row[17])  # Column R

        if week not in week_matchups:
            week_matchups[week] = set()  # Use a set to prevent duplicates
        week_matchups[week].add((team1, team2))
    except (ValueError, IndexError):
        continue

# Caching functions
@lru_cache(maxsize=128)
def get_pokeapi_data(endpoint: str):
    """Cached function to get data from the PokéAPI."""
    url = f"https://pokeapi.co/api/v2/{endpoint}/"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

# Function to correct spelling using fuzzy matching
def correct_spelling(name, category):
    """Function to correct spelling using fuzzy matching."""
    if category == 'pokemon':
        choices = pokemon_names
    elif category == 'move':
        choices = move_names
    elif category == 'ability':
        choices = ability_names
    elif category == 'type':
        choices = type_names
    else:
        return name

    match, score = process.extractOne(name, choices)
    return match if score > 70 else name

# Initialize fuzzy matching data
pokemon_names = []
move_names = []
ability_names = []
type_names = []

@bot.event
async def on_ready():
    global pokemon_names, move_names, ability_names, type_names

    # Load data for fuzzy matching
    pokemon_data = get_pokeapi_data('pokemon?limit=1000')['results']
    pokemon_names = [p['name'] for p in pokemon_data]
    move_data = get_pokeapi_data('move?limit=1000')['results']
    move_names = [m['name'] for m in move_data]
    ability_data = get_pokeapi_data('ability?limit=1000')['results']
    ability_names = [a['name'] for a in ability_data]
    type_data = get_pokeapi_data('type')['results']
    type_names = [t['name'] for t in type_data]

    print(f'{bot.user.name} has connected to Discord!')

@bot.command(name='type')
async def type_info(ctx, *, types: str):
    type_list = types.split()
    if len(type_list) > 2:
        await ctx.send("Please provide one or two types only.")
        return

    type_list = [correct_spelling(t, 'type') for t in type_list]
    type_data = [get_pokeapi_data(f'type/{t.lower()}') for t in type_list]
    if None in type_data:
        await ctx.send("One of the types provided was not found. Please check the types and try again.")
        return

    # Prepare the data containers
    effective_against = [set(), set()]
    weak_to = [set(), set()]
    resistant_to = [set(), set()]
    immune_to = [set(), set()]

    # Fill the containers with data from API
    for i, data in enumerate(type_data):
        effective_against[i].update([t['name'] for t in data['damage_relations']['double_damage_to']])
        weak_to[i].update([t['name'] for t in data['damage_relations']['double_damage_from']])
        resistant_to[i].update([t['name'] for t in data['damage_relations']['half_damage_from']])
        immune_to[i].update([t['name'] for t in data['damage_relations']['no_damage_from']])

    # Displaying types differently based on the number of types provided
    if len(type_list) == 1:
        # If only one type, simplify the output
        embed = discord.Embed(title=f"{type_list[0].title()} Type Interactions", color=discord.Color.blue())
        embed.add_field(name="Super Effective Against", value=', '.join(effective_against[0]).title() or "None", inline=False)
        embed.add_field(name="Weak To", value=', '.join(weak_to[0]).title() or "None", inline=False)
        embed.add_field(name="Resistant To", value=', '.join(resistant_to[0]).title() or "None", inline=False)
        embed.add_field(name="Immune To", value=', '.join(immune_to[0]).title() or "None", inline=False)
    else:
        # Calculate combined interactions
        combined_weak_to = weak_to[0].union(weak_to[1]) - resistant_to[0] - immune_to[0] - resistant_to[1] - immune_to[1]
        combined_resistant_to = ((resistant_to[0].union(resistant_to[1])) - weak_to[0]) - weak_to[1]
        combined_immune_to = immune_to[0].union(immune_to[1])
        x4_weak = weak_to[0].intersection(weak_to[1])
        x4_resistant = resistant_to[0].intersection(resistant_to[1])

        embed = discord.Embed(title=f"Type Interactions for {type_list[0].title()} and {type_list[1].title()}", color=discord.Color.blue())
        embed.add_field(name=f"{type_list[0].title()} is Super Effective Against", value=', '.join(effective_against[0]).title() or "None", inline=False)
        embed.add_field(name=f"{type_list[1].title()} is Super Effective Against", value=', '.join(effective_against[1]).title() or "None", inline=False)
        embed.add_field(name="Combined Weak To", value=', '.join(combined_weak_to).title() or "None", inline=False)
        embed.add_field(name="Combined Resistant To", value=', '.join(combined_resistant_to).title() or "None", inline=False)
        embed.add_field(name="Combined Immune To", value=', '.join(combined_immune_to).title() or "None", inline=False)
        embed.add_field(name="4x Weak To", value=', '.join(x4_weak).title() or "None", inline=False)
        embed.add_field(name="4x Resistant To", value=', '.join(x4_resistant).title() or "None", inline=False)

    await ctx.send(embed=embed)

@bot.command(name='pokemon')
async def pokemon_info(ctx, *, name: str):
    name = correct_spelling(name, 'pokemon')
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
    query = correct_spelling(query, 'pokemon')
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

@bot.command(name='week')
async def week(ctx, week_number: int):
    if week_number in week_matchups:
        matchups = week_matchups[week_number]
        # Convert team identifiers to names and avoid duplicates
        seen_matchups = set()
        formatted_matchups = []
        for match in matchups:
            if match not in seen_matchups and (match[1], match[0]) not in seen_matchups:
                seen_matchups.add(match)
                formatted_matchups.append(f"{teams[match[0]]} vs {teams[match[1]]}")
        response = f"**Matchups for Week {week_number}:**\n" + "\n".join(formatted_matchups)
    else:
        response = "Invalid week number. Please enter a number between 1 and 7."
    
    await ctx.send(response)

@bot.command(name='tera')
async def tera(ctx):
    # Fetch the data from the "Rules" sheet, ranges C11:C16 and D11:D16
    rules_sheet = client.open("Oshawott Draft League").worksheet('Rules')
    tera_numbers = rules_sheet.get('C11:C16')
    tera_rules = rules_sheet.get('D11:D16')

    # Prepare the response message
    response = "**Terastalisation Rules**\n"
    for number, rule in zip(tera_numbers, tera_rules):
        response += f"{number[0]}: {rule[0]}\n"
    
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
    ability_name = correct_spelling(ability_name, 'ability')
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