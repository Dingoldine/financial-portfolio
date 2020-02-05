# Intrinio Company Search, ALSO NEED PAYMENT 
""" 
company_api = intrinio_sdk.CompanyApi()

page_size = 10 # int | The number of results to return (optional) (default to 100)
for assetName in df['Asset']:
    query = assetName # str | Search parameters
    try:
        api_response = company_api.search_companies(query, page_size=page_size)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling CompanyApi->search_companies: %s\r\n" % e)

    try:
        searchEndpoint = f'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={assetName}&apikey={alphaVantageKey}'
        api_response = company_api.get_company(assetName)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling CompanyApi->get_company: %s\r\n" % e)

"""
############################################
# Alpha Vantage, search for symbol 
"""       
for assetName in df['Asset']:
    print(assetName)
    searchEndpoint = f'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={assetName}&apikey={alphaVantageKey}'
    try:
        response = requests.get(searchEndpoint)
        # If the response was successful, no Exception will be raised
        response.raise_for_status()
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')  # Python 3.6
    except Exception as err:
        print(f'Other error occurred: {err}')  # Python 3.6
    else:
        print('Success!')
        jsonResponse = response.json()
        # if still able to make call because of api limit
        searchResult = jsonResponse.get('bestMatches', 'error')
        if not (searchResult == 'error'):
            # if actually recieve any results 
            if (len(searchResult) > 0):
                bestMatch = searchResult[0]
                symbol = bestMatch["1. symbol"]
                name = bestMatch["2. name"]
                print(f'Searching for {assetName} gave result: \n Symbol: {symbol} \n Name: {name}')
                
                # test get QUOTE API 
                # url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={bestMatch["1. symbol"]}&apikey={alphaVantageKey}'
                # response = requests.get(url)
                # jsonResponse = response.json()
                # print(jsonResponse) 

                    # TRY IEX CLOUD, DID NOT WORK AS PLANNED AS YOU NEED TO PAY 
                searchEndpoint = f'https://cloud.iexapis.com/v1/stock/{symbol}/advanced-stats?token={iexCloudKey}'
                # searchEndpoint = f'https://cloud.iexapis.com/v1/stock/{symbol}/balance-sheet?token={iexCloudKey}'
                try:
                    response = requests.get(searchEndpoint)
                    # If the response was successful, no Exception will be raised
                    response.raise_for_status()
                except HTTPError as http_err:
                    print(f'HTTP error occurred: {http_err}')  # Python 3.6
                except Exception as err:
                    print(f'Other error occurred: {err}')  # Python 3.6
                else:
                    print('Success!')
                    jsonResponse = response.json()
                    print(jsonResponse)

            else:
                print(f'No results for {assetName}')
        else:
            print(jsonResponse) 
    """
############################################
# scrape Börsdata, did not work as planned because of poorly named urls 
# open up a browser session, Need to pay for their API
"""     
opt = webdriver.FirefoxOptions()
browser = webdriver.Firefox(options=opt)

# poll for elements for 60 seconds max, before shutdown
browser.implicitly_wait(60)
counter = 0
for assetName in df['Asset']:
    try:
        target = assetName.replace(" ", "-")
        url = f'https://borsdata.se/{target}/nyckeltal'
        browser.get(url)

        #wait for javascipt to load then scrape, this part is tricky to optimize, HOW TO KNOW THAT ENTIRE PAGE HAS LOADED?
        time.sleep(4)

        soup  = BeautifulSoup(browser.page_source, 'lxml')
        
        # with open('htmlBorsdata.txt', 'r') as f:
        #     html = f.read()
        # soup = BeautifulSoup(html)
        tables = soup.find_all("table", {"class": "style1"})

        # if nothing was found instead use the search field
        if not(tables):
            payload  = target.split("-")[0]
            
            searchFieldXPATH = "/html/body/div[2]/div/div[1]/div/input"

            seachField = WebDriverWait(browser, 10).until(
                EC.element_to_be_clickable((By.XPATH, searchFieldXPATH))
            )
            seachField.send_keys(payload)
            seachField.send_keys(Keys.ENTER)
            print(f'searching for {payload}')
            searchResultXPATH = "/html/body/div[2]/div/div[1]/div/div[4]/div/div/div[1]/div"
            #complex part wait for above div content to load
            time.sleep(2)
            try:
                searchResults = WebDriverWait(browser, 10).until(
                    EC.element_to_be_clickable((By.XPATH, searchResultXPATH))
                )
            except TimeoutException:        
                print("No results my brother")
                continue
            # find the first clickable link, highest ranked search result and click
            link = searchResults.find_element_by_tag_name("a") 
            # else click the best match
            print("clicking", link.get_attribute("innerHTML"))
            link.click()
            #wait for javascipt to load then scrape, this part is tricky to optimize, HOW TO KNOW THAT ENTIRE PAGE HAS LOADED?
            time.sleep(3)
            soup  = BeautifulSoup(browser.page_source, 'lxml')
            tables = soup.find_all("table", {"class": "style1"})
            
        for index, table in enumerate(tables):
            heading, value = parseTable(table)
            # creates a new column with the string value of heading as the name, and inserts the value, at index assetName
            df.loc[df['Asset'] == assetName, heading] = value
    
    
    except NoSuchElementException: 
        browser.quit()
        sys.exit()
    """
############################################
# FLIP AND TURN A Dataframe
'''
df=df.rename(columns = {'Unnamed: 0':'Year'}) # rename
fcol = df.columns # header should be the first col
df = df.T # transpose
df.insert(0, '-', fcol) # insert
header = df.iloc[0] # new headers should be first row
df = df[1:] #take the data less the header row
df.columns = header # update headers
df.reset_index(drop=True, inplace=True) # reset index
df.rename_axis(None, inplace=True) # rename
df.columns.name = None # rename
'''

###########################################

# USED BEFORE TO PARSE DTA SCRAPED FROM BÖSRDATA
# def parseTable(table):
#     # always seems to have this class
#     heading = table.find('td', {"class":"textCompName"})
#     no_whitespace_heading = re.sub('\s+', '', heading.text.strip())

#     ## always seems to be second entry 
#     value = table.find_all('td')[1]
#     no_whitespace_value = re.sub('\s+', '', value.text.strip())

#     # remove /aktie in value field
#     no_whitespace_value = no_whitespace_value.replace('/aktie', '')

#     return no_whitespace_heading, no_whitespace_value

####################################################

# def extractRelevantResult(table):
#     print(table)
#     print(table.get_attribute("innerHTML"))
#     link = table.find_element_by_tag_name("a") 
#     print(link)
#     print(link.get_attribute("innerHTML"))
#     link.click()