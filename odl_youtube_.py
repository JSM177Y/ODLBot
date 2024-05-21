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
POSTED_VIDEOS_FILE = 'posted_videos.txt'

# YouTube API setup
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Set up Discord intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

# Discord Bot setup
bot = commands.Bot(command_prefix='!', intents=intents)

def read_posted_videos():
    if os.path.exists(POSTED_VIDEOS_FILE):
        with open(POSTED_VIDEOS_FILE, 'r') as file:
            return file.read().splitlines()
    return []

def write_posted_video(video_id):
    with open(POSTED_VIDEOS_FILE, 'a') as file:
        file.write(video_id + '\n')

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    check_new_video.start()  # Start the loop to check for new videos

@tasks.loop(minutes = 30)
async def check_new_video():
    try:
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
            posted_videos = read_posted_videos()

            if video_id and video_id not in posted_videos:
                write_posted_video(video_id)
                video_title = latest_video['snippet']['title']
                video_url = f'https://www.youtube.com/watch?v={video_id}'
                channel = bot.get_channel(DISCORD_CHANNEL_ID)
                if channel:
                    if not channel.permissions_for(channel.guild.me).send_messages:
                        print(f"Do not have permission to send messages in {channel.name}")
                        return
                    await channel.send(f'🎥 **New Video Uploaded:** {video_title}\n{video_url}')
                    print(f"Posted new video: {video_title}")
                else:
                    print("Channel not found.")
            else:
                print("No new video or same video found.")
        else:
            print("No new videos found in the latest API response.")
    except Exception as e:
        print(f"Error during YouTube video check: {e}")

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)