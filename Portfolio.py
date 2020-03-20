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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException, UnexpectedAlertPresentException, ElementClickInterceptedException
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

# for complex string matching
from fuzzywuzzy import fuzz, process

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
    target_global = 0.5
    target_eu = 0.1
    target_nordic = 0.1
    target_developing_markets = 0.2
    target_bonds = 0.1 
    target_alternative = 0

    def __init__(self, stocks, funds, etfs, certificates, misc):
        assert(self.target_bonds + self.target_developing_markets + self.target_global + self.target_nordic + self.target_alternative + self.target_eu == 1)
        s, f, c = self.cleanAndRename(stocks, funds, etfs, certificates)
        self.stocks = s
        self.funds = f
        self.certificates = c
        self.misc = misc

    def cleanAndRename(self, stocks, funds, etfs, cert):
        unnecessary_columns = ['Unnamed: 0', '+/- %', 'Konto', 'Senast', 'Tid']
        new_column_names = ['Asset', 'Amount', 'Purchase', 'Market Value', 'Change', 'Profit']
        
        stocks = stocks.drop(unnecessary_columns, axis=1)
        stocks.columns = new_column_names
        
        if(cert != None):
            cert = cert.drop(unnecessary_columns, axis=1)
            cert.columns = new_column_names
        else:
            cert = pd.DataFrame(columns=new_column_names) 

        frames = [funds, etfs]
        concat_funds = pd.concat(frames, keys=['Funds', 'ETFs'])
        concat_funds = concat_funds.drop(unnecessary_columns, axis=1)
        concat_funds.columns = new_column_names

        return (stocks,concat_funds, cert)

    def checkRules(self):
        stock_value = self.stocks['Market Value'].sum()
        funds_value = self.funds['Market Value'].sum()
        cert_value = self.certificates['Market Value'].sum()

        self.stocks['Weight'] = self.stocks['Market Value'] /  stock_value
        self.funds['Weight'] = self.funds['Market Value'] /  funds_value
        self.certificates['Weight'] = self.certificates['Market Value'] /  cert_value

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
        html = Utils.readTxtFile(instrument)

        soup = BeautifulSoup(html, 'lxml')
        fee = soup.find("h3", attrs= {'data-e2e': 'fon-guide-total-fee'}).text.strip()

        keyData = soup.find_all('div', {'class': 'border-space-item'})
        
        keyDataDict = {'Fee': fee}
        translationDict = {
            'Typ': 'Type',
            'Alternativa': 'Alternative',
            'Aktiefond': 'Equity',
            'Räntefond': 'Fixed Income',
            'Kategori': 'Category',
            'Hedgefond, Multi-strategi': 'Hedgefund, Multi-strategy',
            'Tillväxtmarknader': 'Emerging Markets',
            'Global, Mix bolag': 'Global Mix',
            'Global, Småbolag': 'Global Small Cap',
            'Ränte - SEK obligationer, Företag': 'Corporate Bonds SEK',
            'Sverige': 'Sweden',
            'Europa, Mix bolag': 'Europe Mix',
            'Ränte - övriga obligationer': 'Fixed Income MISC',
            'Asien ex Japan': 'Asia ex Japan',
            'Jämförelseindex': 'Index',
            'Indexfond': 'Index Fund',
            'Fondens startdatum': 'Start date',
            'Fondbolag': 'Company',
            'Hemsida': 'Website',
            'Legalt säte': 'Registered In',
            'Antal ägare hos Avanza': 'Owners at Avanza',
            'Förvaltat kapital': 'AUM',
            'Standardavvikelse': 'Standard Deviation',
            'Sharpekvot': 'Sharpe Ratio',
            'Ja': 'Yes',
            'Nej': 'No',
            'Kina': 'China',
            'Sydkorea': 'Korea',
            'Storbritannien': 'United Kingdom',
            'Kanada': 'Canada',
            'Frankrike': 'France',
            'Schweiz': 'Switzerland',
            'Brasilien': 'Brazil',
            'Sydafrika': 'South Africa',
            'Nederländerna': 'Netherlands',
            'Ryssland': 'Russia',
            'Italien': 'Italy',
            'Spanien': 'Spain',
            'Belgien': 'Belgium',
            'Saudiarabien': 'Saudi Arabia',
            'Mexiko': 'Mexico',
            'Indonesien': 'Indonesia',
            'Filippinerna': 'Philippines',
            'Hongkong': 'Hong Kong',
            'Norge': 'Norway',
            'Danmark': 'Denmark',
            'Indien': 'India',
            'Australien': 'Australia',
            'Tyskland': 'Germany',
            'USA': 'United States'
        }

        for div in keyData:
            key = div.label.text.strip()
            translatedKey = translationDict.get(key)
            if(translatedKey == None):
                translatedKey = key
            span = div.find('span', {'class': 'u-body-text'})
            if (span != None):
                value = div.find('span', {'class': 'u-body-text'}).text.strip()
                translatedValue = translationDict.get(value)
                if (translatedValue == None):
                    translatedValue = value
                keyDataDict[translatedKey] = translatedValue
                continue
            value = div.find('a', {'class': 'u-body-text'}).text.strip()
            keyDataDict[translatedKey] = value
        keyDataDF = pd.DataFrame(list(keyDataDict.items()))

        exposureDiv = soup.find('div', {'class': 'allocation-lists-wrapper'})
        allocationDivs = exposureDiv.find_all('div')
    
        sectorDF = None
        countryDF = None
        stocksDF = None
        for div in allocationDivs:
            heading = div.find('h5')
            if(heading == None):
                continue
            else:
                headingText = heading.text.strip()
            
            if headingText == 'Länder':
                ## countries and regions
                # print(allocationDataLists[0])
                countryDict = {}
                countryAllocations = div.find('ul', {'class': 'allocation-list'})
                if(countryAllocations == None):
                    continue 
                countries = countryAllocations.find_all('span', {'class': 'u-ellipsis'})
                percentages = countryAllocations.find_all('span', {'class': 'percent'})
                #countries = list(set(countries))
                for i in range(len(countries)):
                    percentageString = percentages[i].text.strip().replace('%', '').replace(',', '.')
                    percentegeFloat = round(float(percentageString)/100, 4)
                    country = countries[i].text.strip()
                    countryInEnglish = translationDict.get(country)
                    if (countryInEnglish == None):
                        countryInEnglish = country
                    countryDict[countryInEnglish] = percentegeFloat
                countryDF  = pd.DataFrame(list(countryDict.items()))
            elif headingText == 'Branscher':
                ## sectors 
                sectorDict = {}
                sectorAllocations = div.find('ul', {'class': 'allocation-list'})
                if(sectorAllocations == None):
                    continue
                sectors = sectorAllocations.find_all('span', {'class': 'u-ellipsis'})
                percentages = sectorAllocations.find_all('span', {'class': 'percent'})
                for i in range(len(sectors)):
                    percentageString = percentages[i].text.strip().replace('%', '').replace(',', '.')
                    percentegeFloat = round(float(percentageString)/100, 4)
                    sectorDict[sectors[i].text.strip()] = percentegeFloat
                sectorDF = pd.DataFrame(list(sectorDict.items()))
            elif headingText == 'Största innehav':
                ## individual stocks
                stockDict = {}
                stockAllocations = div.find('ul', {'class': 'allocation-list'})
                if(stockAllocations == None):
                    continue
                stocks = stockAllocations.find_all('span', {'class': 'u-ellipsis'})
                percentages = stockAllocations.find_all('span', {'class': 'percent'})
                stocks = list(OrderedDict.fromkeys(stocks)) #remove duplicates
                # c= [c.text.strip() for c in stocks]
                # print(c)
                # p = [p.text.strip() for p in percentages]
                # print(p)
                for i in range(len(stocks)):
                    percentageString = percentages[i].text.strip().replace('%', '').replace(',', '.').replace('−', '-')
                    percentegeFloat = round(float(percentageString)/100, 4)
                    stockDict[stocks[i].text.strip()] = percentegeFloat
                stocksDF = pd.DataFrame(list(stockDict.items()))

            else:
                #do nothing
                pass
                
        return {'key-data': keyDataDF, 'instruments': stocksDF, 'sectors': sectorDF, 'countries': countryDF}

    def fundsBreakdown(self):
        print("#################### FUNDS #####################")
        df = self.funds
        Utils.printDf(df)
        finalSectorAlloc = pd.DataFrame(columns=[0, 1])
        finalCountryAlloc = pd.DataFrame(columns=[0, 1])
        finalInstrumentAlloc = pd.DataFrame(columns=[0, 1])
        for instrument in df['Asset']:
            print('instrument: ', instrument)
            data = self.parseFundDetailsPage(instrument)
            fundData = data.get('key-data')
            # add fund data to the fund dataframe
            for row in fundData.itertuples():
                key = row._1
                value = row._2
                df.loc[df['Asset'] == instrument, key] = value
            
            instrumentAlloc = data.get('instruments')
            sectorAlloc = data.get('sectors')
            countryAlloc = data.get('countries')
            weight = df.loc[df['Asset'] == instrument, 'Weight'][0]

            if instrumentAlloc is not None:
                instrumentAlloc[1] = instrumentAlloc[1].multiply(weight)
                finalInstrumentAlloc = pd.merge(instrumentAlloc, finalInstrumentAlloc, how='outer', left_on=0, right_on=0, suffixes=('_left', '_right'))
            # calculate total exposure
            if sectorAlloc is not None:
                sectorAlloc[1] = sectorAlloc[1].multiply(weight)
                finalSectorAlloc = pd.merge(sectorAlloc, finalSectorAlloc, how='outer', left_on=0, right_on=0, suffixes=('_left', '_right'))
            
            if countryAlloc is not None:
                countryAlloc[1] = countryAlloc[1].multiply(weight)
                finalCountryAlloc = pd.merge(countryAlloc, finalCountryAlloc, how='outer', left_on=0, right_on=0, suffixes=('_left', '_right'))

        # total exposure
        finalSectorAlloc = self.modifyAllocationDF(finalSectorAlloc)
        Utils.printDf(finalSectorAlloc.sort_values('Weight', ascending=False))
        
        finalCountryAlloc = self.modifyAllocationDF(finalCountryAlloc)
        
        ######################################

        wb = Utils.readExcel('ctryprem2020.xlsx')
        #sheet_names = wb.sheet_names()
        #print('Sheet Names', sheet_names)
        erpByCountry = wb.sheet_by_name('ERPs by country')
        #headings index is 6
        headings = erpByCountry.row_values(6) 

        def getCountryRiskPremium(x):
            country = x[0]
            #loop over content
            for row in range(7, erpByCountry.nrows):
                excelCountry = erpByCountry.cell(row, 0).value
                if(country==excelCountry):
                    region = erpByCountry.cell(row, 1).value
                    rating = erpByCountry.cell(row, 2).value
                    defaultSpread = erpByCountry.cell(row, 3).value
                    erp = erpByCountry.cell(row, 4).value
                    countryRiskPremium = erpByCountry.cell(row, 5).value
                    x['Region'] = region
                    x[headings[2]] = rating
                    x[headings[3]] = defaultSpread
                    x[headings[4]+'(Damodaran)'] = erp
                    x[headings[5]] = countryRiskPremium
                    break
                elif (country == 'Other'):
                    # take the global weighted average from damodarans sheet
                    regionalWeightedAverageSheet = wb.sheet_by_name('Regional Weighted Averages')
                    globalERP = regionalWeightedAverageSheet.cell(178,1).value
                    globalCountryRiskPremium = regionalWeightedAverageSheet.cell(178, 2).value
                    globalDefaultSpread = regionalWeightedAverageSheet.cell(178, 3).value
                    x['Region'] = 'Global'
                    x[headings[3]] = globalDefaultSpread
                    x[headings[4]+'(Damodaran)'] = globalERP
                    x[headings[5]] = globalCountryRiskPremium
                    break
            return x
        ######################################

        finalCountryAlloc = finalCountryAlloc.apply(getCountryRiskPremium, axis=1)
        Utils.printDf(finalCountryAlloc.sort_values('Weight', ascending=False))

        finalInstrumentAlloc = self.modifyAllocationDF(finalInstrumentAlloc)
        Utils.printDf(finalInstrumentAlloc.sort_values('Weight', ascending=False))
        # conditions = [
        #     df['Asset'] == 'AMF Räntefond Lång',
        #     df['Asset'] == 'Avanza Emerging Markets',
        #     df['Asset'] == 'Avanza Global',
        #     df['Asset'] == 'Länsförsäkringar Tillväxtmrkd Idxnära A',
        #     df['Asset'] == 'Spiltan Aktiefond Investmentbolag',
        #     df['Asset'] == 'Spiltan Globalfond Investmentbolag',
        #     df['Asset'] == 'SPP Aktiefond Europa',
        #     df['Asset'] == 'Swedbank Robur Access Asien',
        #     df['Asset'] == 'DBX MSCI EUROPE ETF (DR)',
        #     df['Asset'] == 'Handelsbanken Gl Småbolag Ind Cri A1 SEK',
        #     df['Asset'] == 'SPP Global Företagsobligations Plus A',
        #     df['Asset'] == 'Atlant Stability',
        #     df['Asset'] == 'Pacific Precious A',
        #     df['Asset'] == 'IKC Avkastningsfond',
        #     df['Asset'] == 'AMF Räntefond Mix',
        #     df['Asset'] == 'Avanza Europa',
        #     df['Asset'] == 'Avanza Zero',
        #     df['Asset'] == 'Länsförsäkringar Global Indexnära'
        # ]

        # outputs = [
        # 'Interests', 
        # 'Emerging Markets',
        # 'Global', 
        # 'Emerging Markets', 
        # 'Nordics', 
        # 'Global', 
        # 'Europe', 
        # 'Emerging Markets',
        # 'Europe',
        # 'Global',
        # 'Interests',
        # 'Interests',
        # 'Commodities',
        # 'Interests',
        # 'Interests',
        # 'Europe',
        # 'Nordics',
        # 'Global'
        # ]

        # res = np.select(conditions, outputs, 'Other')
        # df = df.assign(Region=pd.Series(res).values)

        def conditions(s):
            C = s['Category']
            if (('Global' in C) or ('MISC' in C)):
                return 'Global'
            elif (('Emerging' in C) or ('Asia ex Japan' in C)):
                return 'Emerging Markets'
            elif ('Europe' in C):
                return 'Europe'
            elif (('Sweden' in C)):
                return 'Sweden'
            elif('Hedgefund' in C):
                return '-'
            else: 
                return '-'

        df['Region'] = df.apply(conditions, axis=1)
        
        # Calculate Equity Weights
        em = df[(df.Region == 'Emerging Markets') & (df.Type == 'Equity')].Weight.sum()
        glob = df[(df.Region == 'Global') & (df.Type == 'Equity')].Weight.sum()
        nord = df[((df.Region == 'Nordics') | (df.Region == 'Sweden')) & (df.Type == 'Equity')].Weight.sum()
        eur = df[(df.Region == 'Europe') & (df.Type == 'Equity')].Weight.sum()

        # Calculate Fixed Income Weights
        interests = df[df.Type == 'Fixed Income'].Weight.sum()

        # Calulate Alternative Fund Weights 
        alternative = df[df.Type == 'Alternative'].Weight.sum()

        # Assert portfolio weight sums to 1
        
        assert((em + glob + nord + eur + interests + alternative) == 1)

        # print fund allocation
        print('EMERGING MARKETS EQUITY:', em)
        print('GLOBAL EQUITY:', glob)
        print('SWEDEN(NORDICS) EQUITY:', nord)
        print('EUROZONE EQUITY:', eur)
        print('FIXED INCOME', interests)
        print('ALTERNATIVE INVESTMENTS:', alternative)

        def rebalance(w, t):
            '''Rebalancing function that assumes portfolio value is fix, takes the current weight w and the target weight t 
            and calculates SEK value to Sell/Buy to achieve target '''
            totValue = df['Market Value'].sum()
            totalBuyAmount = 0
            investedInType = w * totValue

            loops = 0
            new_weight = w
            while True:
                loops += 1
                # break when close enough or loops is at max limit
                if(np.isclose(new_weight, t, rtol=1e-03, atol=1e-04) or loops == 20000):
                    #print(new_weight ,totalBuyAmount, t, loops)
                    break

                # Underweight 
                if (new_weight <= t):
                
                    # current SEK amounts
                    investedInType += 100
                    totalBuyAmount += 100
                    new_weight = investedInType/totValue
                    

                # Overweight
                if (new_weight >= t):
                
                    # decrease by 100kr
                    investedInType -= 100
                    totalBuyAmount -= 100
                    
                    new_weight = investedInType/totValue
                
            return totalBuyAmount
        
        x = rebalance(em,  self.target_developing_markets)

        y = rebalance(glob, self.target_global)

        z = rebalance(nord,  self.target_nordic)

        å = rebalance(eur, self.target_eu)

        ä = rebalance(interests, self.target_bonds)

        ö = rebalance(alternative, self.target_alternative)

        # make sure margin of error is between these two ranges
        assert(-500 < x + y+ z+ å + ä + ö < 500)
        print('Adjust EM', x, 'KR')
        print('Adjust Glob', y , 'KR')
        print('Adjust Nord', z , 'KR')
        print('Adjust EUR', å, 'KR')
        print('Adjust Fixed income', ä, 'KR')
        print('Adjust Alternative', ö, 'KR')
        Utils.printDf(df)
        
        print("#################### END OF FUNDS #####################")
        


    def modifyAllocationDF(self, df):
        df.loc[:,'Weight'] = df.sum(axis=1)  # take the sum accros each row and store in new col Weight
        df = df.iloc[:,[0, -1]] # extract the column containing instrument name and their Total sum
        df = df.round(4) # round everything
        tot = df['Weight'].sum() # sum accross column 
        df = df.append([{0: 'Other', 'Weight': 1-tot}], ignore_index=True)   # add new row called other
        assert (round(df['Weight'].sum(), 4) == 1)  # make sure the new sum is 1
        return df

    def saveStockInfoToExcel(self):
        """ Turns txt files containing stock info to an excel file """ 
        for asset in self.stocks['Asset']:
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
            
            incomeStatementSummary = financialSummary.iloc[1:6].astype(float)
            latestYear = incomeStatementSummary.columns.values[-1]
            latestEPS = incomeStatementSummary.loc['Basic EPS', latestYear]
            self.stocks.loc[self.stocks['Asset'] == asset, f'EPS ({latestYear})'] = latestEPS
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
            entireIncomeStatement.name = 'Income Statement'

            entireBalanceSheet = dataframeList[1]
            entireBalanceSheet = organizeDataframe(entireBalanceSheet)
            entireBalanceSheet.name = 'Balance Sheet'

            entireCashFlowStatement = dataframeList[2]
            entireCashFlowStatement = organizeDataframe(entireCashFlowStatement)
            entireCashFlowStatement.name = 'Cash Flow Statement'
            # print("INCOME STATEMENT")
            # Utils.printDf(entireIncomeStatement)
            # print("BALANCE SHEET")
            # Utils.printDf(entireBalanceSheet)
            # print("CASHFLOW STATEMENT")
            # Utils.printDf(entireCashFlowStatement)

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
        Utils.printDf(self.stocks)


    def stocksBreakdown(self):
 
        wb =  Utils.readExcel('indname.xls')
        companyExcelList = wb.sheet_by_name('Industry sorted (Global)')

        ## complex string lookup, MIGHT NEED ATTENTION LATER
        for asset in self.stocks['Asset']:
            matches = {}
            # Treat this complex case, only one that does not get market correct currently, NEED IMPROVEMENT LATER
            if (asset == 'SCA B'):
                asset = 'Svenska Cellulosa Aktiebolaget'
            for row in range(1, companyExcelList.nrows):
                excelName = companyExcelList.cell(row, 1).value
                matchRatio =  fuzz.ratio(excelName.lower(), asset.lower())
                partialRatio = fuzz.partial_ratio(excelName.lower(), asset.lower())
                if((matchRatio > 61 and asset.split(' ')[0] + ' ' in excelName) or (partialRatio > 75 and asset.split(' ')[0] + ' ' in excelName)):
                    # print('partial:', partialRatio, 'full:', matchRatio)
                    # print(asset, excelName)
                    industryGroup = companyExcelList.cell(row, 0).value
                    ticker = companyExcelList.cell(row, 2).value
                    country = companyExcelList.cell(row, 3).value
                    broadRegion = companyExcelList.cell(row, 4).value
                    subRegion = companyExcelList.cell(row, 5).value
                    # print(asset, excelName, industryGroup, ticker, country, broadRegion, subRegion)
                    matches[excelName] = [ticker, country, broadRegion, subRegion, industryGroup]
                    

            if len(matches) > 1:
                highest = process.extractOne(asset.lower(), list(matches.keys()))
                d = matches.get(highest[0])
            
            elif len(matches) < 1:
                #print('NO MATCH:', asset) 
                d = []
            else:
                d = list(matches.values())[0] 

            # reverse special case
            if asset == 'Svenska Cellulosa Aktiebolaget':
                asset = 'SCA B'

            if len(d) > 0:
                self.stocks.loc[self.stocks['Asset'] == asset, 'Ticker'] = d[0]
                self.stocks.loc[self.stocks['Asset'] == asset, 'Country'] = d[1]
                self.stocks.loc[self.stocks['Asset'] == asset, 'Broad Region'] = d[2]
                self.stocks.loc[self.stocks['Asset'] == asset, 'Sub Region'] = d[3]
                self.stocks.loc[self.stocks['Asset'] == asset, 'Industry Group (Damodaran)'] = d[4]
            
            financialsWB = Utils.readExcel(f'{asset}.xlsx')
            if(financialsWB == FileNotFoundError):
                print(financialsWB)
            # do calculations TO BE DONE
        moneyLosingStocks = self.stocks[(self.stocks['EPS (2019)'] < 0) | (self.stocks['EPS (2018)'] < 0)]
        moneyLosingStocks.Weight.sum()

        if moneyLosingStocks.Weight.sum() > self.max_growth_stocks: # growth stocks are money losing
            print('TO MUCH MONEY IN MONEY LOSING STOCKS')
            # CALCULATE HOW MUCH TO SELL IN TERMS OF SEK IN ANY OF OR A MIX OF THE MONEY LOSING COMPANIES



        Utils.printDf(self.stocks)
    
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
        
        # poll for elements for 5 seconds max, before shutdown
        browser.implicitly_wait(0)
        wait = WebDriverWait(browser, 35)

        latest_button_xpath = ""

        def waitforload():
             wait.until(lambda d: d.execute_script(
                'return (document.readyState == "complete" || document.readyState == "interactive")')
            )

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
                    waitforload()
                    return
                except (UnexpectedAlertPresentException, TimeoutException) as e:
                    browser.refresh()
                    retries += 1
                    print(latest_button_xpath)
                    clickElement(latest_button_xpath)
            raise(e)

        def clickElement(XPATH):
            retries = 0
            while retries < 5:
                print('Clicking Element:', XPATH)
                print('Attempt Number:', retries + 1)
                try:
                    button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, XPATH))
                    )
                    coordinates = button.location_once_scrolled_into_view
                    browser.execute_script(f'window.scrollTo({coordinates["x"]}, {coordinates["y"]});') #scroll to element
                    ActionChains(browser).move_to_element(button).perform() #hover ove
                    button.click()
                    waitforload()
                    return
                except (TimeoutException, NoSuchElementException, ElementClickInterceptedException, \
                    UnexpectedAlertPresentException) as e:
                    browser.refresh()
                    retries += 1
            
            raise(e)

        url = "http://www.nasdaqomxnordic.com/shares"

        browser.get(url)

        midCapXPATH = "/html/body/section/div/div/div/section/div/article/div/section/form/div[4]/ul/li[2]"
        smallCapXPATH = "/html/body/section/div/div/div/section/div/article/div/section/form/div[4]/ul/li[3]"

        clickElement(midCapXPATH)

        clickElement(smallCapXPATH)

        ## Wait until table loading dissapears
        loadingImgXPATH = "/html/body/section/div/div/div/section/div/article/div/div[2]/img"
        wait.until(
            EC.invisibility_of_element_located((By.XPATH, loadingImgXPATH))
        )
        
        ## add links to dicts 
        foundAssetsDict = {}
        notFound = []
        print("Searching For Assets In Main Market...")
        for assetName in df['Asset']:
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

            clickElement(firstNorthXPATH)                  
            firstNorthGMXPATH = latest_button_xpath = "/html/body/section/div/div/div/section/div/article/div/section/form/div[5]/ul/li[2]"

            clickElement(firstNorthGMXPATH)
            
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
            try:
                # go to asset page
                browser.get(href)
                
                keyRatiosXPATH = latest_button_xpath = "/html/body/section/div/div/div/section/section/section/nav/ul/li[4]/a"
                
                clickElement(keyRatiosXPATH)

                # Switch to iframe containing morningstar data
                switchToMorningstarFrame()
                

                # Get Page Source
                keyRatiosPage = browser.page_source    
                soup = BeautifulSoup(keyRatiosPage, 'lxml')
                Utils.saveTxtFile(str(soup.prettify()), f'{asset}_keyRatios') # Save file

                # switch back to original frame
                browser.switch_to.default_content()

                overviewXPATH = latest_button_xpath = "/html/body/section/div/div/div/section/section/section/nav/ul/li[2]/a"

                clickElement(overviewXPATH)

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
                
                clickElement(companyFinancialsXPATH)

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
                #downloadFactsheet(browser, asset, downloadDir)

                
                 
            except (TimeoutException, NoSuchElementException) as e:
                raise(e)
             
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

def downloadFactsheet(browser, name, directory):
    
    factsheetLinkXPATH = "/html/body/section/div/div/div/section/section/section/nav/ul/li[6]/a"
    factsheetLink = wait.until(
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



