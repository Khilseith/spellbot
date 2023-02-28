import json
from string import capwords
from typing import List, Tuple

import discord
from discord import app_commands
from discord.ext import commands
from fuzzywuzzy import fuzz, process


class Spell(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    def chunk_text(
        self, text, max_chunk_size=1024, chunk_on=("\n\n", "\n", ". ", " "), chunker_i=0
    ):
        """# Chunk Text

        Recursively chunks *text* into a list of str, with each element no longer than *max_chunk_size*.
        Prefers splitting on the elements of *chunk_on*, in order.
        """
        if len(text) <= max_chunk_size:  # the chunk is small enough
            return [text]
        if chunker_i >= len(chunk_on):  # we have no more preferred chunk_on characters
            # optimization: instead of merging a thousand characters, just use list slicing
            return [
                text[:max_chunk_size],
                *self.chunk_text(
                    text[max_chunk_size:], max_chunk_size, chunk_on, chunker_i + 1
                ),
            ]

        # split on the current character
        chunks = []
        split_char = chunk_on[chunker_i]
        for chunk in text.split(split_char):
            chunk = f"{chunk}{split_char}"
            if (
                len(chunk) > max_chunk_size
            ):  # this chunk needs to be split more, recurse
                chunks.extend(
                    self.chunk_text(chunk, max_chunk_size, chunk_on, chunker_i + 1)
                )
            elif (
                chunks and len(chunk) + len(chunks[-1]) <= max_chunk_size
            ):  # this chunk can be merged
                chunks[-1] += chunk
            else:
                chunks.append(chunk)

        # remove extra split_char from last chunk
        chunks[-1] = chunks[-1][: -len(split_char)]
        return chunks

    def get_level(self, level):
        """# Get Level

        Formats a level from it's relative number

        ## Args:
            - level (interger): the level one wishes to be formated

        ## Returns:
            - str: the level in formatted form
        """
        if level == 0:
            return "Cantrip"
        if level == 1:
            return "1st-level"
        if level == 2:
            return "2nd-level"
        if level == 3:
            return "3rd-level"
        return f"{level}th-level"

    def create_embed_queue(self, embed, pieces):
        """# Create Embed Queue

        Creates a queue of embeds using pices made by chunk_text

        ## Args:
            - embed (instance of embed class): The first embed to be in the queue
            - pieces (list): list of chunks to be put into embeds

        ## Returns:
            - list: an embed queue in list form
        """
        embed_queue = [embed]
        if len(pieces) > 1:
            for i, piece in enumerate(pieces[1::2]):
                temp_embed = discord.Embed()
                temp_embed.colour = 0xAC26EB
                if (next_idx := (i + 1) * 2) < len(
                    pieces
                ):  # this is chunked into 1024 pieces, and descs can handle 2
                    temp_embed.description = piece + pieces[next_idx]
                else:
                    temp_embed.description = piece
                embed_queue.append(temp_embed)

        return embed_queue

    def get_school(self, letter):
        """# Get School

        Formats a school of magic from it's letter

        ## Args:
            - letter (str): The School's letter

        ## Returns:
            - str: The reformated School
        """
        match letter:
            case "V":
                return "Evocation"
            case "A":
                return "Abjuration"
            case "E":
                return "Enchantment"
            case "I":
                return "Illusion"
            case "D":
                return "Divinitation"
            case "N":
                return "Necromancy"
            case "T":
                return "Transmutation"
            case "C":
                return "Conjuration"
            case _:
                return letter

    def create_spell_embed(self, spell) -> Tuple[discord.Embed, List[str]]:
        embed = discord.Embed(title=capwords(spell["name"]))
        embed.color = 0xAC26EB

        embed.add_field(name="Level:", value=self.get_level(spell["level"]))

        embed.add_field(name="Type:", value=self.get_school(spell["school"]))

        if spell["ritual"]:
            embed.add_field(name="Ritual?", value="Yes.")

        embed.add_field(name="Casttime:", value=spell["casttime"])

        embed.add_field(name="Range:", value=spell["range"])

        comp = []
        if spell["components"]["verbal"]:
            comp.append("V")
        if spell["components"]["somatic"]:
            comp.append("S")
        if spell["components"]["material"]:
            comp.append("M (" + spell["components"]["material"] + ")")

        if comp == []:
            comp = "None."
        elif len(comp) == 1:
            comp = comp[0]
        else:
            comp = ", ".join(comp)

        embed.add_field(name="Components:", value=comp)

        embed.add_field(name="Duration:", value=spell["duration"])

        embed.add_field(name="Classes:", value=spell["classes"], inline=True)

        if spell["subclasses"]:
            embed.add_field(name="Subclassses:", value=spell["subclasses"], inline=True)

        pieces = self.chunk_text(spell["description"])

        embed.add_field(name="Description:", value=pieces[0], inline=False)

        return embed, pieces

    @app_commands.command(
        name="spelldescription", description="Obtain the details of any given spell"
    )
    @app_commands.describe(spell="The spell you want the description of")
    async def sd(self, interaction: discord.Interaction, spell: str):
        spell = spell.lower()

        with open("spells2.json") as f:
            f = json.load(f)

        foundSpell = None

        for i in f:
            if i["name"].lower() == spell:
                foundSpell = i
                break

        if foundSpell is None:
            embed = discord.Embed(title="Spell Not Found", color=0xFF1100)
            embed.description = "No spell with the name {} found.".format(spell)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed, pieces = self.create_spell_embed(foundSpell)

        await interaction.response.send_message(
            embeds=self.create_embed_queue(embed, pieces)
        )

    @sd.autocomplete("spell")
    async def sd_autocomplete(
        self, _: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        with open("spells2.json") as f:
            f = json.load(f)

        listOfSpells = []

        for i in f:
            listOfSpells.append(capwords((i["name"])))

        if len(current) == 0:
            return [
                app_commands.Choice(name=spell, value=spell)
                for spell in listOfSpells[:12]
            ]

        matches = process.extract(
            current, listOfSpells, scorer=fuzz.token_sort_ratio, limit=12
        )
        return [app_commands.Choice(name=match[0], value=match[0]) for match in matches]

    @app_commands.command(
        name="spells", description="Get the list of spells matching a set of paramaters"
    )
    @app_commands.describe(
        level="The of the spells you are searching for",
        type="School of the spells you are searching for",
        spellclass="Class which has the spells you are looking for",
        ritual="true/false if you are looking for only rituals",
    )
    async def spells(
        self,
        interaction: discord.Interaction,
        level: int = -1,
        type: str = "none",
        spellclass: str = "none",
        ritual: bool = False,
    ):
        with open("spells2.json") as f:
            f = json.load(f)

        listOfSpells = []

        for i in f:
            if not i["ritual"] and ritual:
                continue
            if level != -1 and i["level"] != level:
                continue
            if type != "none" and type.lower() != self.get_school(i["school"]).lower():
                continue
            if spellclass != "none" and spellclass.lower() not in i[
                "classes"
            ].lower().split(", "):
                continue

            listOfSpells.append(capwords(i["name"]))

        if listOfSpells == []:
            embed = discord.Embed(title="No Spells Found")
            embed.color = 0xFF1100
            embed.description = "No spells found with the given paramaters."
            await interaction.response.send_message(embed=embed, ephemeral=True)

        pieces = self.chunk_text("\n".join(listOfSpells))

        embed = discord.Embed(description=pieces[0])
        embed.title = f"{len(listOfSpells)} Spells Found!"
        embed.color = 0xAC26EB

        await interaction.response.send_message(
            embeds=self.create_embed_queue(embed, pieces)
        )

    @spells.autocomplete("spellclass")
    async def spellclass_autocomplete(
        self, _: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        classes = [
            "Artificer",
            "Warlock",
            "Wizard",
            "Sorcerer",
            "Rouge",
            "Ranger",
            "Paladin",
            "Monk",
            "Fighter",
            "Druid",
            "Bard",
            "Barbarian",
        ]

        if len(current) == 0:
            return [
                app_commands.Choice(name=dndClass, value=dndClass)
                for dndClass in classes
            ]

        matches = process.extract(
            current, classes, scorer=fuzz.token_sort_ratio, limit=3
        )
        return [app_commands.Choice(name=match[0], value=match[0]) for match in matches]

    @spells.autocomplete("type")
    async def type_autocomplete(
        self, _: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        spellTypes = [
            "Evocation",
            "Abjuration",
            "Enchantment",
            "Illusion",
            "Divinitation",
            "Necromancy",
            "Transmutation",
            "Conjuration",
        ]

        if len(current) == 0:
            return [
                app_commands.Choice(name=spellType, value=spellType)
                for spellType in spellTypes
            ]

        matches = process.extract(
            current, spellTypes, scorer=fuzz.token_sort_ratio, limit=3
        )
        return [app_commands.Choice(name=match[0], value=match[0]) for match in matches]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Spell(bot))
