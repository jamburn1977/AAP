import os
import discord
from discord.ext import commands
import requests

# Initialize Bot with appropriate intents
intents = discord.Intents.default()
intents.members = True  # Required to check member roles
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://yourdomain.com/webhook.php")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "YOUR_SECURE_WEBHOOK_SECRET_KEY")
ALLOWED_ROLE_ID = int(os.getenv("ALLOWED_ROLE_ID", "123456789012345678"))
# ...
bot.run(os.getenv("DISCORD_BOT_TOKEN"))

@bot.event
async def on_ready():
        print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
        print("Bot is ready to dispatch awards to your web server.")

@bot.slash_command(name="award", description="Give an award to a member and sync it to the website database.")
async def award(
        ctx: discord.ApplicationContext, 
        member: discord.Member, 
        award_name: str, 
        reason: str = "No reason provided"
):
        # 1. Verify if the issuer has the required role
        if not any(role.id == ALLOWED_ROLE_ID for role in ctx.author.roles):
                await ctx.respond("❌ You do not have the required role to issue awards.", ephemeral=True)
                return
        
        # 2. Prepare payload data
        payload = {
                "recipient_discord_id": str(member.id),
                "recipient_username": member.display_name,
                "issuer_discord_id": str(ctx.author.id),
                "issuer_username": ctx.author.display_name,
                "award_name": award_name,
                "reason": reason
        }
        
        headers = {
                "Authorization": WEBHOOK_SECRET,
                "Content-Type": "application/json"
        }
        
try:
                # 3. Send data to your GoDaddy PHP Webhook
                response = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=10)
                
                # Attempt to parse JSON safely
                try:
                        result = response.json()
                except Exception:
                        # If GoDaddy returns HTML or PHP warnings instead of clean JSON, show the text
                        await ctx.respond(f"🚨 Web server returned non-JSON (HTTP {response.status_code}):\n```text\n{response.text[:300]}\n```", ephemeral=True)
                        return
                
                if response.status_code == 200 and result.get("status") == "success":
                        await ctx.respond(f"🏆 Successfully awarded **{award_name}** to {member.mention} and saved it to the database!")
                else:
                        error_msg = result.get("message", "Unknown error")
                        await ctx.respond(f"⚠️ Failed to record award on the web server: {error_msg}", ephemeral=True)
                        
        except Exception as e:
                await ctx.respond(f"🚨 Connection error occurred: {str(e)}", ephemeral=True)

# Run the bot using your Discord Bot Token
bot.run("Token")