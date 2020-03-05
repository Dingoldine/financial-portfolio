from bs4 import BeautifulSoup
from selenium import webdriver
#from selenium.webdriver import Firefox
#from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from modules import Excel, Utils

import time
import inspect
import logging
import numpy as np
import csv
import pandas as pd
import re
from Portfolio import Portfolio
import sys, os
myself = lambda: inspect.stack()[1][3]


def parseTable(table):

    n_rows=0
    column_names = []
    rows = []

    # Find number of rows and columns
    # we also find the column titles if we can
    for row in table.find_all('tr'):
        #print(row)
        # Determine the number of rows in the table
        entry = []

        td_tags = row.find_all('td')
        if len(td_tags) > 0:
            n_rows+=1
        
        for td in td_tags:
            inner_links = td.find_all('a')
            if (len(inner_links) > 0):
                for a in inner_links:
                    if (a.text.strip() == "" or a.text.strip() == "Superräntan" or td.text.strip() == "Köp"):
                        pass
                    else:
                        #print(a.text.strip())
                        entry.append(" ".join(a.text.split()))
            else:
                if (td.text.strip() == "" or td.text.strip() == "Superräntan" or td.text.strip() == "Köp"):
                    pass
                else:
                    # number Values 
                    no_whitespace_string = re.sub(r'\s+', '', td.text.strip())
                        
                    other_comma_representation_string = no_whitespace_string.replace(",", ".")

                    entry.append(other_comma_representation_string)
            
        # Handle column names if we find them
        th_tags = row.find_all('th') 
        if len(th_tags) > 0 and len(column_names) == 0:
            for th in th_tags:
                column_names.append(th.text.strip())
       
        #append instrument data to list
        if len(entry) > 0:
            rows.append(entry)

    return column_names, rows

def parseHTML(data):
    try:
        soup  = BeautifulSoup(data, 'lxml')

        tables = soup.find_all("table", {"class": "tableV2"})
        
        dataframes = []
        # we only care about the first 4 tables
        for table in tables[:4]:
            captionTag = table.find('h2')
            # only parse if they have a caption
            if(captionTag != None):
                caption = captionTag.text.strip()
                #print(table.prettify())
                headers, rows = parseTable(table)
                df, err = buildDataframe(headers, rows, caption) 
                #Utils.printDf(df)f
                if(err):
                    continue
                dataframes.append(df)

        return dataframes

    except Exception as e:
        print("Something went wrong in " + myself())
        log_error(e)


def buildDataframe(headers, rows, caption):
    print(caption)

    def stocks(headers, rows):
        #cleanup headers
        del headers[-1] #remove "verktyg"
        del headers[0] #remove buy/sell
        #cleanup rows
        _ = rows.pop(0) #no need for summary row
        for row in rows:
            del row[0] #remove buy 
            del row[0] #remove sell
        df = pd.DataFrame.from_records(rows, columns=headers)
        df.name = "Stocks"
        return(df)

    def funds(headers, rows):
        #cleanup headers
        del headers[-1] #remove "verktyg"
        del headers[0] #remove buy/sell
        #cleanup rows
        
        _ = rows.pop(0) #no need for buy all funds row
        _ = rows.pop(0) #no need for summary row
        for row in rows:
            
            del row[0]  #remove buy
            del row[0]  #rm sell
            del row[0]  #rm byt
        df = pd.DataFrame.from_records(rows, columns=headers)
        df.name = "Funds"
        return(df)

    def etfs(headers, rows):
        #cleanup headers
        del headers[-1] #remove "verktyg"
        del headers[0] #remove buy/sell
        #cleanup rows
        _ = rows.pop(0) #no need for summary row
        for row in rows:
            # del row[0]  #remove buy
            del row[0]  #rm sell
            pass

        df = pd.DataFrame.from_records(rows, columns=headers)
        df.name = "ETFs"
        return(df)

    def cert(headers, rows):
        #cleanup headers
        del headers[-1] #remove "verktyg"
        del headers[0] #remove buy/sell
        #cleanup rows
        _ = rows.pop(0) #no need for summary row
        for row in rows:
            del row[0]  #remove buy
            del row[0]  #rm sell
        df = pd.DataFrame.from_records(rows, columns=headers)
        df.name = "Certificates"
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
    if (function=='Invalid value'):
        return None, True
    
    df = function(headers, rows)
    return df, None

def log_error(e):
    """
    It is always a good idea to log errors. 
    This function just prints them, but you can
    make it do anything.
    """
    logging.exception("message")

def get_portfolio(browser):
   
    portfolioViewLinkXPATH = "/html/body/aza-app/div/main/div/aza-feed-latest/aza-base-page/div/ \
    aza-pull-to-refresh/div/div[2]/aza-page-container/div/div[1]/ \
    aza-feed-development/aza-card/section[5]/a"

    try:
        # go to instruments page
        portfolio_view = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, portfolioViewLinkXPATH))
        )
        portfolio_view.click()

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
            fundDetailsButton = WebDriverWait(browser, 10).until(
                EC.element_to_be_clickable((By.XPATH, fundDetailsButtonXPATH))
            )
            #extra wait for safety
            time.sleep(1)
            fundDetailsButton.click()

            fundDetailsBoxXPATH = '/html/body/aza-app/div/main/div/aza-fund-guide/ \
            aza-subpage/div/div/div/div[2]/div[1]/aza-card[2]/div/div[2]/div'
            fundDetailsBox = WebDriverWait(browser, 60).until(
                EC.visibility_of_element_located((By.XPATH, fundDetailsBoxXPATH))
            )
            # extra wait
            time.sleep(1)
            html = BeautifulSoup(browser.page_source, 'lxml')

            Utils.saveTxtFile(str(html.prettify()), instrument)
            # print(fundDetailsBox.text)
            # fundDetails = fundDetailsBox.get_attribute('innerHTML')
           
            # allocationInfoXPATH = '/html/body/aza-app/div/main/div/aza-fund-guide/aza-subpage/div/div/div/aza-card'

            # allocationInfoElement = WebDriverWait(browser, 10).until(
            #     EC.visibility_of_element_located((By.XPATH, allocationInfoXPATH))
            # )
            # print(allocationInfoElement.text)

            # allocationInfo = allocationInfoElement.get_attribute('innerHTML')
           

            # totalFeeXPATH = '/html/body/aza-app/div/main/div/aza-fund-guide/aza-subpage/div/div/div/div[2]/div[2]/aza-card[1]/div/h3'
            
            # feeElement = WebDriverWait(browser, 10).until(
            #     EC.visibility_of_element_located((By.XPATH, totalFeeXPATH))
            # )
            # fee = feeElement.text
            # print(fee)
            # fundDictionary[instrument] = [fundDetails, allocationInfo, fee]
        #go back
        browser.execute_script(f'window.history.go(-{len(fundDictionary)})')
        
        #wait for javascipt to load then scrape
        time.sleep(5)
        soup  = BeautifulSoup(browser.page_source, 'lxml')
    
        return str(soup.prettify())

    except Exception as e:
        print("Something went wrong in " + myself() )
        log_error(e)
        return None

    finally:
        browser.quit()


def loginToAvanza(url, payload):
    
    opt = webdriver.FirefoxOptions()
    #opt.add_argument('-headless')
    waitingTime = 60
    log_path = os.path.abspath(os.getcwd()) + '/geckodriver/geckodriver.log'
    browser = webdriver.Firefox(options=opt, service_log_path=log_path)
    browser.implicitly_wait(waitingTime)

    browser.get(url)

    headerLoginButtonXPATH = "/html/body/aza-app/div/div/aza-header/div/aza-header-login/button"
    
    inputfieldXPATH = "/html/body/aza-app/aza-right-overlay-area/aside/ng-component/ \
    aza-login-overlay/aza-right-overlay-template/div[2]/div/aza-login/div/ \
    aza-toggle-switch-view/div/aza-bank-id/form/div[1]/div[2]/input"

    loginButtonXPATH = "/html/body/aza-app/aza-right-overlay-area/aside/ng-component/ \
    aza-login-overlay/aza-right-overlay-template/div[2]/div/aza-login/div/ \
    aza-toggle-switch-view/div/aza-bank-id/form/div[1]/div[2]/button[1]"
    time.sleep(2)
    try:
        headerLogin =  WebDriverWait(browser, waitingTime).until(
            EC.presence_of_element_located((By.XPATH, headerLoginButtonXPATH))
        )

        headerLogin.click()

        username = WebDriverWait(browser, waitingTime).until(
            EC.presence_of_element_located((By.XPATH, inputfieldXPATH))
        )
        
        username.send_keys(payload.get("pid"))
        
        login = WebDriverWait(browser, waitingTime).until(
            EC.presence_of_element_located((By.XPATH, loginButtonXPATH))
        )

        login.click()

        return browser

    except Exception as e:
        print("Something went wrong in" + myself())
        log_error(e)
        browser.quit()
        sys.exit(e)

        
def initiatePortfolio():
    # for pandas version >= 0.21.0
    saveLocation = os.path.abspath(os.getcwd()) + "/excel_files"
    df_map = pd.read_excel(f'{saveLocation}/portfolio.xlsx', sheet_name=None)
    stocks = df_map.get("Stocks", None)
    funds = df_map.get("Funds", None)
    etfs = df_map.get("ETFs", None)
    certif = df_map.get("Certificates", None)
    summary = df_map.get("Potfolio Summary", None)
    return Portfolio(stocks, funds, etfs, certif, summary)


if __name__ == '__main__':

    login_url = 'https://www.avanza.se/start/startsidan.html(right-overlay:login/login-overlay)'

    payload = {
	"pid": "199312013676", 
    }

    # login and get new data
    #browser = loginToAvanza(login_url, payload)

    #html = get_portfolio(browser)

    #Utils.saveTxtFile(html, 'htmlAvanza') 

    # use old data
    html = Utils.readTxtFile('htmlAvanza')


    
    # run 
    dataframes = parseHTML(html)

    Excel.create(dataframes, 'portfolio', 1) 
    
    portfolio = initiatePortfolio()
    portfolio.checkRules()
    portfolio.fundsBreakdown() 
    portfolio.scrapeNasdaq()
    portfolio.saveStockInfoToExcel()
    portfolio.readStockInfoFromExcel('Kindred Group')
