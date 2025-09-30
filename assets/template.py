# =========================
# ||                     ||
# ||   MODULE TEMPLATE   ||
# ||                     ||
# =========================
# This is a template for creating new modules.
# Modules are discord.py cogs.
# Copy this file, rename it, and add your commands.
#
# It's recommended to keep modules focused on a single area of
# functionality. For example, a module for automatic role
# assignment, suggesting expressions, or an economy.
#
# It's best practice to store any data in /data/your_module_name
# as a mySQL database for concurrent edits and less memory usage
# compared to opening and storing a JSON file. It's also
# recommended to store any configuration data in
# /config/your_module_name.yml, and using YAML so you can comment
# and document your config options. Instructions for adding web
# dashboard limits, descriptions and readable names will be added
# to the Github wiki at some point if they aren't already.
#
# A NAME and VERSION attribute are required. A SOURCE is highly
# recommended if your module is in a repo. A DESCRIPTION and an
# AUTHOR are optional, but recommended.

import os
import yaml
from discord.ext import commands
from logger import Logger

logger = Logger("TemplateModule")

NAME = "TemplateModule"
VERSION = "1.0.0"
DESCRIPTION = "A template module for Squishy."
AUTHOR = "enhancedrock"
SOURCE = "https://github.com/enhancedrock/squishy"

class TemplateModule(commands.Cog):
    """A template module for Squishy."""

    def __init__(self, squishy):
        self.squishy = squishy
        self.load_config()

    def load_config(self):
        """Load configuration from YAML file."""
        config_path = 'config/template_module.yml'
        if not os.path.exists(config_path):
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    {
                        'subtext': '"This is the subtext in the config."'
                    }, f
                    )
        with open('config/template_module.yml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    @commands.command(brief="Hello to you, good sir!",
                      description="A sample command that replies to its executor with a greeting.")
    async def hello(self, ctx):
        """A sample command that demonstrates functionality."""
        await ctx.send(f"Hello there, {ctx.author.mention}!")

async def setup(squishy) -> None:
    """Load the TemplateModule cog."""
    logger.info("Loading TemplateModule...")
    try:
        await squishy.add_cog(TemplateModule(squishy))
        logger.info("TemplateModule loaded.")
    except Exception as e:
        logger.error(f"Failed to load TemplateModule: {e}")
        raise e
