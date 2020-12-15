import time
from colorama import Fore

def logWithTimestamp(message, color=""):
    formattedMessage = "[" + time.strftime("%r", time.localtime()) + "] " + color + message + Fore.RESET
    print(formattedMessage)

def logInfo(message, color = ""):
    logWithTimestamp(Fore.MAGENTA + "[Info] " + Fore.RESET + color + message + Fore.RESET)