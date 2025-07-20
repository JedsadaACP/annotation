import pandas as pd

# Create a dataframe
data = {
    'OriginalContainerNo': ['CON123', 'CON456', 'CON789'],
    'CorrectedContainerNo': ['CON123', 'CON457', 'CON789'],
    'OriginalLicensePlate': ['LP123', 'LP456', 'LP789'],
    'CorrectedLicensePlate': ['LP123', 'LP456', 'LP790'],
    'OriginalProvince': ['Bangkok', 'Chiang Mai', 'Phuket'],
    'CorrectedProvince': ['Bangkok', 'Chiang Mai', 'Phuket'],
    'ImagePath1': ['', '', ''],
    'ImagePath2': ['', '', ''],
    'ImagePath3': ['', '', ''],
    'ImagePath4': ['', '', '']
}
df = pd.DataFrame(data)

# Create a Pandas Excel writer using XlsxWriter as the engine.
writer = pd.ExcelWriter('dummy_data.xlsx', engine='xlsxwriter')

# Convert the dataframe to an XlsxWriter Excel object.
df.to_excel(writer, sheet_name='Sheet1', index=False)

# Close the Pandas Excel writer and output the Excel file.
writer.close()
