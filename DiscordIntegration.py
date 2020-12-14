import discord
import asyncio
import json
from colorama import Fore

import Logging

client = discord.Client()
members = []

async def init_users():
    global members
    membersFile = open("UserInfo.txt", "r")
    info = membersFile.read()
    membersFile.close()
    memberIds = info.split(',')
    for id in memberIds:
        newMember = await client.fetch_user(int(id))
        members.append(newMember)
    Logging.logWithTimestamp("Discord ready")

async def discord_notify(message):
    success = 0
    failed = 0
    for member in members:
        if member != None:
            try:
                channel = await member.create_dm()
                await channel.send(message)
                success += 1
            except:
                failed += 1
        else:
            failed += 1
    if success > 0:
        Logging.logWithTimestamp("Discord notified succeeded " + str(success) + '/' + str(len(members)) + " times", Fore.YELLOW)
    if failed > 0:
        Logging.logWithTimestamp("Discord notify failed " + str(failed) + '/' + str(len(members)) + " times", Fore.RED)

tokenFile = open("DiscordToken.txt", "r")
discordBotToken = tokenFile.read()
tokenFile.close()

def init_discord(mainFunc):
    client.loop.create_task(mainFunc())
    client.run(discordBotToken)
