import copy

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from collections import Counter
import copy
import datetime

pd.options.mode.chained_assignment = None
PATH = 'data/Grapes-Vineyard A.xlsx'
PATH_B = 'data/Grapes-Vineyard B.xlsx'
COLS_OUT = ['Acceptance', 'Rachis Index', 'Bleaching index ', 'Cracking index', 'Shatter', 'Firmness',
            'Weightloss (%)', 'Decay (%)']
PATH_VINYARDS = 'data/Decay assesment in vineyards A and B (6) (1).xlsx'
PATH_STORAGE = 'data/Erdom room tempeartures.xlsx'
TREAT_DESCRIPTION = {
     1:['room 10 S617.01.22',12,'room 10 S617.01.22',0],
     2:['Room 20 S5 17.01.22',12,'Room 20 S5 17.01.22',0],
     3:['Room 16 log2',1,'room 10 S617.01.22',2.5],
     4:['Room 16 log2',2,'room 10 S617.01.22',2.5],
     5:['Room 16 log2',3,'room 10 S617.01.22',2.5],
     6: ['Room 22 log.3', 1, 'room 10 S617.01.22',5],
     7: ['Room 22 log.3', 2, 'room 10 S617.01.22',5],
     8: ['Room 22 log.3', 3, 'room 10 S617.01.22',5],
     9: ['room 19 S4 17.01.22', 1, 'room 10 S617.01.22',10],
     10: ['room 19 S4 17.01.22', 2, 'room 10 S617.01.22',10],
     11: ['room 19 S4 17.01.22', 3, 'room 10 S617.01.22',10],
     12: ['Room 40+10log.1', 1, 'room 10 S617.01.22',15],
     13: ['Room 40+10log.1', 2, 'room 10 S617.01.22',15],
     14: ['Room 40+10log.1', 3, 'room 10 S617.01.22',15]
     }
RELEVANT_STORAGE_DATA = ['treatment','Humidity_cumsum', 'Temperature_cumsum', 'Humidity_max', 'Temperature_max', 'Temperature_max_relative',
                          'mapped_period', 'avg_temp_in_period', 'std_temp_in_period', 'avg_humidity_in_period',
                          'std_humidity_in_period']

COLS_ONLY_OUT = ['Weightloss (%)','Bleaching index ','Decay', 'Decay (%)', 'Shriveling ']
NOT_PRINT_TRENDS = ['Vineyard', 'Treatment', 'Replication', 'Time', 'Vineyard_Number_of_measures', 'Vineyard_index',
                    'Vineyard_Std_index','Vineyard_Incidence', 'new_time', 'treatment','mapped_period' ]

DIMS_FOR_GRAPHS = ['Vineyard', 'Treatment', 'new_time', 'disruption_temperature', 'disruption_length']
COLS_HUE = ['disruption_length', 'disruption_temperature']


def get_storage_data(path_storage):
    '''
    this function receive path to storgae and does the following
        1. read the excel file
        2. clean non relevant data from room 3 and 10 and then combine them to 1 room.
        3. add to each room the base temp
        4. per each sheet in the excel -
            a. clean data before test started
            b. add week column
            c. add room column
    '''
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
    dfs_baselines = {'Room 16 log2':[2.5],'Room 20 S5 17.01.22':[0.0],'room 19 S4 17.01.22':[10], 'room 10 S617.01.22':[0],'Room 22 log.3':[5],'Room 40+10log.1':[15]}
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
        ####
        all_base_temps = pd.DataFrame(dfs_baselines).T
        all_base_temps.columns = ['room_temp']
        dfs[sheet] = dfs[sheet].merge(all_base_temps, left_on='room', right_index=True)
        # dfs[sheet]['Temperature_max_relative'] = (dfs[sheet]['Temperature'] - dfs[sheet]['room_temp']).max()
    return dfs


def get_data(path, path_b) -> pd.DataFrame:
    '''
    :param path: path to vinyard a excel file
    :param path_b: path to vinyard b excel file
    :return: data frame contains the concat of the 2 vinyards
    '''
    df_a = pd.read_excel(path, sheet_name='Sheet1')
    df_b = pd.read_excel(path_b, sheet_name='Sheet1')
    column_names = df_a.columns
    df_b.columns = column_names
    final_df = pd.concat([df_a, df_b])
    return final_df


def get_vinyards_data(path) -> pd.DataFrame:
    '''
    :param path: path of additional data per each Vinyard
    :return: data frame contains additional features in vinyard level
    '''
    df_v = pd.read_excel(path, sheet_name='Decay evaluation 10.10.21',usecols='M:R')
    df_v = df_v.iloc[14:17]
    names = ['Vineyard', 'Vineyard_Number_of_measures', 'Vineyard_index', 'Vineyard_Std_index', 'Vineyard_Incidence', 'Vineyard_Std_Incidence']
    df_v = df_v[1:]
    df_v.columns = names
    return df_v


def get_prep_df(path, path_b, path_v, treatment_dict: dict) -> pd.DataFrame:
    '''

    x:param path: using get_data function to create raw_data of measures
    :param path_b: using get_data function to create raw_data of measures
    :param path_v: path to vinyards to insert to get_vinyards_data function
    :param treatment_dict:
    :return: dataframe with cleaned column names, mapped period to numbers. in adition it adds the disruption length and disruption temp per each treatment.
    '''

    new_df = get_data(path,path_b)
    new_df.drop(columns='Unnamed: 16', inplace=True)
    new_df.rename(columns={'Shattering(%)': 'Shattering(%) (T0)'}, inplace=True)
    new_df.rename(columns={'Shattering(%).1': 'Shattering(%)'}, inplace=True)
    new_df.rename(columns={'Shattering(%).1': 'Shattering(%)'}, inplace=True)
    new_df.rename(columns={'Rachis index  (T0)': 'Rachis Index  (T0)'}, inplace=True)
    df_vinyards = get_vinyards_data(path=path_v)
    new_df = pd.merge(left=new_df, right=df_vinyards, left_on='Vineyard', right_on='Vineyard')
    match = {
        'I': 1,
        'II': 2,
        'III': 3,
        'IV': 4
    }
    new_df['new_time'] = new_df['Time'].map(match).fillna(0)
    new_df = new_df.merge(pd.DataFrame(treatment_dict).T[[1, 3]], how='left', left_on='Treatment', right_index=True)
    new_df.rename(columns={1: 'disruption_length', 3: 'disruption_temperature'}, inplace=True)
    return new_df


def plot_correl_matrix(corr_mat: pd.DataFrame):
    '''

    :param corr_mat: correlation matrix prepared to create the datafram
    :return: figure of correlation matrix
    '''
    corr_mat.index = pd.CategoricalIndex(corr_mat.index)
    corr_mat.sort_index(level=0, inplace=True)
    sns.set(font_scale=0.6)
    grpah = sns.heatmap(corr_mat, cmap='YlGnBu')
    plt.rcParams["axes.labelsize"] = 15
    plt.show()


def create_pearson_correl(df: pd.DataFrame, col_list_in: list, col_list_out: list):
    '''

    :param df: raw_data
    :param col_list_in: relevant columns list from measures taken from time 0
    :param col_list_out: relevant columns list from measures that we want to check correl 78
    :return:2 plots.
        1. correlation matrix of all features taken in entrance to storage
        2. correlation matrix of all features taken in entrance to storage vs relevant output features.
    '''
    #in features vs in features
    df_in = df[col_list_in]
    correl = df_in.corr()
    plot_correl_matrix(correl)
    plt.savefig('in_vs_in_correl')

    #in features vs. out features
    df_out = df[col_list_out]
    results = pd.concat([df.loc[:, ~df.columns.isin(['Vineyard', 'Treatment', 'Replication', 'Time'])], df_out.add_suffix('_out')], axis=1)
    correl_out = results.corr()
    out_cols = [col for col in correl_out.columns if '_out' in col]
    correl_out = correl_out[out_cols]
    correl_out = correl_out[~correl_out.index.str.contains('_out')]
    plot_correl_matrix(correl_out)
    plt.savefig('in_vs_out_correl')


def get_storage_per_treatment(storage_df:dict, exp_desc: dict):
    '''
    :param storage_df: dictionary contains all storage data, key stands for the treatment
    :param exp_desc: dictionary contains all storage relevant data per treatment
    :return: dictionary contains log of storage data including interuptions.
    '''
    storage_df_per_treatment = {}
    for treatment, values in exp_desc.items():
        mask_first_period = storage_df[values[0]]['weeks'] <= values[1]
        first_period = storage_df[values[0]].loc[mask_first_period]
        mask_second_period = storage_df[values[2]]['weeks'] > values[1]
        second_period = storage_df[values[2]].loc[mask_second_period]
        storage_df_per_treatment[treatment] = pd.concat([first_period, second_period])
    return storage_df_per_treatment


def enrich_storage_per_treatment(storage_dict:dict):
    '''
    :param storage_dict: receive dict with log of the storage data
    :return: dictionary contains some statistics on log of the per each treatment
    '''
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
    '''
    :param row: mapping function from weeks to period in test
    :return: period in test, numbered 1-4
    '''
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
    '''
    :param storage_dict: dictionary contians storage data
    :return: dict contains statistics per each period per treatment
    '''
    final_storage_data_per_treatment = {}
    data_storage_for_all_periods = {}
    for treatments, values in storage_dict.items():
        df = values
        for i in range(1, 5): # 4 periods
            mask = df['mapped_period'] <= i
            relevant_data = df.loc[mask]
            relevant_data['avg_temp_in_period'] = relevant_data['Temperature'].mean()
            relevant_data['std_temp_in_period'] = relevant_data['Temperature'].std()
            relevant_data['avg_humidity_in_period'] = relevant_data['Humidity'].mean()
            relevant_data['std_humidity_in_period'] = relevant_data['Humidity'].std()
            final_storage_data_per_treatment[i] = relevant_data.iloc[-1:]
        data_storage_for_all_periods[treatments] = pd.concat(final_storage_data_per_treatment)
    return pd.concat(data_storage_for_all_periods)


def flatten_data_to_grpah(dim_list: list, df: pd.DataFrame, col_name: str, col_name_t0: str = None) -> pd.DataFrame:
    '''
    :param dim_list:
    :param df:
    :param col_name:
    :param col_name_t0:
    :return:
    '''
    temp_df = pd.DataFrame()
    if col_name_t0 is not None:
        temp_df = df[DIMS_FOR_GRAPHS]
        temp_df['new_time'] = 0 # create manually time 0
        temp_df[col_name] = df[[col_name_t0]]
    dim_list_for_flatten = dim_list + [col_name]
    df_for_graph = pd.concat([df[dim_list_for_flatten], temp_df], ignore_index=True)
    return df_for_graph


def plot_graph(df: pd.DataFrame, col_name: str, dim_list: list, hue: str, tmp_dim_list: list,axs):
    df_plot = df.fillna(np.inf).groupby(dim_list)[[col_name]].mean().replace(np.inf, np.nan).reset_index()
    dim_list_for_grpah = dim_list + [col_name]
    axs = sns.lineplot(data=df_plot, x="new_time",
                      y=col_name, hue=hue, ci=None,legend=True)
    sns.color_palette("Paired")
    axs.xaxis.set_major_locator(ticker.MultipleLocator(1))
    axs.set(xlabel='time', ylabel=col_name, title=col_name + ' over time by ' +hue)
    axs.plot()



def get_all_t0(df: pd.DataFrame):
    '''
    :paxam df: this function get raw data with all columns
    :return: 2 lists of all relevant columns in the data that has data in entrance to storage and the column name in out of storage
    '''
    relevant_t0 = [col for col in df.columns if '(T0)' in col]
    relevant_columns_t0_list = [col.replace('(T0)', '').rstrip() for col in relevant_t0 if '(T0)' in col]
    list_t0 = list(set(df.columns).intersection(relevant_columns_t0_list))
    return sorted(relevant_t0), sorted(list_t0)


def get_data_storage(path_storage,treat_dict):
    '''
    :param path_storage: path to storage data
    :param treat_dict: tretment dictionary contains treatment and storage data
    :return: raw_data enriched with statistics about storage: temp, humidity, etc.
    '''
    df_storage = get_storage_data(path_storage=path_storage)
    storge_data_per_treatment = get_storage_per_treatment(storage_df=df_storage, exp_desc=treat_dict)
    data_storage_enriched_per_treatment = enrich_storage_per_treatment(storge_data_per_treatment)
    final_storage_data = get_relevant_data_per_period(data_storage_enriched_per_treatment)
    final_storage_data = final_storage_data.reset_index().rename(columns={'level_0': 'treatment', 'level_1': 'time_'})
    df_storage_data_final = raw_data.merge(final_storage_data[RELEVANT_STORAGE_DATA], how='inner', left_on=['Treatment', 'new_time']
                                         , right_on=['treatment', 'mapped_period'])
    return df_storage_data_final


if __name__ == '__main__':

    raw_data = get_prep_df(path=PATH, path_b=PATH_B,path_v=PATH_VINYARDS, treatment_dict=TREAT_DESCRIPTION)
    full_data_w_storage = get_data_storage(path_storage= PATH_STORAGE, treat_dict=TREAT_DESCRIPTION)

    ## create all graphs
    # print grpahs with t0

    relevant_t0_cols, relevant_cols = get_all_t0(full_data_w_storage)
    temp_dim_list = copy.copy(DIMS_FOR_GRAPHS)
    temp_dim_list.remove("new_time")

    Tot = len(relevant_cols)
    Cols = 4
    # Compute Rows required
    Rows = Tot // Cols
    Rows += Tot % Cols

    for i, hue in enumerate(temp_dim_list):
            # Create figure with appropriate space between subplots
            fig = plt.figure(figsize=(15, 15))
            fig.subplots_adjust(hspace=0.4, wspace=0.3)
            for col, col_t0, idx in list(zip(relevant_cols, relevant_t0_cols, range(len(relevant_cols)))):
                ax = fig.add_subplot(Rows, 4, idx + 1)
                data_for_grpah = flatten_data_to_grpah(dim_list=DIMS_FOR_GRAPHS,df=full_data_w_storage, col_name=col, col_name_t0=col_t0)
                plot_graph(df=data_for_grpah, col_name=col,dim_list=DIMS_FOR_GRAPHS, hue=hue, tmp_dim_list=temp_dim_list, axs=ax)
            fig2 = plt.gcf()
            plt.show()
            plt.draw()
            fig2.savefig(hue + 't0')

    # print grpahs without t0

    # t1_list = list((Counter(full_data_w_storage) - Counter(COLS_ONLY_OUT) - Counter(relevant_t0_cols) - Counter(
    #     relevant_cols) - Counter(NOT_PRINT_TRENDS) - Counter(COLS_HUE)).elements())
    # cols_to_print = t1_list + COLS_ONLY_OUT
    # Tot = len(cols_to_print)
    # Cols = 4
    # # Compute Rows required
    # Rows = Tot // Cols
    # Rows += Tot % Cols
    # for i, hue in enumerate(temp_dim_list):
    #     fig = plt.figure(figsize=(20, 20))
    #     fig.subplots_adjust(hspace=0.4, wspace=0.3)
    #     for col, idx in list(zip(cols_to_print, range(len(cols_to_print)))):
    #         ax = fig.add_subplot(Rows, 4, idx + 1)
    #         data_for_grpah = flatten_data_to_grpah(dim_list=DIMS_FOR_GRAPHS,df=full_data_w_storage, col_name=col)
    #         plot_graph(df=data_for_grpah, col_name=col, dim_list=DIMS_FOR_GRAPHS, hue=hue, tmp_dim_list=temp_dim_list, axs=ax)
    #     fig1= plt.gcf()
    #     plt.show()
    #     plt.draw()
    #     fig1.savefig(hue+'t1')
    #     plt.close()


    # create correlation matrix
    in_cols = [col for col in raw_data.columns if 'T0' in col]
    create_pearson_correl(raw_data, col_list_in=in_cols, col_list_out=COLS_OUT)
    print("Done!!!")
