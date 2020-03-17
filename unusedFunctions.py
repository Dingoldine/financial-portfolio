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

def readStockInfoFromExcel(self, asset):
    keys = ['Margins (in % of sales)', 'Profitability', 'Compound Revenue Growth', 
    'Compound OpMargin Growth', ' EPS Growth', 'Cash Flow', 'Balance Sheet Items(in % Terms)', 
    'Liquidity-Financial Health', 'Efficiency', 'Income Statement Summary', 'Balance Sheet Summary', 
    'Cash Flow Summary', 'Ratios', 'Dividends']
    # df_map = pd.read_excel(f'{saveLocation}/portfolio.xlsx', sheet_name=None)