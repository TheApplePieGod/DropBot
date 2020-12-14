import time
from colorama import Fore

def logWithTimestamp(message, color=""):
    formattedMessage = "[" + time.strftime("%r", time.localtime()) + "] " + message
    if color == "":
        print(formattedMessage)
    else:
        print(color + formattedMessage + Fore.RESET)