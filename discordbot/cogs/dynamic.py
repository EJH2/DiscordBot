"""
Dynamic Rules!
"""
import asyncio
import json

import sqlalchemy.exc
from discord.ext import commands

from discordbot.bot import DiscordBot
from discordbot.cogs.utils import checks
from discordbot.cogs.utils import util
from discordbot.cogs.utils.tables import Dynamic_Rules, Table


async def needs_setup(ctx):
    server = ctx.guild
    async with ctx.bot.db.get_session() as s:
        query = await s.select(Dynamic_Rules).where(Dynamic_Rules.guild_id == server.id).all()
        query = await query.flatten()
    if len(query) == 0:
        await ctx.send("You don't have Dynamic Rules set up! Use {}dynamicrules setup".format(
            ctx.bot.command_prefix_))
    return True


class DynamicRules:
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.db = bot.db
        self.db.bind_tables(Table)

    @commands.group(invoke_without_command=True, aliases=["dynrules"])
    async def dynamicrules(self, ctx):
        """
        Base command for Dynamic Rules!
        """
        raise commands.BadArgument("Invalid subcommand passed: {0.subcommand_passed}".format(ctx))

    @dynamicrules.command(name="setup")
    @commands.check(checks.permissions(manage_messages=True))
    async def dynamicrules_setup(self, ctx):
        """
        Sets up the server to use Dynamic Rules. This is to de-clutter the DB.
        """
        server = ctx.guild
        async with self.bot.db.get_session() as s:
            query = await s.select(Dynamic_Rules).where(Dynamic_Rules.guild_id == server.id).all()
            query = await query.flatten()
        if len(query) == 0:
            try:
                async with self.bot.db.get_session() as s:
                    await s.add(Dynamic_Rules(guild_id=server.id, attrs="{}"))
                await ctx.send("Dynamic Rules entry successfully created for this server!")
            except sqlalchemy.exc.SQLAlchemyError as e:
                await ctx.send("Could not set up dynamic rules: {}".format(e))
        else:
            await ctx.send("Dynamic rules is already set up for this server!")

    @dynamicrules.group(name="get", invoke_without_command=True)
    @commands.check(checks.permissions(manage_messages=True))
    @commands.check(needs_setup)
    async def dynamicrules_get(self, ctx, *, entry: str):
        """
        Gets a dynamic rules setting for the server.

        Passing "all" will show all settings.
        """
        server = ctx.guild
        async with self.bot.db.get_session() as s:
            query = await s.select(Dynamic_Rules).where(Dynamic_Rules.guild_id == server.id).first()
        assert isinstance(query, Dynamic_Rules)
        attrs = json.loads(query.attrs)
        attr_list = [(key, attrs[key]) for key in attrs]
        if len(attr_list) == 0:
            return await ctx.send("You have no Dynamic Rules Overwrites!")
        else:
            await ctx.send(attrs.get(entry, "None"))

    @dynamicrules_get.command(name="all")
    @commands.check(checks.permissions(manage_messages=True))
    @commands.check(needs_setup)
    async def dynamicrules_get_all(self, ctx):
        """
        Gets all dynamic rules settings for the server.
        """
        server = ctx.guild
        async with self.bot.db.get_session() as s:
            query = await s.select(Dynamic_Rules).where(Dynamic_Rules.guild_id == server.id).first()
        assert isinstance(query, Dynamic_Rules)
        attrs = json.loads(query.attrs)
        attr_list = [(key, attrs[key]) for key in attrs]
        if len(attr_list) == 0:
            return await ctx.send("You have no Dynamic Rules Overwrites!")
        else:
            await ctx.send(util.neatly(attr_list, "autohotkey"))

    @dynamicrules.command(name="set")
    @commands.check(checks.permissions(manage_messages=True))
    @commands.check(needs_setup)
    async def dynamicrules_set(self, ctx, entry: str, *, value: str):
        """
        Set a dynamic rules value for the server.
        """
        server = ctx.guild
        try:
            async with self.bot.db.get_session() as s:
                query = await s.select(Dynamic_Rules).where(Dynamic_Rules.guild_id == server.id).first()
                assert isinstance(query, Dynamic_Rules)
                attrs = json.loads(query.attrs)
                attrs[entry] = value
                query.attrs = json.dumps(attrs)
                await s.add(query)
                await ctx.send("Successfully set `{}` to `{}`!".format(entry, value))
        except sqlalchemy.exc.SQLAlchemyError as e:
            await ctx.send("Could not set dynamic rules entry: {}".format(e))

    @dynamicrules.group(name="clear", invoke_without_command=True)
    @commands.check(checks.permissions(manage_messages=True))
    @commands.check(needs_setup)
    async def dynamicrules_clear(self, ctx, *, entry: str):
        """
        Clear a dynamic rules entry for the server.

        Passing "all" will clear all settings.
        """
        server = ctx.guild
        try:
            async with self.bot.db.get_session() as s:
                query = await s.select(Dynamic_Rules).where(Dynamic_Rules.guild_id == server.id).first()
                assert isinstance(query, Dynamic_Rules)
                attrs = json.loads(query.attrs)
                try:
                    del attrs[entry]
                except KeyError:
                    return await ctx.send("You have no entry named `{}`!".format(entry))
                query.attrs = json.dumps(attrs)
                await s.add(query)
            await ctx.send("Successfully cleared `{}`!".format(entry))
        except sqlalchemy.exc.SQLAlchemyError as e:
            await ctx.send("Could not clear dynamic rules entry: {}".format(e))

    @dynamicrules_clear.group(name="all")
    @commands.check(checks.permissions(manage_messages=True))
    @commands.check(needs_setup)
    async def dynamicrules_clear_all(self, ctx):
        """
        Clears all dynamic rules entries for the server.

        Careful, this action is IRREVERSIBLE!
        """
        await ctx.send("Are you sure you want to clear *all* entries? This action is IRREVERSIBLE! "
                       "If yes, type `yes` in 10 seconds, or the action will be aborted.")

        def check(m):
            return m.author == ctx.author and m.content.lower() == "yes"

        try:
            await ctx.bot.wait_for("message", check=check, timeout=10)
        except asyncio.TimeoutError:
            return await ctx.send("Timeout limit reached, aborting.")
        server = ctx.guild
        try:
            async with self.bot.db.get_session() as s:
                query = await s.select(Dynamic_Rules).where(Dynamic_Rules.guild_id == server.id).first()
                assert isinstance(query, Dynamic_Rules)
                attrs = {}
                query.attrs = json.dumps(attrs)
                await s.add(query)
                await ctx.send("Successfully cleared all entries!")
        except sqlalchemy.exc.SQLAlchemyError as e:
            await ctx.send("Could not clear all dynamic rules entries: {}".format(e))


def setup(bot: DiscordBot):
    bot.add_cog(DynamicRules(bot))