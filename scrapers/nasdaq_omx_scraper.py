from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException, UnexpectedAlertPresentException
from bs4 import BeautifulSoup
import pandas as pd
import constants
from helpermodules import Utils, Excel
import time, os, shutil, sys
from scrapers._scraping_functions import waitforload, clickElement


def organizeDataframe(df):
    df=df.rename(columns = {'Unnamed: 0': 'Data'}) # rename
    leftMostCol = df.columns.values[0]
    df.set_index(leftMostCol, inplace=True) # Turn this column to index
    df.index.name = None # Remove the name 
    return df



def saveStockInfoToExcel():
        """ Turns txt files containing stock info to an excel file """ 
        df_map = pd.read_excel(f'{constants.excelSaveLocation}/portfolio.xlsx', sheet_name=None)
        stocks = df_map.get("Stocks", None)

        for asset in stocks['Asset']:
            print(f'opening {asset}_keyRatios')

            try:
                html = Utils.readTxtFile(f'{asset}_keyRatios')
                
                dataframeList = pd.read_html(html, header=None)

            except Exception as e:
                print('Something went wrong.. \n Message ', e)
                continue

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
            
            # THIS TABLE HAS MULTIPLE TBODY TAGs,
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

            html = Utils.readTxtFile(f'{asset}_overview')

            soup  = BeautifulSoup(html, 'lxml')
            companyProfile = soup.find("div", {"id": "CompanyProfile"})
            currencyInfo = soup.find('p', {'class', 'disclaimer'})

            generalInfo = pd.DataFrame(columns=[""])
            generalInfo.name = "Overview"
            for child in companyProfile.find_all("div", {"class": "item"}):
                if (child.find('h3')):
                    strings = list([s for s in child.strings if len(s) > 1])
                    key = strings[0].strip()
                    value = strings[1].strip()
                    generalInfo.loc[key] = [value]
            

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
            
            incomeStatementSummary = financialSummary.iloc[1:6].astype(float)
            latestYear = incomeStatementSummary.columns.values[-1]
            latestEPS = incomeStatementSummary.loc['Basic EPS', latestYear]
            stocks.loc[stocks['Asset'] == asset, f'EPS ({latestYear})'] = latestEPS
            incomeStatementSummary.name = 'Income Statement Summary'
            

            balanceSheetSummary = financialSummary.iloc[7:13].astype(float)
            balanceSheetSummary.name = 'Balance Sheet Summary'
            
            cashFlowSummary = financialSummary.iloc[14:].astype(float)
            cashFlowSummary.name = 'Cash Flow Summary'

            # rename column
            ratios = dataframeList[1]
            ratios=ratios.rename(columns = {1: 'Ratios'}) # rename
            ratios.name = "Ratios"

            dividends = dataframeList[2]
            dividends.name = 'Dividends'

            print(f'opening {asset}_financials.txt')
            html = Utils.readTxtFile(f'{asset}_financials')
            dataframeList = pd.read_html(html)
        
            entireIncomeStatement = dataframeList[0]
            entireIncomeStatement = organizeDataframe(entireIncomeStatement)
            entireIncomeStatement = entireIncomeStatement.apply(pd.to_numeric, errors='coerce') 
            entireIncomeStatement.name = 'Income Statement'

            entireBalanceSheet = dataframeList[1]
            entireBalanceSheet = organizeDataframe(entireBalanceSheet)
            entireBalanceSheet = entireBalanceSheet.apply(pd.to_numeric, errors='coerce') 
            entireBalanceSheet.name = 'Balance Sheet'

            entireCashFlowStatement = dataframeList[2]
            entireCashFlowStatement = organizeDataframe(entireCashFlowStatement)
            entireCashFlowStatement = entireCashFlowStatement.apply(pd.to_numeric, errors='coerce') 
            entireCashFlowStatement.name = 'Cash Flow Statement'

            dataframes = [
                generalInfo,
                marginRatios, 
                profitabilityRatios, 
                revenueGrowth,
                operatingIncomeGrowth,
                EPSGrowth, 
                cashFlowRatios, 
                balaceSheetItems, 
                financialHealthRatios, 
                efficiencyRatios,
                entireIncomeStatement,
                incomeStatementSummary,
                entireBalanceSheet,
                balanceSheetSummary,
                entireCashFlowStatement,
                cashFlowSummary,
                ratios,
                dividends
                ]
            # save to file
            Excel.create(dataframes, asset, 1, currencyInfo.text.strip())



def scrape():
    df_map = pd.read_excel(f'{constants.excelSaveLocation}/portfolio.xlsx', sheet_name=None)
    stocks = df_map.get("Stocks", None)
    # Scrape Nasdaq Nordic 
    fp = webdriver.FirefoxProfile()
    # Set browser preferences
    
    fp.set_preference("browser.preferences.instantApply",True)
    fp.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/plain, application/octet-stream, application/binary, text/csv, application/csv, application/excel, text/comma-separated-values, text/xml, application/xml, application/pdf, text/html, application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8")
    fp.set_preference("browser.helperApps.alwaysAsk.force",False)
    fp.set_preference("browser.download.manager.showWhenStarting",False)
    fp.set_preference("browser.download.dir", constants.pdfDownloadDir)
    fp.set_preference("pdfjs.disabled", True)
    # Use this to disable Acrobat plugin for previewing PDFs in Firefox (if you have Adobe reader installed on your computer)
    fp.set_preference("plugin.scan.Acrobat", "99.0")
    fp.set_preference("plugin.scan.plid.all", False)
    # 0 desktop, 1 Default Download, 2 User defined
    fp.set_preference("browser.download.folderList", 2)
    
    opt = webdriver.FirefoxOptions()
    browser = webdriver.Firefox(options=opt, firefox_profile=fp, service_log_path=constants.GECKO_LOG_PATH)
    
    # poll for elements for --  seconds max, before shutdown
    browser.implicitly_wait(0)
    wait = WebDriverWait(browser, 35)

    latest_button_xpath = ""

    def switchToMorningstarFrame():
        morningstarFrameXPATH = '//*[@id="MorningstarIFrame"]'
        retries = 0
        while retries < 5:  
            try:
                print('Waiting for Iframe and Iframe Tables:')
                print('Attempt Number:', retries + 1)
                # wait for iframe to be availible
                wait.until(
                    EC.frame_to_be_available_and_switch_to_it((By.XPATH, morningstarFrameXPATH))
                )
                # wait for all tables to load
                wait.until(
                    EC.visibility_of_all_elements_located((By.XPATH, "//table"))
                )   
                waitforload(browser, 10)
                return
            except (UnexpectedAlertPresentException, TimeoutException) as e:
                browser.refresh()
                retries += 1
                print(latest_button_xpath)
                clickElement(browser, latest_button_xpath, 5)
        raise(e)


    url = "http://www.nasdaqomxnordic.com/shares"

    try:
        browser.get(url)

        midCapXPATH = "/html/body/section/div/div/div/section/div/article/div/section/form/div[4]/ul/li[2]"
        smallCapXPATH = "/html/body/section/div/div/div/section/div/article/div/section/form/div[4]/ul/li[3]"

        clickElement(browser, midCapXPATH, 5)

        clickElement(browser, smallCapXPATH, 5)

        ## Wait until table loading dissapears
        loadingImgXPATH = "/html/body/section/div/div/div/section/div/article/div/div[2]/img"
        wait.until(
            EC.invisibility_of_element_located((By.XPATH, loadingImgXPATH))
        )
        
        ## add links to dicts 
        foundAssetsDict = {}
        notFound = []
        print("Searching For Assets In Main Market...")
        for assetName in stocks['Asset']:
            try:
                asset = browser.find_element(By.XPATH, f'/html/body/section/div/div/div/section/div/article/div/div[2]/table[1]/tbody/tr/td/a[.="{assetName}"]')
                #add to dict
                foundAssetsDict[str(asset.get_attribute("innerHTML")).strip()] = asset.get_attribute("href")
            except NoSuchElementException:
                print(f'Could not find  {assetName} in Main Market')
                notFound.append(assetName)
        
        if len(notFound) > 0:
            print("Searching For Assets In First North...")
            firstNorthXPATH = '/html/body/section/div/div/div/section/div/article/div/section/form/div[1]/div/label[2]'

            clickElement(browser, firstNorthXPATH, 5)                  
            firstNorthGMXPATH = latest_button_xpath = "/html/body/section/div/div/div/section/div/article/div/section/form/div[5]/ul/li[2]"

            clickElement(browser, firstNorthGMXPATH, 5)
            
            ## Wait until table loading dissapears
            wait.until(
                EC.invisibility_of_element_located((By.XPATH, loadingImgXPATH))
            )

            for assetName in notFound:
                try:
                    asset = browser.find_element(By.XPATH, f'/html/body/section/div/div/div/section/div/article/div/div[2]/table[1]/tbody/tr/td/a[.="{assetName}"]')
                    #add to dict
                    foundAssetsDict[str(asset.get_attribute("innerHTML")).strip()] = asset.get_attribute("href")
                except NoSuchElementException:
                    print("couldnt find: ", assetName, "in First North")

        # EXTRACT RATIOS
        for asset, href in foundAssetsDict.items(): 
        
            # go to asset page
            browser.get(href)
            
            keyRatiosXPATH = latest_button_xpath = "/html/body/section/div/div/div/section/section/section/nav/ul/li[4]/a"
            
            clickElement(browser, keyRatiosXPATH, 5)

            # Switch to iframe containing morningstar data
            switchToMorningstarFrame()
            

            # Get Page Source
            keyRatiosPage = browser.page_source    
            soup = BeautifulSoup(keyRatiosPage, 'lxml')
            Utils.saveTxtFile(str(soup.prettify()), f'{asset}_keyRatios') # Save file

            # switch back to original frame
            browser.switch_to.default_content()

            overviewXPATH = latest_button_xpath = "/html/body/section/div/div/div/section/section/section/nav/ul/li[2]/a"

            clickElement(browser, overviewXPATH, 5)

            switchToMorningstarFrame()

            # Make sure company profile has loaded
            companyProfileXPATH = "/html/body/div[2]/div[2]/form/div[4]/div[2]/div/div/div[3]/div[3]/div[1]/h2"
            wait.until(
                EC.text_to_be_present_in_element((By.XPATH, companyProfileXPATH), "Company Profile")
            )
            wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="CompanyProfile"]'))
            )

            overviewPage = browser.page_source 
            soup = BeautifulSoup(overviewPage, 'lxml')
            Utils.saveTxtFile(str(soup.prettify()), f'{asset}_overview')

            # switch back to original frame
            browser.switch_to.default_content()

            companyFinancialsXPATH = latest_button_xpath =  '/html/body/section/div/div/div/section/section/section/nav/ul/li[5]/a'
            
            clickElement(browser, companyFinancialsXPATH, 5)

            switchToMorningstarFrame()

            # Make sure table content loads
            incomeStatementCaptionXPATH = "/html/body/div[2]/div[2]/form/div[4]/div[2]/div/div/div[3]/div[2]/table/caption"
            wait.until(
                EC.text_to_be_present_in_element((By.XPATH, incomeStatementCaptionXPATH), "Income Statement")
            )

            financialsPage = browser.page_source 
            soup = BeautifulSoup(financialsPage, 'lxml')
            Utils.saveTxtFile(str(soup.prettify()), f'{asset}_financials')

            # switch back to original frame
            browser.switch_to.default_content()

            # Download Fact Sheet
            factsheetLinkXPATH = "/html/body/section/div/div/div/section/section/section/nav/ul/li[6]/a"

            #click instantly downloads because of browser preferences
            clickElement(browser, factsheetLinkXPATH, 5)
        
    except Exception as e:
        Utils.log_error(e)
        browser.quit()
        sys.exit(e)

            
                
            