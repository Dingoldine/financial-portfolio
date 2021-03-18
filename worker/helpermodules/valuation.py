#cSpell:disable 
from helpermodules import Utils
import numpy as np
def valuation(asset):
    # Name
    try:
        financialsWB = Utils.readExcel(f'{asset}.xlsx')
        stocksOverviewWB = Utils.readExcel('Stocks.xlsx')

        overviewSheet = stocksOverviewWB.sheet_by_index(0)
       
        #Get Sheets
        incomestatementSheet = financialsWB.sheet_by_name('Income Statement')
        balanceSheet = financialsWB.sheet_by_name('Balance Sheet')

        # Industry / Sector
        for rowidx in range(overviewSheet.nrows):
            row_values = overviewSheet.row_values(rowidx)
            if row_values[0] == asset:
                countryOfIncorporation = row_values[8]
                sector = row_values[11]

        # Cost of capital Calculation
        ERP = getEquityRiskPremium(countryOfIncorporation)
        getCostOfCapital(sector)
        print(countryOfIncorporation, ERP)

        # get financial data INCOME STATEMENT  
        # Revenues last 2 years
        # Operating income before interest and taxes (EBIT) last 2 years'
        # Non-operating income (FOR IMPROVEMENT EXTRACT THE INTEREST EXPENSE ONLY) last 2 years
        for rowidx in  range(incomestatementSheet.nrows):
            row_values = incomestatementSheet.row_values(rowidx)
            accountingEntry = row_values[0]
            if accountingEntry == "Revenue":
                revenues = row_values[-2:]
            elif accountingEntry == "Operating income before interest and taxes":
                ebit = row_values[-2:]
            elif accountingEntry == "Non-operating income": # Should Only be interest expenses (often need to look in footnotes manually)
                nonOpIncome = row_values[-2:]
            elif accountingEntry == "Provision for income taxes":
                taxesPaid = np.array(row_values[-2:])
            elif accountingEntry == "Income before income taxes":
                taxableIncome = np.array(row_values[-2:])

        print(revenues, ebit, nonOpIncome, taxableIncome, taxesPaid)
        # get financial data Balance Sheet
        #Cash and Marketable Securities last 2 years (Total cash, cash equivalents, and short-term investments)
        # Total Liabilities (BOOK Value of Debt in balance sheet) last 2 years
        # Total Stockholders Equity (Last 2 Years)
        for rowidx in range(balanceSheet.nrows):
            row_values = balanceSheet.row_values(rowidx)
            accountingEntry = row_values[0]
            if accountingEntry == "Total cash, cash equivalents, and short-term investments":
                cash = row_values[-2:]
            elif accountingEntry == "Total Liabilities":
                totalLiabilities = np.array(row_values[-2:])
            elif accountingEntry == "Total stockholders' equity": # Should Only be interest expenses (often need to look in footnotes manually)
                totalEquity = np.array(row_values[-2:])
            elif accountingEntry == "Minority Interests": # Should Only be interest expenses (often need to look in footnotes manually)
                minorityInterests = np.array(row_values[-2:])

        print(cash, totalLiabilities, totalEquity, totalLiabilities/totalEquity, minorityInterests)

        # Capitalize R&D expences, last 1-10 years
        RandD = []
        capResAndDev(RandD)

        # handle Operating lease commitment as debt? 
        handleLeases()
        
        # Effective Tax Rate
        """ Enter your effective (not marginal) tax rate for your firm. You will find this in your 
        company's annual report. If you cannot, you can compute it as follows, 
        from the income statement: Effective tax rate = Taxes paid/ Taxable income
        If your effective tax rate varies across years, you can use an average. 
        If the effective tax rate is less than zero, enter zero.
        If you have a money losing company, don't enter zero
        but enter the tax rate that you will have when you start making money.
        """
        # Most recent or an average ?? 
        effectiveTaxrate = taxesPaid/taxableIncome
        print(effectiveTaxrate)
        
        # Marginal Tax Rate
        """
        This is a statutory tax rate. I use the tax rate of the country the company is domiciled in. 
        """
        wb = Utils.readExcel('ctryprem2020.xlsx')
        regionalBreakdownSheet = wb.sheet_by_name('Regional breakdown')
        for row in range(7, regionalBreakdownSheet.nrows):
            excelCountry = regionalBreakdownSheet.cell(row, 0).value
            if(countryOfIncorporation==excelCountry):
                marginalTaxrate = regionalBreakdownSheet.cell(row, 7).value
        print(marginalTaxrate)

        # Cross holdings and other non-operating assets
        """ Enter the market value of those non-cash assets whose earnings are 
        (and will never) show up as part of operating income. 
        The most common non-operating assets are minority holdings in other companies
        (which are not consoldiated). You can find the book value of these holdings on the balance sheet, 
        but see if you can convert to market value. 
        (I apply a price to book ratio, based on the sector that the company is in to the book value)
        ."""
        # Minority Interests
        """
        Enter the "market" value of minority interests. This is a uniquely accounting item 
        and will be on the liability side of your company's balance sheet. It reflects the requirement 
        that if you own more than 50% of another company or have effective control of it, 
        you have to consolidate that company's statements with yours. Thus, you count 100% of that
        subsidiaries assets, revenues and operating income with your company, even if you own only 60%. 
        The minority interest reflects the book value of the 40% of the equity in the subsidiary 
        that does not belong to you. Again, it is best if you can convert the book value to a 
        market value by applying the price to book ratio for the sector in which the 
        subsidiary operates 
        """
        if len([x for x in minorityInterests if x != 0]):
            handleMinorityInterests()
        
        # Shares Outstanding


        # Current Stock Price


    except:
        raise


def getEquityRiskPremium(country):
    ## TO DO ###
    # get income per operating region or income by operating country 
    # (HAVE TO LOOK IN ANNUAL REPORT MANUALLY)
    
    # for now just go with incorporated country
    wb = Utils.readExcel('ctryprem2020.xlsx')
    erpByCountry = wb.sheet_by_name('ERPs by country')
    for row in range(7, erpByCountry.nrows):
        excelCountry = erpByCountry.cell(row, 0).value
        if(country==excelCountry):
          erp = erpByCountry.cell(row, 4).value

    return erp

# currently can't handle multi-business companies
def getCostOfCapital(sector, multibusiness = False):
    print(sector)


    if not (multibusiness):


        pass
    pass

def handleMinorityInterests():
    print('handle minority interests')

def capResAndDev(RandD):
    pass

def handleLeases():
    pass