from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from helpermodules import Utils
from scrapers._scraping_functions import clickElement, waitforload
import constants
import pandas as pd
import re


def _parseTable(table):
    n_rows = 0
    column_names = []
    rows = []

    # Find number of rows and columns
    # we also find the column titles if we can
    for row in table.find_all('tr'):
        # Determine the number of rows in the table
        entry = []

        td_tags = row.find_all('td')
        if len(td_tags) > 0:
            n_rows += 1

        for td in td_tags:
            inner_links = td.find_all('a')
            if (len(inner_links) > 0):
                for a in inner_links:
                    if (a.text.strip() == "" or a.text.strip() == "Superräntan" or td.text.strip() == "Köp"):
                        pass
                    else:
                        entry.append(" ".join(a.text.split()))
            else:
                if (td.text.strip() == "" or td.text.strip() == "Superräntan" or td.text.strip() == "Köp"):
                    pass
                else:
                    # number Values
                    no_whitespace_string = re.sub(r'\s+', '', td.text.strip())

                    other_comma_representation_string = no_whitespace_string.replace(
                        ",", ".")

                    entry.append(other_comma_representation_string)

        # Handle column names if we find them
        th_tags = row.find_all('th')
        if len(th_tags) > 0 and len(column_names) == 0:
            for th in th_tags:
                column_names.append(th.text.strip())

        # append instrument data to list
        if len(entry) > 0:
            rows.append(entry)

    return column_names, rows


def _parseHTML(data):
    try:
        soup = BeautifulSoup(data, 'lxml')

        tables = soup.find_all("table", {"class": "tableV2"})

        dataframes = {}
        # we only care about the first 4 tables
        for table in tables[:4]:
            captionTag = table.find('h2')
            # only parse if they have a caption
            if(captionTag != None):
                caption = captionTag.text.strip()
                headers, rows = _parseTable(table)
                df, err = _buildDataframe(headers, rows, caption)
                if(err):
                    continue
                dataframes.update({df.name: df.to_json(orient='index')})

        return dataframes

    except Exception as e:
        Utils.log_error(e)


def _buildDataframe(headers, rows, caption):
    unnecessary_columns = ['+/- %', 'Konto', 'Tid']
    new_column_names = ['Asset', 'Shares', 'Latest Price', 'Purchase Price',
                        'Market Value (SEK)', 'Change', 'Profit', 'Currency']

    def stocks(headers, rows):
        # cleanup headers
        del headers[-1]  # remove "verktyg"
        del headers[0]  # remove buy/sell
        # cleanup rows
        _ = rows.pop(0)  # no need for summary row
        for row in rows:
            del row[0]  # remove buy
            del row[0]  # remove sell
        df = pd.DataFrame.from_records(rows, columns=headers)
        df.name = "Stocks"
        df["Currency"] = "SEK"
        df.drop(unnecessary_columns, axis=1, inplace=True)
        df.columns = new_column_names
        return(df)

    def funds(headers, rows):
        # cleanup headers
        del headers[-1]  # remove "verktyg"
        del headers[0]  # remove buy/sell
        # cleanup rows

        _ = rows.pop(0)  # no need for buy all funds row
        _ = rows.pop(0)  # no need for summary row
        for row in rows:
            del row[0]  # remove buy
            del row[0]  # rm sell
            del row[0]  # rm byt
        df = pd.DataFrame.from_records(rows, columns=headers)
        df.name = "Funds"
        df["Currency"] = "SEK"
        df.drop(unnecessary_columns, axis=1, inplace=True)
        df.columns = new_column_names
        return(df)

    def etfs(headers, rows):
        # cleanup headers
        del headers[-1]  # remove "verktyg"
        del headers[0]  # remove buy/sell
        # cleanup rows
        _ = rows.pop(0)  # no need for summary row
        for row in rows:
            # del row[0]  #remove buy
            del row[0]  # rm sell

        df = pd.DataFrame.from_records(rows, columns=headers)
        df["Currency"] = "SEK"
        df.name = "ETFs"
        df.drop(unnecessary_columns, axis=1, inplace=True)
        df.columns = new_column_names
        return df

    def cert(headers, rows):
        # cleanup headers
        del headers[-1]  # remove "verktyg"
        del headers[0]  # remove buy/sell
        # cleanup rows
        _ = rows.pop(0)  # no need for summary row
        for row in rows:
            del row[0]  # remove buy
            del row[0]  # rm sell
        df = pd.DataFrame.from_records(rows, columns=headers)
        df["Currency"] = "SEK"
        df.name = "Certificates"
        df.drop(unnecessary_columns, axis=1, inplace=True)
        df.columns = new_column_names
        return(df)

    def summary(headers, rows):
        flat_list = []
        for index, row in enumerate(rows):
            header = row.pop(0)
            if index == 1:
                header = header + ' %'
            if index == 3:
                header = header + ' %'
            headers.append(header)

            flat_list.append(row[0].strip("%").strip())
        data_list = []
        data_list.append(flat_list)
        df = pd.DataFrame.from_records(data=data_list, columns=headers)
        df.name = "Portfolio Summary"
        return(df)

    switcher = {
        'Aktier': stocks,
        'Fonder': funds,
        2: etfs,
        'Certifikat': cert,
        'Summary': summary,
    }

    function = switcher.get(caption, "Invalid value")
    if (function == 'Invalid value'):
        return None, True

    df = function(headers, rows)
    return df, None


def _get_fund_details(browser):
    # wait for table to load
    fundTableXPATH = "//table[contains(@class, 'groupInstTypeTable')][2]"
    _ = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.XPATH, fundTableXPATH))
    )

    # find all fund links
    allLinksXPATH = "//table[contains(@class, 'groupInstTypeTable')][2]// \
        *[contains(@class, 'instrumentName')]//*[contains(@class, 'ellipsis')]/a"
    instrumentlinks = browser.find_elements(By.XPATH, allLinksXPATH)
    fundDictionary = {}
    for link in instrumentlinks:
        fundDictionary[link.text.strip()] = link.get_attribute('href')

    # navigate to each fund and get fund info
    for instrument, href in fundDictionary.items():
        print(instrument)
        browser.get(href)

        fundDetailsButtonXPATH = '/html/body/aza-app/div/main/div/aza-fund-guide/aza-subpage/div/div/ \
            div/div[2]/div[1]/aza-card[2]/div/div[1]/aza-toggle-switch/aza-toggle-option[3]/button'

        clickElement(browser, fundDetailsButtonXPATH, 5, extraWaitTime=3)

        # wait for fund details to load
        fundDetailsBoxXPATH = '/html/body/aza-app/div/main/div/aza-fund-guide/ \
            aza-subpage/div/div/div/div[2]/div[1]/aza-card[2]/div/div[2]/div'
        _ = WebDriverWait(browser, 60).until(
            EC.visibility_of_element_located(
                (By.XPATH, fundDetailsBoxXPATH))
        )

        html = BeautifulSoup(browser.page_source, 'lxml')
        # store page content
        fundDictionary.update({instrument: str(html)})

    # go back
    browser.execute_script(f'window.history.go(-{len(fundDictionary)})')

    return fundDictionary


def _get_portfolio(browser):
    """Saves a txt file of all fund detail pages and returns portfolio view html """

    try:
        browser.get(
            "https://www.avanza.se/min-ekonomi/innehav/innehav-old.html")

        # wait for javascript to load then scrape--
        waitforload(browser, 20)
        soup = BeautifulSoup(browser.page_source, 'lxml')

        return str(soup.prettify())

    except Exception as e:
        Utils.log_error(e)
        raise

    finally:
        browser.quit()


def _loginToAvanza(url, dbModel):
    """Function that log in to Avanza, returns selenium driver object"""
    try:
        opt = webdriver.FirefoxOptions()
        fp = webdriver.FirefoxProfile()

        opt.add_argument('-headless')
        opt.profile = fp

        browser = webdriver.Firefox(
            options=opt, service_log_path=constants.GECKO_LOG_PATH, executable_path=constants.GECKO_EXECUTABLE_PATH)
        # poll for elements for --  seconds max, before shutdown
        browser.implicitly_wait(0)
        wait = WebDriverWait(browser, 60)

        browser.get(url)

        acceptCookiesButtonXPATH = "/html/body/aza-app/div/aza-cookie-message/div/div[1]/div/button"

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

        # wait until logged in view found
        sideMenuXPATH = "/html/body/aza-app/div/aza-personal-menu/div/nav"
        wait.until(EC.presence_of_element_located((By.XPATH, sideMenuXPATH)))

        return browser
    except Exception as e:
        Utils.log_error(e)
        browser.quit()
        raise

def scrape(dbModel):

    login_url = 'https://www.avanza.se/start(right-overlay:login/login-overlay)'

    # login and get new data
    browser = _loginToAvanza(login_url, dbModel)

    html = _get_portfolio(browser)

    dataframes = _parseHTML(html)

    return dataframes
