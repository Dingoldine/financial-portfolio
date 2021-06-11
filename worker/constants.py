import os

# Directory Paths
excelSaveLocation = os.path.abspath(os.getcwd()) + "/excel_files"
txtSaveLocation = os.path.abspath(os.getcwd()) + "/text_files"
pdfDownloadDir = os.path.abspath(os.getcwd()) + "/pdf"

# GECKODRIVER LOG PATH
GECKO_LOG_PATH = os.path.abspath(os.getcwd()) + '/geckodriver/geckodriver.log'
GECKO_EXECUTABLE_PATH = '/usr/local/bin/geckodriver'