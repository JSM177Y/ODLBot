import os
import discord
from discord.ext import commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = 1210301630814224465  # Your Discord channel ID
GOOGLE_CREDENTIALS_FILE = '/home/jsm177y/ODLBot/odlbot-421819-5192c6bbcd6c.json'  # Path to your .json credentials

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

@bot.command(name='tera')
async def tera(ctx):
    response = """
**Terastalisation Rules**
1. Teams will have 15 points to spend on Tera Captains.
2. Captaining a Pokemon costs the same as the price you drafted it for.
3. A Tera Captain will have access to 3 Tera Crystals, one has to be of the same type as the user (1 of 2 STAB's if it is dual type), and then any 2 types, this includes Stellar.
4. Teams can assign 2 or 3 Tera Captains and must stay within the 15 point budget.
5. You can only Tera captain Pokemon 9 points and under, with some exceptions...

**Banned from being Tera Captains:**
- Alcremie, Araquanid, Basculegion-Female, Basculegion-Male, Blaziken, Cetitan, Chandelure, Comfey, Delphox, Diancie, Emboar, Fezandipiti, Floatzel, Frosmoth, Hisuian Braviary, Hitmonlee, Hoopa, Iron Thorns, Kilowattrel, Lucario, Meloetta, Oricorio, Paldean Tauros Aqua, Paldean Tauros Blaze, Polteageist, Porygon2, Regieleki, Registeel, Sinistcha, Staraptor, Torterra, Venomoth
    """
    await ctx.send(response)

@bot.command(name='banned')
async def banned(ctx):
    response = """
**Banned Abilities, Items, Moves, and Conditions**
**Abilities Banned:**
- Moody, Sand Veil, Snow Cloak, Speed Boost (on Blaziken only), Sheer Force (on Landorus only)

**Items Banned:**
- Bright Powder, Lax Incense, King's Rock, Focus Band, Razor Fang, Quick Claw

**Moves Banned:**
- Accupressure, Confuse Ray, Flatter, Supersonic, Swagger, Sweet Kiss, Shed Tail, Last Respects, Revival Blessing, Take Heart (banned on Manaphy)

**Specific Rules:**
- Baton Pass is allowed but cannot be used to pass stats or Substitute.
- If more than 1 Pokémon gets slept due to Effect Spore, Relic Song, or Dire Claw then it will not result in a loss, otherwise sleep clause is in effect.
    """
    await ctx.send(response)

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
