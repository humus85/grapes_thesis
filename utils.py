import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import datetime


PATH = 'data/Grapes-Vineyard A.xlsx'
PATH_B = 'data/Grapes-Vineyard B.xlsx'
COLS_OUT = ['Acceptance', 'Rachis Index', 'Bleaching index ', 'Cracking index', 'Shattering', 'Firmness (N)',
            'Weightloss (%)', 'Decay (%)']
PATH_VINYARDS = 'data/Decay assesment in vineyards A and B (6) (1).xlsx'
PATH_STORAGE = 'data/Erdom room tempeartures.xlsx'
TREAT_DESCRIPTION = {
     1:['room 10 S617.01.22',12,'room 10 S617.01.22'],
     2:['Room 20 S5 17.01.22',12,'Room 20 S5 17.01.22'],
     3:['Room 16 log2',1,'room 10 S617.01.22'],
     4:['Room 16 log2',2,'room 10 S617.01.22'],
     5:['Room 16 log2',3,'room 10 S617.01.22'],
     6: ['Room 22 log.3', 1, 'room 10 S617.01.22'],
     7: ['Room 22 log.3', 2, 'room 10 S617.01.22'],
     8: ['Room 22 log.3', 3, 'room 10 S617.01.22'],
     9: ['room 19 S4 17.01.22', 1, 'room 10 S617.01.22'],
     10: ['room 19 S4 17.01.22', 2, 'room 10 S617.01.22'],
     11: ['room 19 S4 17.01.22', 3, 'room 10 S617.01.22'],
     12: ['Room 40+10log.1', 1, 'room 10 S617.01.22'],
     13: ['Room 40+10log.1', 2, 'room 10 S617.01.22'],
     14: ['Room 40+10log.1', 3, 'room 10 S617.01.22']
     }
RELEVANT_STORAGE_DATA = ['treatment','Humidity_cumsum', 'Temperature_cumsum', 'Humidity_max', 'Temperature_max', 'Temperature_max_relative',
                          'mapped_period', 'avg_temp_in_period', 'std_temp_in_period', 'avg_humidity_in_period',
                          'std_humidity_in_period']

def get_storage_data(path_storage):
    xl = pd.ExcelFile(path_storage)
    dfs = {}
    dfs_base = {''}
    for sheet in ([s for s in xl.sheet_names if s!='Sheet1']):
        dfs[sheet] = pd.read_excel(path_storage, sheet_name=sheet, usecols='A:E')
    #room 10 was malfunction at 24/12/21 so, I'm removing this data and paste data from room 3
    dfs['room 10 S617.01.22'] = dfs['room 10 S617.01.22'].drop(dfs['room 10 S617.01.22'].tail(2311).index)
    dfs['Room 3 S2 17.01.22'] = dfs['Room 3 S2 17.01.22'].drop(dfs['Room 3 S2 17.01.22'].head(2702).index)
    dfs['room 10 S617.01.22'] = dfs['room 10 S617.01.22'].append(dfs['Room 3 S2 17.01.22'], ignore_index=True)
    dfs.pop('Room 3 S2 17.01.22', None)
    dfs_baselines = {'Room 16 log2':[2.5],'Room 20 S5 17.01.22':[0.0],'room 19 S4 17.01.22':[10],'room 10 S617.01.22':[0],'Room 22 log.3':[5],'Room 40+10log.1':[15]}
    # create columns for each storage room
    for sheet in ([s for s in xl.sheet_names if s != 'Sheet1' and s != 'Room 3 S2 17.01.22']):
        # clean data before test started, intendend to room 10 mainly
        mask = dfs[sheet]['Date'] >= '2021-10-21'
        dfs[sheet] = dfs[sheet].loc[mask]
        # add week
        first_date = dfs[sheet]['Date'].iloc[0]
        dfs[sheet]['weeks'] = dfs[sheet]['Date'] - first_date
        dfs[sheet]['weeks'] = np.floor((dfs[sheet]['weeks'] / np.timedelta64(1, 'W')) + 1)
        # add aditional data
        dfs[sheet]['room'] = sheet
        # dfs[sheet]['Humidity_cumsum'] = dfs[sheet]['Humidity'].cumsum()
        # dfs[sheet]['Temperature_cumsum'] = dfs[sheet]['Temperature'].cumsum()
        # dfs[sheet]['Humidity_max'] = dfs[sheet]['Humidity'].max()
        # dfs[sheet]['Temperature_max'] = dfs[sheet]['Temperature'].max()
        # dfs[sheet]['Temperature_max_relative'] = (dfs[sheet]['Temperature'] - dfs[sheet]['room_temp']).max()
        ####
        all_base_temps = pd.DataFrame(dfs_baselines).T
        all_base_temps.columns = ['room_temp']
        dfs[sheet] = dfs[sheet].merge(all_base_temps, left_on='room', right_index=True)
        # dfs[sheet]['Temperature_max_relative'] = (dfs[sheet]['Temperature'] - dfs[sheet]['room_temp']).max()
    return dfs


def get_data(path, path_b) -> pd.DataFrame:
    df_a = pd.read_excel(path, sheet_name='Sheet1')
    df_b = pd.read_excel(path_b, sheet_name='Sheet1')
    column_names = df_a.columns
    df_b.columns = column_names
    final_df = pd.concat([df_a, df_b])
    return final_df


def get_vinyards_data(path) -> pd.DataFrame:
    df_v = pd.read_excel(path, sheet_name='Decay evaluation 10.10.21',usecols='M:R')
    df_v = df_v.iloc[14:17]
    names = ['Vineyard', 'Vineyard_Number_of_measures', 'Vineyard_index', 'Vineyard_Std_index', 'Vineyard_Incidence', 'Vineyard_Std_index']
    df_v = df_v[1:]
    df_v.columns = names
    return df_v


def get_prep_df(path,path_b,path_v) -> pd.DataFrame:
    new_df = get_data(path,path_b)
    new_df.drop(columns='Unnamed: 16', inplace=True)
    new_df.rename(columns={'Shattering(%)': 'Shattering(%) (T0)'}, inplace=True)
    df_vinyards = get_vinyards_data(path=path_v)
    new_df = pd.merge(left=new_df, right=df_vinyards, left_on='Vineyard', right_on='Vineyard')
    match = {
        'I': 1,
        'II': 2,
        'III': 3,
        'IV': 4
    }
    new_df['new_time'] = new_df['Time'].map(match).fillna(0)
    return new_df


def plot_correl_matrix(corr_mat: pd.DataFrame):
    corr_mat.index = pd.CategoricalIndex(corr_mat.index)
    corr_mat.sort_index(level=0, inplace=True)
    sns.set(font_scale=0.6)
    grpah = sns.heatmap(corr_mat, cmap='YlGnBu')
    plt.rcParams["axes.labelsize"] = 15
    plt.show()


def create_pearson_correl(df: pd.DataFrame, col_list_in: list, col_list_out: list):
    df_in = df[col_list_in]
    correl = df_in.corr()
    plot_correl_matrix(correl)

    df_out = df[col_list_out]
    results = pd.concat([df.loc[:, ~df.columns.isin(['Vineyard', 'Treatment', 'Replication', 'Time'])], df_out.add_suffix('_out')], axis=1)
    correl_out = results.corr()
    out_cols = [col for col in correl_out.columns if '_out' in col]
    correl_out = correl_out[out_cols]
    correl_out = correl_out[~correl_out.index.str.contains('_out')]
    plot_correl_matrix(correl_out)


def get_storage_per_treatment(storage_df:dict,exp_desc:dict):
    storage_df_per_treatment = {}
    for treatment, values in exp_desc.items():
        mask_first_period = storage_df[values[0]]['weeks'] <= values[1]
        first_period = storage_df[values[0]].loc[mask_first_period]
        mask_second_period = storage_df[values[2]]['weeks'] > values[1]
        second_period = storage_df[values[2]].loc[mask_second_period]
        storage_df_per_treatment[treatment] = pd.concat([first_period, second_period])
    return storage_df_per_treatment


def enrich_storage_per_treatment(storage_dict:dict):
    for treatment, df_treatment_storage in storage_dict.items():
        df_treatment_storage['Humidity_cumsum'] = df_treatment_storage['Humidity'].cumsum()
        df_treatment_storage['Temperature_cumsum'] = df_treatment_storage['Temperature'].cumsum()
        df_treatment_storage['Humidity_max'] = df_treatment_storage['Humidity'].max()
        df_treatment_storage['Temperature_max'] = df_treatment_storage['Temperature'].max()
        df_treatment_storage['Temperature_max_relative'] = (
                    df_treatment_storage['Temperature'] - df_treatment_storage['room_temp']).max()
        df_treatment_storage['mapped_period'] = df_treatment_storage.apply(map_weeks, axis=1)
        storage_dict[treatment] = df_treatment_storage
    return storage_dict


def map_weeks(row):
    if row['weeks'] <= 3:
        return 1
    elif row['weeks'] <= 6:
        return 2
    elif row['weeks'] <= 9:
        return 3
    elif row['weeks'] <= 12:
        return 4
    else:
        return 9999


def get_relevant_data_per_period(storage_dict:dict):
    final_storage_data_per_treatment = {}
    data_storage_for_all_periods = {}
    for treatments, values in storage_dict.items():
        df = values
        for i in range(1, 5):
            mask = df['mapped_period'] <= i
            relevant_data = df.loc[mask]
            relevant_data['avg_temp_in_period'] = relevant_data['Temperature'].mean()
            relevant_data['std_temp_in_period'] = relevant_data['Temperature'].std()
            relevant_data['avg_humidity_in_period'] = relevant_data['Humidity'].mean()
            relevant_data['std_humidity_in_period'] = relevant_data['Humidity'].std()
            final_storage_data_per_treatment[i] = relevant_data.iloc[-1:]
        data_storage_for_all_periods[treatments] = pd.concat(final_storage_data_per_treatment)
    return pd.concat(data_storage_for_all_periods)


if __name__ == '__main__':

    raw_data = get_prep_df(path=PATH, path_b=PATH_B,path_v=PATH_VINYARDS)
    df_storage = get_storage_data(path_storage=PATH_STORAGE)
    storge_data_per_treatment = get_storage_per_treatment(df_storage, TREAT_DESCRIPTION)
    data_storage_enriched_per_treatment = enrich_storage_per_treatment(storge_data_per_treatment)
    final_storage_data = get_relevant_data_per_period(data_storage_enriched_per_treatment)
    final_storage_data = final_storage_data.reset_index().rename(columns={'level_0': 'treatment', 'level_1': 'time_'})
    full_data_w_storage = raw_data.merge(final_storage_data[RELEVANT_STORAGE_DATA], how= 'inner',left_on=['Treatment','new_time']
                                         ,right_on=['treatment','mapped_period'])

    in_cols = [col for col in raw_data.columns if 'T0' in col]
    create_pearson_correl(raw_data, col_list_in=in_cols, col_list_out=COLS_OUT)
    print("Done!!!")
