import discord
import asyncio
from colorama import Fore

import Logging

client = discord.Client()
member = None

async def init_users():
    global member
    infoFile = open("UserInfo.txt", "r")
    info = infoFile.read()
    infoFile.close()
    member = await client.fetch_user(int(info))
    Logging.logWithTimestamp("Discord ready")

async def discord_notify(message):
    if member != None:
        channel = await member.create_dm()
        await channel.send(message)
        Logging.logWithTimestamp("Discord notified", Fore.YELLOW)
    else:
        Logging.logWithTimestamp("Discord notify failed", Fore.RED)

tokenFile = open("DiscordToken.txt", "r")
discordBotToken = tokenFile.read()
tokenFile.close()

def init_discord(mainFunc):
    client.loop.create_task(mainFunc())
    client.run(discordBotToken)
