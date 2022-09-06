import asyncio
from collections import OrderedDict

import discord
from d20 import roll
from discord import app_commands
from discord.ext import commands

from utils.roll import RollBuilder


class Roll(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    @app_commands.command(name="rolldice")
    async def roll(self, interaction: discord.Interaction):
        view = RollBuilder(OrderedDict())
        embed = discord.Embed(
            title="Dice",
        )
        embed.set_author(
            name=interaction.user.__str__(),
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="quickroll", description="Quickly Roll Some Dice")
    @app_commands.describe(
        ammount="# of dice",
        sides="# of sides on the dice",
        modifier="Number to add/subract to total",
        goal="Number to try to beat",
    )
    async def qroll(
        self,
        interaction: discord.Interaction,
        ammount: int,
        sides: int,
        modifier: int = 0,
        goal: int = 0,
    ):
        if (
            ammount >= 10
            or sides >= 100
            or sides <= 1
            or modifier >= 500
            or modifier <= -500
            or goal <= -500
            or goal >= 500
        ):
            em = discord.Embed(
                title="Error!",
                description="""
                Number of dice must be a number 1 - 10.
                The Die/Dice can have 1-100 sides.
                The Modifier and the DC have to be between -500 and 500. """,
                color=0xFF1100,
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return

        # Create the roll
        r = roll(f"{ammount}d{sides} + {modifier}")

        # Get raw dice rolls
        rolls = str(r)
        rolls = rolls.replace(f"{ammount}d{sides} (", "").replace(
            f") + {modifier} = `{str(r.total)}`", ""
        )

        # Get total
        total = str(r.total)

        # Rolling Message

        # determine modifier
        m = ""

        if modifier > 0:
            m = f" + {modifier}"
        elif modifier < 0:
            m = str(modifier).replace("-", "")
            m = f" - {m}"

        # Create Embed
        embed = discord.Embed(
            title="Rolling...", description=f"Rolling {ammount}d{sides}{m}"
        )
        await interaction.response.send_message(embed=embed)

        # If DC
        if int(goal) != 0:
            em = discord.Embed()

            total = int(total)

            # Succes message
            if total >= goal:
                em.title = "Roll Sucess!"
                em.color = 0x00D138
                em.add_field(name="Rolled:", value=rolls, inline=False)
                if modifier != 0:
                    em.add_field(name="Modifier:", value=str(modifier))
                em.add_field(name="Total:", value=f"{str(total)} ≥ {str(goal)}")
                await asyncio.sleep(1)
                await interaction.edit_original_response(embed=em)

            # Failure message
            elif total < goal:
                em.title = "Roll Failure"
                em.color = 0xFF1100
                em.add_field(name="Rolled:", value=rolls, inline=False)
                if modifier != 0:
                    em.add_field(name="Modifier:", value=str(modifier))
                em.add_field(name="Total:", value=f"{str(total)} < {str(goal)}")
                await asyncio.sleep(1)
                await interaction.edit_original_response(embed=em)

            return

        embed = discord.Embed(
            title="Rolled:",
            description=rolls,
            color=0xFEFEFE,
        )

        if modifier != 0:
            embed.add_field(name="Modifier:", value=str(modifier))

        if int(ammount) != 1 or modifier != 0:
            embed.add_field(name="Total:", value=total)

        await asyncio.sleep(1)
        await interaction.edit_original_response(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Roll(bot))
