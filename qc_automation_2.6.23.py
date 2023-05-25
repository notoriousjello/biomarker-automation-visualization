import pandas as pd
import numpy as np
from datetime import date
import os


def long_assign_missing_key(row):
    if np.isnan(row['Calc. Conc. Mean']):
        if row['Detection Range'] == 'Below Fit Curve Range':
            return -99
        elif row['Detection Range'] == 'Above Fit Curve Range':
            return -88
        else:
            return np.nan
    else:
        return row['Calc. Conc. Mean']


def per_panel_qc(file_path):
    """
    takes a file path to a folder of MSD data saved as excel files
    file name must include "_RAW"
    returns a dataframe containing the by plate QC summary data
    """
    # initiate counter
    index = 0
    headers_to_ignore = ['removed samples', 'samples removed', 'read_me', 'read me']
    for file in os.listdir(file_path):
        # for file in directory:
        # Exclude hidden files, file name must end in "RAW"
        if 'RAW' in file and '~$' not in file:
            print(file)
            xls = pd.ExcelFile(file_path + file, engine='openpyxl')

            for sheet in xls.sheet_names:
                if sheet.lower() not in headers_to_ignore:
                    raw_data = pd.read_excel(xls, sheet, skiprows=[0])  #  removes first row.
                    # create a dataframe of samples by excluding standards, QCs, and blanks
                    samples = raw_data[~raw_data['Sample Group'].str.contains("Standard|QC|Blank")].copy()
                    # create a dataframe of qcs by only including the QC sample group
                    qc = raw_data[raw_data['Sample Group'].str.contains('QC')].copy()
                    qc = qc.replace(np.nan, -99)
                    # Create column called "Well" to differentiate the QCs as they often have the same name
                    qc['QC'] = qc['Sample'] + '_concentration' + "_" + qc['Well']
                    qc = pd.pivot_table(qc, values='Calc. Concentration',
                                        index=['Plate Name', 'Assay'], columns='QC',
                                        aggfunc='mean', dropna=False).reset_index()
                    # Calculate intraplate CV using: 100*(std/mean)
                    qc['intraplate_cv'] = 100 * (qc.filter(like='QC').std(1) / qc.filter(like='QC').mean(1))
                    # Replace intraplate values that include at least 1 out of detection range sample with -99
                    qc.loc[qc['intraplate_cv'] <= 0, 'intraplate_cv'] = -99

                    if index == 0:
                        all_samples = samples
                        all_qc = qc
                    else:
                        all_samples = pd.concat([all_samples, samples], ignore_index=True, axis=0)
                        all_qc = pd.concat([all_qc, qc], ignore_index=True, axis=0)
                    index += 1
                    # count the number of samples / plate and assay
    total_count = all_samples.groupby(['Plate Name', 'Assay', 'Sample Group'])['Sample'].count().reset_index()
    print(total_count)
    # count the samples in each detection range for every assay on of every sample group on every plate
    counts = all_samples.groupby(['Plate Name', 'Sample Group', 'Assay', 'Detection Range'])[
        'Sample'].count().reset_index()
    counts = pd.pivot_table(counts, values='Sample', index=['Plate Name', 'Sample Group', 'Assay'],
                            columns='Detection Range', aggfunc='mean', dropna=False).reset_index()
    cols = list(counts)
    cols.insert(0, cols.pop(cols.index('Assay')))
    counts = counts.loc[:, cols]
    # sometimes these detection ranges don't exist in the dataset, add them back in
    if 'Below Detection Range' not in counts.columns:
        counts.insert(loc=3, column='Below Detection Range', value=np.nan)
    if 'Below Fit Curve Range' not in counts.columns:
        counts.insert(loc=3, column='Below Fit Curve Range', value=np.nan)
    if 'Above Fit Curve Range' not in counts.columns:
        counts.insert(loc=3, column='Above Fit Curve Range', value=np.nan)
    if 'Above Detection Range' not in counts.columns:
        counts.insert(loc=3, column='Above Detection Range', value=np.nan)
    counts = counts.drop(columns=['In Detection Range'])
    counts = pd.merge(counts, total_count, on=['Plate Name', 'Assay', 'Sample Group'])
    counts = counts.rename(columns={'Sample': 'samples_measured'})
    columns = ['Above Detection Range', 'Above Fit Curve Range', 'Below Detection Range', 'Below Fit Curve Range']
    # create a column for each detection range indicating the percent of total samples
    index = 5
    for column in columns:
        column_name = column + ' Percent'
        counts.insert(loc=index, column=column_name, value=100 * (counts[column] / counts['samples_measured']))
        index += 2

    counts = counts.fillna(0)
    counts = pd.merge(counts, all_qc, on=['Plate Name', 'Assay'], how='left')
    counts = counts.sort_values(by=['Assay', 'Plate Name', 'Sample Group'])
    cols = list(counts)
    cols.insert(3, cols.pop(cols.index('samples_measured')))
    counts = counts.fillna('NA')
    return counts


def qc_summary(qc_panel, llods):
    """
    Takes a per plate qc dataframe
    Returns a summarized dataframe for each assay
    """
    # determine the mean of the QC values
    cols = qc_panel.columns.drop(['Assay', 'Plate Name', 'Sample Group'])
    qc_panel[cols] = qc_panel[cols].apply(pd.to_numeric, errors='coerce')
    qc_panel['mean'] = qc_panel.filter(like='QC').mean(1, skipna=False)
    llods.name = 'llods'
    # groupby assay and aggregate based on the following criteria
    qc = (qc_panel.groupby(['Assay', 'Sample Group'], as_index=False)
          .agg({'samples_measured': 'sum', 'Plate Name': 'count', 'Above Detection Range': 'sum',
                'Above Fit Curve Range': 'sum', 'Below Detection Range': 'sum', 'Below Fit Curve Range': 'sum',
                'intraplate_cv': 'mean', 'mean': lambda x: 100 * (x.std() / x.mean())})
          .rename(columns={'samples_measured': 'total_samples_measured', 'Plate Name': 'plate_count',
                           'intraplate_cv': 'average_intraplate_cv', 'mean': 'interplate_cv'}))
    qc.loc[qc['average_intraplate_cv'] <= 0, 'average_intraplate_cv'] = -99
    qc.loc[qc['interplate_cv'] <= 0, 'interplate_cv'] = -99
    # add in percent columns
    columns = ['Above Detection Range', 'Above Fit Curve Range', 'Below Detection Range', 'Below Fit Curve Range']
    index = 4
    for column in columns:
        column_name = column + ' Percent'
        qc.insert(loc=index, column=column_name, value=100 * (qc[column] / qc['total_samples_measured']))
        index += 2

    qc = qc.merge(llods, on=['Assay'])
    return qc


def long_msd(raw_data):
    """
    Takes a list of MSD files in csv format
    Identifier column must be named "Sample"
    Saves a long format csv of: 1) imputed data 2) non-imputed data
    """
    raw_data = raw_data[raw_data['Sample Group'].str.contains("Standard|QC|Blank") == False].copy()
    raw_data = raw_data[['Sample', 'Assay', 'Sample Group', 'Calc. Conc. Mean', 'Detection Range', 'Plate Name']]
    raw_data.insert(loc=1, column='Subject', value=raw_data['Sample'].str.split('_').str[0])
    raw_data.insert(loc=2, column='Visit', value=raw_data['Sample'].str.split('_').str[1])
    raw_data['Calc. Conc. Mean'] = raw_data.apply(lambda x: long_assign_missing_key(x), axis=1)
    # raw_data = raw_data.drop(columns=['Sample'])
    return raw_data


def wide_msd(raw_data):
    """
    Takes a list of MSD files in csv format
    Identifier column must be named "Sample"
    Saves a long format csv of: 1) imputed data 2) non-imputed data
    """
    raw_data = raw_data[~raw_data['Sample Group'].str.contains("Standard|QC|Blank")].copy()
    raw_data = raw_data[~raw_data['Sample'].str.contains('Blank')]
    raw_data.insert(loc=2, column='Visit', value=raw_data['Sample'].str.split('_').str[1])

    # Dependence on Visit presence. Will break if Visit is not provided.
    raw_data['Wide'] = raw_data['Assay'] + '_' + raw_data['Sample Group'] + '_' + raw_data['Visit']
    llods = raw_data.groupby('Assay')['Calc. Conc. Mean'].min() / 2
    raw_data['llod'] = raw_data['Assay'].map(llods)
    raw_data = raw_data[['Wide', 'Sample', 'Calc. Conc. Mean', 'llod']]
    raw_data = raw_data.fillna(-99)
    imputed = raw_data.copy()
    imputed['Calc. Conc. Mean'] = np.where(imputed['Calc. Conc. Mean'] == -99, imputed['llod'],
                                           imputed['Calc. Conc. Mean'])
    wide = pd.pivot_table(raw_data, values='Calc. Conc. Mean', index=['Sample'], columns='Wide',
                          aggfunc='mean').reset_index()
    wide_imputed = pd.pivot_table(imputed, values='Calc. Conc. Mean', index=['Sample'], columns='Wide',
                                  aggfunc='mean').reset_index()
    wide.insert(loc=1, column='Subject', value=wide['Sample'].str.split('_').str[0])
    wide_imputed.insert(loc=1, column='Subject', value=wide_imputed['Sample'].str.split('_').str[0])
    wide = wide.drop(columns=['Sample'])
    wide_imputed = wide_imputed.drop(columns=['Sample'])
    return wide, wide_imputed, llods


# def read_me(readme, file_path):
#     file_path = file_path[:-1]
#     readme = readme[readme.iloc[:, 1] == file_path]
#     readme = readme.tail(1)
#     readme = readme.T.reset_index().rename(columns={'index': 'Parameter', 1: 'Field'})
#     readme = readme.dropna()
#     readme['Parameter'] = readme['Parameter'].str.split('.').str[0]
#     # add section header and move to top
#     readme.loc[-1] = ['Identification of assay, plates, and operators', '']
#     readme.index = readme.index + 1
#     readme = readme.sort_index()
#     readme.loc[len(readme.index)] = ['', '']
#     dict = {
#         'Parameter': ['Tabs', 'LongData', 'WideData', 'WideDataImputed', 'QC Summary', 'Plate QC', '', 'Definitions',
#                       'Below Fit Curve Range', 'Below Detection Range',
#                       'Above Fit Curve Range', 'Above Detection Range', 'Intraplate CV', '',
#                       'Key for missingness and out of range values', 'missing (not measured)', 'Below Fit Curve Range',
#                       'Above Fit Curve Range', '', 'Report Generation', 'Prepared by'],
#         'Field': ['', 'Sample MSD values',
#                   'Pivoted data with columns in assay_sample_visit format (see key below for out of range and missing values)',
#                   'Imputed version of WideData, LLOD = lowest sample concentration / 2',
#                   'QC summary information for each assay', 'QC summary information for each plate',
#                   '', '', 'Signal is below the bottom of the bottom of the curve fit. No concentration is given.',
#                   'Signal is above the bottom of the curve, but below the detection limit as defined by the Detection Limit Properties',
#                   'Signal is within 110%\ of S001 signal when dose curve is in the linear range or within 110% of the dose curve plateau. NaN occurs when signals are way above 110% of S001 and/or when camera is saturated (>1,500,000 RU).',
#                   'Signal is above the top of detection range as defined by the Detection Limit Properties',
#                   '100*std/mean of QC well concentrations', '', '', 'NA', '-99', '-89', '', '', 'Hana Morris, Ted Liu']
#     }
#     to_add = pd.DataFrame(dict)
#     readme = pd.concat([readme, to_add], ignore_index=True)
#     readme.reset_index()
#     today = date.today()
#     date_string = today.strftime('%m.%d.%y')
#     # readme.loc[len(readme.index)]  = ['Prepared on', date_string]
#     return readme


def compile_all(folder):
    # index = 0
    #readme_excel = pd.read_csv(path_to_readme)
    #print(readme_excel)
    # file_path = readme_excel[
    #     readme_excel['File path to folder with raw data, graphs, protocol'].str.contains(folder)]

    # Need to use iloc due to new col header changes.
    #file_path = readme_excel[readme_excel.iloc[:, 1].str.contains(folder, na=False)]
    #print(file_path)
    #file_path = file_path.iloc[-1, 1]
    #file_path += '\\'
    file_path = folder

    print(file_path)
    # per_panel_qc(file_path)

    headers_to_ignore = ['removed samples', 'samples removed', 'read_me', 'read me']
    for file in os.listdir(file_path):
        # for file in directory (note: this technically would include anything in the directory but it should only be files):
        # Exclude .DS files
        if 'RAW' in file and '$' not in file:
            xls = pd.ExcelFile(file_path + file)
            output_file = file.replace('RAW.xlsx', 'ANALYZED.xlsx')
            # identify date in folder name
            folder_components = folder.split('_')
            to_replace = ''
            for x in folder_components:
                to_replace += x
            # to_replace = folder_components[-3] + '_' + folder_components[-2] + '_' + folder_components[-1]
            today = date.today()
            date_string = today.strftime('%m.%d.%y')
            # replace folder date with today's date
            output_file = output_file.replace(to_replace, date_string)
            writer = pd.ExcelWriter(file_path + output_file, engine='xlsxwriter')
            for sheet in xls.sheet_names:
                if sheet.lower() not in headers_to_ignore:
                    raw_data = pd.read_excel(xls, sheet, skiprows=[0]) #
                    long = long_msd(raw_data)
                    long.to_excel(writer, sheet_name='LongData', na_rep='NA', index=False)
                    wide, imputed, llods = wide_msd(raw_data)
                    wide.to_excel(writer, sheet_name='WideData', na_rep='NA', index=False)
                    imputed.to_excel(writer, sheet_name='WideDataImputed', na_rep='NA', index=False)
    qc_panel = per_panel_qc(file_path)
    qc_panel.to_excel(writer, sheet_name='Plate QC', na_rep='NA', index=False)
    qc_all = qc_summary(qc_panel, llods)
    qc_all.to_excel(writer, sheet_name='QC summary', na_rep='NA', index=False)
    # readme = read_me(readme_excel, temp_path)
    # readme.to_excel(writer, sheet_name='ReadMe', na_rep='NA', index=False)
    writer.close()


def main():
    # linked to google forms spreadsheet
    #readme_url = 'https://docs.google.com/spreadsheets/d/1nLa51D0_87Ta4o8WdcRH0S1P0u43IxF7O-0ZlIFB6uE/edit#gid=434516371'
    #url_1 = readme_url.replace('/edit#gid=', '/export?format=csv&gid=')
    msd_folder = 'C:\\Users\\notjello\\Documents\\GitHub\\biomarker-automation-visualization\\Studies\\KRI\\ICICLE\\EGF\\'
    compile_all(msd_folder)



if __name__ == '__main__':
    main()
