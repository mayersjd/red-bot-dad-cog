from collections import defaultdict
import datetime
import discord
import logging
import random
random.seed()
import re
from redbot.core import checks, commands, Config
from redbot.core.data_manager import cog_data_path
from redbot.core.bot import Red
from typing import List

from .jokes.joke import Joke, NoSuchOption


log = logging.getLogger("red.dad")
_DEFAULT_GUILD = dict()



class Dad(commands.Cog):
    def __init__(self, bot:Red, jokes:List[Joke]):
        """Init for the Dad cog

        Parameters
        ----------
        bot: Red
            The Redbot instance instantiating this cog.
        jokes: List[Joke]
            The list of Joke objects to be loaded.
        """
        # Setup
        super().__init__()
        self.bot = bot
        # Register jokes
        self.jokes = jokes
        self.guild_options_information = dict()
        for jk in self.jokes.values():
            jk.register_guild_settings(_DEFAULT_GUILD, 
                    self.guild_options_information)

        self._conf = Config.get_conf(
                None, 91919191, 
                cog_name=f"{self.__class__.__name__}", force_registration=True
                )
        self._conf.register_guild(**_DEFAULT_GUILD)
        self.shut_up_until = defaultdict(lambda: None)
        # Dad Presence Data
        self.dad_presences = [
            ("Balance the check book", "🏦"),
            ("Go to work", "🏢"),
            ("Grill some steaks", "🥩"),
            ("Mow the lawn", "🌿"),
            ("Rake the leaves", "🍁"),
            ("Sleep in chair", "😴"),
            ("Sort the ties", "👔"),
            ("Spray for weeds", "🌿"),
            ("Trim the hedges", "🪚"),
            ("Walk the dog", "🐕"),
            ("Wash the car", "🚗"),
            ("Wear socks with sandals", "🧦"),
            ("Watch the History Channel", "📺")
        ]
        # Dad Variants data
        self.dad_variants = ["dad", "father", "daddy", "papa"]
        # Recognized rude responses
        self.rude_responses = [
            "😡",
            "🤬",
            "💀",
            "😴",
            "☠️",
            "🖕",
            "🚫",
            "⛔",
            "💩"
        ]
        # Shut Up Dad Data
        self.shut_up_variants = ["shut up", "be quiet", "not now"]


    # Helper commands
    async def acknowledge_reference(self, message:discord.Message):
        """Acknowledge if this bot is mentioned or "dad"
        "dad" means synonyms, possibly in other languages.

        Parameters
        ----------
        message: discord.Message
            Message to possibly acknowledge

        """
        async def _ack():
            await message.add_reaction("😉")

        if self.bot.user.mentioned_in(message):
            return await _ack()

        for dad_variant in self.dad_variants:
            if dad_variant in message.content.lower():
                return await _ack()


    async def ground_rude_person(self, payload:discord.RawReactionActionEvent)\
            -> None:
        """Ground users who reacted to Dad's messages "rudely"
        Parameters
        ----------
        payload: discord.RawReactionActionEvent
            An object detailing the message and the reaction.
        """
        # Check if the emoji is "offensive" to Dad
        if not str(payload.emoji.name) in self.rude_responses:
            # It's not, so quit
            return

        # Get the channel
        channel = self.bot.get_channel(payload.channel_id)

        # Get Message
        msg = await channel.fetch_message(payload.message_id)

        # Is Dad the author?
        if not msg.author.id == self.bot.user.id:
            # It's not, so quit
            return

        # They were rude, ground them
        await channel.send(f"{payload.member.mention} you're grounded")


    def if_shut_up(self, ctx:commands.Context) -> bool:
        """Is Dad supposed to shut up?

        Parameters
        ----------
        ctx: commands.Context
            The context in which we determine if Dad is
            supposed to shut up.

        Returns
        -------
        bool
            Boolean as to rather Dad is supposed to shut up.
        """
        # Get shut up time
        shut_up_time = self.shut_up_until[ctx.guild.id]
        # If shut up time is not None
        if shut_up_time is not None:
            # Dad was told to shut up, but can he talk now?
            if datetime.datetime.now() > shut_up_time:
                # He can talk now, so erase the shut up until time
                self.shut_up_until[ctx.guild.id] = None
                return False
            else:
                # Dad is still in time out
                return True


    async def set_random_dad_presence(self) -> None:
        """Set a random dad-like presence"""
        act, emoji = random.choice(self.dad_presences)
        # Set up for if Discord eventually allows Custom Activities for bots
        name = f"{act} {emoji}"
        cust_act = discord.Game(name)
        await self.bot.change_presence(activity=cust_act)



    def shut_up(self, ctx:commands.Context, shut_up_time:datetime.timedelta)\
            -> None:
        """Tell Dad to shut up in this guild for the specified time.

        Parameters
        ----------
        ctx: commands.Context
            The context in which we tell Dad to shut up. 
        shut_up_time: datetime.timedelta
            The amount of time to be quiet.
        """
        self.shut_up_until[ctx.guild.id] = datetime.datetime.now() +\
                                           shut_up_time


    async def told_to_shut_up(self, message:discord.Message) -> None:
        """Shut dad up if a user told him to shut up in their message.
        Note that the user has to be an admin.

        Parameters
        ----------
        message: discord.Message
            Message to possibly be told to shut up in.
        """
        if self.bot.user.mentioned_in(message):
            for shut_up_variant in self.shut_up_variants:
                if shut_up_variant in message.content.lower():
                    # Check if admin
                    admin = await self.bot.is_owner(message.author)
                    admin = admin or message.guild.owner == message.author
                    member_snowflakes = message.author._roles
                    guild_settings = self.bot._config.guild(message.guild)
                    for snowflake in await guild_settings.admin_role():
                        if member_snowflakes.has(snowflake):
                            admin = True
                    # Respond
                    if admin:
                        minutes = 5
                        self.shut_up(message, 
                                     datetime.timedelta(seconds=minutes*60)
                                    )
                        await message.channel.send(
                                f"Okay son, I'll leave you alone for "\
                                    f"{minutes} minutes"
                                )
                    else:
                        await message.channel.send("No son, I am the boss")


    # Listeners
    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        """Perform actions when a message is received

        Parameters
        ---------
        message: discord.Message
            The message to perform actions upon.
        """
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return
        author = message.author
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            return
        if await self.bot.is_automod_immune(message):
            return

        # Randomly change the status after a message is received
        if random.randint(1,100) == 1:
            await self.set_random_dad_presence()

        # Is a user requesting quiet time?
        await self.told_to_shut_up(message)

        # Is Dad allowed to talk?
        if self.if_shut_up(message):
            # Nope
            return 

        # Dad always notices when he's talked about
        # If 'dad' is mentioned, then acknowledge it
        await self.acknowledge_reference(message)

        # Does Dad notice the joke?
        for jk in random.sample(list(self.jokes.values()), len(self.jokes)):
            if await jk.make_joke(self, message):
                # Joke was successful, end
                break


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload:discord.RawReactionActionEvent)\
            -> None:
        """Perform actions when a reaction is added to a message.
        Parameters
        ----------
        payload: discord.RawReactionActionEvent
            An object detailing the message and the reaction.
        """
        await self.ground_rude_person(payload)


    @commands.Cog.listener()
    async def on_ready(self):
        await self.set_random_dad_presence()


    # Commands
    @commands.guild_only()
    @commands.admin()
    @commands.group()
    async def dad_settings(self, ctx:commands.Context) -> None:
        """Admin commands"""


    @dad_settings.command()
    async def shut_up_dad(self, ctx:commands.Context, minutes:int):
        """Admin command for shutting Dad up

        Parameters
        ----------
        minutes: int
            Number of minutes to tell Dad to shut up.
        """
        self.shut_up(ctx, datetime.timedelta(seconds=60*minutes))

        contents = dict(
                title="Okay Boomer",
                description=f"Dad will be quit for {minutes} minutes"
                )
        embed = discord.Embed.from_dict(contents)
        return await ctx.send(embed=embed)


    @dad_settings.command()
    async def list_options(self, ctx:commands.Context):
        """List the values for all the options for jokes"""
        guild_option_strings = []
        for opt in self.guild_options_information.values():
            guild_option_strings.append(
                    f"{opt.name}: "\
                    f"{await Joke.get_guild_option(self, ctx, opt.name)}"
                )
        guild_option_strings = '\n'.join(sorted(guild_option_strings))
        contents = dict(
                title = "Response Chances",
                description = f"**Guild**: \n {guild_option_strings}"
                )
        await ctx.send(embed=discord.Embed.from_dict(contents))


    @dad_settings.command()
    async def set_option(self, ctx:commands.Context, name:str, 
            new_value):
        """Set the option for a joke.
        Parameters
        ----------
        name: str
            The name of the option to modify.
        new_value: "any"
            The new value.
        """
        try:
            await Joke.set_guild_option_value(self, ctx, name, new_value)
            title = "Set Response Chance: Success"
            description = f"Set {name} to {new_value}"
            if "chance" in name:
                description += "%"
        except NoSuchOption as e:
            title = "Set Option: Failure"
            description = str(e)
        except ValueError as e:
            title = "Set Option: Failure"
            description = str(e)
        contents = dict(
                title = title,
                description = description
                )
        await ctx.send(embed=discord.Embed.from_dict(contents))

