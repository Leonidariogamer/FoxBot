import requests
import random
from deep_translator import GoogleTranslator

# Function to fetch posts from e621 based on tags
def fetch_e621_post(tags):
    tags = ' '.join(tags)
    url = f'https://e621.net/posts.json?tags={tags}&limit=100'
    headers = {'User-Agent': 'DiscordBot (your.email@example.com)'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data['posts']:
            return random.choice(data['posts'])
    return None

# Function to translate text using Google Translate API
def translate_text(text, target_language='en'):
    translator = GoogleTranslator(source='auto', target=target_language)
    return translator.translate(text)
