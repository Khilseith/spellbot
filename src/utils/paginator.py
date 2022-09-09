import discord


class Paginator(discord.ui.View):
    def __init__(self, pages: list[discord.Embed]) -> None:
        super().__init__(timeout=30.0)
        self.pages = pages
        self.page = 0

    @discord.ui.button(label="<-", style=discord.ButtonStyle.primary)
    async def button_left(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ):

        pervious_page = self.page

        if self.page > 0:
            self.page -= 1

        if self.page != pervious_page:
            await interaction.response.edit_message(embed=self.pages[self.page])
        else:
            await interaction.response.defer()

    @discord.ui.button(label="->", style=discord.ButtonStyle.primary)
    async def button_right(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ):
        pervious_page = self.page

        if self.page < len(self.pages):
            self.page += 1

        if self.page != pervious_page:
            await interaction.response.edit_message(embed=self.pages[self.page])
        else:
            await interaction.response.defer()
