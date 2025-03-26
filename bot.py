import discord
from discord.ext import commands
import gspread
import re
import os
from google.oauth2.service_account import Credentials
import json

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Store in Railway
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")  # Store in Railway

# Load Google Service Account credentials from Railway environment variable
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")
creds_dict = json.loads(SERVICE_ACCOUNT_JSON)  # Convert string back to dictionary
creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1  # Access first sheet

# Email Validation Regex
EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

# Discord Bot Setup
intents = discord.Intents.default()
intents.members = True  # Ensure the bot can read member details
bot = commands.Bot(command_prefix="!", intents=intents)

# Store user data temporarily
pending_verifications = {}

@bot.event
async def on_member_join(member):
    """Sends a DM to new members asking for their name."""
    try:
        dm_channel = await member.create_dm()
        await dm_channel.send(
            f"👋 Welcome to {member.guild.name}, {member.mention}!\n\n"
            "To get verified, please provide your **full name**. Type it below:"
        )
        pending_verifications[member.id] = {"step": 1}  # Start verification
    except discord.Forbidden:
        print(f"❌ Could not send DM to {member.name} (privacy settings).")

@bot.event
async def on_message(message):
    """Handles user responses in DM for verification."""
    if message.author.bot:
        return

    user_id = message.author.id

    if user_id in pending_verifications:
        step = pending_verifications[user_id]["step"]

        if step == 1:
            # Store name and ask for email
            pending_verifications[user_id]["name"] = message.content
            pending_verifications[user_id]["step"] = 2
            await message.author.send("✅ Got it! Now, please enter your **email address**:")

        elif step == 2:
            # Validate email format
            email = message.content
            if not re.match(EMAIL_REGEX, email):
                await message.author.send("❌ Invalid email format. Please enter a **valid email address**:")
                return  # Stay on this step

            pending_verifications[user_id]["email"] = email
            pending_verifications[user_id]["step"] = 3
            await message.author.send("✅ Email saved! Now, please enter your **Country**:")

        elif step == 3:
            # Store country and complete verification
            country = message.content
            pending_verifications[user_id]["country"] = country

            name = pending_verifications[user_id]["name"]
            email = pending_verifications[user_id]["email"]

            # Save to Google Sheets
            sheet.append_row([str(user_id), name, email, country])

            # Assign the Verified Role
            guild = bot.get_guild(message.guild.id)  # Get the server
            member = guild.get_member(user_id)
            role = discord.utils.get(guild.roles, name="Verified")  # Change to your verified role

            if role and member:
                await member.add_roles(role)
                await message.author.send("✅ You are now verified and have access to the server!")
            else:
                await message.author.send("⚠️ Verification failed: Role not found.")

            # Remove user from pending verification
            del pending_verifications[user_id]

@bot.event
async def on_ready():
    """Bot is ready."""
    print(f"✅ {bot.user.name} is online!")

# Run the bot
bot.run(BOT_TOKEN)
