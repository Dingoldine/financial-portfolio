from typing import Dict
import requests, json
from requests.models import Response
from requests.sessions import Session
from requests.exceptions import HTTPError
import configparser, os

BASE_URL =  "https://trader.degiro.nl"
Config = configparser.ConfigParser()

Config.read('config.ini')

USERNAME = Config["DEGIRO"]["username"]
PASSWORD = Config["DEGIRO"]["password"]

def parseResponse(res: Response, s: Session):
    print("####### COOKIES #######")
    print(json.dumps(s.cookies.get_dict(), indent=2))
    print("####### RESPONSE HEADERS #######")
    print(json.dumps(dict(res.headers), indent=2))
    print("####### RESPONSE CONTENT #######")
    splitContentType = res.headers.get('content-type').split(";")
    if (splitContentType[0] == 'application/json'):
        data = eval(res.text.replace('true', 'True').replace('false', 'False'))
        print(json.dumps(data, indent=2))
        return data
    else:
        return {}

def checkError(res: Response):
    if not (res.status_code == 200):
        print(f'REQUEST ERROR: \n Code {res.status_code},\nReason: \n {res.reason}')
        raise HTTPError

def printSession(s: Session):
    print(json.dumps(dict(s.headers), indent=2))

def extractSessionID(s: Session):
    return s.cookies.get_dict().get('JSESSIONID')

# def extractAccountInfo(res: Response):
#     https://trader.degiro.nl/trading/secure/v5/account/info/121008181;jsessionid=5E4877BF0E02E8F8CD70AC15F3DDFE67.prod_b_114_1

def extractAccountID(res: Response):
    return '121008181'

def parseHoldings(data: Dict, portfolio: Dict): # res: Response, 
        holdingsDict = data.get("data")
        return mergeDicts(holdingsDict, portfolio)
        

def parsePortfolio(data: Dict):
    positionsDict = {}
    interestingFields = ["value", "size", "price", "breakEvenPrice"]
    for position in data.get("portfolio").get("value"):
        fieldDict = {}
        for field in position.get("value"):
            fieldKey = field.get("name") 
            if fieldKey in interestingFields:
                val = field.get("value")
                fieldDict.update({fieldKey: val})
        positionsDict.update({position.get("id"): fieldDict})
    
    d = {k: v for k, v in positionsDict.items() if k.isdigit()}

    return list(d.keys()), positionsDict

def scrapeLIVE():
    with requests.Session() as session:
        request_headers = {
            'Host': 'trader.degiro.nl',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
            # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            # 'Referer': 'https://trader.degiro.nl/login/se',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive'
        }

        session.headers.update(request_headers)

        print(json.dumps(session.cookies.get_dict(), indent=2))
        
        res = session.get(f'{BASE_URL}/login/se' , headers=request_headers)
        checkError(res)
        _ = parseResponse(res, session)

        session.headers.update({'Origin': 'https://trader.degiro.nl'})
        
        res = session.post(BASE_URL + "/login/secure/login", json={"username": USERNAME,"password": PASSWORD,"queryParams":{}})
        checkError(res)
        _ = parseResponse(res, session)

        sessionID = extractSessionID(session)

        res = session.get(f'{BASE_URL}/pa/secure/client?sessionId={sessionID}')
        checkError(res)
        parseResponse(res, session)

        res = session.get(f'{BASE_URL}/pa/secure/client?sessionId={sessionID}')
        checkError(res)
        _ = parseResponse(res, session)
        intAccount = extractAccountID(res)
        params = '&portfolio=0'
        
        res = session.get(f'{BASE_URL}/trading/secure/v5/update/{intAccount};jsessionid={sessionID}?{params}')
        checkError(res)
        response_data = parseResponse(res, session)
        productIDs, portfolio_dict = parsePortfolio(response_data)

        session.headers.update({'referer': 'https://trader.degiro.nl/trader/'})
           
        #session.post(f'{BASE_URL}/v5/products/info?intAccount={intAccount}&sessionId={sessionID}')
        #print(brotli.decompress(res.content))

        res = session.post(f'{BASE_URL}/product_search/secure/v5/products/info?intAccount={intAccount}&sessionId={sessionID}', json=productIDs)
        checkError(res)
        response_data = parseResponse(res, session)
        holdings = parseHoldings(response_data, portfolio_dict)
        print(json.dumps(holdings, indent=2))

def mergeDicts(d1: Dict, d2: Dict):
    d3 = {}
    for k in set(d1.keys()).union(d2.keys()):

        if (k in d1 and k in d2):
            if isinstance(d1[k], dict) and isinstance(d2[k], dict): #if value is a dict in both at key k
                merged = d1[k] | d2[k]
                d3.update({k: merged})
        else:
            if k in d1.keys(): d3.update({k: d1[k]})
            elif k in d2.keys(): d3.update({k: d2[k]})
    return d3


def scrapeTEST():
    with open(os.path.join(os.getcwd(), 'portfolioResponse.json'), "r") as file:
        portfolioList = eval(file.read().replace('true', 'True').replace('false', 'False')).get("portfolio").get("value")
        positionsDict = {}
        interestingFields = ["value", "size", "price", "breakEvenPrice"]
        for position in portfolioList:
            fieldDict = {}
            for field in position.get("value"):
                fieldKey = field.get("name") 
                if fieldKey in interestingFields:
                    val = field.get("value")
                    fieldDict.update({fieldKey: val})
            positionsDict.update({position.get("id"): fieldDict})



        with open(os.path.join(os.getcwd(), 'requestResponse.txt'), 'r') as secondFile:
            stockHoldings = eval(secondFile.read().replace('true', 'True').replace('false', 'False')).get('data')
            return mergeDicts(stockHoldings, positionsDict)

