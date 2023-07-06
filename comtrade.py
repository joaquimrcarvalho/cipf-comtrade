"""
Module comtrade.

Auxiliary functions and data to access the
UN Comtrade API.


"""
import logging
import os
from typing import Union
import warnings
import re
import json
from pathlib import Path
import urllib.request

import requests
import pandas as pd

from ratelimit import limits, sleep_and_retry

SUPPORT_DIR = 'support'

Path(SUPPORT_DIR).mkdir(parents=True, exist_ok=True)

APIKEY = None
BASE_URL_PREVIEW = "https://comtradeapi.un.org/public/v1/preview/"
BASE_URL_API = "https://comtradeapi.un.org/data/v1/get/"

CALLS_PER_PERIOD = 1  # number of calls per period
PERIOD_SECONDS = 12  # period in seconds

# we use a copy of the codebook in git because the original cannot be downloaded
#   without human action
CODE_BOOK_URL = "https://raw.githubusercontent.com/joaquimrcarvalho/cipf-comtrade/main/support/codebook.xlsx"
CODE_BOOK_FILE = "support/codebook.xlsx"

COUNTRY_CODES: dict = {}
COUNTRY_CODES_REVERSE: dict = {}
MOS_CODES: dict = {}
CUSTOMS_CODE: dict = {}
FLOWS_CODES: dict = {}
MOT_CODES: dict = {}
QTY_CODES: dict = {}
QTY_CODES_DESC: dict = {}
COLS_DESC_DF = None
COLS_DESC: dict = {}
PLP_CODES: dict = {}
PLP_CODES_REVERSE: dict = {}
PLP_TUPLES: list = []
PLP_TUPLES_REVERSE: list = []


# Specific codes for Portuguese Speaking Countries
# in the future package move this to a separate file
m49_angola = 24
m49_brazil = 76
m49_cabo_verde = 132
m49_china = 156
m49_hong_kong = 344
m49_macau = 446
m49_guine_equatorial = 226
m49_guine_bissau = 624
m49_mozambique = 508
m49_portugal = 620
m49_stome_principe = 678
m49_timor = 626


# make list of Portuguese Speaking Countries
m49_plp = [m49_angola,m49_brazil,m49_cabo_verde,m49_guine_bissau,
            m49_guine_equatorial,m49_mozambique,m49_portugal,
            m49_stome_principe,m49_timor]
# make string of Portuguese Speaking Countries codes
m49_plp_list = ",".join(map(str,m49_plp))


# HS Codes are not included in the codebook
HS_CODES_FILE = 'support/harmonized-system.csv'
HS_CODES_URL = 'https://github.com/datasets/harmonized-system/blob/master/data/harmonized-system.csv?raw=true'

HS_CODES_DF = None
HS_CODES_L2_DF = None

HS_CODES: dict = {}
HS_CODES_L2: dict = {}

# label for the percentage of a commodity in the total trade of a country
PERC_CMD_IN_PARTNER = 'perc_cmd_for_partner'

# label for the percentage of a country in the total trade of a commodity
PERC_PARTNER_IN_CMD = 'perc_partner_for_cmd'

global INIT_DONE

INIT_DONE = False # flag to avoid multiple initialization

def init(apy_key: Union[str,None]=None, code_book_url: Union[None,str]=None, force_init: bool=False):
    """Set the API Key and codebooks for the module
    
    Args:
        apy_key (Union[str,None], optional): API Key. Defaults to None.
        code_book_url (Union[None,str], optional): URL to download codebook. Defaults to None.
        force_init (bool, optional): Force initialization. Defaults to False.
    """

    global APIKEY
    global CODE_BOOK_URL
    global INIT_DONE

    global PLP_CODES
    global PLP_CODES_REVERSE
    global PLP_TUPLES
    global PLP_TUPLES_REVERSE

    # if already initialized, do nothing
    if INIT_DONE and not force_init:
        return

    APIKEY = apy_key
    INIT_DONE = True

    if not os.path.isfile(CODE_BOOK_FILE):
        logging.info(f"Downloading codebook from {CODE_BOOK_URL}")
        urllib.request.urlretrieve(CODE_BOOK_URL, CODE_BOOK_FILE)
        print("un-comtrade codeboox downloaded")

    # Get the worksheets from the Excel workbook
    code_book_xls = pd.ExcelFile(CODE_BOOK_FILE)
    worksheets = code_book_xls.sheet_names

    # if not cached save each work sheet again
    for worksheet in worksheets:
        cache_file = f"support/{worksheet}.csv"
        if not os.path.isfile(cache_file):
            xls = pd.read_excel(CODE_BOOK_FILE, sheet_name=worksheet)
            xls.to_csv(cache_file, index=False)
            print(f"Worksheet {worksheet} saved to {cache_file}")

    COUNTRY_CODE_FILE="support/REF COUNTRIES.csv"
    MOS_CODE_FILE="support/REF  MOS.csv"
    CUSTOMS_CODE_FILE="support/REF CUSTOMS.csv"
    FLOWS_CODE_FILE="support/REF FLOWS.csv"
    MOT_CODE_FILE="support/REF MOT.csv"
    QTY_CODE_FILE="support/REF QTY.csv"
    COLS_DESCRIPTION_FILE="support/COMTRADE+ COMPLETE.csv"


    # Process codebook tables into dictionnaries
    global COUNTRY_CODES 
    COUNTRY_CODES = pd.read_csv(COUNTRY_CODE_FILE, index_col=0).squeeze().to_dict()

    global COUNTRY_CODES_REVERSE
    COUNTRY_CODES_REVERSE = {v: k for k, v in COUNTRY_CODES.items()}

    global MOS_CODES
    MOS_CODES = pd.read_csv(MOS_CODE_FILE, index_col=0).squeeze().to_dict()

    global CUSTOMS_CODE
    CUSTOMS_CODE = pd.read_csv(CUSTOMS_CODE_FILE, index_col=0).squeeze().to_dict()

    # flows have two columns: description and category. Category maps to "M" or "X" the variants
    global FLOWS_CODES
    FLOWS_CODES = pd.read_csv(FLOWS_CODE_FILE, index_col=0,usecols=[0,1]).squeeze().to_dict()

    global FLOWS_CODES_CAT
    FLOWS_CODES_CAT = pd.read_csv(FLOWS_CODE_FILE, index_col=0,usecols=[0,2]).squeeze().to_dict()

    global MOT_CODES
    MOT_CODES = pd.read_csv(MOT_CODE_FILE, index_col=0).squeeze().to_dict()

    # quantity codes have two columns: abbreviations (m2,km,...) and full description
    global QTY_CODES
    QTY_CODES = pd.read_csv(QTY_CODE_FILE, index_col=0,usecols=[0,1]).squeeze().to_dict()

    global QTY_CODES_DESC
    QTY_CODES_DESC = pd.read_csv(QTY_CODE_FILE, index_col=0,usecols=[0,2]).squeeze().to_dict()
    # Additionally the codebook contains a description of the columns

    global COLS_DESC_DF
    COLS_DESC_DF = pd.read_csv(COLS_DESCRIPTION_FILE, index_col=0,usecols=[0,5])

    global COLS_DESC
    COLS_DESC = COLS_DESC_DF.squeeze().to_dict()

    global HS_CODES_DF
    # HS Codes are not included in the codebook
    if os.path.isfile(HS_CODES_FILE):
        logging.info(f"Loading HS codes from {HS_CODES_FILE}")
        HS_CODES_DF = pd.read_csv(HS_CODES_FILE) # read table
    else:
        logging.info(f"Downloading HS codes from {HS_CODES_URL}")
        HS_CODES_DF = pd.read_csv(HS_CODES_URL) # read from CODE_BOOK_url
        HS_CODES_DF.to_csv(HS_CODES_FILE)

    global HS_CODES
    HS_CODES = dict(zip(HS_CODES_DF.hscode, HS_CODES_DF.description)) #  dict for decoding

    global HS_CODES_L2_DF
    HS_CODES_L2_DF = HS_CODES_DF[HS_CODES_DF.level == 2]  # create subset of level 2 codes

    global HS_CODES_L2
    HS_CODES_L2 = dict(zip(HS_CODES_L2_DF.hscode, HS_CODES_L2_DF.description)) # dict for decoding 

    # extract dict and tuples for plp_list from country_codes
    PLP_CODES = {k: v for k, v in COUNTRY_CODES.items() if k in m49_plp}
    PLP_CODES_REVERSE = {v: k for k, v in PLP_CODES.items()}
    PLP_TUPLES = list(PLP_CODES.items())
    PLP_TUPLES_REVERSE = list(PLP_CODES_REVERSE.items())

    #global INIT_DONE
    #INIT_DONE = True


def getURL(apiKey:Union[str,None]=None):
    """Get the URL for the API call"""

    if apiKey == 'APIKEYHERE':
        apiKey=None
    if apiKey is None:
        uncomtrade_url = BASE_URL_PREVIEW
    else:
        uncomtrade_url = BASE_URL_API

    # log to info
    logging.info("baseURL: "+uncomtrade_url)

    if apiKey is not None:
        logging.info("APIKEY: "+apiKey[:8])

    return uncomtrade_url


@sleep_and_retry
@limits(calls=CALLS_PER_PERIOD, period=PERIOD_SECONDS)
def get_data(typeCode: str, freqCode: str, 
                    reporterCode: str = '49', 
                    partnerCode: str = '024,076,132,226,624,508,620,678,626',
                    partner2Code: str = 0,
                    period: str = None,
                    clCode: str = "HS",
                    cmdCode: str = "TOTAL",
                    flowCode: str = "M,X",
                    customsCode:str = 'C00', 
                    more_pars = {},
                    qtyUnitCodeFilter = None,
                    motCode = None,
                    apiKey:Union[str,None]=None,
                    timeout: int = 10,
                    echo_url: bool = False
                    )-> Union[pd.DataFrame,None]:
    """ Makes a query to UN Comtrade+ API, returns a pandas DataFrame

    Args:
        typeCode (str): Type of data to retrieve, C for commodities, S for Services
        freqCode (str): Frequency of data, A for annual, M for monthly
        reporterCode (str, optional): Reporter country code. Defaults to '49'.
        partnerCode (str, optional): Partner country code. Defaults to '024,076,132,226,624,508,620,678,626'.
        partner2Code (str, optional): Partner2 country code. Defaults to 0 (world). Use -1 to remove 0 (world)
        period (str, optional): Period of data, e.g. 2018, 2018,2019, 2018,2019,2020. Defaults to None.
        clCode (str, optional): Classification code, HS for Harmonized System, SITC for Standard International Trade Classification. Defaults to "HS".
        cmdCode (str, optional): Commodity code, TOTAL for all commodities. Defaults to "TOTAL".
        flowCode (str, optional): Flow code, M for imports, X for exports. Defaults to "M,X".
        customsCode (str, optional): Customs code, C00 for all customs. Defaults to 'C00'.
        more_pars (dict, optional): Additional parameters to pass to the API.
        qtyUnitCodeFilter (str, optional): Quantity unit code, e.g. 1 for tonnes, 2 for kilograms. Defaults to None.
        motCode (str, optional): Mode of transport code, e.g. 0 for all, 1 for sea, 2 for air. Defaults to None. If -1 is passed removes results with motCode = 0, 
        apiKey (str,optional): API Key for umcomtrade+
        timeout (int, optional): Timeout for the API call. Defaults to 10.
        echo_url (bool, optional): Echo the CODE_BOOK_url to the console. Defaults to False.
    
     """
    if apiKey is None:
        apiKey = APIKEY

    base_url=f"{getURL(apiKey)}/{typeCode}/{freqCode}/{clCode}"
    if partner2Code == -1:  # -1 
        partner2CodePar = None
    else:
        partner2CodePar = partner2Code
        
    pars = {
            'reporterCode':reporterCode,
            'period':period,
            'partnerCode':partnerCode,
            'partner2CodePar':partner2CodePar,
            'cmdCode':cmdCode,
            'flowCode':flowCode,
            'customsCode':customsCode,
            'subscription-key':apiKey,
            }
    error: bool = False
    resp = requests.get(base_url,
            {**pars, **more_pars},
            timeout=timeout)
    if echo_url:
        sanitize = re.sub("subscription-key=.*","subscription-key=HIDDEN",resp.url)
        print(sanitize)
    if resp.status_code != 200:
        warnings.warn(f"Server returned HTTP Status: {str(resp.status_code)}",)     
        errorInfo = json.loads(resp.content)
        message = errorInfo.get('message',resp.content)
        warnings.warn(f"Server returned error: {message}")
        df = None
        error = True
    else:
        resp_json = json.loads(resp.content)
        error_json = resp_json.get('statusCode',None)
        if error_json is not None:
            error_message = resp_json.get('message',None)
            warnings.warn(f"Server returned JSON error: {error_json}: {error_message}")        
            df = None
            error = True
        
    if error:
        return None
    else:
        results = json.loads(resp.content)['data']
        if len(results) == 0:
            warnings.warn("Query returned no results")
            df = None
        else:
            df = pd.DataFrame(results)

            if partnerCode is None:
                # when partnerCode is None, the API returns partnerCode = 0 for the world
                #  and partnerCode for each partner. We remove the world entry
                df = df[df.partnerCode != 0]

            if qtyUnitCodeFilter is not None:
                df = df[df.qtyUnitCode == qtyUnitCodeFilter]

            if motCode is not None:
                if motCode == -1: # Remove motCode = 0
                    lenBefore = len(df)
                    df = df[df.motCode != 0]
                    lenAfter = len(df)
                    if lenBefore != lenAfter:
                        warnings.warn(f"Removed {lenBefore-lenAfter} results with motCode = 0")
                else:           # Keep only specified motCode
                    df = df[df.motCode == motCode]
            else:
                motCodes = df['motCode'].unique()
                if len(motCodes) > 1 and 0 in motCodes:
                    warnings.warn("Query returned different motCodes including 0 (all), check for duplicate results when aggregating. Use motCode = -1 to remove motCode = 0, or motCode=0 to remove details")
            
            if len(df['isAggregate'].unique()) > 1:
                warnings.warn("Query returned different isAggregate values, check for duplicate results when aggregating")
                
            # check for multiple partner2Codes and potentially duplicate results
            
            if partner2Code == -1: # Remove partner2Code = 0
                df = df[df.partner2Code != 0]
            elif partner2Code is not None: # Keep only specified partner2Code
                df = df[df.partner2Code == partner2Code]
            
            partner2Codes = df['partner2Code'].unique()
            if len(partner2Codes) > 1 and 0 in partner2Codes:
                warnings.warn("Query returned different partner2Codes including 0 (all), check for duplicate results when aggregating. Use partner2Code = -1 to remove partner2Code = 0, or partner2Code=0 to remove details")  


            # Convert the country codes to country names
            if 'reporterCode' in df.columns.values:
                df.reporterDesc = df.reporterCode.map(COUNTRY_CODES)
            if 'partnerCode' in df.columns.values:
                df.partnerDesc = df.partnerCode.map(COUNTRY_CODES)
            if 'partner2Code' in df.columns.values:
                df.partner2Desc = df.partner2Code.map(COUNTRY_CODES)

            # Convert flowCode
            if 'flowCode' in df.columns.values:
                df['flowDesc'] = df.flowCode.map(FLOWS_CODES)
            # Convert the HS codes
            if 'cmdCode' in df.columns.values:
                df['cmdDesc'] = df.cmdCode.map(HS_CODES)

            # Convert customsCode
            if 'customsCode' in df.columns.values:
                df['customsDesc'] = df.customsCode.map(CUSTOMS_CODE)

            # Convert mosCode
            if 'mosCode' in df.columns.values:
                df['mosDesc'] = df.mosCode.map(MOS_CODES)

            # Convert motCode
            if 'motCode' in df.columns.values:
                df['motDesc'] = df.motCode.map(MOT_CODES)

            # Convert qtyUnitCode
            if 'qtyUnitCode' in df.columns.values:
                df['qtyUnitAbbr'] = df.qtyUnitCode.map(QTY_CODES)
                df['qtyUnitDesc'] = df.qtyUnitCode.map(QTY_CODES_DESC)

            # Convert altQtyUnitCode
            if 'altQtyUnitCode' in df.columns.values:
                df['altQtyUnitAbbr'] = df.altQtyUnitCode.map(QTY_CODES)
                df['altQtyUnitDesc'] = df.altQtyUnitCode.map(QTY_CODES_DESC)

            # Generate a formated version of the value for readability here
            if 'primaryValue' in df.columns.values:
                df['primaryValueFormated'] = df.primaryValue.map('{:,.2f}'.format)
            # return the DataFrame
        return df


def top_commodities(reporterCode, 
                    partnerCode=0, 
                    years=None, 
                    flowCode='M,X', 
                    partner2Code=0,
                    motCode=None, rank_filter=5, 
                    partner_first=False, 
                    extra_cols = None,
                    return_data = False,
                    timeout=120, echo_url=False):
    """Get the top commodities (level 2 HS nomenclature) traded between countries for a given year range
    
    Args:
        reporterCode (str): reporter country code, e.g. 49 for China
        partnerCode (str): partner country code, 0 for the world, None for all, code or CSV
        partner2Code (str): partner2 country code, 0 for world, 
                            -1 all but World, None for all, default 0
        years (str): year range, e.g. 2010,2011,2012
        flowCode (str): flow code, e.g. M for imports, X for exports, defaults to M,X
        motCode (str, optional): Mode of transport code, e.g. 0 for all, 1 for sea, 2 for air. 
                                 Defaults to None. If -1 is passed removes results with motCode = 0
        rank_filter (int): number of top commodities to return, default 5
        partner_first (bool): if True, return top 5 partners and for each partner 
                                the top 5 commodities;
                                if False return top 5 commotidites and for each 
                                commodity the top 5 partners. Default False

        extra_cols (list): other than the default columns, add extra columns to the DataFrame
        return_data (bool): return the original data before clipping, If true
                            returns a tuple (top_commodities, data)
        echo_url (bool): print the url to the console, default False
    
        
    """
    df = get_data("C",# C for commodities, S for Services
                     "A",# (freqCode) A for annual and M for monthly
                     flowCode=flowCode,
                     cmdCode="AG2",
                     reporterCode=reporterCode,
                     partnerCode=partnerCode,
                     partner2Code=partner2Code,
                     period=years,
                     motCode=motCode,
                     timeout=timeout,
                     echo_url=echo_url
                     )
    
    if df is None:  
        warnings.warn("No data returned, check the parameters")
        return None
    
    if extra_cols is None:
        extra_cols = []

    # Total value of commodities per HS code
    df['sum_cmd'] = df.groupby(['reporterDesc','refYear','flowCode','cmdCode'])['primaryValue'].transform('sum')  
    # Total value of commodities per partner
    df['sum_partner'] = df.groupby(['reporterDesc','refYear','flowCode','partnerCode'])['primaryValue'].transform('sum')
    # rank of commodity per HS code
    df['rank_cmd'] = df.groupby(['reporterDesc','refYear','flowCode'])['sum_cmd'].rank(ascending=False,method='dense')
    df['rank_cmd'] = df['rank_cmd'].astype(int)

    # value of trade as percentage of total same HS code
    df[PERC_PARTNER_IN_CMD] = df['primaryValue']/df['sum_cmd']
    # value of trade as percentage of total same partner
    df[PERC_CMD_IN_PARTNER] = df['primaryValue']/df['sum_partner']

    # rank of partner per HS code
    df['rank_cmd_partner'] = df.groupby(['reporterDesc','refYear','flowCode','cmdCode'])['primaryValue'].rank(ascending=False,method='dense')
    df['rank_cmd_partner'] = df['rank_cmd_partner'].astype(int)

    # global rank of partner
    df['rank_partner'] = df.groupby(['reporterDesc','refYear','flowCode'])['sum_partner'].rank(ascending=False,method='dense')
    df['rank_partner'] = df['rank_partner'].astype(int)

    # chage result according to partner_first
    if partner_first:
        rank_cut = (df['rank_partner'] <= rank_filter) & (df['rank_partner_cmd'] <= rank_filter)
        sort_list = ['refYear','flowCode','rank_partner','rank_partner_cmd']
        sort_order = [True,True,True,True]
        show_cols = ['reporterDesc','refYear','flowCode','flowDesc','rank_partner','partnerDesc',
                     'rank_partner_cmd','rank_cmd','cmdCode', 'cmdDesc','primaryValueFormated',
                     PERC_CMD_IN_PARTNER,PERC_PARTNER_IN_CMD]
    else:
        rank_cut = (df['rank_cmd'] <= rank_filter) & (df['rank_cmd_partner'] <= rank_filter)
        sort_list = ['refYear','flowCode','rank_cmd','rank_cmd_partner']
        sort_order = [True,True,True,True]
        show_cols = ['reporterDesc','refYear','flowCode','flowDesc','rank_cmd','cmdCode','cmdDesc',
                     'rank_cmd_partner','rank_partner','partnerDesc','primaryValueFormated',
                     PERC_CMD_IN_PARTNER,PERC_PARTNER_IN_CMD]


    pco = df[rank_cut].sort_values(sort_list, ascending=sort_order)[show_cols+extra_cols]
    if return_data:
        return (pco, df)
    else:
        return pco

def get_global_stats(reporterCode, years,timeout=120, echo_url=False):
    """
    Get the Import/Export totals for a given country and year range

    Args:
        reporterCode (str): reporter country code, e.g. 49 for China
        years (str): year range, e.g. 2010,2011,2012
        timeout (int): timeout in seconds for the request, default 120
        echo_url (bool): print the url to the console, default False
    
    Returns:
        DataFrame: DataFrame with the totals for each year and flow indexed
                   by year and flow code"""
    
    global_stats = get_data('C','A',reporterCode, 0, 0, years, motCode=0, timeout=timeout, echo_url=echo_url)
    global_stats.set_index(['refYear','flowCode'], inplace=True)
    return global_stats

def top_partners(reporterCode=0, 
                 years=None,  
                 cmdCode='TOTAL', 
                 flowCode='M,X', 
                 partnerCode=None,
                 partner2Code=0,
                 motCode=0, 
                 customsCode=None,
                 rank_filter=5,   
                 extra_cols=None,
                 return_data=False,
                 timeout=120, echo_url=False):
    """Get the top trade partners of a country 
        (as reported by said country) 
        for a given year range
    
    Args:
        reporterCode (str): reporter country code, e.g. 49 for China
        years (str): year range, e.g. 2010,2011,2012
        cmdCode (str): HS code, e.g. TOTAL for all commodities, or AG2, AG4 or specific
        flowCode (str): flow code, e.g. M for imports, X for exports, defaults to M,X
        partnerCode (str, optional): partner country code, e.g. 842 for USA, defaults to None (all)
        partner2Code (str, optional): second partner country code, e.g. 842 for USA, defaults to 0 (world)
                                    None for all, -1 for all but world.
        motCode (str, optional): Mode of transport code, e.g. 0 for all, 1 for sea, 2 for air. 
                                 Defaults to None. If -1 is passed removes results with motCode = 0
        customsCode (str, optional): Customs procedure code, e.g. C00 for all, C05 for free zone.
        rank_filter (int): number of top commodities to return, default 5
        extra_cols (list): other than the default columns, add extra columns to the DataFrame
        return_data (bool): return the DataFrame with the results and the DataFrame with the
                            full data as a tuple, default False
        echo_url (bool): print the url to the console, default False
    
    """
    # TODO Not sure this is good idea. Maybe if "few" show these cols.
    show_cols = ['reporterDesc','refYear','flowCode','rank_cmd','partnerCode','partnerDesc','cmdCode','cmdDesc',
                    'primaryValue','primaryValueFormated']
    df = get_data("C",# C for commodities, S for Services
                     "A",# (freqCode) A for annual and M for monthly
                     flowCode=flowCode,
                     cmdCode=cmdCode,
                     reporterCode=reporterCode,
                     partnerCode=partnerCode,
                     partner2Code=partner2Code,
                     period=years,
                     motCode=motCode,
                     customsCode=customsCode,
                     timeout=timeout,
                     echo_url=echo_url
                     )

    if extra_cols is None:
        extra_cols = []

    # check if this is not beiing handled in getdata
    df = df[df['partnerCode'] != 0]

    # Total value of commodities per HS code
    df['sum_cmd'] = df.groupby(['reporterDesc','refYear','flowCode','cmdCode'])['primaryValue'].transform('sum')  

    df['sum_partner'] = df.groupby(['reporterDesc','refYear','flowCode','partnerCode'])['primaryValue'].transform('sum')
    df['per_partner'] = df['primaryValue'] / df['sum_partner']  
    
    # global rank of partner
    df['rank_partner'] = df.groupby(['reporterDesc','refYear','flowCode'])['sum_partner'].rank(ascending=False,method='dense')
    df['rank_partner'] = df['rank_partner'].astype(int)

    # rank of commodity per partner
    df['rank_partner_cmd'] = df.groupby(['reporterDesc','refYear','flowCode','partnerCode'])['primaryValue'].rank(ascending=False,method='dense')
    df['rank_partner_cmd'] = df['rank_partner_cmd'].astype(int)

    # rank of partner per HS code
    df['rank_cmd_partner'] = df.groupby(['reporterDesc','refYear','flowCode','cmdCode'])['primaryValue'].rank(ascending=False,method='dense')
    df['rank_cmd_partner'] = df['rank_cmd_partner'].astype(int)

    # value of trade as percentage of total same HS code
    df[PERC_PARTNER_IN_CMD] = df['primaryValue']/df['sum_cmd']
    # value of trade as percentage of total same partner
    df[PERC_CMD_IN_PARTNER] = df['primaryValue']/df['sum_partner']

    sort_list = ['refYear','flowCode','cmdCode','primaryValue']
    sort_order = [True,True,True,False]
    
    rank_cut = (df['rank_partner'] <= rank_filter) & (df['rank_partner_cmd'] <= rank_filter)
    pco_cut = df[rank_cut]
    pco_cut_sorted = pco_cut.sort_values(sort_list, ascending=sort_order)

    diff_cols = set(show_cols+extra_cols) - set(pco_cut_sorted.columns)
    if len(diff_cols) > 0:
        raise ValueError(f"Column(s) {diff_cols} not found in DataFrame {pco_cut_sorted.columns}")
    if return_data:
        return (pco_cut_sorted[show_cols+extra_cols], df)  
    else:
        return pco_cut_sorted[show_cols+extra_cols]

def year_range(year_start=1984,year_end=2030):
    """Return a string with comma separeted list of years
    
    Args:
        year_start (int, optional): Start year. Defaults to 1984.
        year_end (int, optional): End year. Defaults to 2030.

    """
    period = ",".join(map(str,list(range(year_start,year_end,1))))
    return period

def excel_col_autowidth(data_frame: pd.DataFrame, excel_file: pd.ExcelWriter, sheet=None):
    """Set the column width in the Excel file to the maximum width of the data in the column
    
    Args:
        data_frame (pd.DataFrame): The DataFrame to format
        excel_file (pd.ExcelWriter): The ExcelWriter object
        sheet (str, optional): The sheet name. Defaults to first one

    """

    # get the name of the first sheet
    if sheet is None:
        sheet = list(excel_file.sheets.keys())[0]

    # for each level of the index
    for indx_n, index in enumerate(data_frame.index.names):
        if index is not None:
            index_col = index
        else:
            index_col = ''

        col_width = max(data_frame.index.get_level_values(indx_n).astype(str).map(len).max(), len(index_col))
        if col_width > 100:
            col_width = 100

        excel_file.sheets[sheet].set_column(indx_n, indx_n, col_width)

    for column in data_frame:
        col_width = max(data_frame[column].astype(str).map(len).max(), len(column))
        if col_width > 100:
            col_width = 100

        col_idx = data_frame.columns.get_loc(column) + indx_n + 1
        excel_file.sheets[sheet].set_column(col_idx, col_idx, col_width)

def excel_format_currency(data_frame: pd.DataFrame, excel_file: pd.ExcelWriter, sheet=None,columns=None, format= '$#,##0', width=None):
    """Format the columns in the Excel file as currency
    
    Args:
        data_frame (pd.DataFrame): The DataFrame to format
        excel_file (pd.ExcelWriter): The ExcelWriter object
        sheet (str, optional): The sheet to format. Defaults to None, first sheet.
        columns (list, optional): The columns to format. Defaults to all numeric columns.
        format (str, optional): The format to use. Defaults to '$#,##0'.
    """
    workbook = excel_file.book
    currency_format = workbook.add_format({'num_format': format})
    if columns is None:
        columns = data_frame.select_dtypes(include=['number']).columns
        # if columns is a string create a list
        if isinstance(columns, str):
            columns = [columns]
        elif columns is None:
            columns = []

    idx_len = len(data_frame.index.names)

    # get the name of the first sheet
    if sheet is None:
        sheet = list(excel_file.sheets.keys())[0]

    
    for column in columns:
        col_idx = data_frame.columns.get_loc(column) + idx_len
        excel_file.sheets[sheet].set_column(col_idx, col_idx, width, currency_format)
        

def excel_format_percent(data_frame: pd.DataFrame, excel_file: pd.ExcelWriter, sheet=None,columns=None, format= '0.00%', width=None):
    """Format the columns in the Excel file as percentage
    
    Args:
        data_frame (pd.DataFrame): The DataFrame to format
        excel_file (pd.ExcelWriter): The ExcelWriter object
        sheet (str, optional): The sheet to format. Defaults to None, first sheet.
        columns (list, optional): The columns to format. Defaults to all numeric columns.
        format (str, optional): The format to use. Defaults to '0.00%'.
    """
    workbook = excel_file.book
    percent_format = workbook.add_format({'num_format': format})
    if columns is None:
        columns = data_frame.select_dtypes(include=['number']).columns
        # if columns is a string create a list
        if isinstance(columns, str):
            columns = [columns]
        elif columns is None:
            columns = []

    idx_len = len(data_frame.index.names)

    # get the name of the first sheet
    if sheet is None:
        sheet = list(excel_file.sheets.keys())[0]

    
    for column in columns:
        col_idx = data_frame.columns.get_loc(column) + idx_len
        excel_file.sheets[sheet].set_column(col_idx, col_idx, width, percent_format)


def checkAggregateValues(df: pd.DataFrame,
                          hcode_column:str, 
                          aggregate_column='isCmdAggregate'):
    """Check if the values in the column hcode_column are aggregate values
    
    Args:
        df (pd.DataFrame): The DataFrame to check
        hcode_column (str): The column containing the hierarchical codes
        aggregate_column (str, optional): The column to set the result. Defaults to 'isCmdAggregate'.

    Returns: The DataFrame with the new column

    Notes:
        The values in the column hcode_column must be 
        sorted in ascending order.
        TODO why not sort in the function?
    """
    lastCode = "---"
    lastIndex = 0
    for row in df.iterrows():
        currentCode = row[1][hcode_column]
        if currentCode != lastCode and currentCode.startswith(lastCode):
            # print(f">>>> Last code {lastCode} index {lastIndex} is parent of {currentCode}")
            df.loc[lastIndex,aggregate_column] = True
        elif currentCode == lastCode:
            # code is the same as last row, copy the value
            df.loc[row[0],aggregate_column] = df.loc[lastIndex,aggregate_column]
            warnings.warn(f"Code {currentCode} is duplicated in row {row[0]} and {lastIndex}")
        else:
            df.loc[lastIndex,aggregate_column] = False
        # print(df.loc[row[0]][['cmdCode','cmdDesc']])
        lastCode = currentCode
        lastIndex = row[0]
    return df