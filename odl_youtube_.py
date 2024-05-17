import os
import discord
from discord.ext import tasks, commands
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
DISCORD_CHANNEL_ID = 1210301630814224465  # Your Discord channel ID
YOUTUBE_CHANNEL_ID = 'UCNU_fAA0EwROJf0IQgXAarA'  # Your YouTube channel ID

# YouTube API setup
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Set up Discord intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

# Discord Bot setup
bot = commands.Bot(command_prefix='!', intents=intents)

# Keep track of the last uploaded video ID
last_video_id = None

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    check_new_video.start()  # Start the loop to check for new videos

@tasks.loop(minutes=1)
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
                if not channel.permissions_for(channel.guild.me).send_messages:
                    print(f"Do not have permission to send messages in {channel.name}")
                    return
                await channel.send(f'🎥 **New Video Uploaded:** {video_title}\n{video_url}')
                print(f"Posted new video: {video_title}")

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)