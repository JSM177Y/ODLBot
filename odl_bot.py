import os
import discord
from discord.ext import tasks, commands
from googleapiclient.discovery import build
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
load_dotenv()

# Variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
DISCORD_CHANNEL_ID = 1210301630814224465  # Your Discord channel ID
YOUTUBE_CHANNEL_ID = 'UCNU_fAA0EwROJf0IQgXAarA'  # Your YouTube channel ID
GOOGLE_CREDENTIALS_FILE = '/home/jsm177y/ODLBot/odlbot-421819-5192c6bbcd6c.json'  # Path to your .json credentials

# YouTube API setup
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

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
try:
    sheet = client.open("Oshawott Draft League").worksheet('Standings')
except gspread.exceptions.APIError as e:
    print("Failed to access the sheet:", e.response)
    exit(1)

# Keep track of the last uploaded video ID
last_video_id = None

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    check_new_video.start()  # Start the loop to check for new videos

@tasks.loop(minutes=10)
async def check_new_video():
    global last_video_id
    request = youtube.search().list(
        part='snippet',
        channelId=YOUTUBE_CHANNEL_ID,
        order='date',
        type='video',
        maxResults=1
    )
    response = request.execute()

    if response['items']:
        latest_video = response['items'][0]
        video_id = latest_video['id']['videoId']
        if video_id != last_video_id:
            last_video_id = video_id
            video_title = latest_video['snippet']['title']
            video_url = f'https://www.youtube.com/watch?v={video_id}'
            channel = bot.get_channel(DISCORD_CHANNEL_ID)
            if channel:
                if not channel.permissions_for(channel.guild.me).send_messages:
                    print(f"Do not have permission to send messages in {channel.name}")
                    return
                await channel.send(f'🎥 **New Video Uploaded:** {video_title}\n{video_url}')
                print(f"Posted new video: {video_title}")

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
    draft_sheet = client.open("Oshawott Draft League").worksheet('MVP Race')
    all_values = sheet.get_all_values()
    data_rows = all_values[3:]  # This skips the first three rows which are assumed to be headers or empty
    response = "**MVP Race - Top 20:**\n"

    # Sorting rows by the 'Diff.' column which is assumed to be at index 10 based on your screenshot
    sorted_rows = sorted(data_rows, key=lambda x: int(x[10].strip() or 0), reverse=True)

    for row in sorted_rows[:20]:  # Only include the top 20
        if all(cell.strip() == '' for cell in row):
            continue
        rank = row[2].strip('#')
        pokemon = row[3]
        coach_name = row[5]
        kills = row[8]
        deaths = row[9]
        diff = row[10]
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

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('Pong!')

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)