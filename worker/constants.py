import os

# Directory Paths
excelSaveLocation = os.path.abspath(os.getcwd()) + "/excel_files"
txtSaveLocation = os.path.abspath(os.getcwd()) + "/text_files"
pdfDownloadDir = os.path.abspath(os.getcwd()) + "/pdf"

# GECKODRIVER LOG PATH
GECKO_LOG_PATH = os.path.abspath(os.getcwd()) + '/geckodriver/geckodriver.log'
GECKO_EXECUTABLE_PATH = '/usr/local/bin/geckodriver'

# MISC
translationDict = {
    'Typ': 'Type',
    'Alternativa': 'Alternative',
    'Blandfond': 'Mix Equity & Fixed Income',
    'Aktiefond': 'Equity',
    'Räntefond': 'Fixed Income',
    'Kategori': 'Category',
    'Branschfond, Ny teknik': 'Sectorfund, Technology',
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