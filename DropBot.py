from bs4 import BeautifulSoup
from urllib import request
import json
import requests
import platform
if platform.system() == "Windows":
    from win10toast import ToastNotifier
import time
from colorama import init, Back, Fore, Style
from asyncio import run, sleep
from playsound import playsound

import DiscordIntegration
import Logging

init(convert=True)

headers = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Content-Type": "application/json",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36",
    "Connection": "keep-alive",
    "X-CLIENT-ID": "FRV"
}

toaster = None
if platform.system() == "Windows":
    toaster = ToastNotifier()

settingsFile = open("data/Settings.txt", "r")
settings = json.loads(settingsFile.read())
settingsFile.close()

class Query:
    def __init__(self, storeIds, query, isURL):
        self.storeIds = storeIds
        self.query = query
        self.isURL = isURL

class Store:
    def __init__(self, id, name, searchURL):
        self.id = id
        self.name = name
        self.searchURL = searchURL

    def getItemName(self, soup):
        raise NotImplementedError("Store subclass must override this method")

    def getItemNameDirect(self, soup):
        raise NotImplementedError("Store subclass must override this method")

    def getStock(self, soup, session):
        raise NotImplementedError("Store subclass must override this method")

    def getStockDirect(self, soup, session):
        raise NotImplementedError("Store subclass must override this method")

class Microcenter(Store):
    def getItemName(self, soup):
        productElem = soup.select_one("li[class=product_wrapper] > div > div > div > div > div > h2 > a[data-name]")
        if productElem == None:
            return "Error"
        else:
            return productElem["data-name"]

    def getItemNameDirect(self, soup):
        productElem = soup.select_one("div[id=details] > h1 > span > span[data-name]")
        if productElem == None:
            return "Error"
        else:
            return productElem["data-name"]

    def getStock(self, soup, session):
        stockElem = soup.select_one('div[class="stock"]')
        if stockElem != None:
            stockText = stockElem.text.strip()
            if stockText == "Sold Out":
                return "Out of stock"
            else:
                return stockText
        else:
            return "Error"

    def getStockDirect(self, soup, session):
        stockElem = soup.select_one('span[class="inventoryCnt"]')
        if stockElem != None:
            stockText = stockElem.text.strip()
            if stockText == "Sold Out":
                return "Out of stock"
            else:
                return stockText
        else:
            return "Error"

class Newegg(Store):
    def getItemName(self, soup):
        productElem = soup.select_one("div[class=item-container] > div > a")
        if productElem == None:
            return "Error"
        else:
            return productElem.text.strip()

    def getItemNameDirect(self, soup):
        productElem = soup.select_one("h1[class=product-title]")
        if productElem == None:
            return "Error"
        else:
            return productElem.text.strip()

    def getStock(self, soup, session):
        # check for 'out of stock' promo
        outOfStock = False
        promoElem = soup.select_one('div[class=item-container] > div > p')
        if promoElem != None:
            promoText = promoElem.text.strip().replace("\"", "").lower()
            outOfStock = promoText == "out of stock"

        if outOfStock:
            return "Out of stock"
        else: # otherwise we need to go to the product page itself and get the info there
            itemElem = soup.select_one('div[class=item-container] > div > a')
            if itemElem != None:
                url = itemElem["href"].replace(" ", "+")
                resp = request.urlopen(url)
                webContent = resp.read()
                productSoup = BeautifulSoup(webContent, 'html.parser')

                return self.getStockDirect(productSoup, session)
            else:
                return "Error"

    def getStockDirect(self, soup, session):
        stockElem = soup.select_one("div[class=product-inventory] > strong")
        if stockElem != None:
            stockText = stockElem.text.strip().replace(".", "")
            if stockText.lower() == "out of stock":
                return "Out of stock"
            else:
                return stockText
        else:
            return "Error"

class Bestbuy(Store):
    def __init__(self, id, name, searchURL):
        super().__init__(id, name, searchURL)
        self.session = requests.Session()

    def getStockFromSKU(self, skuVal, session):
        url = "https://www.bestbuy.com/fulfillment/ispu/api/ispu/v2"
        data = { "channel":"Ecommerce", "checkRetailAvailability":True, "lookupInStoreQuantity":True, "requestInfos": [{ "additionalLocationIds": [], "condition": None, "itemSeqNumber": "1", "locationId": "0", "sku": skuVal }], "searchNearby":False }
            
        resp = session.post(url, json=data, headers=headers)
        obj = json.loads(resp.text)

        return "In stock" if obj["responseInfos"][0]["pickupEligible"] else "Out of stock"

    def getItemName(self, soup):
        productElem = soup.select_one("h4[class=sku-header] > a")
        if productElem == None:
            return "Error"
        else:
            return productElem.text.strip()

    def getItemNameDirect(self, soup):
        titleElem = soup.select_one("div[class=sku-title] > h1")
        if titleElem == None:
            return "Error"
        else:
            return titleElem.text.strip()

    def getStock(self, soup, session):
        valueElements = soup.select("div[class=sku-attribute-title] > span[class=sku-value]")
        if valueElements == None or len(valueElements) < 2:
            return "Error"
        else: # post to their stock api to get info
            skuVal = valueElements[1].text.strip()
            return self.getStockFromSKU(skuVal, session)

    def getStockDirect(self, soup, session):
        valueElement = soup.select_one("div[class='sku product-data'] > span[class='product-data-value body-copy']")
        if valueElement == None:
            return "Error"
        else: # post to their stock api to get info
            skuVal = valueElement.text.strip()
            return self.getStockFromSKU(skuVal, session)

stores = []
stores.append(Microcenter(len(stores), "Microcenter", "https://www.microcenter.com/search/search_results.aspx?Ntt="))
stores.append(Newegg(len(stores), "Newegg", "https://www.newegg.com/p/pl?d="))
stores.append(Bestbuy(len(stores), "Bestbuy", "https://www.bestbuy.com/site/searchpage.jsp?sc=Global&usc=All+Categories&st="))

queryList = []
queryList.append(Query([], "NVIDIA GeForce RTX 3070 8GB GDDR6 PCI Express 4.0 Graphics Card", False))
#queryList.append(Query([2], "https://www.bestbuy.com/site/nvidia-geforce-rtx-nvlink-bridge-for-30-series-products-space-gray/6441554.p?skuId=6441554", True))

iteration = 0
sleepDelay = 8
timeoutDelay = 5

async def queryStock():
    for query in queryList:

        searchingStores = []
        searchQuery = ""

        searchingStores.extend(query.storeIds)
        if query.isURL:
            if len(query.storeIds) != 1:
                print("URL query [" + query.query +  "] must have one store associated with it")
            else:
                searchQuery = query.query
        else:
            searchQuery = query.query.replace(" ", "+")
            if len(searchingStores) == 0:
                searchingStores.extend([i for i in range(0, len(stores))])

        for storeId in searchingStores:
            store = stores[storeId]

            url = searchQuery
            if not query.isURL:
                url = store.searchURL + url

            session = requests.Session()
            try:
                resp = session.get(url, headers=headers, timeout=timeoutDelay)
                soup = BeautifulSoup(resp.text, 'html.parser')
            except:
                soup = BeautifulSoup("", 'html.parser')

            itemName = ""
            stockStatus = ""

            try:
                if query.isURL:
                    itemName = store.getItemNameDirect(soup)
                else:
                    itemName = store.getItemName(soup)
            except:
                itemName = "Error"

            try:
                if query.isURL:
                    stockStatus = store.getStockDirect(soup, session)
                else:
                    stockStatus = store.getStock(soup, session)
            except:
                stockStatus = "Error"

            stockStatusColor = ""
            if stockStatus != "Error" and stockStatus != "Out of stock":
                stockStatusColor = Fore.LIGHTGREEN_EX
                foundMessage = itemName + " found at " + store.name
                if platform.system() == "Windows":
                    toaster.show_toast("DropBot", foundMessage, threaded=True)
                if settings["notifyOnDiscord"]:
                    await DiscordIntegration.discord_notify(foundMessage)
                if settings["playSounds"]:
                    playsound("data/NotifySound.wav")
            elif stockStatus == "Error":
                stockStatusColor = Fore.YELLOW
            else:
                stockStatusColor = Fore.RED

            infoString = Fore.LIGHTCYAN_EX + "[" +  store.name + "] " + Fore.RESET + itemName + " :: " + stockStatusColor + stockStatus + Fore.RESET
            Logging.logWithTimestamp(infoString)

            session.close()

async def main():
    global iteration
    await DiscordIntegration.client.wait_until_ready()
    await DiscordIntegration.init_users()
    while not DiscordIntegration.client.is_closed():
        await queryStock()
        iteration += 1
        await sleep(sleepDelay)

DiscordIntegration.init_discord(main)