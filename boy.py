import os
import re
import time
import string
import requests
import discord
from discord import app_commands
from discord.ext import commands
from rich.console import Console

ascii_art = """
__        __   _                            _         
\ \      / /__| | ___ ___  _ __ ___   ___  | |_ ___   
 \ \ /\ / / _ \ |/ __/ _ \| '_ ` _ \ / _ \ | __/ _ \  
  \ V  V /  __/ | (_| (_) | | | | | |  __/ | || (_) | 
   \_/\_/ \___|_|\___\___/|_| |_| |_|\___|  \__\___/  
                                                     
"""
print(ascii_art)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
console = Console(highlight=False)

def cprint(color, content):
    console.print(f"[bold {color}]{content}[/bold {color}]")

def download_xml(clothing_id):
    url = f'https://assetdelivery.roblox.com/v1/asset/?id={clothing_id}'
    response = requests.get(url)
    if response.status_code == 200:
        if not os.path.exists('xml_temp'):
            os.mkdir('xml_temp')
        with open(f'xml_temp/{clothing_id}.xml', 'wb') as file:
            file.write(response.content)
        cprint('purple', f'Successfully downloaded temporary file: {clothing_id}.xml')
    else:
        cprint('red', f'Failed to download temporary file: {clothing_id}')

def extract_new_id(xml_file_path):
    with open(xml_file_path, 'r') as file:
        xml_content = file.read()
    match = re.search(r'<url>.*\?id=(\d+)</url>', xml_content)
    if match:
        return match.group(1)
    else:
        return None

def get_item_name(item_id):
    url = f'https://economy.roblox.com/v2/assets/{item_id}/details'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get('Name', 'Unknown')
    else:
        cprint('yellow', f'Failed to get item name for ITEM_ID: {item_id}')
        return 'Unknown'

def sanitize_filename(name):
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    return ''.join(char for char in name if char in valid_chars)

def add_suffix_if_exists(file_name):
    base_name, ext = os.path.splitext(file_name)
    index = 1
    while os.path.exists(file_name):
        file_name = f'{base_name}_{index}{ext}'
        index += 1
    return file_name

def download_clothing_image(clothing_id, new_id):
    item_name = get_item_name(new_id)
    if item_name == 'Unknown':
        item_name = clothing_id
    item_name = sanitize_filename(item_name)
    file_name = f'clothes/{item_name}.png'
    file_name = add_suffix_if_exists(file_name)
    url = f'https://assetdelivery.roblox.com/v1/asset/?id={new_id}'
    response = requests.get(url)
    if response.status_code == 200:
        if not os.path.exists('clothes'):
            os.mkdir('clothes')
        with open(file_name, 'wb') as file:
            file.write(response.content)
        cprint('purple', f'Successfully downloaded {file_name}!')
        return file_name
    else:
        cprint('red', f'Failed to download {file_name}')
        return None

def get_roblox_user_info(username):
    url = f'https://users.roblox.com/v1/usernames/users'
    payload = {"usernames": [username], "excludeBannedUsers": False}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        if data['data']:
            user = data['data'][0]
            return {
                "id": user.get('id', 'Unknown'),
                "display_name": user.get('displayName', 'Unknown'),
                "username": user.get('name', 'Unknown'),
                "is_banned": user.get('isBanned', False)
            }
        else:
            return None
    else:
        return None

@bot.event
async def on_ready():
    cprint('green', f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        cprint('green', f"Synced {len(synced)} slash commands.")
    except Exception as e:
        cprint('red', f"Failed to sync commands: {e}")

@bot.tree.command(name='download', description='Download clothing image by clothing ID.')
async def download(interaction: discord.Interaction, clothing_id: str):
    if clothing_id.isdigit():
        await interaction.response.defer()
        download_xml(clothing_id)
        xml_file_path = f'xml_temp/{clothing_id}.xml'
        new_id = extract_new_id(xml_file_path)
        if new_id:
            image_path = download_clothing_image(clothing_id, new_id)
            os.remove(xml_file_path)
            if image_path:
                await interaction.followup.send(file=discord.File(image_path))
                os.remove(image_path)
            else:
                await interaction.followup.send("Failed to download the clothing image.")
        else:
            await interaction.followup.send(f"Failed to get new ID from {clothing_id}.xml")
    else:
        await interaction.response.send_message("Please provide a valid clothing ID (numeric only).")

@bot.tree.command(name='lookup', description='Lookup a Roblox account by username.')
async def lookup(interaction: discord.Interaction, username: str):
    await interaction.response.defer()
    user_info = get_roblox_user_info(username)
    if user_info:
        embed = discord.Embed(
            title=f"Roblox User: {user_info['username']}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Display Name", value=user_info['display_name'], inline=False)
        embed.add_field(name="User ID", value=user_info['id'], inline=False)
        embed.add_field(name="Banned", value="Yes" if user_info['is_banned'] else "No", inline=False)
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Could not find any information for username: {username}.")

@bot.tree.command(name='massdownload', description='Download multiple clothing images by a list of IDs.')
async def massdownload(interaction: discord.Interaction, clothing_ids: str):
    await interaction.response.defer()
    ids = clothing_ids.split(',')
    if not os.path.exists('clothes'):
        os.mkdir('clothes')
    results = []
    files_to_send = []
    for clothing_id in ids:
        clothing_id = clothing_id.strip()
        if clothing_id.isdigit():
            try:
                download_xml(clothing_id)
                xml_file_path = f'xml_temp/{clothing_id}.xml'
                new_id = extract_new_id(xml_file_path)
                if new_id:
                    image_path = download_clothing_image(clothing_id, new_id)
                    os.remove(xml_file_path)
                    if image_path:
                        files_to_send.append(discord.File(image_path))
                        results.append(f"✅ {clothing_id}: Downloaded successfully.")
                    else:
                        results.append(f"❌ {clothing_id}: Failed to download image.")
                else:
                    results.append(f"❌ {clothing_id}: Failed to get new ID.")
            except Exception as e:
                results.append(f"❌ {clothing_id}: Error - {str(e)}")
        else:
            results.append(f"❌ {clothing_id}: Invalid ID (must be numeric).")
    await interaction.followup.send("\n".join(results))
    if files_to_send:
        await interaction.followup.send(files=files_to_send)
    for file in files_to_send:
        os.remove(file.fp.name)

bot.run('YOUR_BOT_TOKEN')
