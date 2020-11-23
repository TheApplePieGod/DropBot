from bs4 import BeautifulSoup
from urllib import request, error, parse
import re
import json
import requests
from win10toast import ToastNotifier

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

toaster = ToastNotifier()

class Store:
    def __init__(self, id, name, searchURL):
        self.id = id
        self.name = name
        self.searchURL = searchURL

    def getItemName(self, soup):
        raise NotImplementedError("Store subclass must override this method")

    def getStock(self, soup, session):
        raise NotImplementedError("Store subclass must override this method")

class Microcenter(Store):
    def getItemName(self, soup):
        productElem = soup.select_one("a[data-name]")
        if productElem == None:
            return "Not found"
        else:
            return productElem["data-name"]

    def getStock(self, soup, session):
        stockElem = soup.select_one('div[class="stock"]')
        if stockElem != None:
            return stockElem.text.strip()
        else:
            return "Not found"

class Newegg(Store):
    def getItemName(self, soup):
        productElem = soup.select_one("div[class=item-container] > div > a")
        if productElem == None:
            return "Not found"
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

                stockElem = productSoup.select_one("div[class=product-inventory] > strong")
                if stockElem != None:
                    return stockElem.text.strip().replace(".", "")
                else:
                    return "Not found"
            else:
                return "Not found"

class Bestbuy(Store):
    def __init__(self, id, name, searchURL):
        super().__init__(id, name, searchURL)
        self.session = requests.Session()

    def getItemName(self, soup):
        productElem = soup.select_one("h4[class=sku-header] > a")
        if productElem == None:
            return "Not found"
        else:
            return productElem.text.strip()

    def getStock(self, soup, session):
        valueElements = soup.select("div[class=sku-attribute-title] > span[class=sku-value]")
        if valueElements == None or len(valueElements) < 2:
            return "Not found"
        else: # post to their stock api to get info
            skuVal = valueElements[1].text.strip()
            url = "https://www.bestbuy.com/fulfillment/ispu/api/ispu/v2"
            data = { "channel":"Ecommerce", "checkRetailAvailability":True, "lookupInStoreQuantity":True, "requestInfos": [{ "additionalLocationIds": [], "condition": None, "itemSeqNumber": "1", "locationId": "0", "sku": skuVal }], "searchNearby":False }
            
            resp = session.post(url, json=data, headers=headers)
            obj = json.loads(resp.text)

            return "In stock" if obj["responseInfos"][0]["pickupEligible"] else "Out of stock"

stores = []
stores.append(Microcenter(0, "Microcenter", "https://www.microcenter.com/search/search_results.aspx?Ntt="))
stores.append(Newegg(1, "Newegg", "https://www.newegg.com/p/pl?d="))
stores.append(Bestbuy(2, "Bestbuy", "https://www.bestbuy.com/site/searchpage.jsp?sc=Global&usc=All+Categories&st="))

#queryList = ["PlayStation 5 Console", "GeForce RTX 3070", "Bose QuietComfort 35 II"]
queryList = ["GeForce RTX 3070 Card"]

def queryStock():
    global stores
    global queryList

    for query in queryList:
        print("Results for: " + query)
        for store in stores:
            print("\nFetching " + store.name + "...")

            url = store.searchURL + query.replace(" ", "+")

            session = requests.Session()
            resp = session.get(url, headers=headers)
            soup = BeautifulSoup(resp.text, 'html.parser')

            print(store.name + " found:")
            print(store.getItemName(soup))
            print("Stock status: " + store.getStock(soup, session))
            session.close()
        print("\n\n\n")


queryStock()