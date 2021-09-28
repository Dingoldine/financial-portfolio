from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from helpermodules import Utils
from scrapers._scraping_functions import clickElement, waitforload
import constants
import json
from seleniumwire.utils import decode



def _get_portfolio(browser):
    try:
        browser.get("https://www.avanza.se/min-ekonomi/innehav.html")
        request = browser.wait_for_request('.*positions$', 20)

        response = request.response

        response_body = decode(response.body, response.headers.get('Content-Encoding', 'identity'))
        
        data = json.loads(response_body)

        return parseAvanzaHoldings(data)

    except Exception as e:
        Utils.log_error(e)
        raise

    finally:
        browser.quit()
        
def parseAvanzaHoldings(holdings):

    asset_dict = {}
    response = dict(holdings)
    
    for entry in response.get("withOrderbook"):

        asset_dict[entry["instrument"]['isin']] = {
            'asset': entry["instrument"]['name'],
            'type': entry["instrument"]['type'],
            'isin': entry["instrument"]['isin'],
            'currency': entry["instrument"]['currency'],
            'price': entry["instrument"]['orderbook']['quote']['latest']['value'],
            'shares':  entry['volume']['value'],
            'value': entry['value']['value'],
            'acquired_value': entry['acquiredValue']['value']
        }
    
    totalBalanceSEK = 0
    for position in response.get('cashPositions'):
        
        totalBalanceSEK += position['totalBalance']['value'] if position['totalBalance']['unit'] == 'SEK' else 0
    
    asset_dict['CASH'] = {
        'asset': 'Cash',
        'type': 'CASH',
        'value': totalBalanceSEK,
        'acquired_value': totalBalanceSEK,
        'currency': 'SEK',
    }

    return asset_dict


def _loginToAvanza(url, dbModel):
    """Function that log in to Avanza, returns selenium driver object"""
    try:
        opt = webdriver.FirefoxOptions()
        fp = webdriver.FirefoxProfile()
        fp.set_preference('browser.cache.disk.parent_directory', '/usr/')
        opt.add_argument('-headless')
        opt.add_argument('--disable-gpu')
        opt.profile = fp

        browser = None

        browser = webdriver.Firefox(
            options=opt, service_log_path=constants.GECKO_LOG_PATH, executable_path=constants.GECKO_EXECUTABLE_PATH)

        browser.implicitly_wait(0)

        browser.get(url)

        acceptCookiesButtonXPATH = "/html/body/aza-app/div/aza-cookie-message/div/div/button"

        loginButtonXPATH = "/html/body/aza-app/aza-right-overlay-area/aside/ng-component/aza-login-overlay/aza-right-overlay-template/main/aza-login/aza-toggle-switch-view/div/aza-bank-id/div[1]/button[1]"

        clickElement(browser, acceptCookiesButtonXPATH, 5)

        clickElement(browser, loginButtonXPATH, 5)

        # data:image/png;base64,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
        qrCodeElementXpath = "/html/body/aza-app/aza-right-overlay-area/aside/ng-component/aza-login-overlay/aza-right-overlay-template/\
            main/aza-login/aza-toggle-switch-view/div/aza-bank-id/div/aza-stack[2]/canvas"

        qrCodeElement = WebDriverWait(browser, 5).until(
            EC.presence_of_element_located((By.XPATH, qrCodeElementXpath))
        )

        # get the canvas as a PNG base64 string
        canvasDataURL = browser.execute_script(
            "return arguments[0].toDataURL('image/png');", qrCodeElement)
        dbModel.store_qr_code(canvasDataURL)

        waitforload(browser, 30)

        return browser
    except Exception as e:
        Utils.log_error(e)
        if browser is not None:
            browser.quit()
        raise

def scrape(dbModel) -> dict:
    login_url = 'https://www.avanza.se/start(right-overlay:login/login-overlay)'
    browser = _loginToAvanza(login_url, dbModel)
    return  _get_portfolio(browser)

    # return json.loads(open("./scrapers/avanza_holdings.json").read())

