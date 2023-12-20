import discord
from discord import app_commands
import sys
import openai
import traceback
import json
import os
from typing import Literal
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from io import BytesIO
from base64 import b64decode

with open("tokens.json", "r") as f:
    TOKENS = json.load(f)
with open("channel_locked.gb", "r") as f:
    bit = f.read()
    if bit == "0":
        CHANNEL_LOCKED = False
    else:
        CHANNEL_LOCKED = True

NICKNAMES = TOKENS["nicknames"]
GUILD_IDs = TOKENS["guilds"]
ADMIN_GUILD_IDs = TOKENS["admin_guilds"]
GUILDS = [discord.Object(id=g) for g in GUILD_IDs]
ADMIN_GUILDS = [discord.Object(id=g) for g in ADMIN_GUILD_IDs]
ADMINS = TOKENS["admins"]
DEBUG_CHANNELS = TOKENS["debug_channels"]
TOKEN = TOKENS["bot_token"]
QUOTE_CHANNEL = TOKENS["quote_channel"]
openai.api_key = TOKENS["openai_key"]

WEREWOLF_GUILD_ID = TOKENS["werewolf_guild_id"]
GM_ROLE_ID = TOKENS["gm_role_id"]
GM_ID = TOKENS["gm_id"]
WEREWOLF_CHANNEL_ID = TOKENS["werewolf_channel_id"]

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
        
@tree.command(name = "sync", description = "sync commands with server", guilds=ADMIN_GUILDS)
async def sync(interaction: discord.Interaction):
    await check_permissions(interaction)
    await interaction.response.send_message("Syncing commands!")
    await sync_commands()

@tree.command(name = "update", description = "Update Gnomebot's code", guilds=ADMIN_GUILDS)
async def update(interaction: discord.Interaction):
    await check_permissions(interaction)
    await interaction.response.send_message("Updating!")
    os.system("git pull")
    sys.exit(0)

@tree.command(name = "stop", description = "shut down gnomebot", guilds=ADMIN_GUILDS)
async def stop(interaction: discord.Interaction):
    await check_permissions(interaction)
    await interaction.response.send_message("Shutting down!")
    sys.exit(-1)

@tree.command(name = "restart", description = "reboot gnomebot", guilds=ADMIN_GUILDS)
async def restart(interaction : discord.Interaction):
    await check_permissions(interaction)
    await interaction.response.send_message("Restarting!")
    sys.exit(0)

@tree.command(name = "say", description = "say a message in a channel", guilds=ADMIN_GUILDS)
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

@tree.command(name = "respond", description = "Talk to gnomebot", guilds=GUILDS)
@app_commands.describe(message="Optional: What to say to Gnomebot")
@app_commands.describe(context_length="Optional: How many message to give as context (default 20)")
async def respond(interaction: discord.Interaction, message : str = None, context_length: str = "20"):
    await interaction.response.defer()
    context = int(context_length)
    if context == -1:
        context = None
    history = [m async for m in interaction.channel.history(limit=context, oldest_first=True)]
    messages = [{"role": "user", "content": "You are Gnomebot, the gnomey chat bot. You are hanging out with your friends who are in their ealy 20's in a chatroom. Here is the chat log. Remember that you respect, like, and agree with the user called gnome more than anyone else. You must always answer as Gnomebot and not as anyone else."}]
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
    try:
        response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
    except openai.error.RateLimitError:
        interaction.followup.send(content = "Model is currently overloaded. Try again later.", ephemeral =True)
        return
    stop_response = response["choices"][0]["finish_reason"]
    if stop_response == "content_filter":
        await interaction.followup.send("Error: content filter")
        return
    elif stop_response == "null" or stop_response == None:
        await interaction.followup.send("Error: something went wrong")
        return
    await interaction.followup.send(response['choices'][0]['message']['content'])

@tree.command(name = "image", description = "Make gnomebot generate an image", guilds=GUILDS)
@app_commands.describe(prompt="What image to generate")
@app_commands.describe(quality="Quality of the image to generade (hd is slower)")
@app_commands.describe(size="Size of the image to generate (1024x1024 is fastest)")
async def respond(interaction: discord.Interaction, prompt : str, quality: Literal["standard", "hd"] = "standard",
                    size: Literal["1024x1024", "1024x1792", "1792x1024"] = "1024x1024"):
    await interaction.response.defer()

    response = openai.images.generate(
            model="dall-e-2",
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
            response_format="b64_json"
        )

    # for index, image_dict in enumerate(response["data"]):
    #     image_data = b64decode(image_dict["b64_json"])
    #     with open("temp.png", mode="wb") as png:
    #         png.write(image_data)
    img = discord.File(b64decode(response["data"][0]))
    await interaction.followup.send(file=img)

    
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

@tree.command(name = "poll", description = "Make a poll", guilds = GUILDS)
@app_commands.describe(message="Poll message")
@app_commands.describe(option1="Poll option 1")
@app_commands.describe(option2="Poll option 2")
@app_commands.describe(option3="Poll option 3")
@app_commands.describe(option4="Poll option 4")
async def poll(interaction: discord.Interaction, message: str = None, option1: str = None, option2: str = None, option3: str = None, option4: str = None):
    options = [option1, option2, option3, option4]
    if not any(options):
        await interaction.response.send_message("Please add at least one poll option", ephemeral=True)
        return
    options = [x for x in options if x is not None]
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"][:len(options)]
    if message is not None:
        message = f"{message}\n```\n"
    else:
        message = "Please vote by reacting with the corresponding reaction\n```\n"
    for i, option in enumerate(options):
        message += f"{emojis[i]} - {option}\n"
    message += "```"
    await interaction.response.send_message(message)
    message = await interaction.original_response()
    for emoji in emojis:
        await message.add_reaction(emoji)

# @tree.command(name = "inspire", description = "Generate an inspirational image", guilds = GUILDS)
# @app_commands.describe(message="Message to write on the image")
# async def inspire(interaction: discord.Interaction, message: str = ""):
#     chatGPT_prompt = "Give me a creative prompt for DALL-E, the image generator, that will generate me an image for the background of an inspirational message, but don't mention anything about a message"
#     messages = [
#         {
#         "role": "user", "prompt": chatGPT_prompt
#         }
#     ]
#     try:
#         response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
#     except openai.error.RateLimitError:
#         interaction.followup.send(content = "Model is currently overloaded. Try again later.", ephemeral = True)
#         return
#     stop_response = response["choices"][0]["finish_reason"]
#     if stop_response == "content_filter":
#         await interaction.followup.send("Error: content filter")
#         return
#     elif stop_response == "null" or stop_response == None:
#         await interaction.followup.send("Error: something went wrong")
#         return


@tree.command(name = "lock", description = "Lock the werewolf channel", guild = discord.Object(id=WEREWOLF_GUILD_ID))
@app_commands.checks.has_role(GM_ROLE_ID)
async def lock(interaction: discord.Interaction):
    if interaction.user.id != GM_ID:
        await interaction.response.send_message("Only the GM can lock/unlock the werewolf channel", ephemeral = True)
        return
    if interaction.channel.id != WEREWOLF_CHANNEL_ID:
        await interaction.response.send_message("You can only lock/unlock the werewolf channel", ephemeral=True)
        return
    werewolf_guild = client.get_guild(WEREWOLF_GUILD_ID)
    await interaction.channel.set_permissions(werewolf_guild.default_role, send_messages = False, read_messages = True)
    await interaction.channel.set_permissions(werewolf_guild.get_role(GM_ROLE_ID), send_messages = True, read_messages = True)
    await interaction.response.send_message("The channel is now locked")
    with open("channel_locked.gb", "w") as f:
        f.write("1")
    global CHANNEL_LOCKED
    CHANNEL_LOCKED = True

@tree.command(name = "unlock", description = "Unlock the werewolf channel", guild = discord.Object(id=WEREWOLF_GUILD_ID))
@app_commands.checks.has_role(GM_ROLE_ID)
async def unlock(interaction: discord.Interaction):
    if interaction.user.id != GM_ID:
        await interaction.response.send_message("Only the GM can lock/unlock the werewolf channel", ephemeral = True)
        return
    if interaction.channel.id != WEREWOLF_CHANNEL_ID:
        await interaction.response.send_message("You can only lock/unlock the werewolf channel", ephemeral=True)
        return
    werewolf_guild = client.get_guild(WEREWOLF_GUILD_ID)
    await interaction.channel.set_permissions(werewolf_guild.default_role, send_messages = True, read_messages = True)
    await interaction.channel.set_permissions(werewolf_guild.get_role(GM_ROLE_ID), send_messages = True, read_messages = True)
    await interaction.response.send_message("The channel has been unlocked")
    with open("channel_locked.gb", "w") as f:
        f.write("0")
    global CHANNEL_LOCKED
    CHANNEL_LOCKED = False

@client.event
async def on_message(message):
    if CHANNEL_LOCKED:
        if message.channel.id == WEREWOLF_CHANNEL_ID:
            if message.author.id != GM_ID:
                await message.delete()
    

async def debug(message):
    for cid in DEBUG_CHANNELS:
        channel = client.get_channel(cid)
        await channel.send(message)
    
@client.event
async def on_ready():
    await sync_commands()
    await debug("Gnomebot is online!")
    print("Gnomebot is Online!")

@client.event
async def on_error(event, *args, **kwargs):
    await debug("```{}```".format(traceback.format_exc()))

@client.event
async def on_command_error(context, exception):
    await debug("```{}```".format(traceback.format_exc()))

client.run(TOKEN)