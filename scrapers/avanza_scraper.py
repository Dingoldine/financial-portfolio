from bs4 import BeautifulSoup
from selenium import webdriver
#from selenium.webdriver import Firefox
#from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from helpermodules import Excel, Utils
from scrapers._scraping_functions import waitforload, clickElement 
import constants

import time
import inspect
import logging
import numpy as np
import csv
import pandas as pd
import re
import sys, os



def _parseTable(table):

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

def _parseHTML(data):
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
                headers, rows = _parseTable(table)
                df, err = _buildDataframe(headers, rows, caption) 
                #Utils.printDf(df)f
                if(err):
                    continue
                dataframes.append(df)
        
        return dataframes

    except Exception as e:

        Utils.log_error(e)


def _buildDataframe(headers, rows, caption):
    print(caption)
    unnecessary_columns = ['+/- %', 'Konto', 'Senast', 'Tid']
    new_column_names = ['Asset', 'Amount', 'Purchase', 'Market Value', 'Change', 'Profit']
    
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
        df.drop(unnecessary_columns, axis=1, inplace=True)
        df.columns = new_column_names
        leftMostCol = df.columns.values[0]
        df.set_index(leftMostCol, inplace=True) # Turn this column to index
        Utils.printDf(df)
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
        df.drop(unnecessary_columns, axis=1, inplace=True)
        df.columns = new_column_names
        leftMostCol = df.columns.values[0]
        df.set_index(leftMostCol, inplace=True) # Turn this column to index
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
        df.drop(unnecessary_columns, axis=1, inplace=True)
        df.columns = new_column_names
        leftMostCol = df.columns.values[0]
        df.set_index(leftMostCol, inplace=True) # Turn this column to index
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
        df.drop(unnecessary_columns, axis=1, inplace=True)
        df.columns = new_column_names
        leftMostCol = df.columns.values[0]
        df.set_index(leftMostCol, inplace=True) # Turn this column to index
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


def _get_portfolio(browser):
    """Saves a txt file of all fund detail pages and returns portfolio view html """

    portfolioViewLinkXPATH = "/html/body/aza-app/div/main/div/aza-feed-latest/aza-base-page/div/ \
    aza-pull-to-refresh/div/div[2]/aza-page-container/div/div[1]/ \
    aza-feed-development/aza-card/section[5]/a"

    try:
        clickElement(browser, portfolioViewLinkXPATH, 5)
        
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

            clickElement(browser, fundDetailsButtonXPATH, 5)

            # wait for fund details to load
            fundDetailsBoxXPATH = '/html/body/aza-app/div/main/div/aza-fund-guide/ \
            aza-subpage/div/div/div/div[2]/div[1]/aza-card[2]/div/div[2]/div'
            _ = WebDriverWait(browser, 60).until(
                EC.visibility_of_element_located((By.XPATH, fundDetailsBoxXPATH))
            )
            
            html = BeautifulSoup(browser.page_source, 'lxml')

            Utils.saveTxtFile(str(html.prettify()), instrument)

        #go back
        browser.execute_script(f'window.history.go(-{len(fundDictionary)})')
        
        #wait for javascipt to load then scrape
        time.sleep(5)
        soup  = BeautifulSoup(browser.page_source, 'lxml')
    
        return str(soup.prettify())

    except Exception as e:
        Utils.log_error(e)
        sys.exit(e)

    finally:
        browser.quit()


def _loginToAvanza(url, payload):
    """Function that log in to Avanza, returns selenium driver object"""
    
    opt = webdriver.FirefoxOptions()
    #opt.add_argument('-headless')
    
    browser = webdriver.Firefox(options=opt, service_log_path=constants.GECKO_LOG_PATH)
    
    # poll for elements for --  seconds max, before shutdown
    browser.implicitly_wait(0)
    wait = WebDriverWait(browser, 35)

    browser.get(url)

    headerLoginButtonXPATH = "/html/body/aza-app/div/div/aza-header/div/aza-header-login/button"
    
    inputfieldXPATH = "/html/body/aza-app/aza-right-overlay-area/aside/ng-component/aza-login-overlay/\
        aza-right-overlay-template/main/div/aza-login/div/aza-toggle-switch-view/div/aza-bank-id/form/div[1]/div[2]/input"

    loginButtonXPATH = "/html/body/aza-app/aza-right-overlay-area/aside/ng-component/aza-login-overlay/\
        aza-right-overlay-template/main/div/aza-login/div/aza-toggle-switch-view/div/aza-bank-id/form/div[1]/div[2]/button[1]"
    
    clickElement(browser, headerLoginButtonXPATH, 5)

    # send login credentials
    try:
        username = WebDriverWait(browser, 5).until(
            EC.presence_of_element_located((By.XPATH, inputfieldXPATH))
        )
        
        username.send_keys(payload.get("pid"))
    except Exception as e:
        Utils.log_error(e)
        sys.exit(e)

    clickElement(browser, loginButtonXPATH, 5)

    # wait for bankID login
    pendingAuthenticationXPATH ="/html/body/aza-app/aza-right-overlay-area/aside/ng-component/\
        aza-login-overlay/aza-right-overlay-template/main/div/aza-login/div/aza-toggle-switch-view/div/aza-bank-id/form/div[1]"
    try:
        wait.until(
            EC.invisibility_of_element_located((By.XPATH, pendingAuthenticationXPATH))
        )
    except TimeoutException as e:
        print("AUTHENTICATION TOOK TOO LONG")
        browser.quit()
        sys.exit(e)

    
    return browser


def scrape():

    login_url = 'https://www.avanza.se/start/startsidan.html(right-overlay:login/login-overlay)'

    payload = {
	"pid": "199312013676", 
    }

    # login and get new data
    browser = _loginToAvanza(login_url, payload)

    html = _get_portfolio(browser)

    # for reuse
    Utils.saveTxtFile(html, 'htmlAvanza') 
    # html = Utils.readTxtFile('htmlAvanza')
    
    dataframes = _parseHTML(html)

    Excel.create(dataframes, 'portfolio', 1)