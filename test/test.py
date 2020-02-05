from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
import time, os

a = {
    '1. symbol': '7ST.FRK',
    '2. name': 'SolTech Energy Sweden AB (publ)',
    '3. type': 'Equity',
    '4. region': 'Frankfurt',
    '5. marketOpen': '08:00',
    '6. marketClose': '20:00',
    '7. timezone': 'UTC+01',
    '8. currency': 'EUR',
    '9. matchScore': '0.8077'
}

b = {
    'Global Quote': {
        '01. symbol': 'UNBA.FRK',
        '02. open': '5.0260',
        '03. high': '5.0260',
        '04. low': '5.0260',
        '05. price': '5.0260',
        '06. volume': '200',
        '07. latest trading day': '2019-12-11',
        '08. previous close': '5.0960',
        '09. change': '-0.0700',
        '10. change percent': '-1.3736%'
    }
}
def find_all_iframes(driver):
    iframes = driver.find_elements_by_xpath("//iframe")

    for index, iframe in enumerate(iframes):
        # Your sweet business logic applied to iframe goes here.
        print(iframe)
        driver.switch_to.frame(index)
        try: 
            elem = driver.find_element(By.XPATH, '/html/body/div[2]/div[2]/form/div[4]/div[2]/div/div/div[3]/div[2]/div[2]/table/tbody[2]/tr[2]/th')
            print(elem.get_attribute('innerHTML'))
        except NoSuchElementException:
            print('not found')
        driver.switch_to.parent_frame()

browser = webdriver.Firefox()
fi = "file://" + os.path.abspath(os.getcwd()) + "/text_files/EQT.html"
browser.get(fi)
time.sleep(3)
frame = browser.find_element(By.XPATH, '//*[@id="MorningstarIFrame"]')
print(frame)
browser.switch_to.frame(frame)
elem = browser.find_element(By.XPATH, '//*[@id="KeyRatiosProfitability"]')
print(elem.get_attribute('innerHTML'))
#find_all_iframes(browser)


