from typing import Dict
import requests, json
from requests.models import Response
from requests.sessions import Session
from requests.exceptions import HTTPError

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
    splitContentType = res.headers.get('content-type').split(";")
    if (splitContentType[0] == 'application/json'):
        print("####### RESPONSE CONTENT #######")
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

def clean(d: Dict):
    keys_to_be_deleted = [
        "contractSize",
        "productTypeId",
        "tradable",
        "exchangeId",
        "onlyEodPrices",
        "orderTimeTypes",
        "buyOrderTypes",
        "sellOrderTypes",
        "productBitTypes",
        "feedQuality",
        "orderBookDepth",
        "vwdIdentifierType",
        "vwdId",
        "qualitySwitchable",
        "qualitySwitchFree",
        "orderBookDepth",
        "vwdModuleId",
        "feedQualitySecondary",
        "orderBookDepthSecondary",
        "qualitySwitchableSecondary",
        "qualitySwitchFreeSecondary",
        "vwdModuleIdSecondary",
        "vwdIdentifierTypeSecondary",
        "vwdIdSecondary",
        "category",
        "closePrice",
        "closePriceDate"
        ]
   
    positionsToDrop = []
    for key, value in d.items():
        # remove old positions returned by degiro
        if (value['size'] == 0.0):
            positionsToDrop.append(key)
            continue
        for key in keys_to_be_deleted:
            try:
                # remove the above specified key/value pairs
                del value[key]
            except KeyError:
                continue

    for key in positionsToDrop:
        del d[key]

    return d

def parseHoldings(data: Dict, portfolio: Dict): # res: Response, 
        holdingsDict = data.get("data")
        return clean(mergeDicts(holdingsDict, portfolio))
        

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

def scrape():
    try:
        with requests.Session() as session:
            request_headers = {
                'Host': 'trader.degiro.nl',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
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
            _ = parseResponse(res, session)

            res = session.get(f'{BASE_URL}/pa/secure/client?sessionId={sessionID}')
            checkError(res)
            account_data = parseResponse(res, session)
            intAccount = account_data.get("data").get('intAccount')

            params = '&portfolio=0'
            res = session.get(f'{BASE_URL}/trading/secure/v5/update/{intAccount};jsessionid={sessionID}?{params}')
            checkError(res)
            response_data = parseResponse(res, session)
            productIDs, portfolio_dict = parsePortfolio(response_data)

            session.headers.update({'referer': 'https://trader.degiro.nl/trader/'})
            
            res = session.post(f'{BASE_URL}/product_search/secure/v5/products/info?intAccount={intAccount}&sessionId={sessionID}', json=productIDs)
            checkError(res)
            response_data = parseResponse(res, session)
            holdings = parseHoldings(response_data, portfolio_dict)
            print(json.dumps(holdings, indent=2))
            return holdings
    except Exception:
        raise

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
