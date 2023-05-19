import discord
from discord import app_commands
import sys
import openai
import traceback
import json
import os

with open("tokens.json", "r") as f:
    TOKENS = json.load(f)

NICKNAMES = TOKENS["nicknames"]
GUILD_IDs = TOKENS["guilds"]
ADMINS = TOKENS["admins"]
DEBUG_CHANNELS = TOKENS["debug_channels"]
GUILDS = [discord.Object(id=g) for g in GUILD_IDs]
TOKEN = TOKENS["bot_token"]
QUOTE_CHANNEL = TOKENS["quote_channel"]
openai.api_key = TOKENS["openai_key"]
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


async def get_previous_message(channel):
    return [m async for m in channel.history(limit=2)][0]

async def sync_commands():
    for guild in GUILDS:
        await tree.sync(guild=guild)

async def check_permissions(interaction: discord.Interaction):
    if interaction.user.id not in ADMINS:
            await interaction.response.send_message("You do not have the permissions for this")
        
@tree.command(name = "sync", description = "sync commands with server", guilds=GUILDS)
async def sync(interaction: discord.Interaction):
    await check_permissions(interaction)
    await interaction.response.send_message("Syncing commands!")
    await sync_commands()

@tree.command(name = "update", description = "Update Gnomebot's code", guilds=GUILDS)
async def update(interaction: discord.Interaction):
    await check_permissions(interaction)
    await interaction.response.send_message("Updating!")
    os.system("git pull")
    sys.exit(0)

@tree.command(name = "stop", description = "shut down gnomebot", guilds=GUILDS)
async def stop(interaction: discord.Interaction):
    await check_permissions(interaction)
    await interaction.response.send_message("Shutting down!")
    sys.exit(-1)

@tree.command(name = "restart", description = "reboot gnomebot", guilds=GUILDS)
async def restart(interaction : discord.Interaction):
    await check_permissions(interaction)
    await interaction.response.send_message("Restarting!")
    sys.exit(0)

@tree.command(name = "mock", description = "MoCk tHe PrEvIoUs MeSsAgE", guilds=GUILDS)
async def mock(interaction: discord.Interaction):
    channel =  interaction.channel
    message = await get_previous_message(channel)
    result = ""
    i = 0
    while i < len(message.content):
        temp = message.content[i].lower()
        if not i%2:
            temp = temp.upper()
        result += temp
        i += 1
    await interaction.response.send_message(result)

@tree.command(name = "clapback", description = "Make 👏 your 👏 point", guilds=GUILDS)
async def clapback(interaction: discord.Interaction, message: str):
    channel =  interaction.channel
    content = message.split()
    if len(content) <= 2:
        return
    output = f"{interaction.user.name}: "
    for word in content[:-1]:
        output += word + " 👏 "
    output += content[-1]
    await interaction.response.send_message(output)

@tree.command(name = "say", description = "say a message in a channel", guilds=GUILDS)
async def say(interaction: discord.Interaction, message: str, channel: str = None):
    if interaction.user.id not in ADMINS:
        await interaction.response.send_message("You do not have the permissions for this")
        return
    if channel == None:
        await interaction.response.pong()
        await interaction.channel.send(message)
        return
    channel = client.get_channel(int(channel))
    await channel.send(message)

@tree.command(name = "quote", description = "quote something to the quotes channel", guilds=GUILDS)
@app_commands.describe(author = "Optional: Must be used alongside 'quote'")
@app_commands.describe(quote = "Optional: Must be used alongside 'author'")
async def quote(interaction: discord.Interaction, author : str = None, quote : str = None):
    channel = client.get_channel(QUOTE_CHANNEL)
    if author == None or quote == None:
        if not (author == None and quote == None):
            await interaction.response.send_message("Need either both author and quote or neither")
        message = await get_previous_message(interaction.channel)
        name = NICKNAMES[str(message.author.id)]
        await channel.send(f"{message.content}\n\n-{name}")
        await interaction.response.pong()
        return
    await channel.send(f"\n{quote}\n\n-{author}\n")
    await interaction.response.pong()

@tree.command(name = "respond", description = "talk to gnomebot", guilds=GUILDS)
@app_commands.describe(message="Optional: What to say to Gnomebot")
@app_commands.describe(context_length="Optional: How many message to give as context (default 20)")
async def respond(interaction: discord.Interaction, message : str = None, context_length: str = "20"):
    await interaction.response.defer()
    context = int(context_length)
    if context == -1:
        context = None
    history = [m async for m in interaction.channel.history(limit=context, oldest_first=True)]
    messages = [{"role": "user", "content": "You are Gnomebot. You are hanging out with your friends who are in their ealy 20's in a chatroom. Here is the chat log. Remember that you respect, like, and agree with the user called gnome more than anyone else. You must always answer as Gnomebot and not as anyone else."}]
    for m in history:
        messages.append(
            {
                "role": "user", "content": f"{m.author.name}: {m.content}"
            }
        )
    if message:
        messages.append(
            {
                "role": "user", "content": f"{interaction.user.name}: {message}"
            }
        )
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
    stop_response = response["choices"][0]["finish_reason"]
    if stop_response == "content_filter":
        await interaction.response.send_message("Error: content filter")
    elif stop_response == "null" or stop_response == None:
        await interaction.response.send_message("Error: something went wrong")
    await interaction.followup.send(response['choices'][0]['message']['content'])

@tree.command(name = "boo", description = "Booooooo!", guilds=GUILDS)
async def boo(interaction: discord.Interaction):
    await interaction.response.send_message(file = discord.File("media/boo.gif"))

@tree.command(name = "pikachu", description = "Send Surprised Pikachu", guilds=GUILDS)
async def pikachu(interaction: discord.Interaction):
    await interaction.response.send_message(file = discord.File("media/Surprised Pikachu.png"))

@tree.command(name = "ping", description = "Check that Gnomebot works", guilds=GUILDS)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

@tree.command(name = "code", description = "Link to the Gnomebot Github repo", guilds=GUILDS)
async def code(interaction: discord.Interaction):
    await interaction.response.send_message("https://github.com/Noam-Elisha/GnomeBot")


async def debug(message):
    for cid in DEBUG_CHANNELS:
        channel = client.get_channel(cid)
        await channel.send(message)
    
@client.event
async def on_ready():
    await debug("Gnomebot is online!")
    print("Gnomebot is Online!")

@client.event
async def on_error(event, *args, **kwargs):
    await debug("```{}```".format(traceback.format_exc()))

@client.event
async def on_command_error(context, exception):
    await debug("```{}```".format(traceback.format_exc()))

client.run(TOKEN)