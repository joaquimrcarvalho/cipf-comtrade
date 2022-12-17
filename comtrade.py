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


SUPPORT_DIR = 'support'

Path(SUPPORT_DIR).mkdir(parents=True, exist_ok=True)

APIKEY = None
BASE_URL_PREVIEW = "https://comtradeapi.un.org/public/v1/preview/"
BASE_URL_API = "https://comtradeapi.un.org/data/v1/get/"

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


# HS Codes are not included in the codebook
HS_CODES_FILE = 'support/harmonized-system.csv'
HS_CODES_URL = 'https://github.com/datasets/harmonized-system/blob/master/data/harmonized-system.csv?raw=true'

HS_CODES_DF = None
HS_CODES_L2_DF = None

HS_CODES: dict = {}
HS_CODES_L2: dict = {}

global INIT_DONE
INIT_DONE = False # flag to avoid multiple initialization

def init(apy_key: Union[str,None]=None, code_book_url: Union[None,str]=None):
    """Set the API Key and codebooks for the module"""

    global APIKEY
    global CODE_BOOK_URL
    global INIT_DONE

    # if already initialized, do nothing
    if INIT_DONE:
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
        partner2Code (str, optional): Partner2 country code. Defaults to 0.
        period (str, optional): Period of data, e.g. 2018, 2018,2019, 2018,2019,2020. Defaults to None.
        clCode (str, optional): Classification code, HS for Harmonized System, SITC for Standard International Trade Classification. Defaults to "HS".
        cmdCode (str, optional): Commodity code, TOTAL for all commodities. Defaults to "TOTAL".
        flowCode (str, optional): Flow code, M for imports, X for exports. Defaults to "M,X".
        customsCode (str, optional): Customs code, C00 for all customs. Defaults to 'C00'.
        more_pars (dict, optional): Additional parameters to pass to the API.
        qtyUnitCodeFilter (str, optional): Quantity unit code, e.g. 1 for tonnes, 2 for kilograms. Defaults to None.
        apiKey (str,optional): API Key for umcomtrade+
        timeout (int, optional): Timeout for the API call. Defaults to 10.
        echo_url (bool, optional): Echo the CODE_BOOK_url to the console. Defaults to False.
    
     """
    if apiKey is None:
        apiKey = APIKEY

    base_url=f"{getURL(apiKey)}/{typeCode}/{freqCode}/{clCode}"
    pars = {
            'reporterCode':reporterCode,
            'period':period,
            'partnerCode':partnerCode,
            'partner2Code':partner2Code,
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
        warnings.warn(f"Server returned HTTP Status: "+str(resp.status_code),)        
        warnings.warn(str(resp.content))
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
            if qtyUnitCodeFilter is not None:
                df = df[df.qtyUnitCode == qtyUnitCodeFilter]

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
                df['primaryValueFormated'] = df.primaryValue.map('{:,}'.format)
            # return the DataFrame
        return df


def year_range(year_start=1984,year_end=2030):
    """Return a string with comma separeted list of years
    
    Args:
        year_start (int, optional): Start year. Defaults to 1984.
        year_end (int, optional): End year. Defaults to 2030.

    """
    period = ",".join(map(str,list(range(year_start,year_end,1))))
    return period