import discord
from discord.ext import commands
import gspread
import re
import os
import json
from google.oauth2.service_account import Credentials

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Stored securely on Contabo
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")  # Stored securely on Contabo
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")  # Stored securely on Contabo

# Check if all environment variables are set
if not BOT_TOKEN or not SPREADSHEET_ID or not SERVICE_ACCOUNT_JSON:
    raise ValueError("❌ Missing environment variables. Check your Contabo setup.")

# Read the JSON file properly
try:
    with open(SERVICE_ACCOUNT_JSON, "r") as f:
        service_account_data = json.load(f)  # Correctly load JSON from file
except Exception as e:
    raise ValueError(f"❌ Error reading service account JSON file: {e}")

# Save JSON data to another file for compatibility
with open("service_account.json", "w") as f:
    json.dump(service_account_data, f)

# Authenticate with Google Sheets API
creds = Credentials.from_service_account_info(service_account_data, scopes=["https://www.googleapis.com/auth/spreadsheets"])
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1  # Access first sheet

print("✅ JSON File Loaded Successfully!")  # Debugging message

# Email Validation Regex
EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

# Discord Bot Setup
intents = discord.Intents.default()
intents.members = True  # Ensure the bot can read member details
intents.message_content = True # Ensure the bot can read messages
bot = commands.Bot(command_prefix="!", intents=intents)

# Store user data temporarily
pending_verifications = {}

# Replace with your actual server ID
GUILD_ID = 1350175315544244234  # Replace with your Discord server's actual ID

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
            guild = bot.get_guild(GUILD_ID)  # Use the hardcoded server ID
            if guild:
                member = guild.get_member(user_id)
                role = discord.utils.get(guild.roles, name="Verified")  # Change to your verified role

                if role and member:
                    await member.add_roles(role)
                    await message.author.send("✅ You are now verified and have access to the server!")
                else:
                    await message.author.send("⚠️ Verification failed: Role not found.")
            else:
                await message.author.send("⚠️ Could not fetch the server. Please contact an admin.")

            # Remove user from pending verification
            del pending_verifications[user_id]

@bot.event
async def on_ready():
    """Bot is ready."""
    print(f"✅ {bot.user.name} is online!")

# Run the bot
bot.run(BOT_TOKEN)
