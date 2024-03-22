import os
import traceback

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.settings import get_prefix

MY_GUILD = discord.Object(id=792524491665702954)


class MyClient(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix=get_prefix, intents=intents)
        self.bot = MY_GUILD

    async def sync(self) -> None:
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)
        await self.tree.sync()

    async def setup_hook(self) -> None:
        for extension in os.listdir("./src/cogs"):
            if extension.endswith(".py"):
                await client.load_extension(f"cogs.{extension[:-3]}")
        await self.sync()


intents: discord.Intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True

client = MyClient(intents=intents)


@client.tree.command()
async def ping(interaction: discord.Interaction):
    """Returns the bot's ping"""
    await interaction.response.send_message(
        embed=discord.Embed(
            title="Pong!", description=f":hourglass: {round(client.latency * 1000)}ms"
        )
    )


@commands.is_owner()
@client.command()
async def load(ctx: commands.Context, extension: str):
    try:
        await client.load_extension(f"cogs.{extension}")
        print(f"Loaded {extension}")
        embed = discord.Embed(
            title="Success",
            description=f"{extension} was properly reloaded",
            color=0x00D138,
        )
    except Exception as err:
        print(f"{extension} failed to reload")
        embed = discord.Embed(
            title="Error", description=f"{extension} failed to reload", color=0xFF0000
        )
        if ctx.guild and ctx.guild.id == MY_GUILD.id:
            embed.add_field(name="Error", value=f"```{err}```")
        traceback.print_tb(err.__traceback__)
    await ctx.send(embed=embed)
    await client.sync()


@commands.is_owner()
@client.command()
async def unload(ctx: commands.Context, extension: str):
    try:
        await client.unload_extension(f"cogs.{extension}")
        print(f"Unloaded {extension}")
        embed = discord.Embed(
            title="Success",
            description=f"{extension} was properly unloaded",
            color=0x00D138,
        )
    except Exception as err:
        print(f"{extension} failed to unload")
        embed = discord.Embed(
            title="Error", description=f"{extension} failed to unload", color=0xFF0000
        )
        if ctx.guild and ctx.guild.id == MY_GUILD.id:
            embed.add_field(name="Error", value=f"```{err}```")
        traceback.print_tb(err.__traceback__)
    await ctx.send(embed=embed)


@commands.is_owner()
@client.command()
async def reload(ctx: commands.Context, extension: str):
    try:
        await client.unload_extension(f"cogs.{extension}")
        await client.load_extension(f"cogs.{extension}")
        print(f"Reloaded {extension}")
        embed = discord.Embed(
            title="Success",
            description=f"{extension} was properly reloaded",
            color=0x00D138,
        )
    except Exception as err:
        print(f"{extension} failed to reload")
        embed = discord.Embed(
            title="Error", description=f"{extension} failed to reload", color=0xFF0000
        )
        if ctx.guild and ctx.guild.id == MY_GUILD.id:
            embed.add_field(name="Error", value=f"```{err}```")
        traceback.print_tb(err.__traceback__)
    await ctx.send(embed=embed)
    await client.sync()


if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("TOKEN")
    if token is None:
        print("No Token Found In The .env")
        exit()
    client.run(token)
