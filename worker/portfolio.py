import numpy as np
import pandas as pd
import requests
from requests.exceptions import HTTPError

# financial apis 
# from pandas_datareader.iex import IEX
# from alpha_vantage.timeseries import TimeSeries
# from alpha_vantage.sectorperformance import SectorPerformances

# from __future__ import print_function
# import intrinio_sdk
# from intrinio_sdk.rest import ApiException
# from pprint import pprint

import constants

from bs4 import BeautifulSoup
import time
from collections import OrderedDict
from helpermodules import Excel, Utils
import constants
#load .env file 
from dotenv import load_dotenv
load_dotenv()
#access dotenv variables
import os
import sys
import re

# for complex string matching
from fuzzywuzzy import fuzz, process

# try:  
#    alphaVantageKey = os.environ.get("ALPHA_VANTAGE_APIKEY")
#    iexCloudKey = os.environ.get("IEX_CLOUD_APIKEY")
#    intrinioKey = os.environ.get("INTRINIO_APIKEY")
# except KeyError: 
#    print("Please set the environment variables")
#    sys.exit(1)
   
# # setup api 
# intrinio_sdk.ApiClient().configuration.api_key['api_key'] = intrinioKey
# sp = SectorPerformances(key=alphaVantageKey, output_format='pandas')
# ts = TimeSeries(key=alphaVantageKey,output_format='pandas', indexing_type='integer')

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

    def __init__(self, dataframes, funds_info):
        assert(self.target_bonds + self.target_developing_markets + self.target_global + \
            self.target_nordic + self.target_alternative + self.target_eu == 1) # make sure fund allocation rules make sense
        
        # for pandas version >= 0.21.0
        df_map = pd.read_excel(f'{constants.excelSaveLocation}/portfolio.xlsx', sheet_name=None)
        self.stocks = df_map.get("Stocks", None)
        funds = df_map.get("Funds", None)
        etfs = df_map.get("ETFs", None)
        # merge ETFs and funds
        frames = [funds, etfs]
        concat_funds = pd.concat(frames, keys=['Funds', 'ETFs'])
        self.funds = concat_funds
        self.certificates = df_map.get("Certificates", None)
        self.summary = df_map.get("Potfolio Summary", None)
        
        if self.certificates is not None:
            self.cert_value = self.certificates['Market Value'].sum()
            self.certificates['Weight'] = self.certificates['Market Value'] /  self.cert_value
        else:
            self.cert_value = 0
        self.stocks_value = self.stocks['Market Value'].sum()   
        self.funds_value = self.funds['Market Value'].sum()
        

        self.portfolio_value = self.stocks_value + self.funds_value + self.cert_value

        self.stocks['Weight'] = self.stocks['Market Value'] /  self.stocks_value
        self.funds['Weight'] = self.funds['Market Value'] /  self.funds_value
        
    def getStocks(self):
        return self.stocks
    def getFunds(self):
        return self.funds

    def generateStocksExcel(self):
        Excel.create([self.stocks], "Stocks", 1)
    
    def checkRules(self):
        stock_weight = self.stocks_value/self.portfolio_value
        fund_weight = self.funds_value/self.portfolio_value
        cert_weight = self.cert_value/self.portfolio_value

        # REDO WITH NUMPY CLOSE TO
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
        print(instrument)
        soup = BeautifulSoup(html, 'lxml')
        fee_tag = soup.find("h2", attrs= {'data-e2e': 'fon-guide-total-fee'})

        if (fee_tag):
            fee = fee_tag.text.strip()
        else:
            raise Exception("Attribute 'data-e2e': 'fon-guide-total-fee' not fouund")

        keyData = soup.find_all('div', {'class': 'border-space-item'})
        
        keyDataDict = {'Fee': fee}

        translationDict = constants.translationDict

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
                    percentageFloat = round(float(percentageString)/100, 4)
                    country = countries[i].text.strip()
                    countryInEnglish = translationDict.get(country)
                    if (countryInEnglish == None):
                        countryInEnglish = country
                    countryDict[countryInEnglish] = percentageFloat
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
                    percentageFloat = round(float(percentageString)/100, 4)
                    sectorDict[sectors[i].text.strip()] = percentageFloat
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
                    percentageFloat = round(float(percentageString)/100, 4)
                    stockDict[stocks[i].text.strip()] = percentageFloat
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

        # convert dtypes
        df['Index Fund'] = df['Index Fund'].map({'Yes': 1, 'No': 0}).astype(bool, errors='raise')
        df['UCITS'] = df['UCITS'].map({'Yes': 1, 'No': 0}).astype(bool, errors='raise')
        df['Start date'] = df['Start date'].apply(pd.to_datetime, errors='raise')
        df['Owners at Avanza'] = df['Owners at Avanza'].str.replace('st', '').str.replace('\s', '', regex=True).apply(pd.to_numeric, errors='raise')
        df['AUM'] = df['AUM'].str.replace('\s|MSEK', '', regex=True).apply(pd.to_numeric, errors='raise') * np.power(10, 6)
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
            # the below 2 are questionable
            elif('Hedgefund' in C):
                return '-'
            elif('Sectorfund' in C):
                 return 'Global'
            else: 
                return '-'

        df['Region'] = df.apply(conditions, axis=1)
 
        # Calculate Equity Weights
        em = df[(df.Region == 'Emerging Markets') & (df.Type == 'Equity')].Weight.sum()
        glob = df[(df.Region == 'Global') & (df.Type == 'Equity')].Weight.sum()
        nord = df[((df.Region == 'Nordics') | (df.Region == 'Sweden')) & (df.Type == 'Equity')].Weight.sum()
        eur = df[(df.Region == 'Europe') & (df.Type == 'Equity')].Weight.sum()

        # Calculate Fixed Income Weights
        interests = df[df.Type.str.contains("Fixed Income")].Weight.sum()
        print(df.Weight.sum())
        # Calulate Alternative Fund Weights 
        alternative = df[df.Type == 'Alternative'].Weight.sum()
        

        s = em + glob + nord + eur + interests + alternative
        # Assert portfolio weight sums to 1
        Utils.printDf(df)
        print(s)
        assert(np.isclose(s, 1, rtol=1e-03, atol=1e-04))

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
        assert(-500 < x + y + z + å + ä + ö < 500)


        # print fund allocation
        print('EMERGING MARKETS EQUITY:', em)
        print('GLOBAL EQUITY:', glob)
        print('SWEDEN(NORDICS) EQUITY:', nord)
        print('EUROZONE EQUITY:', eur)
        print('FIXED INCOME', interests)
        print('ALTERNATIVE INVESTMENTS:', alternative)
        print('Adjust EM', x, 'KR')
        print('Adjust Glob', y , 'KR')
        print('Adjust Nord', z , 'KR')
        print('Adjust EUR', å, 'KR')
        print('Adjust Fixed income', ä, 'KR')
        print('Adjust Alternative', ö, 'KR')

        fundAllocationData = [
            ["Emerging Markets Equity", em, self.target_developing_markets, f'Adjust by {x} Kr'],
            ["Global Equity", glob, self.target_global, f'Adjust by {y} Kr'],
            ["Sweden(Nordics) Equity", nord, self.target_nordic,  f'Adjust by {z} Kr'],
            ["Eurozone Equity", eur, self.target_eu,  f'Adjust by {å} Kr'],
            ["Fixed Income", interests, self.target_bonds,  f'Adjust by {ä} Kr'],
            ["Alternative Investments", alternative, self.target_alternative,  f'Adjust by {ö} Kr']
        ]
        
        # Get ready for create excel
        fundAllocationDf = pd.DataFrame(fundAllocationData, columns = ['Type', 'Weight', 'Target Weight', 'Actions']) 
        fundAllocationDf.name = "Weight Breakdown"
        fundAllocationDf.set_index(fundAllocationDf.columns.values[0], inplace=True) # Turn leftmost column to index
        # Utils.printDf(df)
        finalCountryAlloc.name = "By Country Breakdown"
        finalCountryAlloc.set_index(finalCountryAlloc.columns.values[0], inplace=True) # Turn leftmost column to index

        finalSectorAlloc.name = "By Sector Breakdown"
        finalSectorAlloc.set_index(finalSectorAlloc.columns.values[0], inplace=True) # Turnmost left column to index
        
        finalInstrumentAlloc.name = "By Instrument Breakdown"
        finalInstrumentAlloc.set_index(finalInstrumentAlloc.columns.values[0], inplace=True) # Turn leftmost column to index

        df = df.reset_index().drop(["level_0","level_1"], axis=1)
        leftMostCol = df.columns.values[0]
        df.set_index(leftMostCol, inplace=True) # Turn this column to index
        df.name = 'Funds'
        dataframeList = [
            df,
            fundAllocationDf,
            finalInstrumentAlloc,
            finalCountryAlloc,
            finalSectorAlloc
        ]

        self.funds = df
        self.funds.name = "Funds"
        Excel.create(dataframeList, 'Funds', 1, "Currency is in SEK")
        print("#################### END OF FUNDS #####################")
        


    def modifyAllocationDF(self, df):
        df.loc[:,'Weight'] = df.sum(axis=1)  # take the sum accros each row and store in new col Weight
        df = df.iloc[:,[0, -1]] # extract the column containing instrument name and their Total sum
        df = df.round(4) # round everything
        tot = df['Weight'].sum() # sum accross column 
        df = df.append([{0: 'Other', 'Weight': 1-tot}], ignore_index=True)   # add new row called other
        assert (round(df['Weight'].sum(), 4) == 1)  # make sure the new sum is 1
        return df

    
    def stocksBreakdown(self):
        print("#################### STOCKS #####################")
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
            
            # get stock financials
            try:
                financialsWB = Utils.readExcel(f'{asset}.xlsx')

                # get sheets
                overviewSheet = financialsWB.sheet_by_name('Overview')
                incomestatementSheet = financialsWB.sheet_by_name('Income Statement')
                
                for rowidx in range(overviewSheet.nrows):
                    row = overviewSheet.row_values(rowidx)
                    if ((row[0] != "") and not ('except "Basic EPS"' in row[0])): # disregard currency row and empty rows
                        self.stocks.loc[self.stocks['Asset'] == asset, row[0]] = row[1]

                for rowidx in range(incomestatementSheet.nrows):
                    row_values = incomestatementSheet.row_values(rowidx)
                    
                    if row_values[0] == "Basic": #basic eps
                        latestEps = row_values[incomestatementSheet.ncols - 1] # latest year
                        latestYear = incomestatementSheet.cell_value(0, incomestatementSheet.ncols - 1)
                        self.stocks.loc[self.stocks['Asset'] == asset, f'EPS ({latestYear})'] = latestEps
            except FileNotFoundError:
                pass
                
            # industry betas
            indDamodaran = self.stocks.loc[self.stocks['Asset'] == asset, 'Industry Group (Damodaran)'].values[0]
            print(indDamodaran)
            try:
                betasGlobalWB = Utils.readExcel('betasGlobal.xls')
                betasUSWB = Utils.readExcel('betasUS.xlsx')

                beta_global_averages = betasGlobalWB.sheet_by_name('Industry Averages')
                beta_us_averages = betasUSWB.sheet_by_name('Industry Averages')

                # global 
                for rowidx in range(beta_global_averages.nrows):
                    row_values = beta_global_averages.row_values(rowidx)
                    if row_values[0] == indDamodaran:
                        self.stocks.loc[self.stocks['Asset'] == asset, 'Unlevered beta (Global)'] = row_values[5]
                
                # us
                for rowidx in range(beta_us_averages.nrows):
                    row_values = beta_us_averages.row_values(rowidx)
                    if row_values[0] == indDamodaran:
                        self.stocks.loc[self.stocks['Asset'] == asset, 'Unlevered beta (US)'] = row_values[5]
            
            except FileNotFoundError:
                raise
     
        theFilter = [col for col in self.stocks if col.startswith('EPS')]
        moneyLosingStocks = self.stocks.loc[(self.stocks[theFilter] < 0).any(axis=1), :]
        Utils.printDf(moneyLosingStocks)
        moneyLosingWeight = moneyLosingStocks.Weight.sum()

        if moneyLosingWeight > self.max_growth_stocks: # growth stocks are money losing
            difference = moneyLosingWeight - self.max_growth_stocks
            # print(self.max_growth_stocks, moneyLosingWeight, difference)
            amountShouldSell = self.stocks['Market Value'].sum() * difference
            print(f'Sell {amountShouldSell} in any/or a mixture of {moneyLosingStocks.Asset.values} to be compliant with portfolio rules')
            # CALCULATE HOW MUCH TO SELL IN TERMS OF SEK IN ANY OF OR A MIX OF THE MONEY LOSING COMPANIES
        
        # convert employees col to int, but IT DOESNT WOR BECAUSE NAN VALUES EXIST IN FRAME, AND THUS IN PANDAS IT WILL BE FLOAT
        self.stocks["Employees"] = self.stocks["Employees"].apply(pd.to_numeric, errors="coerce")
    
        self.stocks.name = "Stocks"
        leftMostCol = self.stocks.columns.values[0]
        self.stocks.set_index(leftMostCol, inplace=True) # Turn this column to index

        print("#################### END OF STOCKS #####################")
