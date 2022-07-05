import copy

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from collections import Counter
import copy
from tsfresh import extract_features, extract_relevant_features, select_features
from scipy import stats
from tsfresh.utilities.dataframe_functions import impute
from tsfresh.feature_extraction import ComprehensiveFCParameters
import datetime
import tsfresh

pd.options.mode.chained_assignment = None


PATH = 'data/untitled folder/Grapes-Vineyard A edited.xlsx' #'data/Grapes-Vineyard A.xlsx'
PATH_B = 'data/untitled folder/Grapes-Vineyard B-edited.xlsx' #'data/Grapes-Vineyard B.xlsx'
COLS_OUT = ['Acceptance', 'Rachis Index', 'Bleaching index ', 'Cracking index', 'Shattering(%)', 'Firmness',
            'Weightloss (%)', 'Decay (%)']
PATH_VINYARDS = 'data/Decay assesment in vineyards A and B (6) (1).xlsx'
PATH_STORAGE = 'data/untitled folder/Erdom room tempeartures (2).xlsx'
TREAT_DESCRIPTION = {
    1: ['room 10 S617.01.22', 12, 'room 10 S617.01.22', 0],
    2: ['Room 20 S5 17.01.22', 12, 'Room 20 S5 17.01.22', 0],
    3: ['Room 16 log2', 1, 'room 10 S617.01.22', 2.5],
    4: ['Room 16 log2', 2, 'room 10 S617.01.22', 2.5],
    5: ['Room 16 log2', 3, 'room 10 S617.01.22', 2.5],
    6: ['Room 22 log.3', 1, 'room 10 S617.01.22', 5],
    7: ['Room 22 log.3', 2, 'room 10 S617.01.22', 5],
    8: ['Room 22 log.3', 3, 'room 10 S617.01.22', 5],
    9: ['room 19 S4 17.01.22', 1, 'room 10 S617.01.22', 10],
    10: ['room 19 S4 17.01.22', 2, 'room 10 S617.01.22', 10],
    11: ['room 19 S4 17.01.22', 3, 'room 10 S617.01.22', 10],
    12: ['Room 40+10log.1', 1, 'room 10 S617.01.22', 15],
    13: ['Room 40+10log.1', 2, 'room 10 S617.01.22', 15],
    14: ['Room 40+10log.1', 3, 'room 10 S617.01.22', 15]
}
RELEVANT_STORAGE_DATA = ['treatment', 'Humidity_cumsum', 'Temperature_cumsum', 'Humidity_max', 'Temperature_max',
                         'Temperature_max_relative',
                         'mapped_period', 'avg_temp_in_period', 'std_temp_in_period', 'avg_humidity_in_period',
                         'std_humidity_in_period','Temperature_dday','kPa']

COLS_ONLY_OUT = ['Weightloss (%)', 'Bleaching index ', 'Decay', 'Decay (%)', 'Shriveling ']
NOT_PRINT_TRENDS = ['Vineyard', 'Treatment', 'Replication', 'Time', 'Vineyard_Number_of_measures', 'Vineyard_index',
                    'Vineyard_Std_index', 'Vineyard_Incidence', 'new_time', 'treatment', 'mapped_period']

DIMS_FOR_GRAPHS = ['Vineyard', 'new_time', 'disruption_temperature', 'disruption_length', 'Treatment']
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
    for sheet in ([s for s in xl.sheet_names if s != 'Sheet1']):
        dfs[sheet] = pd.read_excel(path_storage, sheet_name=sheet, usecols='A:I')
    # room 10 was malfunction at 24/12/21 so, I'm removing this data and paste data from room 3
    dfs['room 10 S617.01.22'] = dfs['room 10 S617.01.22'].drop(dfs['room 10 S617.01.22'].tail(2311).index)
    dfs['Room 3 S2 17.01.22'] = dfs['Room 3 S2 17.01.22'].drop(dfs['Room 3 S2 17.01.22'].head(2702).index)
    dfs['room 10 S617.01.22'] = dfs['room 10 S617.01.22'].append(dfs['Room 3 S2 17.01.22'], ignore_index=True)
    dfs.pop('Room 3 S2 17.01.22', None)
    dfs_baselines = {'Room 16 log2': [2.5], 'Room 20 S5 17.01.22': [0.0], 'room 19 S4 17.01.22': [10],
                     'room 10 S617.01.22': [0], 'Room 22 log.3': [5], 'Room 40+10log.1': [15]}
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
    df_v = pd.read_excel(path, sheet_name='Decay evaluation 10.10.21', usecols='M:R')
    df_v = df_v.iloc[14:17]
    names = ['Vineyard', 'Vineyard_Number_of_measures', 'Vineyard_index', 'Vineyard_Std_index', 'Vineyard_Incidence',
             'Vineyard_Std_Incidence']
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

    new_df = get_data(path, path_b)
    new_df.drop(columns='Unnamed: 16', inplace=True)
    new_df.rename(columns={'Shattering(%)': 'Shattering(%) (T0)'}, inplace=True)
    new_df.rename(columns={'Shattering(%).1': 'Shattering(%)'}, inplace=True)
    new_df.rename(columns={'Shattering(%).1': 'Shattering(%)'}, inplace=True)
    new_df.rename(columns={'Rachis index  (T0)': 'Rachis Index  (T0)'}, inplace=True)
    # remove shatter due to redundant
    new_df = new_df.drop('Shatter (T0)', axis=1)
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


def corr_sig(df=None):
    p_matrix = np.zeros(shape=(df.shape[0],df.shape[1]))
    for col in df.columns:
        for col2 in df.drop(col,axis=1).columns:
            _, p = stats.pearsonr(df[col],df[col2])
            p_matrix[df.columns.to_list().index(col),df.columns.to_list().index(col2)] = p
    return p_matrix


def plot_correl_matrix(corr_mat: pd.DataFrame, correlation_name: str, vinyeard:str,p_values_flag):
    '''
    :param corr_mat: correlation matrix prepared to create the dataframe
    :return: figure of correlation matrix
    '''

    corr_mat.index = pd.CategoricalIndex(corr_mat.index)
    corr_mat.sort_index(level=0, inplace=True)
    sns.set(font_scale=0.6)
    if correlation_name == 'in_vs_in':
        cols = corr_mat.columns.sort_values()  # plot ordered heatmap
        corr_mat = corr_mat[cols]
        mask = np.triu(np.ones_like(corr_mat)).astype(bool)
        grpah = sns.heatmap(corr_mat, mask=mask, square=True, cmap='YlGnBu', vmin=-1, vmax=1, annot=True, fmt='.2f')
        grpah.invert_xaxis()
    else:
        grpah = sns.heatmap(corr_mat, cmap='YlGnBu', vmin=-1, vmax=1, annot=True, fmt='.3f')
    plt.rcParams["axes.labelsize"] = 15
    fig5 = plt.gcf()
    plt.tight_layout()
    plt.show()
    plt.draw()
    fig5.savefig('figures_update/new/' + correlation_name + ', Vineyard: ' + vinyeard + 'P_values:' + p_values_flag +'.png')
    # plt.show()


def create_pearson_correl(df: pd.DataFrame, col_list_in: list, col_list_out: list):
    '''
    :param df: raw_data
    :param col_list_in: relevant columns list from measures taken from time 0
    :param col_list_out: relevant columns list from measures that we want to check correl 78
    :return:2 plots.
        1. correlation matrix of all features taken in entrance to storage
        2. correlation matrix of all features taken in entrance to storage vs relevant output features.
    '''
    # in features vs in features
    df_in = df[col_list_in + ['Vineyard']]
    df_out = df[col_list_out]

    for Vineyard in df_in['Vineyard'].unique():
        correl = df_in[df_in['Vineyard'] == Vineyard].corr()
        p_values = corr_sig(correl)
        plot_correl_matrix(correl, correlation_name='in_vs_in', vinyeard=Vineyard,p_values_flag='False')

        p_values_df = pd.DataFrame(p_values, columns=correl.columns.values.tolist(),
                                   index=correl.index.values.tolist())
        plot_correl_matrix(p_values_df, correlation_name='in_vs_in', vinyeard=Vineyard, p_values_flag='True')

    # in features vs. out features


        # [df.loc[:, ~df.columns.isin(['Vineyard', 'Treatment', 'Replication', 'Time','new_time'])], df_out.add_suffix('_out')],
        results = pd.concat([df_in, df_out.add_suffix('_out')], axis=1)
        correl_out = results[results['Vineyard'] == Vineyard].corr()
        out_cols = [col for col in correl_out.columns if '_out' in col]
        correl_out = correl_out[out_cols]
        correl_out = correl_out[~correl_out.index.str.contains('_out')]
        plot_correl_matrix(correl_out, correlation_name='in_vs_out', vinyeard=Vineyard,p_values_flag='False')

        p_values_square = corr_sig(correl_out)
        p_values_df = pd.DataFrame(p_values_square, columns=correl_out.columns.values.tolist(),
                                   index=correl_out.index.values.tolist())
        plot_correl_matrix(p_values_df, correlation_name='in_vs_out', vinyeard=Vineyard, p_values_flag='True')

def get_storage_per_treatment(storage_df: dict, exp_desc: dict):
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


def enrich_storage_per_treatment(storage_dict: dict):
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
        Temperature_dday = df_treatment_storage.groupby('Date')['Temperature'].mean().reset_index()
        Temperature_dday['Temperature'] = Temperature_dday['Temperature'].cumsum()
        df_treatment_storage['Temperature_dday'] = df_treatment_storage.merge(Temperature_dday,left_on='Date',right_on='Date')['Temperature_y']
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


def get_data_from_tsfresh(treatment_num: int, df: pd.DataFrame, storage_features: list = ['Humidity', 'Temperature']):
    '''
    :param treatment_num: int that represnt the treatment. this will be the key for tsfresh package
    :param df: dataframe of the storage frm treatment side. i.e. storage log per treatment
    :param storage_features: list of all features exist in the log.
    :return: df with x rows per each treatment, each row is a feature.
    '''
    data_for_tsfresh = df[['Date', 'Time', 'Humidity', 'Temperature']]
    data_for_tsfresh['treatment'] = treatment_num
    data_for_tsfresh.reset_index(inplace=True)
    tsfresh_extracted_features = {}
    for feature in storage_features:
        data_tsfresh = data_for_tsfresh[['treatment', 'index', feature]]
        extracted_features = extract_features(data_tsfresh, column_id='treatment', column_sort='index')
        tsfresh_extracted_features[feature] = extracted_features
    return pd.concat([tsfresh_extracted_features['Humidity'],tsfresh_extracted_features['Temperature']],axis=1)

def get_relevant_data_per_period(storage_dict: dict):
    '''
    :param storage_dict: dictionary contians storage data
    :return: dict contains statistics per each period per treatment
    '''
    final_storage_data_per_treatment = {}
    data_storage_for_all_periods = {}
    for treatments, values in storage_dict.items():
        df = values
        for i in range(1, 5):  # 4 periods
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
    :param dim_list: list of all dimensions that we want to create brakedown by + new_time column for function itself.
    :param df: raw_data
    :param col_name: relevant column names that we would like to create the grpahs
    :param col_name_t0: same list, but with values that have data on time 0 of storage
    :return: small df, from which we can simply create multiple subplots
    '''
    temp_df = pd.DataFrame()
    if col_name_t0 is not None:
        temp_df = df[DIMS_FOR_GRAPHS]
        temp_df['new_time'] = 0  # create manually time 0
        temp_df[col_name] = df[[col_name_t0]]
    dim_list_for_flatten = dim_list + [col_name]
    df_for_graph = pd.concat([df[dim_list_for_flatten], temp_df], ignore_index=True)
    return df_for_graph


def plot_graph(df: pd.DataFrame, col_name: str, dim_list: list, hue: str, tmp_dim_list: list, axs,
               ytickslim = None ,dist_week=None, dist_temp=None):
    '''

    :param df: flatten data frame with structered known data
    :param col_name: name of the feature that the figure will be based on.
    :param dim_list: dimensions list brakedown
    :param hue: variable to brake the lines with
    :param tmp_dim_list: dimensions list brakedown (hue)
    :param axs: changing axs to plot the figure on.
    :param ytickslim: set the y axis ticks to be equal in all subplots.
    :return: each facets with multiple subplots.
    '''
    df_plot = df.fillna(np.inf).groupby(dim_list)[[col_name]].mean().replace(np.inf, np.nan).reset_index()
    dim_list_for_grpah = dim_list + [col_name]
    sns.set_palette("Set2")
    axs = sns.lineplot(data=df_plot, x="new_time",
                       y=col_name, hue=hue, ci=95, legend=True, palette='Set2',
                       err_style="bars")
    if df_plot is None:
        axs = sns.lineplot(data=pd.DataFrame(), x="new_time",
                           y=col_name, hue=hue)
    axs.xaxis.set_major_locator(ticker.MultipleLocator(1))
    axs.set(xlabel='time', ylabel=col_name)
    axs.tick_params(axis='both', labelsize=20)
    axs.set_xlabel('Week', fontsize=21)
    axs.set_ylabel(col_name, fontsize=21)
    if ytickslim:
        axs.set_ylim(bottom=ytickslim[0], top=ytickslim[1])
    if dist_week:
        axs.set_title(label=col_name + ':  weeks_dist: ' + str(dist_week) + '  temp_dist: ' + str(dist_temp), size=20)
    else:
        axs.set_title(label=col_name + ' by ' + hue, size=20)
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


def get_data_storage(path_storage, treat_dict):
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
    df_storage_data_final = raw_data.merge(final_storage_data[RELEVANT_STORAGE_DATA], how='inner',
                                           left_on=['Treatment', 'new_time']
                                           , right_on=['treatment', 'mapped_period'])
    return df_storage_data_final


# def is_interesting_data_for_plot(df:pd.DataFrame):


def create_all_subplots(features_list: list, full_storage_data: pd.DataFrame, data_place_in_dict: int,
                        features_list_t0: list = None, dimension_list=DIMS_FOR_GRAPHS, ncols=4):
    '''
    :param data_place_in_dict: adding int for creating proper naming for the graph.
    :param features_list: list of all features exist in the data, on this features we will plot all relevant subplot
    :param features_list_t0:list of all features exist in the data, these features have also measure in t0,on this features we will plot all relevant subplot
    :param dim_list:all the relevant dimensions that we will brakedown the data with
    :param ncols: num of cols that will be in the subplot
    :param dimension_list: all the relevant dimensions that we will brakedown the data with
    :param full_storage_data: full data before treatment
    :return: number of facets, in each facet there will be subplots
    '''
    temp_dim_list = copy.copy(DIMS_FOR_GRAPHS)
    temp_dim_list.remove("new_time")

    # Compute Rows required
    Tot = len(relevant_cols)
    Cols = ncols
    Rows = Tot // Cols
    Rows += Tot % Cols

    data = (features_list, features_list_t0, range(len(features_list)))
    if features_list_t0 is None:
        data = (features_list, range(len(features_list)))

    for i, hue in enumerate(temp_dim_list):
        fig = plt.figure(figsize=(28, 28))
        fig.subplots_adjust(hspace=0.4, wspace=0.3)
        i_print = 1
        for tup in zip(*data):
            data_for_grpah = flatten_data_to_grpah(dim_list=dimension_list, df=full_storage_data, col_name=tup[0],
                                                   col_name_t0=tup[
                                                       1] if features_list_t0 is not None else None)  # take t0 data if exist
            df_plot_check = data_for_grpah.fillna(np.inf).groupby(dimension_list)[[tup[0]]].mean().replace(np.inf,
                                                                                                           np.nan).reset_index()
            # new_df['new_time'] = new_df['Time'].map(match).fillna(0)
            data_for_grpah['disruption_length'] = np.where(data_for_grpah['disruption_length'] == 12, 0,
                                                           data_for_grpah[
                                                               'disruption_length'])  # mapping 12 to 0 for graphs
            data_for_grpah['new_time'] = data_for_grpah['new_time'] * 3
            #y lim axis changes
            if 'Decay (' in tup[0]:
                ylim = (data_for_grpah.iloc[:, -1].quantile(0.01), 10)
            elif 'FER_RG' in tup[0]:
                ylim = (3,5)
            elif 'Ferrari' in tup[0]:
                ylim = (0.3,0.7)
            else:
                ylim = (data_for_grpah.iloc[:, -1].quantile(0.01), data_for_grpah.iloc[:, -1].quantile(0.99))
            if 1 == 1:
                    # (df_plot_check[[hue, tup[0]]][tup[0]]).nunique() > max(df_plot_check[hue].nunique(), 4):
                ax = fig.add_subplot(Rows, ncols, i_print)
                plot_graph(df=data_for_grpah, col_name=tup[0], dim_list=dimension_list, hue=hue,
                           tmp_dim_list=temp_dim_list, axs=ax, ytickslim=ylim)
                i_print += 1
                ax.get_legend().remove()
        handles, labels = ax.get_legend_handles_labels()
        fig.legend(handles, labels, fontsize=18, loc='lower right', bbox_to_anchor=(1, 0.1))
        fig2 = plt.gcf()
        plt.show()
        plt.draw()
        fig2.savefig('figures_update/' + str(data_place_in_dict) + '_' + hue + '_' + str(i) + '.png',bbox_inches='tight')


def create_all_subplots_per_each_fruit_feature(features_list: list, full_storage_data: pd.DataFrame,
                                               data_place_in_dict: int,
                                               features_list_t0: list = None, dimension_list=DIMS_FOR_GRAPHS
                                               ):
    '''

    :return: number of facets, in each facet there will be subplots
    '''
    temp_dim_list = copy.copy(DIMS_FOR_GRAPHS)
    temp_dim_list.remove("new_time")

    # Compute Rows required,added 1 for folded dim
    Cols = full_storage_data['disruption_length'].nunique() + 1  # for folded data
    Rows = full_storage_data['disruption_temperature'].nunique() + 1  # for folded data

    data = (features_list, features_list_t0, range(len(features_list)))
    if features_list_t0 is None:
        data = (features_list, range(len(features_list)))

    # loop for each feature
    # still there is a bug in TA, TSS
    for i, feature in enumerate(data[0]):
        fig = plt.figure(figsize=(42, 42))
        fig.subplots_adjust(hspace=0.4, wspace=0.3)
        i_print = 1
        # change 12 weeks to 0 weeks - i.e. - no interruptions
        full_storage_data['disruption_length'] = np.where(full_storage_data['disruption_length'] == 12, 0,
                                                          full_storage_data['disruption_length'])
        data_for_grpah = flatten_data_to_grpah(dim_list=dimension_list, df=full_storage_data, col_name=data[0][i],
                                               col_name_t0=data[1][
                                                   i] if features_list_t0 is not None else None)  # take t0 data if exist
        data_for_grpah['new_time'] = data_for_grpah['new_time'] * 3
        ylim = (data_for_grpah.iloc[:,-1].quantile(0.01),data_for_grpah.iloc[:,-1].quantile(0.99))

        #fake assign for print only (i.e. split humidity with fake)
        data_for_grpah['disruption_length'] = np.where((
            (data_for_grpah['disruption_length'] == 0) & (data_for_grpah['Treatment'] == 2)), 1, data_for_grpah['disruption_length'])
        #9999 is fake for folding placeholder
        for temp in sorted(sorted(full_storage_data['disruption_temperature'].unique()) + [9999]):
            for length in sorted(sorted(full_storage_data['disruption_length'].unique()) + [9999]):
                #don't print bottom right
                if temp == 9999 and length == 9999:
                    break
                ax = fig.add_subplot(Rows, Cols, i_print)
                #added this part for treatments 1+2 where it is same temp but humidity is different
                if temp == 0 and length == 0:  # need 2 prints: treatment 1,2
                    plot_data_df = data_for_grpah[(data_for_grpah['disruption_temperature'] == temp) & (
                                                  data_for_grpah['Treatment'] == 1)]
                    plot_graph(df=plot_data_df, col_name=data[0][i], dim_list=dimension_list, hue='Vineyard',
                               tmp_dim_list=temp_dim_list, axs=ax, dist_week=length,
                               dist_temp=temp, ytickslim=ylim)
                    i_print += 1
                    if len(plot_data_df):
                        ax.get_legend().remove()
                    ax = fig.add_subplot(Rows, Cols, i_print)

                elif temp == 0 and length == 1:  # need 2 prints: treatment 1,2
                    plot_data_df = data_for_grpah[(data_for_grpah['disruption_temperature'] == temp) & (
                            data_for_grpah['Treatment'] == 2)]
                    plot_graph(df=plot_data_df, col_name=data[0][i], dim_list=dimension_list, hue='Vineyard',
                               tmp_dim_list=temp_dim_list, axs=ax, dist_week=0,
                               dist_temp=temp, ytickslim=ylim)
                    i_print += 1
                    if len(plot_data_df):
                        ax.get_legend().remove()
                    ax = fig.add_subplot(Rows, Cols, i_print)
                    # assign data back
                    data_for_grpah['disruption_length'] = np.where(
                        ((data_for_grpah['disruption_temperature'] == 0) &
                         (data_for_grpah['disruption_length'] == 1) & (data_for_grpah['Treatment'] == 2)), 0,
                        data_for_grpah['disruption_length'])
                #folded by temp
                elif length == 9999:
                    plot_data_df = data_for_grpah[(data_for_grpah['disruption_temperature'] == temp)]
                    plot_graph(df=plot_data_df, col_name=data[0][i], dim_list=dimension_list, hue='Vineyard',
                               tmp_dim_list=temp_dim_list, axs=ax, dist_week='All',dist_temp=temp, ytickslim=ylim)
                    i_print += 1
                # folded by length
                elif temp == 9999:
                    plot_data_df = data_for_grpah[(data_for_grpah['disruption_length'] == length)]
                    plot_graph(df=plot_data_df, col_name=data[0][i], dim_list=dimension_list, hue='Vineyard',
                               tmp_dim_list=temp_dim_list, axs=ax, dist_week=length,dist_temp='All', ytickslim=ylim)
                    i_print += 1
                else:
                    plot_data_df = data_for_grpah[(data_for_grpah['disruption_temperature'] == temp) & (
                                data_for_grpah['disruption_length'] == length)]
                    plot_graph(df=plot_data_df, col_name=data[0][i], dim_list=dimension_list, hue='Vineyard',
                               tmp_dim_list=temp_dim_list, axs=ax, dist_week=0 if length == 12 else length,
                               dist_temp=temp, ytickslim=ylim)
                    i_print += 1

                    if len(plot_data_df):
                        ax.get_legend().remove()

        handles, labels = ax.get_legend_handles_labels()
        # fig.legend(handles, labels, fontsize=18, loc='lower right', bbox_to_anchor=(1, 0.1))
        fig2 = plt.gcf()
        plt.show()
        plt.draw()
        fig2.savefig('features_by_matrix/test/' + str(data_place_in_dict) + '_' + feature + '_' + str(i) + '.png',bbox_inches='tight')


if __name__ == '__main__':
    raw_data = get_prep_df(path=PATH, path_b=PATH_B, path_v=PATH_VINYARDS, treatment_dict=TREAT_DESCRIPTION)
    full_data_w_storage = get_data_storage(path_storage=PATH_STORAGE, treat_dict=TREAT_DESCRIPTION)

    # print all subplots
    relevant_t0_cols, relevant_cols = get_all_t0(df=full_data_w_storage)
    storage_list = ['Temperature_dday','kPa']

    data_to_plot = {1: [relevant_cols, relevant_t0_cols],  # data that collected both in and out
                     # 2: [COLS_ONLY_OUT, 'None'],  # data collected only in out storage
                    #3: [storage_list, 'None']  # data relevant for storage only
                    }
    # 1 image with all features, per 3 dimensions: vineyard, length, temp
    for feature_list in enumerate(data_to_plot.values()):
        create_all_subplots(features_list=feature_list[1][0], full_storage_data=full_data_w_storage,
                            features_list_t0=feature_list[1][1] if feature_list[1][1] != 'None' else None,
                            dimension_list=DIMS_FOR_GRAPHS, ncols=4, data_place_in_dict=feature_list[0])


    # matrix plotting + folded dim
    # for feature_list in enumerate(data_to_plot.values()):
    #     create_all_subplots_per_each_fruit_feature(features_list=feature_list[1][0], full_storage_data=full_data_w_storage,
    #                             features_list_t0=feature_list[1][1] if feature_list[1][1] != 'None' else None,
    #                             dimension_list=DIMS_FOR_GRAPHS, data_place_in_dict=feature_list[0])


    # # create correlation matrix
    # in_cols = [col for col in raw_data.columns if 'T0' in col and col!= 'Shatter (T0)']
    # create_pearson_correl(raw_data, col_list_in=in_cols, col_list_out=COLS_OUT)
    print("Done!!!")