from collections import OrderedDict
from enum import Enum
from typing import NamedTuple

import d20
import discord
from discord import ui

from utils.errors import BadRoll


class Selectors(Enum):
    lowest = "lowest"
    highest = "highest"
    exact = "exact"
    greater = "greater"
    less = "less"


class DropOrKeep(Enum):
    drop = "drop"
    keep = "keep"


class MultiplyOrDivide(Enum):
    multiply = "multiply"
    divide = "divide"


class RerollOn(Enum):
    once = "ro"
    untilNoneLeft = "rr"
    rerollOnceKeepOriginal = "ra"


class KeepType(NamedTuple):
    type: Selectors
    number: int
    dropOrKeep: DropOrKeep


class MultiplyDivide(NamedTuple):
    value: int
    multiplyOrDivide: MultiplyOrDivide


class Reroll(NamedTuple):
    type: Selectors
    when: RerollOn
    number: int


PARAMATERS = [
    "type",
    "keep",
    "modifier",
    "negate",
    "multiplyDivide",
    "minMax",
    "reroll",
]


class Die:
    def __init__(
        self,
        ammount: int,
        sides: int,
        type: str | None = None,
        keep: KeepType | None = None,
        modifier: int = 0,
        negate: bool = False,
        multiplyDivide: MultiplyDivide | None = None,
        min: int | None = None,
        max: int | None = None,
        reroll: Reroll | None = None,
    ):
        self.ammount = ammount
        self.sides = sides
        self.type = type
        self.keep = keep
        self.modifier = modifier
        self.negate = negate
        self.multiplyDivide = multiplyDivide
        self.min = min
        self.max = max
        self.reroll = reroll

    def __str__(self):

        reroll: str = ""
        if self.reroll is not None:
            match RerollOn(self.reroll.when):
                case RerollOn.once:
                    reroll += "ro"
                case RerollOn.untilNoneLeft:
                    reroll += "rr"
                case RerollOn.rerollOnceKeepOriginal:
                    reroll += "ra"

            match Selectors(self.reroll.type):
                case Selectors.lowest | Selectors.highest as x:
                    reroll += x.name[0]
                case Selectors.exact:
                    pass
                case Selectors.greater:
                    reroll += ">"
                case Selectors.less:
                    reroll += "<"

            if reroll.startswith("rr") and (
                reroll.endswith("l") or reroll.endswith("h")
            ):
                raise BadRoll(
                    "Rerolling continuiously the lowest or highest dice leads to infinite rolling.",
                    {"reroll": self.reroll},
                )

            number = self.reroll.number

            reroll += str(number)

        keep: str = ""
        if self.keep is not None:
            keep = "k" if DropOrKeep(self.keep.dropOrKeep) == DropOrKeep.keep else "p"
            match Selectors(self.keep.type):
                case Selectors.lowest | Selectors.highest as x:
                    keep += x.name[0]
                case Selectors.exact:
                    pass
                case Selectors.greater:
                    keep += ">"
                case Selectors.less:
                    keep += "<"

            keep += str(self.keep.number)

        multiplyDivide: str = ""
        if self.multiplyDivide is not None:
            match MultiplyOrDivide(self.multiplyDivide.multiplyOrDivide):
                case MultiplyOrDivide.multiply:
                    multiplyDivide += " *"
                case MultiplyOrDivide.divide:
                    multiplyDivide += " /"
            multiplyDivide += f" {self.multiplyDivide.value}"

        if self.modifier > 0:
            modifier = f" + {self.modifier}"
        elif self.modifier < 0:
            modifier = f" - {self.modifier}"
        else:
            modifier = ""

        negate = "-" if self.negate else ""

        min = f"mi{self.min}" if self.min is not None else ""
        max = f"ma{self.max}" if self.max is not None else ""
        type = f"[{self.type}]" if self.type else ""

        return f"{negate}({self.ammount}d{self.sides}{min}{max}{reroll}{keep}{modifier}){multiplyDivide}{type}"


class Dice:
    def __init__(self, dice: list[Die], DC: int | None = None):
        self.dice = dice
        self.DC = DC

    def roll(self):
        return d20.roll("(" + ", ".join(str(die) for die in self.dice) + ")")


class MinMaxButton(ui.Button["RollBuilder"]):
    def __init__(self):
        super().__init__(custom_id="minMax", label="Set min/max", disabled=True)
        self.view: RollBuilder

    async def callback(self, interaction: discord.Interaction) -> None:
        modal = MinMaxModal(self.view)
        await interaction.response.send_modal(modal)
        await modal.wait()
        await interaction.edit_original_response(view=self.view)


class ModifierButton(ui.Button["RollBuilder"]):
    def __init__(self):
        super().__init__(custom_id="modifier", label="Set modifier", disabled=True)
        self.view: RollBuilder

    async def callback(self, interaction: discord.Interaction) -> None:
        modal = ModifierModal(self.view)
        await interaction.response.send_modal(modal)
        await modal.wait()
        await interaction.edit_original_response(view=self.view)


class KeepButton(ui.Button["RollBuilder"]):
    def __init__(self):
        super().__init__(custom_id="keep", label="Set Keeps", disabled=True)
        self.view: RollBuilder

    async def callback(self, interaction: discord.Interaction) -> None:
        modal = KeepModal(self.view)
        await interaction.response.send_modal(modal)
        await modal.wait()
        await interaction.edit_original_response(view=self.view)


class RerollButton(ui.Button["RollBuilder"]):
    def __init__(self):
        super().__init__(custom_id="reroll", label="Set Reroll", disabled=True)
        self.view: RollBuilder

    async def callback(self, interaction: discord.Interaction) -> None:
        modal = RerollModal(self.view)
        await interaction.response.send_modal(modal)
        await modal.wait()
        await interaction.edit_original_response(view=self.view)


class MultiplyDivideButton(ui.Button["RollBuilder"]):
    def __init__(self):
        super().__init__(
            custom_id="multiplyDivide", label="Multiply/Divide", disabled=True
        )
        self.view: RollBuilder

    async def callback(self, interaction: discord.Interaction) -> None:
        modal = MultiplyDivideModal(self.view)
        await interaction.response.send_modal(modal)
        await modal.wait()
        await interaction.edit_original_response(view=self.view)


class RollButton(ui.Button["RollBuilder"]):
    def __init__(self):
        super().__init__(
            label="Roll",
            style=discord.ButtonStyle.green,
            custom_id="roll",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        # Make linter behave
        self.view: RollBuilder

        if len(self.view.dice) <= 0:
            return await interaction.response.send_message(
                content="No dice to roll!", ephemeral=True
            )
        roll = Dice(list(self.view.dice.values())).roll()
        embed = discord.Embed(title="Roll", description=str(roll))
        embed.set_author(
            name=interaction.user.__str__(),
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None,
        )
        self.view.stop()
        await interaction.response.send_message(embed=embed)


class DiceSelector(ui.Select["RollBuilder"]):
    def __init__(self):
        options: list[discord.SelectOption] = []
        options.append(
            discord.SelectOption(label="New", description="Add a new die", emoji="🆕")
        )

        super().__init__(
            options=options,
            min_values=1,
            max_values=1,
            placeholder="Pick a die to edit",
            custom_id="selector",
            row=0,
        )

    def disable_enable_buttons(self, status: bool) -> None:
        buttons = list(
            filter(lambda child: isinstance(child, ui.Button), self.view.children)
        )
        if len(buttons) == 0:
            return
        for button in buttons:
            if not isinstance(button, ui.Button) or button.custom_id not in PARAMATERS:
                continue
            button.disabled = status

    async def callback(self, interaction: discord.Interaction):
        # Make the linter behave
        self.view: RollBuilder

        # Check if the user is making a new die
        if self.values[0] == "New":
            self.disable_enable_buttons(True)

            # Prompt the user to pick sides and ammount and if they don't defer
            oldLength = len(self.view.dice)
            modal = NewDieModal(self.view)
            await interaction.response.send_modal(modal)
            await modal.wait()
            if len(self.view.dice) <= oldLength:
                return await interaction.response.defer()

            # Unselect their currently selected "New" option
            self.values.pop()

            # Add the new die to the list of dice and select it
            newDie = next(reversed(self.view.dice))
            self.add_option(label=newDie, emoji="🎲")
            self.values.append(newDie)

            # Update the message

            embed: discord.Embed = (await interaction.original_response()).embeds[0]
            embed.clear_fields().description = ", ".join(self.view.dice.keys())
            return await interaction.edit_original_response(embed=embed, view=self.view)

        if interaction.message is None:
            raise Exception("Should not be possible")
        embed: discord.Embed = interaction.message.embeds[0]
        if len(embed.fields) >= 1:
            await interaction.response.defer()
            return
        embed.add_field(name="Currently Editing", value=self.values[0])
        self.disable_enable_buttons(False)
        await interaction.response.edit_message(embed=embed, view=self.view)


class RollBuilder(ui.View):
    def __init__(self, dice: OrderedDict[str, Die]):
        super().__init__()
        self.dice = dice

        self.add_item(DiceSelector())
        self.add_item(MinMaxButton())
        self.add_item(ModifierButton())
        self.add_item(KeepButton())
        self.add_item(RerollButton())
        self.add_item(MultiplyDivideButton())
        self.add_item(RollButton())

    def getCurrentDie(self) -> Die | None:
        # Filter out the die selector without the linter getting angry
        children = list(
            filter(lambda child: isinstance(child, DiceSelector), self.children)
        )
        selector = children[0] if len(children) == 1 else None
        if selector is None or not isinstance(selector, DiceSelector):
            raise Exception("This should never happen")

        return self.dice.get(selector.values[0])


class NewDieModal(ui.Modal, title="New Die"):
    def __init__(self, view: RollBuilder):
        super().__init__()
        self.view = view

    ammount = discord.ui.TextInput(
        label="# of dice",
        default="1",
        min_length=1,
        max_length=3,
        required=True,
        style=discord.TextStyle.short,
    )
    sides = discord.ui.TextInput(
        label="# of sides",
        default="1",
        required=True,
        style=discord.TextStyle.short,
        max_length=3,
        min_length=1,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # Verify ints were submitted
        sides = int(self.sides.value)
        ammount = int(self.ammount.value)

        dieLabel = f"{ammount}d{sides}"
        # Prevent conflicts
        if self.view.dice.get(dieLabel) is not None:
            return await interaction.response.send_message(f"{dieLabel} already exists")

        self.view.dice[dieLabel] = Die(ammount, sides)
        await interaction.response.defer()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError):
            await interaction.response.send_message(
                "Both values must be intergers.", ephemeral=True
            )


class MinMaxModal(ui.Modal, title="Set the Min/Max"):
    def __init__(self, view: RollBuilder):

        super().__init__()
        self.view = view
        die = view.getCurrentDie()
        if die is None:
            raise Exception("Should never happen")
        self.die = die

    min = discord.ui.TextInput(
        label="Minimum value",
        required=False,
        min_length=1,
        max_length=3,
        style=discord.TextStyle.short,
    )
    max = discord.ui.TextInput(
        label="Maximum value",
        required=False,
        min_length=1,
        max_length=3,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        min = self.min.value
        max = self.max.value

        dieLabel = f"{self.die.ammount}d{self.die.sides}"

        if min:
            min = int(min)
            self.view.dice[dieLabel].min = min
        if max:
            max = int(max)
            self.view.dice[dieLabel].max = max
        await interaction.response.defer()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError):
            await interaction.response.send_message(
                "Both values must be intergers", ephemeral=True
            )


class TypeModal(ui.Modal, title="Set the damage type of the die"):
    def __init__(self, view: RollBuilder):
        super().__init__()
        self.view = view
        die = view.getCurrentDie()
        if die is None:
            raise Exception("Should never happen")
        self.die = die

    type = discord.ui.TextInput(
        label="Type", required=True, style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        type = self.type.value

        dieLabel = f"{self.die.ammount}d{self.die.sides}"

        self.view.dice[dieLabel].type = type.replace("]", "").replace("[", "")
        await interaction.response.defer()


class NegateModal(ui.Modal, title="Negate the result of the die?"):
    def __init__(self, view: RollBuilder):
        super().__init__()
        self.view = view
        die = view.getCurrentDie()
        if die is None:
            raise Exception("Should never happen")
        self.die = die

    negate = discord.ui.TextInput(
        label="Yes or No", required=True, style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        negate = self.negate.value.lower()
        if negate in ("yes", "y", "true", "t", "1", "enable", "on"):
            negate = True
        elif negate in ("no", "n", "false", "f", "0", "disable", "off"):
            negate = False
        else:
            raise ValueError()

        dieLabel = f"{self.die.ammount}d{self.die.sides}"

        self.view.dice[dieLabel].negate = negate
        await interaction.response.defer()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError):
            await interaction.response.send_message(
                "Your answer must be in the form of a yes/no or a true/false",
                ephemeral=True,
            )


class ModifierModal(ui.Modal, title="Set the modifier of the die"):
    def __init__(self, view: RollBuilder):
        super().__init__()
        self.view = view
        die = view.getCurrentDie()
        if die is None:
            raise Exception("Should never happen")
        self.die = die

    modifier = discord.ui.TextInput(
        label="Modifer",
        required=False,
        min_length=1,
        max_length=3,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        modifier = int(self.modifier.value)

        dieLabel = f"{self.die.ammount}d{self.die.sides}"

        self.view.dice[dieLabel].modifier = modifier
        await interaction.response.defer()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError):
            await interaction.response.send_message(
                "Value must be an interger", ephemeral=True
            )


class KeepModal(ui.Modal, title="What dice to keep"):
    def __init__(self, view: RollBuilder):
        super().__init__()
        self.view = view
        die = view.getCurrentDie()
        if die is None:
            raise Exception("Should never happen")
        self.die = die

    selector = discord.ui.TextInput(
        label="Selector",
        required=False,
        style=discord.TextStyle.short,
        placeholder="lowest | highest | exact | greater | less",
    )

    number = discord.ui.TextInput(
        label="Number",
        required=True,
        style=discord.TextStyle.short,
        min_length=1,
        max_length=3,
        placeholder="Number for the selector (3 with highest for slector would keep highest 3)",
    )

    dropKeep = discord.ui.TextInput(
        label="Drop Or Keep",
        required=False,
        style=discord.TextStyle.short,
        placeholder="drop | keep",
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:

        try:
            selector = Selectors(self.selector.value.lower())
        except ValueError:
            await interaction.response.send_message(
                f"{self.selector.value} is not one of the options for `Selectors`",
                ephemeral=True,
            )
            return
        try:
            dropKeep = DropOrKeep(self.dropKeep.value.lower())
        except ValueError:
            await interaction.response.send_message(
                f"{self.dropKeep.value} is not one of the options for `Drop Or Keep`",
                ephemeral=True,
            )
            return

        number = int(self.number.value)

        dieLabel = f"{self.die.ammount}d{self.die.sides}"
        keep = KeepType(
            type=selector.value,
            number=number,
            dropOrKeep=dropKeep.value,
        )

        self.view.dice[dieLabel].keep = keep
        await interaction.response.defer()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError):
            await interaction.response.send_message(
                "Value must be an interger", ephemeral=True
            )


class RerollModal(ui.Modal, title="What to ReRoll on"):
    def __init__(self, view: RollBuilder):
        super().__init__()
        self.view = view
        die = view.getCurrentDie()
        if die is None:
            raise Exception("Should never happen")
        self.die = die

    selector = discord.ui.TextInput(
        label="Selector",
        required=False,
        style=discord.TextStyle.short,
        placeholder="lowest | highest | exact | greater | less",
    )

    number = discord.ui.TextInput(
        label="Number",
        required=True,
        style=discord.TextStyle.short,
        min_length=1,
        max_length=3,
        placeholder="Number for the selector (3 with highest for slector would keep highest 3)",
    )

    rerollOn = discord.ui.TextInput(
        label="What to reroll on",
        required=True,
        style=discord.TextStyle.short,
        placeholder="rr (Reroll untill gone) | ro (reroll once) | ra (reroll and add original)",
    )

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        try:
            selector = Selectors(self.selector.value.lower())
        except ValueError:
            await interaction.response.send_message(
                f"{self.selector.value} is not one of the options for `Selectors`",
                ephemeral=True,
            )
            return
        try:
            rerollOn = RerollOn(self.rerollOn.value.lower())
        except ValueError:
            await interaction.response.send_message(
                f"{self.rerollOn.value} is not one of the options for `Drop Or Keep`",
                ephemeral=True,
            )
            return

        number = int(self.number.value)
        dieLabel = f"{self.die.ammount}d{self.die.sides}"

        reroll = Reroll(type=selector.value, when=rerollOn.value, number=number)
        self.view.dice[dieLabel].reroll = reroll
        await interaction.response.defer()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError):
            await interaction.response.send_message(
                "Value must be an interger", ephemeral=True
            )


class MultiplyDivideModal(ui.Modal, title="Multiply or Divide"):
    def __init__(self, view: RollBuilder):
        super().__init__()
        self.view = view
        die = view.getCurrentDie()
        if die is None:
            raise Exception("Should never happen")
        self.die = die

    number = discord.ui.TextInput(
        label="Number",
        required=True,
        style=discord.TextStyle.short,
        min_length=1,
        max_length=3,
    )

    multiplyDivide = discord.ui.TextInput(
        label="Multiply or Divide",
        required=True,
        style=discord.TextStyle.short,
        placeholder="multiply | Divide",
    )

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        number = int(self.number.value)
        try:
            multiplyDivide = MultiplyOrDivide(self.multiplyDivide.value.lower())
        except ValueError:
            await interaction.response.send_message(
                f"{self.multiplyDivide.value} is not one of the options for `Multiply or Divide`",
                ephemeral=True,
            )
            return
        dieLabel = f"{self.die.ammount}d{self.die.sides}"
        multiplyOrDivide = MultiplyDivide(
            value=number, multiplyOrDivide=multiplyDivide.value
        )
        self.view.dice[dieLabel].multiplyDivide = multiplyOrDivide
        await interaction.response.defer()
