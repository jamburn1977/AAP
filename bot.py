import os
import discord
from discord.ext import commands, tasks
import requests

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://yourdomain.com/webhook.php")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "YOUR_SECURE_WEBHOOK_SECRET_KEY")
ALLOWED_ROLE_ID = int(os.getenv("ALLOWED_ROLE_ID", "123456789012345678"))

# Global cache so autocomplete responds instantly without network lag
CACHED_AWARDS = ["MVP", "Veteran", "Top Recruiter"]

@tasks.loop(minutes=5)
async def refresh_awards_cache():
        global CACHED_AWARDS
        try:
                response = requests.get(
                        f"{WEBHOOK_URL}?action=get_awards", 
                        headers={"Authorization": WEBHOOK_SECRET}, 
                        timeout=5
                )
                if response.status_code == 200:
                        data = response.json()
                        fetched = data.get("awards", [])
                        if fetched:
                                CACHED_AWARDS = fetched
        except Exception:
                pass

async def get_award_choices(ctx: discord.AutocompleteContext):
        # Returns instantly from memory—zero network delay, zero timeouts!
        return [award for award in CACHED_AWARDS if ctx.value.lower() in award.lower()]

@bot.event
async def on_ready():
        print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
        if not refresh_awards_cache.is_running():
                refresh_awards_cache.start()

@bot.slash_command(name="award", description="Give an award to a member, assign their role, and log it to the database.")
@discord.option("award_name", description="Select an award from your database", autocomplete=get_award_choices)
async def award(
        ctx: discord.ApplicationContext, 
        member: discord.Member, 
        award_name: str, 
        reason: str = "No reason provided"
):
        if not any(role.id == ALLOWED_ROLE_ID for role in ctx.author.roles):
                await ctx.respond("❌ You do not have the required role to issue awards.", ephemeral=True)
                return
        
        await ctx.defer(ephemeral=False)
        
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
                response = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=10)
                
                try:
                        result = response.json()
                except Exception:
                        await ctx.followup.send(f"🚨 Web server returned non-JSON (HTTP {response.status_code}):\n```text\n{response.text[:300]}\n```", ephemeral=True)
                        return
                
                if response.status_code == 200 and result.get("status") == "success":
                        role_id_str = result.get("role_id")
                        role_assigned_text = ""
                        
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
                        
                        # Public success message for everyone to see!
                        await ctx.followup.send(f"🏆 Successfully awarded **{award_name}** to {member.mention}{role_assigned_text} and saved it to the database!", ephemeral=False)
                else:
                        error_msg = result.get("message", "Unknown error")
                        # Errors stay private (ephemeral)
                        await ctx.followup.send(f"⚠️ Failed to record award on the web server: {error_msg}", ephemeral=True)
                        
        except Exception as e:
                await ctx.followup.send(f"🚨 Connection error occurred: {str(e)}", ephemeral=True)

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
