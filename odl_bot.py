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
    print("Checking for new videos...")
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
                # Check if the bot has permission to send messages
                if not channel.permissions_for(channel.guild.me).send_messages:
                    print(f"Do not have permission to send messages in {channel.name}")
                    return
                await channel.send(f'🎥 **New Video Uploaded:** {video_title}\n{video_url}')
                print(f"Posted new video: {video_title}")

@bot.command(name='standings')
async def standings(ctx):
    try:
        # Get all values from the sheet
        all_values = sheet.get_all_values()
        
        # Debug: print all_values to see what is being retrieved
        print(all_values)

        # Headers are assumed to be on the third row
        headers = all_values[2]
        # Data is assumed to start on the fourth row
        data_rows = all_values[3:]

        response = "**Standings:**\n"

        # Debug: Check if data_rows is empty
        if not data_rows:
            await ctx.send("No data found in the sheet.")
            return

        for row in data_rows:
            # Debug: print each row to see what is being processed
            print(row)

            # Make sure we're only adding non-empty rows
            if any(cell.strip() for cell in row):
                # Extract data using column headers; adjust the indices as necessary
                rank = row[0]
                team_name = row[2]
                coach_name = row[3]
                record = row[4]
                response += f"{rank}: {team_name} - {coach_name}, {record}\n"
            else:
                # If the row is empty, skip to the next one
                continue

        await ctx.send(response)
    except Exception as e:
        print(e)
        await ctx.send(f"Error fetching standings: {str(e)}")

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('Pong!')  # Simple command to test if the bot is responsive

bot.run(DISCORD_TOKEN)
