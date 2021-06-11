# cSpell: disable
import constants
import pandas as pd
import pandas.io.formats.excel
pandas.io.formats.excel.ExcelFormatter.header_style = None


def create(dataframes, filename, index_level=1, currency=None):
    '''Takes a list of dataframes and creates an excelfile with given filename, \
    index_level should be 1 if the dataframes has column names. \
    Default currency information is None, provide a string explaining currency of items in Dataframe if necessary.'''

    writer = pd.ExcelWriter(f'{constants.excelSaveLocation}/{filename}.xlsx', engine='xlsxwriter')  # pylint: disable=abstract-class-instantiated 
    for df in dataframes: 
        df.to_excel(writer, df.name)
        # add index widths formatting
        max_index_len = df.index.astype(str).map(len).max() + 1 
        worksheet = writer.sheets[df.name]  # pull worksheet object
        worksheet.set_column(0, 0, max_index_len)  # set first col width to length of maximum index

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
        wrap_format = workbook.add_format({'text_wrap': True,  'valign': 'top'})
        # set height of row if automatic alingment don't work for libreOffice calc or whatever
        worksheet.set_row(len(df) + 3, 40)
        worksheet.write(len(df) + 3, 0, currency, wrap_format)
       
    writer.save()
    print(f'saved to excel: {filename}.xlsx')

