import os
import discord
from discord.ext import commands
import requests

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
ALLOWED_ROLE_ID = int(os.getenv("ALLOWED_ROLE_ID", "0"))

@bot.event
async def on_ready():
        print(f"Logged in as {bot.user.name}")

@bot.slash_command(name="award", description="Give an award to a member")
async def award(ctx: discord.ApplicationContext, member: discord.Member, award_name: str, reason: str = "No reason provided"):
        if not any(role.id == ALLOWED_ROLE_ID for role in ctx.author.roles):
                await ctx.respond("❌ You do not have the required role.", ephemeral=True)
                return
        
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
                result = response.json()
                if response.status_code == 200 and result.get("status") == "success":
                        await ctx.respond(f"🏆 Successfully awarded **{award_name}** to {member.mention}!")
                else:
                        msg = result.get("message", "Unknown error")
                        await ctx.respond(f"⚠️ Failed: {msg}", ephemeral=True)
        except Exception as e:
                await ctx.respond(f"🚨 Error: {str(e)}", ephemeral=True)

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
