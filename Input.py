import Globals
import sys
import signal
from Logging import logWithTimestamp 
from colorama import Fore

def async_input():
    while Globals.acceptCommands:
        data = input()
        Globals.inputQueue.put(data)

def handle_input():
    while not Globals.inputQueue.empty():
        command = Globals.inputQueue.get()
        success = False
        if command == "stop":
            Globals.acceptCommands = False
            sys.exit(0)
            success = True
        elif command == "pause":
            Globals.running = False
            success = True
        elif command == "resume":
            Globals.running = True
            success = True

        if success:
            logWithTimestamp("Command [" + command + "] successful", Fore.LIGHTGREEN_EX)
        else:
            logWithTimestamp("Unknown command: " + command, Fore.RED)