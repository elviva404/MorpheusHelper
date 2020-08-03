import io
from typing import Optional, Tuple, List

from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from discord import Member, TextChannel, Guild, Message, File, Embed, Attachment
from discord.ext.commands import Bot, CommandError

from permissions import PermissionLevel


def make_error(message) -> str:
    return f":x: Error: {message}"


async def is_teamler(member: Member) -> bool:
    return await PermissionLevel.SUPPORTER.check_permissions(member)


def zip_default(*args, default=None):
    length = max(map(len, args))
    return zip(*[[*a] + [default] * (length - len(a)) for a in args])


async def update_reactions(message: Message, reactions: List[str]):
    if message.reactions and (not reactions or message.reactions[0].emoji != reactions[0]):
        await message.clear_reactions()
    remove = []
    add = []
    for o, n in zip_default([reaction.emoji for reaction in message.reactions], reactions):
        if o != n or remove or add:
            if o:
                remove.append(o)
            if n:
                add.append(n)
    for emoji in remove:
        await message.clear_reaction(emoji)
    for emoji in add:
        await message.add_reaction(emoji)


async def send_to_changelog(guild: Guild, message: str):
    channel: Optional[TextChannel] = guild.get_channel(await Settings.get(int, "logging_changelog", -1))
    if channel is not None:
        await channel.send(message)


async def get_prefix() -> str:
    return await Settings.get(str, "prefix", ".")


async def set_prefix(new_prefix: str):
    await Settings.set(str, "prefix", new_prefix)


async def attachment_to_file(attachment: Attachment) -> File:
    file = io.BytesIO()
    await attachment.save(file)
    return File(file, filename=attachment.filename, spoiler=attachment.is_spoiler())


async def get_files_from_message(message: Message) -> List[File]:
    return [await attachment_to_file(attachment) for attachment in message.attachments]


async def read_normal_message(bot: Bot, channel: TextChannel, author: Member, delete=False) -> Tuple[str, List[File]]:
    msg: Message = await bot.wait_for("message", check=lambda m: m.channel == channel and m.author == author)
    files: List[File] = await get_files_from_message(msg)
    if delete:
        await msg.delete()
    return msg.content, files


async def read_embed(bot: Bot, channel: TextChannel, author: Member) -> Embed:
    await channel.send(translations.send_embed_title)
    title: str = (await bot.wait_for("message", check=lambda m: m.channel == channel and m.author == author)).content
    if len(title) > 256:
        raise CommandError(translations.title_too_long)
    await channel.send(translations.send_embed_content)
    content: str = (await bot.wait_for("message", check=lambda m: m.channel == channel and m.author == author)).content
    return Embed(title=title, description=content)


async def read_complete_message(message: Message) -> Tuple[str, List[File], Optional[Embed]]:
    for embed in message.embeds:
        if embed.type == "rich":
            break
    else:
        embed = None

    return message.content, [await attachment_to_file(attachment) for attachment in message.attachments], embed
