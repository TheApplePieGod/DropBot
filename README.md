# DropBot

A customizable python bot which can monitor various websites for when a product goes back in stock and becomes available for purchase.

Current supported websites include: [Microcenter](https://www.microcenter.com/), [Newegg](https://www.newegg.com/), [Bestbuy](https://www.bestbuy.com/), [B&H Photo Video](https://www.bhphotovideo.com/), and [Amazon](https://www.amazon.com/).

- Full customizability when monitoring a specific product
    - Specify a direct link to the product or a search term that will be searched on a customizable selection of stores
- Max web timeout and search cycle speed settings
- If on windows, a native notification will appear when new stock is found
- Optional setting to play a very loud audio cue when a product is found in stock
- Optional discord bot integration which will message specified users when new stock is found
- Detailed real-time logging
    - ![Logging](https://raw.githubusercontent.com/TheApplePieGod/DropBot/main/images/Logging.png)
- Various browser spoofing techniques to circumvent bot detection
- Inline commands such as 'pause', 'stop', etc.
- Tested on Windows 10 and Linux
### Coming soon:
- Optional 'max price' option for each query
- Customizable cooldown between stock alerts for the same product
