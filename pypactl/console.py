from aioconsole import AsynchronousCli
from argparse import ArgumentParser

class Console(AsynchronousCli):
    def __init__(self, commands):
        super().__init__({})
        self.commands = commands
        if 'exit' not in self.commands:
            self.commands['exit'] = (self.exit_command, ArgumentParser(description="Exit."))
        if 'help' not in self.commands:
            self.commands['help'] = (self.help_command, ArgumentParser(description="Display the help message."))
