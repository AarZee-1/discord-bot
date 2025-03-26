import discord
from discord.ext import commands
import gspread
import re
from google.oauth2.service_account import Credentials

# Bot Token (Replace with your actual bot token)
BOT_TOKEN = "MTM1MTIyMjQwODE5NTA4NDQxNA.GePxrr.s3uKJktXTX3c5LiRujSA1CLIevqFBMpS-hpLDU"  

# Google Sheets Setup
SERVICE_ACCOUNT_FILE = "fair-ceiling-454016-u1-6de8587783ba.json"  # JSON key file  
SPREADSHEET_ID = "1YxJxVv56zoZ6G388Tp7r1USzAyQ47g8IIWtfVTeQ550"  # Google Sheets ID  

# Email Validation Regex
EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

# Authenticate with Google Sheets
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1  # Access first sheet

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
