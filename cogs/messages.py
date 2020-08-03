import re
from typing import Optional

from PyDrocsid.events import StopEventHandling
from PyDrocsid.translations import translations
from discord import Message, PartialEmoji, Member, TextChannel, NotFound, Embed, HTTPException, Forbidden
from discord.abc import Messageable
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context

from permissions import PermissionLevel
from util import make_error, read_complete_message, get_files_from_message, read_normal_message, update_reactions

PENCIL = "📝"
FILE_FOLDER = "📁"
CLIPBOARD = "📋"
WHITE_CHECK_MARK = "✅"
X = "❌"
LABEL = "🏷"
PAINTBRUSH = "🖌"
ARROW_LEFT = "⬅"
WASTEBASKET = "🗑"


async def create_message_dialog(channel: Messageable, author: Member, destination: TextChannel):
    embed = Embed(title=translations.compose_message, color=0x03AD28, description=translations.msg_dlg_intro)
    embed.add_field(name=translations.author, value=author.mention, inline=True)
    embed.add_field(name=translations.channel, value=destination.mention, inline=True)
    msg: Message = await channel.send(embed=embed)
    for emoji in (PENCIL, FILE_FOLDER, CLIPBOARD, X):
        await msg.add_reaction(emoji)


class MessagesCog(Cog, name="Messages"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_message(self, msg: Message) -> Optional[Message]:
        if len(msg.embeds) != 1:
            return None
        for field in msg.embeds[0].fields:
            match = re.match(r"^https://discord(app)?.com/channels/\d+/(\d+)/(\d+)$", field.value)
            if match is not None:
                break
        else:
            return None

        channel_id, message_id = map(int, match.groups()[1:])
        channel: Optional[TextChannel] = self.bot.get_channel(channel_id)
        if channel is None:
            return None
        try:
            return await channel.fetch_message(message_id)
        except NotFound:
            return None

    async def read_message(self, channel: TextChannel, member: Member, text: str) -> str:
        tmp: Message = await channel.send(text)
        response, _ = await read_normal_message(self.bot, channel, member, delete=True)
        await tmp.delete()
        return response * (response != ".")

    async def update_dialog(self, root_message: Message, mode: int, **kwargs):
        msg: Optional[Message] = await self.get_message(root_message)
        root_embed = root_message.embeds[0]

        content = kwargs.get("content", "")
        files = kwargs.get("files", [])
        embed = kwargs.get("embed", None)
        if msg is not None:
            if "content" not in kwargs:
                content = msg.content
            if "files" not in kwargs:
                files = await get_files_from_message(msg)
            if "embed" not in kwargs:
                embed = [*msg.embeds, None][0]
            await msg.delete()

        for i, field in enumerate(root_embed.fields):
            if field.name == translations.preview:
                root_embed.remove_field(i)
                break

        if files or content or embed is not None:
            msg = await root_message.channel.send(content=content, files=files, embed=embed)
            root_embed.add_field(name=translations.preview, value=msg.jump_url, inline=False)

        root_embed.description = translations.msg_dlg_intro if mode == 0 else translations.msg_dlg_embed
        if mode == 0 and (files or content or embed is not None):
            root_embed.description += translations.msg_dlg_send

        await root_message.edit(embed=root_embed)

        if mode == 0:
            reactions = [PENCIL, FILE_FOLDER, CLIPBOARD, X]
            if files or content or embed is not None:
                reactions.append(WHITE_CHECK_MARK)
        else:
            reactions = [LABEL, PENCIL, PAINTBRUSH, ARROW_LEFT, WASTEBASKET]
        await update_reactions(root_message, reactions)

    async def handle_main_menu(self, message: Message, emoji: str, member: Member):
        if emoji == X:
            await message.delete()
            if (msg := await self.get_message(message)) is not None:
                await msg.delete()
        elif emoji == WHITE_CHECK_MARK:
            for field in message.embeds[0].fields:
                if (match := re.match(r"^<#(\d+)>$", field.value)) is not None:
                    break
            else:
                raise StopEventHandling
            channel: Optional[TextChannel] = self.bot.get_channel(int(match.group(1)))
            msg: Optional[Message] = await self.get_message(message)
            if channel is None or msg is None:
                raise StopEventHandling

            content, files, embed = await read_complete_message(msg)
            try:
                await channel.send(content=content, embed=embed, files=files)
            except (HTTPException, Forbidden):
                await message.channel.send(make_error(translations.msg_could_not_be_sent))

            await message.clear_reactions()
            embed = message.embeds[0]
            embed.description = f":white_check_mark: {translations.msg_sent}"
            await message.edit(embed=embed)
        elif emoji == PENCIL:
            content = await self.read_message(message.channel, member, translations.send_message)
            await self.update_dialog(message, 0, content=content)
        elif emoji == FILE_FOLDER:
            tmp: Message = await message.channel.send(translations.send_file)
            _, files = await read_normal_message(self.bot, message.channel, member, delete=True)
            await tmp.delete()
            await self.update_dialog(message, 0, files=files)
        elif emoji == CLIPBOARD:
            embed = Embed()
            msg: Optional[Message] = await self.get_message(message)
            if msg and msg.embeds:
                embed = msg.embeds[0]
            await self.update_dialog(message, 1, embed=embed)

    async def handle_embed_menu(self, message: Message, emoji: str, member: Member):
        msg: Optional[Message] = await self.get_message(message)
        if msg and msg.embeds:
            embed = msg.embeds[0]
        else:
            await self.update_dialog(message, 0, embed=None)
            return

        if emoji == LABEL:
            embed.title = await self.read_message(message.channel, member, translations.send_embed_title)
            await self.update_dialog(message, 1, embed=embed)
        elif emoji == PENCIL:
            embed.description = await self.read_message(message.channel, member, translations.send_embed_content)
            await self.update_dialog(message, 1, embed=embed)
        elif emoji == PAINTBRUSH:
            color = await self.read_message(message.channel, member, translations.send_embed_color)
            match = re.match(r"^#?([0-9a-fA-F]{6})$", color)
            if match is None:
                await message.channel.send(make_error(translations.invalid_color), delete_after=3)
                return

            embed.color = int(match.group(1), 16)
            await self.update_dialog(message, 1, embed=embed)
        elif emoji == ARROW_LEFT:
            await self.update_dialog(message, 0)
        elif emoji == WASTEBASKET:
            await self.update_dialog(message, 0, embed=None)

    async def on_raw_reaction_add(self, message: Message, emoji: PartialEmoji, member: Member):
        if message.guild is None or member.bot or message.author != self.bot.user:
            return
        if len(message.embeds) != 1 or message.embeds[0].title != translations.compose_message:
            return
        if message.embeds[0].description.startswith(":white_check_mark:"):
            return

        await message.remove_reaction(emoji, member)
        for field in message.embeds[0].fields:
            if field.value == member.mention:
                break
        else:
            raise StopEventHandling

        if translations.msg_dlg_intro.strip() in message.embeds[0].description:
            await self.handle_main_menu(message, str(emoji), member)
        elif translations.msg_dlg_embed.strip() in message.embeds[0].description:
            await self.handle_embed_menu(message, str(emoji), member)

        raise StopEventHandling

    @commands.command()
    @PermissionLevel.OWNER.check
    @guild_only()
    async def test(self, ctx: Context, channel: TextChannel):
        await create_message_dialog(ctx, ctx.author, channel)
