import discord


class Paginator(discord.ui.View):
    def __init__(self, pages: list[discord.Embed]) -> None:
        super().__init__(timeout=30.0)
        self.pages = pages
        self.page = 0

    @discord.ui.button(
        label="<<-", custom_id="full_left", style=discord.ButtonStyle.primary
    )
    async def button_full_left(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ):
        self.page = 0
        self.update_button_status()
        return await interaction.response.edit_message(
            embed=self.pages[self.page], view=self
        )

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
            self.update_button_status()
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
            self.update_button_status()
            return await interaction.response.edit_message(
                embed=self.pages[self.page], view=self
            )

        return await interaction.response.defer()

    @discord.ui.button(
        label="->>", custom_id="full_right", style=discord.ButtonStyle.primary
    )
    async def button_full_right(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ):
        self.page = len(self.pages) - 1
        self.update_button_status()
        return await interaction.response.edit_message(
            embed=self.pages[self.page], view=self
        )

    def update_button_status(self):
        for child in self.children:
            if not isinstance(child, discord.ui.Button):
                continue

            match child.custom_id:
                case "full_left":
                    child.disabled = self.page == 0
                case "left":
                    child.disabled = self.page == 0
                case "right":
                    child.disabled = self.page == len(self.pages) - 1
                case "full_right":
                    child.disabled = self.page == len(self.pages) - 1
