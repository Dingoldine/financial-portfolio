import numpy as np
import pandas as pd
import requests
from requests.exceptions import HTTPError

# financial apis 
from pandas_datareader.iex import IEX
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.sectorperformance import SectorPerformances

# from __future__ import print_function
import intrinio_sdk
from intrinio_sdk.rest import ApiException
from pprint import pprint

# scraping 
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
import time
from collections import OrderedDict
from modules import Excel, Utils

#load .env file 
from dotenv import load_dotenv
load_dotenv()
#access dotenv variables
import os
import sys
import re
import shutil
try:  
   alphaVantageKey = os.environ.get("ALPHA_VANTAGE_APIKEY")
   iexCloudKey = os.environ.get("IEX_CLOUD_APIKEY")
   intrinioKey = os.environ.get("INTRINIO_APIKEY")
except KeyError: 
   print("Please set the environment variables")
   sys.exit(1)
   
# setup api 
intrinio_sdk.ApiClient().configuration.api_key['api_key'] = intrinioKey
sp = SectorPerformances(key=alphaVantageKey, output_format='pandas')
ts = TimeSeries(key=alphaVantageKey,output_format='pandas', indexing_type='integer')


class Portfolio:

    bank = 'Avanza'         #   class variables shared by all instances
    #   Constraints
    tot_weight_stocks = 0.2
    tot_weight_funds = 0.8
    #   portfolio weight constraints
    #   foreign stocks
    max_foreign_stocks = 0.3
    min_foreign_stocks = 0.1
    #   max growth (EPS<0)
    max_growth_stocks = 0.2
    #   max single stock
    max_single_stock = 0.2

    # target weight for funds 
    target_global = 0.4
    target_eu = 0.15
    target_nordic = 0.2
    target_developing_markets = 0.15
    target_bonds = 0.1 

    def __init__(self, stocks, funds, etfs, certificates, misc):

        s, f, c = self.cleanAndRename(stocks, funds, etfs, certificates)
        self.stocks = s
        self.funds = f
        self.certificates = c
        self.misc = misc

    def cleanAndRename(self, stocks, funds, etfs, cert):
        unnecessary_columns = ['Unnamed: 0', '+/- %', 'Konto', 'Senast', 'Tid']
        new_column_names = ['Asset', 'Amount', 'Purchase', 'MarketValue', 'Change', 'Profit']
        
        stocks = stocks.drop(unnecessary_columns, axis=1)
        stocks.columns = new_column_names
        
        cert = cert.drop(unnecessary_columns, axis=1)
        cert.columns = new_column_names

        frames = [funds, etfs]
        concat_funds = pd.concat(frames, keys=['Funds', 'ETFs'])
        concat_funds = concat_funds.drop(unnecessary_columns, axis=1)
        concat_funds.columns = new_column_names

        return (stocks,concat_funds, cert)


    def checkRules(self):
        stock_value = self.stocks.MarketValue.sum()
        funds_value = self.funds.MarketValue.sum() 
        cert_value = self.certificates.MarketValue.sum()

        self.stocks['Weight'] = self.stocks.MarketValue /  stock_value
        self.funds['Weight'] = self.funds.MarketValue /  funds_value
        self.certificates['Weight'] = self.certificates.MarketValue /  cert_value

        portfolio_value = stock_value + funds_value + cert_value

        stock_weight = stock_value/portfolio_value
        fund_weight = funds_value/portfolio_value
        cert_weight = cert_value/portfolio_value

        allowedStockTargetDeviation = 0.03
        print('stock weight', stock_weight.round(3))
        if not ( Portfolio.tot_weight_stocks - allowedStockTargetDeviation <= stock_weight):
            print('too little money in  stocks')
        elif not( stock_weight <= Portfolio.tot_weight_stocks  + allowedStockTargetDeviation):
            print('too much money in stocks')
    
            
        allowedFundTargetDeviation = 0.03
        print('fund weight', (fund_weight+cert_weight).round(3))
        if not ( Portfolio.tot_weight_funds - allowedFundTargetDeviation <= fund_weight + cert_weight):
            print('too little money in  funds')
        elif not( fund_weight + cert_weight <= Portfolio.tot_weight_funds  + allowedFundTargetDeviation):
            print('too much money in funds')
        
    def parseFundDetailsPage(self, instrument):
        avanzaGlobal = Utils.readTxtFile(instrument)

        soup = BeautifulSoup(avanzaGlobal, 'lxml')
        fee = soup.find("h3", attrs= {'data-e2e': 'fon-guide-total-fee'}).text.strip()
        print('fund fee', fee)

        keyData = soup.find_all('div', {'class': 'border-space-item'})

        keyDataDict = {}
        for div in keyData:
            key = div.label.text.strip()
            span = div.find('span', {'class': 'u-body-text'})
            if (span != None):
                value = div.find('span', {'class': 'u-body-text'}).text.strip()
                keyDataDict[key] = value
                continue
            value = div.find('a', {'class': 'u-body-text'}).text.strip()
            keyDataDict[key] = value
        keyDataDF = pd.DataFrame(list(keyDataDict.items()))


        allocationDataLists = soup.find_all('ul', {'class': 'allocation-list'})
        # we know there is no country/sector data ie special fund, dont bother returning anything
        if (len(allocationDataLists) == 1): 
            # instrumentDict = {}
            # instrumentAllocations = allocationDataLists[0]
            # instruments = instrumentAllocations.find_all('span', {'class': 'u-ellipsis'})
            # percentages = instrumentAllocations.find_all('span', {'class': 'percent'})
            # instruments = list(set(instruments)) #remove duplicates
            # for i in range(len(instruments)):
            #     instrumentDict[instruments[i].text.strip()] = percentages[i].text.strip()
            # instrumentsDF = pd.DataFrame(list(instrumentDict.items()))

            # return {'key-data': keyDataDF, 'instruments': instrumentsDF}
            print('special fund, return nothing')
            return {}
        else:
            ## countries and regions
            countryDict = {}
            countryAllocations = allocationDataLists[0]
            countries = countryAllocations.find_all('span', {'class': 'u-ellipsis'})
            percentages = countryAllocations.find_all('span', {'class': 'percent'})
            #countries = list(set(countries))
            for i in range(len(countries)):
                percentageString = percentages[i].text.strip().replace('%', '').replace(',', '.')
                percentegeFloat = round(float(percentageString)/100, 4)
                countryDict[countries[i].text.strip()] = percentegeFloat
            countryDF  = pd.DataFrame(list(countryDict.items()))

            
            ## sectors 
            sectorDict = {}
            sectorAllocations = allocationDataLists[1]
            sectors = sectorAllocations.find_all('span', {'class': 'u-ellipsis'})
            percentages = sectorAllocations.find_all('span', {'class': 'percent'})
            for i in range(len(sectors)):
                percentageString = percentages[i].text.strip().replace('%', '').replace(',', '.')
                percentegeFloat = round(float(percentageString)/100, 4)
                sectorDict[sectors[i].text.strip()] = percentegeFloat
            sectorDF = pd.DataFrame(list(sectorDict.items()))

            ## individual stocks
            stockDict = {}
            stockAllocations = allocationDataLists[2]
            stocks = stockAllocations.find_all('span', {'class': 'u-ellipsis'})
            percentages = stockAllocations.find_all('span', {'class': 'percent'})
            stocks = list(OrderedDict.fromkeys(stocks)) #remove duplicates
            c= [c.text.strip() for c in stocks]
            print(c)
            p = [p.text.strip() for p in percentages]
            print(p)
            for i in range(len(stocks)):
                percentageString = percentages[i].text.strip().replace('%', '').replace(',', '.').replace('−', '-')
                percentegeFloat = round(float(percentageString)/100, 4)
                stockDict[stocks[i].text.strip()] = percentegeFloat
            stocksDF = pd.DataFrame(list(stockDict.items()))



            return {'key-data': keyDataDF,'countries': countryDF,'sectors': sectorDF,'instruments': stocksDF}

    def fundsBreakdown(self):
        df = self.funds
        Utils.printDf(df)
        finalSectorAlloc = pd.DataFrame(columns=[0, 1])
        finalCountryAlloc = pd.DataFrame(columns=[0, 1])
        finalInstrumentAlloc = pd.DataFrame(columns=[0, 1])
        for instrument in df['Asset']:
            print('instrument name', instrument)
            data = self.parseFundDetailsPage(instrument)
            if (len(data) == 0):
                continue
            instrumentAlloc = data.get('instruments')
            sectorAlloc = data.get('sectors')
            countryAlloc = data.get('countries')
            fundData = data.get('key-data')
            
            weight = df.loc[df['Asset'] == instrument, 'Weight'][0]
            print('instrument weight', weight)
            instrumentAlloc[1] = instrumentAlloc[1].multiply(weight)
            sectorAlloc[1] = sectorAlloc[1].multiply(weight)
            countryAlloc[1] = countryAlloc[1].multiply(weight)
            Utils.printDf(instrumentAlloc)
            finalInstrumentAlloc = pd.merge(instrumentAlloc, finalInstrumentAlloc, how='outer', left_on=0, right_on=0, suffixes=('_left', '_right'))

            Utils.printDf(finalInstrumentAlloc)
            finalSectorAlloc = pd.merge(sectorAlloc, finalSectorAlloc, how='outer', left_on=0, right_on=0, suffixes=('_left', '_right'))
            
            finalCountryAlloc = pd.merge(countryAlloc, finalCountryAlloc, how='outer', left_on=0, right_on=0, suffixes=('_left', '_right'))
            # Utils.printDf(finalCountryAlloc)

        finalSectorAlloc.loc[:,'Total'] = finalSectorAlloc.sum(axis=1)
        finalSectorAlloc = finalSectorAlloc.iloc[:,[0, -1]]
        Utils.printDf(finalSectorAlloc.sort_values('Total', ascending=False))

        finalCountryAlloc.loc[:,'Total'] = finalCountryAlloc.sum(axis=1)
        finalCountryAlloc = finalCountryAlloc.iloc[:,[0, -1]]
        Utils.printDf(finalCountryAlloc.sort_values('Total', ascending=False))
        print(finalCountryAlloc['Total'].sum())

        finalInstrumentAlloc.loc[:,'Total'] = finalInstrumentAlloc.sum(axis=1)
        finalInstrumentAlloc = finalInstrumentAlloc.iloc[:,[0, -1]]
        Utils.printDf(finalInstrumentAlloc.sort_values('Total', ascending=False))


        conditions = [
            df['Asset'] == 'AMF Räntefond Lång',
            df['Asset'] == 'Avanza Emerging Markets',
            df['Asset'] == 'Avanza Global',
            df['Asset'] == 'Länsförsäkringar Tillväxtmrkd Idxnära A',
            df['Asset'] == 'Spiltan Aktiefond Investmentbolag',
            df['Asset'] == 'Spiltan Globalfond Investmentbolag',
            df['Asset'] == 'SPP Aktiefond Europa',
            df['Asset'] == 'Swedbank Robur Access Asien',
            df['Asset'] == 'DBX MSCI EUROPE ETF (DR)',
            df['Asset'] == 'Handelsbanken Gl Småbolag Ind Cri A1 SEK',
            df['Asset'] == 'SPP Global Företagsobligations Plus A',
            df['Asset'] == 'Atlant Stability'
        ]

        outputs = [
        'Interests', 
        'Emerging Markets',
        'Global', 
        'Emerging Markets', 
        'Nordics', 
        'Global', 
        'Europe', 
        'Emerging Markets',
        'Europe',
        'Global',
        'Interests',
        'Interests',
        ]

        res = np.select(conditions, outputs, 'Other')
        df = df.assign(Market=pd.Series(res).values)

        # em = df[df.Market == 'Emerging Markets'].Weight.sum().round(3)
        # glob = df[df.Market == 'Global'].Weight.sum().round(3)
        # nord = df[df.Market == 'Nordics'].Weight.sum().round(3)
        # eur = df[df.Market == 'Europe'].Weight.sum().round(3)
        # interests = df[df.Market == 'Interests'].Weight.sum().round(3)

        # # print fund rule check
        # Utils.printDf(df)
        # print('Emerging Market weight', em)
        # print('Global weight', glob)
        # print('Nordics weight', nord)
        # print('Eur weight', eur)
        # print('Interests', interests)

    def saveStockInfoToExcel(self):
        for asset in self.stocks['Asset']:
            print(f'opening {asset}_keyRatios.txt')
            savePath = os.path.abspath(os.getcwd()) + "/text_files"
            try:
                with open(f'{savePath}/{asset}_keyRatios.txt','r') as f:
                    html = f.read()
                
                dataframeList = pd.read_html(html, header=None)

            except Exception as e:
                print('Something went wrong.. \n Message ', e)
                continue
            # need to extract table containing multiple tbody tags
            # soup = BeautifulSoup(html, 'lxml')
            # multipleTbodyTableDiv = soup.find('div', {'id': 'KeyRatiosGrowthRates'})
            # table = multipleTbodyTableDiv.find('table')
            # for tbody in table('tbody'):
            #     tbody.unwrap()
            # print(table.prettify())
            _ = dataframeList.pop() # no need for morningstar disclaimer table

            for index, df in enumerate(dataframeList):
                df = organizeDataframe(df)
                
                dataframeList[index] = df

            # extracted them because I migh wanna do something with them? 
            marginRatios = dataframeList[0]
            marginRatios.name = 'Margins (in % of sales)'
            
            profitabilityRatios = dataframeList[1]
            profitabilityRatios.name = 'Profitability'
            # print(profitabilityRatios.loc['Net Margin'].values.tolist())
            
            # THIS TABLE HAS MULTIPLE TBODY TAGs, IT BEOMES A PROBLEM
            ## need to split into sub-dataframes
            growthRateRatios = dataframeList[2]

            revenueGrowth = growthRateRatios.iloc[1:4]
            revenueGrowth.name = 'Compound Revenue Growth'

            operatingIncomeGrowth = growthRateRatios.iloc[5:8]
            operatingIncomeGrowth.name = 'Compound OpMargin Growth'

            EPSGrowth = growthRateRatios.iloc[9:]
            EPSGrowth.name = ' EPS Growth'

            cashFlowRatios = dataframeList[3]
            cashFlowRatios.name = 'Cash Flow'

            balaceSheetItems = dataframeList[4]
            balaceSheetItems.name = 'Balance Sheet Items(in % Terms)'

            financialHealthRatios = dataframeList[5]
            financialHealthRatios.name = 'Liquidity-Financial Health'

            efficiencyRatios = dataframeList[6]
            efficiencyRatios.name = 'Efficiency'

            print(f'opening {asset}_overview.txt')
            savePath = os.path.abspath(os.getcwd()) + "/text_files"
            with open(f'{savePath}/{asset}_overview.txt','r') as f:
                html = f.read()

            soup  = BeautifulSoup(html, 'lxml')
            companyProfile = soup.find("div", {"id": "CompanyProfile"})
            # need to use somehow
            currencyInfo = soup.find('p', {'class', 'disclaimer'})

            print(currencyInfo.text.strip())
            for child in companyProfile.find_all("div", {"class": "item"}):
                if (child.find('h3')):
                    strings = list([s for s in child.strings if len(s) > 1])
                    key = strings[0].strip()
                    value = strings[1].strip()
                    self.stocks.loc[self.stocks['Asset'] == asset, key] = value
                
        
            dataframeList = pd.read_html(html)
            _ = dataframeList.pop() # no need for morningstar disclaimer table

            # the first two are similar so we parse them first 
            for index, df in enumerate(dataframeList):
                # drop last row
                df = df.iloc[:-1]
                df = organizeDataframe(df)
                
                
                dataframeList[index] = df
                
            # need to split into seperate DFs because html contained multiple <tbody>
            financialSummary = dataframeList[0]
            
            incomeStatementSummary = financialSummary.iloc[1:6]
            incomeStatementSummary.name = 'Income Statement Summary'
            

            balanceSheetSummary = financialSummary.iloc[7:13]
            balanceSheetSummary.name = 'Balance Sheet Summary'
            
            cashFlowSummary = financialSummary.iloc[14:]
            cashFlowSummary.name = 'Cash Flow Summary'

            # rename column
            ratios = dataframeList[1]
            ratios=ratios.rename(columns = {1: 'Ratios'}) # rename
            ratios.name = "Ratios"

            dividends = dataframeList[2]
            dividends.name = 'Dividends'

            dataframes = [
                marginRatios, 
                profitabilityRatios, 
                revenueGrowth,
                operatingIncomeGrowth,
                EPSGrowth, 
                cashFlowRatios, 
                balaceSheetItems, 
                financialHealthRatios, 
                efficiencyRatios,
                incomeStatementSummary,
                balanceSheetSummary,
                cashFlowSummary,
                ratios,
                dividends
                ]
            # save to file
            Excel.create(dataframes, asset, 1)
    
    def readStockInfoFromExcel(self, asset):
        keys = ['Margins (in % of sales)', 'Profitability', 'Compound Revenue Growth', 
        'Compound OpMargin Growth', ' EPS Growth', 'Cash Flow', 'Balance Sheet Items(in % Terms)', 
        'Liquidity-Financial Health', 'Efficiency', 'Income Statement Summary', 'Balance Sheet Summary', 
        'Cash Flow Summary', 'Ratios', 'Dividends']
        # df_map = pd.read_excel(f'{saveLocation}/portfolio.xlsx', sheet_name=None)


    def scrapeNasdaq(self):
        df = self.stocks
        # Scrape Nasdaq Nordic 
        fp = webdriver.FirefoxProfile()
        # Set browser preferences
        downloadDir = os.path.abspath(os.getcwd()) + "/fact_sheets"
        fp.set_preference("browser.preferences.instantApply",True)
        fp.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/plain, application/octet-stream, application/binary, text/csv, application/csv, application/excel, text/comma-separated-values, text/xml, application/xml, application/pdf, text/html, application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8")
        fp.set_preference("browser.helperApps.alwaysAsk.force",False)
        fp.set_preference("browser.download.manager.showWhenStarting",False)
        fp.set_preference("browser.download.dir", downloadDir)
        fp.set_preference("pdfjs.disabled", True)
        # Use this to disable Acrobat plugin for previewing PDFs in Firefox (if you have Adobe reader installed on your computer)
        fp.set_preference("plugin.scan.Acrobat", "99.0")
        fp.set_preference("plugin.scan.plid.all", False)
        # 0 desktop, 1 Default Download, 2 User defined
        fp.set_preference("browser.download.folderList", 2)
        log_path = os.path.abspath(os.getcwd()) + '/geckodriver/geckodriver.log'
        opt = webdriver.FirefoxOptions()
        browser = webdriver.Firefox(options=opt, firefox_profile=fp, service_log_path=log_path)
        
        # poll for elements for 10 seconds max, before shutdown
        browser.implicitly_wait(5)
        url = "http://www.nasdaqomxnordic.com/shares"
        browser.get(url)

        #wait for javascipt to load then scrape, this part is tricky to optimize, HOW TO KNOW THAT ENTIRE PAGE HAS LOADED?
        #time.sleep(4)
        
        midCapXPATH = "/html/body/section/div/div/div/section/div/article/div/section/form/div[4]/ul/li[2]"
        smallCapXPATH = "/html/body/section/div/div/div/section/div/article/div/section/form/div[4]/ul/li[3]"
        # searchFieldXPATH = "/html/body/section/div/div/div/section/div/article/div/div[2]/table[1]/thead/tr[2]/td[2]/input"
        midcapCheckbox = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, midCapXPATH))
        )
        midcapCheckbox.click()
        smallcapCheckbox = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, smallCapXPATH))
        )
        smallcapCheckbox.click()

        # wait for table to update
        time.sleep(4)
        
        myDict = {}
        notFound = []
        print("Searching For Assets In Main Market...")
        for assetName in df['Asset']:
            try:
                asset = browser.find_element(By.XPATH, f'/html/body/section/div/div/div/section/div/article/div/div[2]/table[1]/tbody/tr/td/a[.="{assetName}"]')
                #print(str(asset.get_attribute("innerHTML")).strip(), asset.get_attribute("href"))
                #add to dict
                myDict[str(asset.get_attribute("innerHTML")).strip()] = asset.get_attribute("href")
            except NoSuchElementException:
                print("couldnt find: ", assetName, "in Main Market")
                notFound.append(assetName)
        
        if len(notFound) > 0:
            print("Searching For Assets In First North...")
            firstNorthXPATH = '/html/body/section/div/div/div/section/div/article/div/section/form/div[1]/div/label[2]'
            firstNorthCheckbox = WebDriverWait(browser, 10).until(
                EC.element_to_be_clickable((By.XPATH, firstNorthXPATH))
            )
            firstNorthCheckbox.click()
            firstNorthGMXPATH = "/html/body/section/div/div/div/section/div/article/div/section/form/div[5]/ul/li[2]"
            firstNorthGMCheckbox = WebDriverWait(browser, 10).until(
                EC.element_to_be_clickable((By.XPATH, firstNorthGMXPATH))
            )
            firstNorthGMCheckbox.click()
            # wait for table to update
            time.sleep(4)

            for assetName in notFound:
                try:
                    asset = browser.find_element(By.XPATH, f'/html/body/section/div/div/div/section/div/article/div/div[2]/table[1]/tbody/tr/td/a[.="{assetName}"]')
                    #add to dict
                    myDict[str(asset.get_attribute("innerHTML")).strip()] = asset.get_attribute("href")
                except NoSuchElementException:
                    print("couldnt find: ", assetName, "in First North")

        # EXTRACT RATIOS
        for asset, href in myDict.items(): 
            try:
                browser.get(href)
                keyRatiosXPATH = "/html/body/section/div/div/div/section/section/section/nav/ul/li[4]/a"
                keyRatiosLink = WebDriverWait(browser, 10).until(
                    EC.element_to_be_clickable((By.XPATH, keyRatiosXPATH))
                )
                keyRatiosLink.click()

                # wait for page to load
                time.sleep(10)
                morningstarFrameXPATH = '//*[@id="MorningstarIFrame"]'
                morningstarFrame = WebDriverWait(browser, 10).until(
                    EC.frame_to_be_available_and_switch_to_it(By.XPATH, morningstarFrameXPATH)
                )
                # Switch to iframe containing morningstar data
                #frame = browser.find_element(By.XPATH, )
                #browser.switch_to.frame(frame)
                #html = browser.execute_script("return document.documentElement.outerHTML")
                html = browser.page_source 
                # tables = browser.find_elements(By.XPATH, "//table")
            
                soup = BeautifulSoup(html, 'lxml')
                saveHtmlToFile(str(soup.prettify()), f'{asset}_keyRatios')
                
                # switch back to original frame
                browser.switch_to.default_content()

                overwiewXPATH = "/html/body/section/div/div/div/section/section/section/nav/ul/li[2]/a"
                overwiewLink = WebDriverWait(browser, 10).until(
                    EC.element_to_be_clickable((By.XPATH, overwiewXPATH))
                )
                overwiewLink.click()
                
                # wait for content to load
                time.sleep(10)
                frame = browser.find_element(By.XPATH, '//*[@id="MorningstarIFrame"]')
                browser.switch_to.frame(frame)
                html = browser.page_source 
                soup = BeautifulSoup(html, 'lxml')
                saveHtmlToFile(str(soup.prettify()), f'{asset}_overview')

                # switch back to original frame
                browser.switch_to.default_content()

                # Download Fact Sheet
                downloadFactsheet(browser, asset, downloadDir)
                 
            except Exception as e:
                print("what happened", e)
             
        # update stocks class variable
        print(df.to_string())
        self.stocks = df
        # browser.quit()

def organizeDataframe(df):
    df=df.rename(columns = {'Unnamed: 0': 'Data'}) # rename
    leftMostCol = df.columns.values[0]
    df.set_index(leftMostCol, inplace=True) # Turn this column to index
    df.index.name = None # Remove the name 
    return df

def find_all_iframes(driver):
    iframes = driver.find_elements_by_xpath("//iframe")

    for index, iframe in enumerate(iframes):
        # Your sweet business logic applied to iframe goes here.
        # print(iframe)
        driver.switch_to.frame(index)
        try: 
            elem = driver.find_element(By.XPATH, '/html/body/div[2]/div[2]/form/div[4]/div[2]/div/div/div[3]/div[2]/div[2]/table/tbody[2]/tr[2]/th')
            print(elem.get_attribute('innerHTML'))
        except NoSuchElementException:
            print('not found')
        driver.switch_to.parent_frame()


def downloadFactsheet(browser, name, directory):
    
    factsheetLinkXPATH = "/html/body/section/div/div/div/section/section/section/nav/ul/li[6]/a"
    factsheetLink = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.XPATH, factsheetLinkXPATH))
    )
    #instantly downloads the factsheet
    factsheetLink.click()
    # wait for download to complete
    # can optimize line below with event and directory watcher
    time.sleep(20)
    # rename the latest file
    newfilename = f'{name}.pdf'
    filename = max([directory + "/" + f for f in os.listdir(directory)], key=os.path.getctime)
    shutil.move(os.path.join(directory, filename), os.path.join(directory, newfilename))

def saveHtmlToFile(html, filename):
    savePath = os.path.abspath(os.getcwd()) + "/text_files"
    print(f'Saving {filename}.txt')
    with open(f'{savePath}/{filename}.txt', 'w') as f:
        f.write(html)
