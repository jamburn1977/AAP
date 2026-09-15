import os
import discord
from discord.ext import commands
import requests

# Initialize Bot with appropriate intents (Members intent required for role assignment)
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration loaded securely from environment variables
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://yourdomain.com/webhook.php")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "YOUR_SECURE_WEBHOOK_SECRET_KEY")
ALLOWED_ROLE_ID = int(os.getenv("ALLOWED_ROLE_ID", "123456789012345678"))

async def get_award_choices(ctx: discord.AutocompleteContext):
        # Dynamically fetches the current list of awards from your PHP backend
        try:
                response = requests.get(
                        f"{WEBHOOK_URL}?action=get_awards", 
                        headers={"Authorization": WEBHOOK_SECRET}, 
                        timeout=5
                )
                if response.status_code == 200:
                        data = response.json()
                        return data.get("awards", ["MVP", "Veteran"])
        except Exception:
                pass
        return ["MVP", "Veteran"]

@bot.event
async def on_ready():
        print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
        print("Bot is ready and synced with your web database.")

@bot.slash_command(name="award", description="Give an award to a member, assign their role, and log it to the database.")
@discord.option("award_name", description="Select an award from your database", autocomplete=get_award_choices)
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
        
        # 2. Immediately defer as ephemeral to prevent Discord 3-second timeouts
        await ctx.defer(ephemeral=True)
        
        # 3. Prepare payload data
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
                # 4. Send data to your GoDaddy PHP Webhook
                response = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=10)
                
                try:
                        result = response.json()
                except Exception:
                        await ctx.followup.send(f"🚨 Web server returned non-JSON (HTTP {response.status_code}):\n```text\n{response.text[:300]}\n```", ephemeral=True)
                        return
                
                if response.status_code == 200 and result.get("status") == "success":
                        role_id_str = result.get("role_id")
                        role_assigned_text = ""
                        
                        # 5. Automatically assign the Discord role if a valid role_id was returned
                        if role_id_str and role_id_str.isdigit():
                                role_id = int(role_id_str)
                                role = ctx.guild.get_role(role_id)
                                if role:
                                        try:
                                                await member.add_roles(role, reason=f"Awarded {award_name} by {ctx.author.display_name}")
                                                role_assigned_text = f" and assigned the **{role.name}** role"
                                        except Exception as role_err:
                                                role_assigned_text = f" (⚠️ Failed to assign Discord role: {role_err})"
                                else:
                                        role_assigned_text = " (⚠️ Role ID found in DB, but role not found in this Discord server)"
                        
                        await ctx.followup.send(f"🏆 Successfully awarded **{award_name}** to {member.mention}{role_assigned_text} and saved it to the database!", ephemeral=True)
                else:
                        error_msg = result.get("message", "Unknown error")
                        await ctx.followup.send(f"⚠️ Failed to record award on the web server: {error_msg}", ephemeral=True)
                        
        except Exception as e:
                await ctx.followup.send(f"🚨 Connection error occurred: {str(e)}", ephemeral=True)

# Run the bot using the environment variable for your Discord Token
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
