from bs4 import BeautifulSoup
from urllib import request
import json
import requests
import platform
import time
from colorama import init, Back, Fore, Style
from asyncio import run, sleep
from playsound import playsound
import Logging
import Globals
from Input import async_input, handle_input
from threading import Thread

settingsFile = open("data/Settings.txt", "r")
settings = json.loads(settingsFile.read())
settingsFile.close()

if platform.system() == "Windows":
    from win10toast import ToastNotifier
if settings["notifyOnDiscord"]:
    import DiscordIntegration

init(convert=True)

toaster = None
if platform.system() == "Windows":
    toaster = ToastNotifier()

class Query:
    def __init__(self, storeIds, excludeIds, query, isURL, active):
        self.storeIds = storeIds
        self.excludeIds = excludeIds
        self.query = query
        self.isURL = isURL
        self.active = active

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
        parentContainer = soup.select_one("div[class=item-container]")
        promoElem = parentContainer.select_one('div > p[class=item-promo]')
        if promoElem != None:
            promoText = promoElem.text.strip().replace("\"", "").lower()
            outOfStock = promoText == "out of stock"

        if outOfStock:
            return "Out of stock"
        else: # otherwise we need to go to the product page itself and get the info there
            itemElem = soup.select_one('div[class=item-container] > div > a')
            if itemElem != None:
                url = itemElem["href"].replace(" ", "+")
                resp = session.get(url, headers=Globals.headers, timeout=settings["maxTimeout"])
                productSoup = BeautifulSoup(resp.text, 'html.parser')

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
            
        resp = session.post(url, json=data, headers=Globals.headers)
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

class BHPhotoVideo(Store):
    def getItemName(self, soup):
        productElem = soup.select_one("span[data-selenium=miniProductPageProductName]")
        if productElem == None:
            return "Error"
        else:
            return productElem.text.strip()

    def getItemNameDirect(self, soup):
        productElem = soup.select_one("h1[data-selenium=productTitle]")
        if productElem == None:
            return "Error"
        else:
            return productElem.text.strip()

    def getStock(self, soup, session):
        ### method 1: direct stock (sometimes you can still buy even though it is techically out of stock, so this method isn't the best)
        #statusElem = soup.select_one('span[data-selenium=stockStatus]')
        #if statusElem == None:
        #   return "Error"
        #else:
        #   statusText = statusElem.text.strip()
        #   if statusText == "In Stock":
        #       return "In stock"
        #   else:
        #       return "Out of stock"

        ### method 2: look for "add to cart" button
        parentElem = soup.select_one('div[data-selenium=miniProductPageQuantityContainer]')
        if parentElem == None:
           return "Error"
        else:
            buttonElem = parentElem.select_one("button[data-selenium=addToCartButton]")
            if buttonElem == None:
                return "Out of stock"
            else:
                return "In stock"

    def getStockDirect(self, soup, session):
        ### method 2: look for "add to cart" button
        parentElem = soup.select_one('div[data-selenium=addToCartSection]')
        if parentElem == None:
           return "Error"
        else:
            buttonElem = parentElem.select_one("button[data-selenium=addToCartButton]")
            if buttonElem == None:
                return "Out of stock"
            else:
                return "In stock"

class Amazon(Store):
    def getSearchedItemRoot(self, soup):
        foundElements = soup.select("span[class='celwidget slot=MAIN template=SEARCH_RESULTS widgetId=search-results']")
        actualElement = None
        for i in range(0, len(foundElements)):
            if foundElements[i].select_one("div[data-component-type='sp-sponsored-result']") == None:
                return foundElements[i]

    def getNameElement(self, soup):
        productRoot = self.getSearchedItemRoot(soup)
        if productRoot == None:
            return None
        else:
            return productRoot.select_one("span[class~='a-text-normal']")

    def getItemName(self, soup):
        textElem = self.getNameElement(soup)
        if textElem == None:
            return "Error"
        else:
            return textElem.text.strip()

    def getItemNameDirect(self, soup):
        productElem = soup.select_one("span[id=productTitle]")
        if productElem == None:
            return "Error"
        else:
            return productElem.text.strip()

    def getStock(self, soup, session):
        # we need to go to the product page itself and get the info there
        textElem = self.getNameElement(soup)
        if textElem == None:
            return "Error"
        else:
            url = "https://amazon.com" + textElem.parent["href"].replace(" ", "+")
            resp = session.get(url, headers=Globals.headers, timeout=settings["maxTimeout"])
            productSoup = BeautifulSoup(resp.text, 'html.parser')
            return self.getStockDirect(productSoup, session)

    def getStockDirect(self, soup, session):
        rightColumn = soup.select_one("div[id=rightCol]")
        if rightColumn == None:
            return "Error"
        else:
            buttonElem = rightColumn.select_one("input[id=add-to-cart-button]")
            if buttonElem == None:
                availabilityElem = soup.select_one("div[id=availability]")
                if availabilityElem == None or "available " not in availabilityElem.text.lower():
                    return "Out of stock"
                else:
                    return "In stock"
            else:
                return "In stock"

stores = []
stores.append(Microcenter(len(stores), "Microcenter", "https://www.microcenter.com/search/search_results.aspx?Ntt="))
stores.append(Newegg(len(stores), "Newegg", "https://www.newegg.com/p/pl?d="))
stores.append(Bestbuy(len(stores), "Bestbuy", "https://www.bestbuy.com/site/searchpage.jsp?sc=Global&usc=All+Categories&st="))
stores.append(BHPhotoVideo(len(stores), "B&H", "https://www.bhphotovideo.com/c/search?Ntt="))
stores.append(Amazon(len(stores), "Amazon", "https://www.amazon.com/s?k="))

queryList = []
#queryList.append(Query([4], [], "https://www.amazon.com/PNY-GeForce-Gaming-Uprising-Graphics/dp/B08HBF5L3K?ref_=ast_sto_dp", True, True))
#queryList.append(Query([2], [], "https://www.bestbuy.com/site/nvidia-geforce-rtx-nvlink-bridge-for-30-series-products-space-gray/6441554.p?skuId=6441554", True, True))

queryFile = open("data/Queries.txt", "r")
queryObj = json.loads(queryFile.read())["queries"]
for elem in queryObj:
    newQuery = Query([], [], elem["queryString"], elem["isURL"], elem["active"])
    for storeName in elem["storeNames"]:
        for i in range(0, len(stores)):
            if stores[i].name.lower() in storeName.lower():
                if len(storeName) > 0 and storeName[0] == '!':
                    newQuery.excludeIds.append(i)
                else:
                    newQuery.storeIds.append(i)
    queryList.append(newQuery)
queryFile.close()

iteration = 0

async def queryStock():
    if Globals.running:
        if iteration % settings["userAgentSwitchCycles"] == 0:
            Globals.switchUserAgent()

        for query in queryList:
            if query.active:
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
                        searchingStores.extend([i for i in range(0, len(stores)) if i not in query.excludeIds])

                for storeId in searchingStores:
                    store = stores[storeId]

                    url = searchQuery
                    if not query.isURL:
                        url = store.searchURL + url

                    session = requests.Session()
                    soup = None
                    try:
                        resp = session.get(url, headers=Globals.headers, timeout=settings["maxTimeout"])
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
    Logging.logWithTimestamp("Notice: Commands will not register until after a cycle has been completed", Fore.YELLOW)
    if settings["notifyOnDiscord"]:
        await DiscordIntegration.client.wait_until_ready()
        await DiscordIntegration.init_users()
        while not DiscordIntegration.client.is_closed():
            handle_input()
            await queryStock()
            handle_input()
            iteration += 1
            await sleep(settings["sleepDelay"])
    else:
        while True:
            handle_input()
            await queryStock()
            handle_input()
            iteration += 1
            await sleep(settings["sleepDelay"])

Globals.inputThread = Thread(target = async_input)
Globals.inputThread.daemon = True
Globals.inputThread.start()

if settings["notifyOnDiscord"]:
    DiscordIntegration.init_discord(main)
else:
    run(main())