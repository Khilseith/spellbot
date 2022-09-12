import discord


class Paginator(discord.ui.View):
    def __init__(self, pages: list[discord.Embed]) -> None:
        super().__init__(timeout=30.0)
        self.pages = pages
        self.page = 0

    @discord.ui.button(
        label="<-", custom_id="left", style=discord.ButtonStyle.primary, disabled=True
    )
    async def button_left(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ):

        pervious_page = self.page

        if self.page > 0:
            self.page -= 1

        if self.page != pervious_page:
            for child in self.children:
                if not isinstance(child, discord.ui.Button):
                    continue

                match child.custom_id:
                    case "left":
                        child.disabled = self.page == 0
                    case "right":
                        child.disabled = self.page == len(self.pages) - 1

            return await interaction.response.edit_message(
                embed=self.pages[self.page], view=self
            )

        return await interaction.response.defer()

    @discord.ui.button(label="->", custom_id="right", style=discord.ButtonStyle.primary)
    async def button_right(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ):
        pervious_page = self.page

        if self.page < len(self.pages):
            self.page += 1

        if self.page != pervious_page:
            for child in self.children:
                if not isinstance(child, discord.ui.Button):
                    continue

                match child.custom_id:
                    case "left":
                        child.disabled = self.page == 0
                    case "right":
                        child.disabled = self.page == len(self.pages) - 1

            return await interaction.response.edit_message(
                embed=self.pages[self.page], view=self
            )

        return await interaction.response.defer()
