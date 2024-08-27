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
VIDEOS_CHANNEL_ID = 1210301630814224465  # Replace with your Discord videos channel ID
CLIPS_AND_HIGHLIGHTS_CHANNEL_ID = 1210293328655028317  # Replace with your Discord clips and highlights channel ID
POSTED_VIDEOS_FILE = 'posted_videos.txt'
CHANNEL_URLS_FILE = 'channel_urls.txt'

# Special channel handle
SPECIAL_CHANNEL_HANDLE = 'OshawottDraftLeague'

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

def read_channel_urls():
    if os.path.exists(CHANNEL_URLS_FILE):
        with open(CHANNEL_URLS_FILE, 'r') as file:
            return file.read().splitlines()
    return []

def get_channel_id_by_custom_handle(handle):
    # Remove the '@' from the handle
    handle = handle.lstrip('@')
    
    request = youtube.search().list(
        part='snippet',
        q=handle,
        type='channel',
        maxResults=1
    )
    response = request.execute()

    if 'items' in response and len(response['items']) > 0:
        return response['items'][0]['snippet']['channelId']

    return None  # Return None if the channel is not found

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    check_new_video.start()  # Start the loop to check for new videos

@tasks.loop(minutes=30)
async def check_new_video():
    try:
        print("Checking for new videos...")
        channel_urls = read_channel_urls()

        for url in channel_urls:
            # Extract the handle from the URL, assuming format is https://www.youtube.com/@handle
            if '@' in url:
                channel_handle = url.split('@')[1]
                channel_id = get_channel_id_by_custom_handle(channel_handle)

                if channel_id:
                    request = youtube.search().list(
                        part='snippet',
                        channelId=channel_id,
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

                            message = f'🎥 **New Video Uploaded:**\n{video_title}\n{video_url}'

                            if channel_handle == SPECIAL_CHANNEL_HANDLE:
                                # Post in the videos channel
                                channel = bot.get_channel(VIDEOS_CHANNEL_ID)
                            else:
                                # Post in the clips and highlights channel
                                channel = bot.get_channel(CLIPS_AND_HIGHLIGHTS_CHANNEL_ID)
                            
                            if channel:
                                if not channel.permissions_for(channel.guild.me).send_messages:
                                    print(f"Do not have permission to send messages in {channel.name}")
                                    return
                                await channel.send(message)
                                print(f"Posted new video: {video_title} in {channel.name}")
                            else:
                                print("Channel not found.")
                        else:
                            print("No new video or same video found.")
                    else:
                        print("No new videos found in the latest API response.")
                else:
                    print(f"Channel not found for handle: {channel_handle}")

    except Exception as e:
        print(f"Error during YouTube video check: {e}")

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
