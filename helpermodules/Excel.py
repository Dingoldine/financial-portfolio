import pandas as pd
import pandas.io.formats.excel
import os
pandas.io.formats.excel.ExcelFormatter.header_style = None
import constants
# from openpyxl import load_workbook


# def addNewSheets(dataframes, filename, index_level = 2):
   
#     try:
#         # open existing file
#         wb = load_workbook(f'{constants.excelSaveLocation}/{filename}.xlsx')

#         writer = pd.ExcelWriter(f'{constants.excelSaveLocation}/{filename}.xlsx', engine='openpyxl') 
#         writer.book = wb
#         # copy existing sheets
#         writer.sheets = {ws.title:ws for ws in writer.book.worksheets}
#         # write new sheets
#         for df in dataframes:
#             df.to_excel(writer, df.name)

#             worksheet = writer.sheets[df.name]  # pull worksheet object
#             # # add index widths formatting
#             # max_index_len = df.index.astype(str).map(len).max() + 1 

#             # worksheet.set_column(0, 0, max_index_len) # set first col width to the length of maximum index
#             # writer.save()

#             # add formatting, set column widths automatically
#             print(worksheet.columns)
#             for idx, col in enumerate(df):  # loop through all columns
#                 series = df[col]
                
#                 max_len = max((
#                     series.astype(str).map(len).max(),  # len of largest item
#                     len(str(series.name))  # len of column name/header
#                     )) + 1  # adding a little extra space
#                 print(chr(idx + index_level))
#                 worksheet.column_dimensions[chr(idx + index_level)].width = max_len  # set column width

#         writer.save()
#         print(f'Added new sheet to excel: {filename}.xlsx')

#     except FileNotFoundError:
#         raise

# def updateSheet(filename, sheet_name):
#     pass

def create(dataframes, filename, index_level=1, currency = None):
    '''Takes a list of dataframes and creates an excelfile with given filename, \
    index_level should be 1 if the dataframes has column names. \
    Default currency information is None, provide a string explaining currency of items in Dataframe if necessary.'''

    writer = pd.ExcelWriter(f'{constants.excelSaveLocation}/{filename}.xlsx', engine='xlsxwriter') # pylint: disable=abstract-class-instantiated 
    for df in dataframes: 
        df.to_excel(writer, df.name)
        # add index widths formatting
        max_index_len = df.index.astype(str).map(len).max() + 1 
        worksheet = writer.sheets[df.name]  # pull worksheet object
        worksheet.set_column(0, 0, max_index_len) # set first col width to the length of maximum index

        # add formatting, set column widths automatically
        for idx, col in enumerate(df):  # loop through all columns
            series = df[col]
            
            max_len = max((
                series.astype(str).map(len).max(),  # len of largest item
                len(str(series.name))  # len of column name/header
                )) + 1  # adding a little extra space

            worksheet.set_column(idx + index_level, idx + index_level, max_len)  # set column width

        # write currency information, set format to wrap text
        workbook = writer.book
        wrap_format = workbook.add_format({'text_wrap': True,  'valign': 'top',})
        #set height of row if automatic alingment don't work for libreOffice calc or whatever
        worksheet.set_row(len(df) + 3, 40)
        worksheet.write(len(df) + 3 , 0, currency, wrap_format)
       
    writer.save()
    print(f'saved to excel: {filename}.xlsx')

