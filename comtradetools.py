"""
Module comtradetools.

Auxiliary functions and data to access the
UN Comtrade API.


"""

# disable Pylint warning about too many arguments
# pylint: disable=R0913
# disable Pylint warning invalid-name
# pylint: disable=C0103
# disable Pylint global-statement
# pylint: disable=W0603
# disable Pylint error E501 (line too long)
# pylint: disable=E501
# flake8: noqa: E501


import logging
import os
import time
import datetime
from typing import Union
import warnings
import re
import json
from pathlib import Path
import urllib.request
import configparser
import hashlib
import pickle

import requests
import pandas as pd

from ratelimit import limits, sleep_and_retry
import comtradeapicall

logging.basicConfig(level=logging.INFO)

SUPPORT_DIR = "support"
CACHE_DIR = "cache"
CONFIG_FILE = "config.ini"

Path(SUPPORT_DIR).mkdir(parents=True, exist_ok=True)
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

APIKEY = None
BASE_URL_PREVIEW = "https://comtradeapi.un.org/public/v1/preview/"
BASE_URL_API = "https://comtradeapi.un.org/data/v1/get/"

# Parameters for rate limiting
CALLS_PER_PERIOD = 1  # number of calls per period
PERIOD_SECONDS = 20  # period in seconds
MAX_RETRIES = 5  # max number of retries for a failed call
RETRY = 0  # number of retries for a failed call
MAX_SLEEP = 6  # maximum number of seconds to sleep between retries


CACHE_VALID_DAYS = 60  # number of days to keep cached data

# we use a copy of the codebook in git because the original cannot be downloaded
#   without human action. The codebook is used to decode the results of the API call
# Note that with the release of comtradeapicall python package, the codebook is no longer used
#   but we keep it here for reference
CODE_BOOK_URL = "https://raw.githubusercontent.com/joaquimrcarvalho/cipf-comtrade/main/support/codebook.xlsx"
CODE_BOOK_FILE = "support/codebook.xlsx"

# Description of the columns in the results of the API call
DATA_ITEM_DF = None
DATA_ITEM_CSV = "support/dataitem.csv"

# Countries, regions, and other geographical areas
# The UN Comtrade division keeps a list of countries and areas that is used for aggregation purposes.
# See: https://unctadstat.unctad.org/EN/Classifications.html
# The list mapping individual countries to their corresponding area is available in the codebook.
# CSV file at https://unctadstat.unctad.org/EN/Classifications/Dim_Countries_Hierarchy_UnctadStat_All_Flat.csv

COUNTRY_GROUPS_URL = "https://unctadstat.unctad.org/EN/Classifications/Dim_Countries_Hierarchy_UnctadStat_All_Flat.csv"
COUNTRY_GROUPS_FILE = "support/Dim_Countries_Hierarchy_UnctadStat_All_Flat.csv"
PARTNER_DF = None
PARTNER_CSV = "support/partner.csv"
REPORTER_DF = None
REPORTER_CSV = "support/reporter.csv"

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
m49_plp = [
    m49_angola,
    m49_brazil,
    m49_cabo_verde,
    m49_guine_bissau,
    m49_guine_equatorial,
    m49_mozambique,
    m49_portugal,
    m49_stome_principe,
    m49_timor,
]
# make string of Portuguese Speaking Countries codes
m49_plp_list = ",".join(map(str, m49_plp))


# HS Codes are not included in the codebook
HS_CODES_FILE = "support/harmonized-system.csv"
HS_CODES_URL = "https://github.com/datasets/harmonized-system/blob/master/data/harmonized-system.csv?raw=true"

HS_CODES_DF = None
HS_CODES_L2_DF = None

HS_CODES: dict = {}
HS_CODES_L2: dict = {}

# label for the percentage of a commodity in the total trade of a country
PERC_CMD_IN_PARTNER = "perc_cmd_for_partner"

# label for the percentage of a country in the total trade of a commodity
PERC_PARTNER_IN_CMD = "perc_partner_for_cmd"

INIT_DONE = False

INIT_DONE = False  # flag to avoid multiple initialization


def setup(
    support_dir: str = "support",
    cache_dir: str = "cache",
    config_file: str = "config.ini",
):
    """Create support directories and config file if they do not exist

    Args:
        support_dir (str, optional): Directory for support files. Defaults to 'support'.
        cache_dir (str, optional): Directory for cached files. Defaults to 'cache'.
        config_file (str, optional): Config file. Defaults to 'config.ini'.
    """
    # create "support" directory if it does not exist
    global SUPPORT_DIR
    Path(support_dir).mkdir(parents=True, exist_ok=True)
    SUPPORT_DIR = support_dir

    # create cache directory if it does not exist
    global CACHE_DIR
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    CACHE_DIR = cache_dir

    # create config file if it does not exist
    global CONFIG_FILE
    if not os.path.isfile(config_file):
        logging.info(f"Creating config file {config_file}")
        content = """
# Config for comtradetools
[comtrade]
# Add API Key. DO NOT SHARE
key = APIKEYHERE
"""
        with open(config_file, "w") as f:
            f.write(content)
        logging.warning(f"Please edit {config_file} and add your API Key")

    CONFIG_FILE = config_file


def get_api_key() -> str:
    """Get the API Key from the config file

    Returns:
        str: API Key
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config["comtrade"]["key"]


def init(
    api_key: Union[str, None] = None,
    code_book_url: Union[None, str] = None,
    force_init: bool = False,
):
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

    APIKEY = api_key
    INIT_DONE = True

    # downloadd codebook if not cached. Note that with the release of comtradeapicall python package, the codebook is no longer used
    #   but we keep it here for reference
    if code_book_url is not None:
        CODE_BOOK_URL = code_book_url

    if not os.path.isfile(CODE_BOOK_FILE) or force_init:
        logging.info("Downloading codebook from %s", CODE_BOOK_URL)
        urllib.request.urlretrieve(CODE_BOOK_URL, CODE_BOOK_FILE)
        print("un-comtrade codebook downloaded to", CODE_BOOK_FILE)

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

    if not os.path.isfile(COUNTRY_GROUPS_FILE) or force_init:
        logging.info(f"Downloading country groups from {COUNTRY_GROUPS_URL}")
        headers = {"user-agent": "Mozilla/5.0"}
        r = requests.get(COUNTRY_GROUPS_URL, headers=headers)
        with open(COUNTRY_GROUPS_FILE, "wb") as f:
            f.write(r.content)
        print("un-comtrade country groups downloaded to", COUNTRY_GROUPS_FILE)

    global COUNTRY_CODE_FILE
    COUNTRY_CODE_FILE = "support/REF COUNTRIES.csv"
    MOS_CODE_FILE = "support/REF  MOS.csv"
    CUSTOMS_CODE_FILE = "support/REF CUSTOMS.csv"
    FLOWS_CODE_FILE = "support/REF FLOWS.csv"
    MOT_CODE_FILE = "support/REF MOT.csv"
    QTY_CODE_FILE = "support/REF QTY.csv"
    COLS_DESCRIPTION_FILE = "support/COMTRADE+ COMPLETE.csv"

    # Process reference tables
    # get descriptions of columns
    global DATA_ITEM_DF
    if not os.path.isfile(DATA_ITEM_CSV) or force_init:
        DATA_ITEM_DF = comtradeapicall.getReference("dataitem")
        DATA_ITEM_DF.to_csv(DATA_ITEM_CSV)
    else:
        DATA_ITEM_DF = pd.read_csv(DATA_ITEM_CSV)

    global PARTNER_DF
    global PARTNER_CSV
    global COUNTRY_CODES
    global PARTNER_CODES

    COUNTRY_CODES = pd.read_csv(COUNTRY_CODE_FILE, index_col=0).squeeze().to_dict()

    if not os.path.isfile(PARTNER_CSV) or force_init:
        PARTNER_DF = comtradeapicall.getReference("partner")
        PARTNER_DF.to_csv(PARTNER_CSV)
    else:
        PARTNER_DF = pd.read_csv(PARTNER_CSV)
    PARTNER_CODES = PARTNER_DF[["id", "text"]].set_index("id").squeeze().to_dict()
    COUNTRY_CODES = PARTNER_CODES

    global REPORTER_DF
    global REPORTER_CSV
    global REPORTER_CODES

    if not os.path.isfile(REPORTER_CSV) or force_init:
        REPORTER_DF = comtradeapicall.getReference("reporter")
        REPORTER_DF.to_csv(REPORTER_CSV)
    else:
        REPORTER_DF = pd.read_csv(REPORTER_CSV)
    REPORTER_CODES = REPORTER_DF[["id", "text"]].set_index("id").squeeze().to_dict()

    COUNTRY_CODES.update(REPORTER_CODES)

    global COUNTRY_CODES_REVERSE
    COUNTRY_CODES_REVERSE = {v: k for k, v in COUNTRY_CODES.items()}

    global MOS_CODES
    MOS_CODES = pd.read_csv(MOS_CODE_FILE, index_col=0).squeeze().to_dict()

    global CUSTOMS_CODE
    CUSTOMS_CODE = pd.read_csv(CUSTOMS_CODE_FILE, index_col=0).squeeze().to_dict()

    # flows have two columns: description and category. Category maps to "M" or "X" the variants
    global FLOWS_CODES
    FLOWS_CODES = (
        pd.read_csv(FLOWS_CODE_FILE, index_col=0, usecols=[0, 1]).squeeze().to_dict()
    )

    global FLOWS_CODES_CAT
    FLOWS_CODES_CAT = (
        pd.read_csv(FLOWS_CODE_FILE, index_col=0, usecols=[0, 2]).squeeze().to_dict()
    )

    global MOT_CODES
    MOT_CODES = pd.read_csv(MOT_CODE_FILE, index_col=0).squeeze().to_dict()

    # quantity codes have two columns: abbreviations (m2,km,...) and full description
    global QTY_CODES
    QTY_CODES = (
        pd.read_csv(QTY_CODE_FILE, index_col=0, usecols=[0, 1]).squeeze().to_dict()
    )

    global QTY_CODES_DESC
    QTY_CODES_DESC = (
        pd.read_csv(QTY_CODE_FILE, index_col=0, usecols=[0, 2]).squeeze().to_dict()
    )
    # Additionally the codebook contains a description of the columns

    global COLS_DESC_DF
    COLS_DESC_DF = pd.read_csv(COLS_DESCRIPTION_FILE, index_col=0, usecols=[0, 5])

    global COLS_DESC
    COLS_DESC = COLS_DESC_DF.squeeze().to_dict()

    global HS_CODES_DF
    # HS Codes are not included in the codebook
    if os.path.isfile(HS_CODES_FILE):
        logging.info(f"Loading HS codes from {HS_CODES_FILE}")
        HS_CODES_DF = pd.read_csv(HS_CODES_FILE)  # read table
    else:
        logging.info(f"Downloading HS codes from {HS_CODES_URL}")
        HS_CODES_DF = pd.read_csv(HS_CODES_URL)  # read from CODE_BOOK_url
        HS_CODES_DF.to_csv(HS_CODES_FILE)

    global HS_CODES  # dict for decoding
    HS_CODES = dict(zip(HS_CODES_DF.hscode, HS_CODES_DF.description))

    global HS_CODES_L2_DF  # create subset of level 2 codes
    HS_CODES_L2_DF = HS_CODES_DF[HS_CODES_DF.level == 2]

    global HS_CODES_L2
    HS_CODES_L2 = dict(
        zip(HS_CODES_L2_DF.hscode, HS_CODES_L2_DF.description)
    )  # dict for decoding

    # extract dict and tuples for plp_list from country_codes
    PLP_CODES = {k: v for k, v in COUNTRY_CODES.items() if k in m49_plp}
    PLP_CODES_REVERSE = {v: k for k, v in PLP_CODES.items()}
    PLP_TUPLES = list(PLP_CODES.items())
    PLP_TUPLES_REVERSE = list(PLP_CODES_REVERSE.items())

    clean_cache()

    # global INIT_DONE
    # INIT_DONE = True


def encode_country(country: str) -> str:
    """Encode country name to country code

    Args:
        country (str): Country name

    Returns:
        str: Country code
    """
    global COUNTRY_CODES_REVERSE

    return COUNTRY_CODES_REVERSE.get(country, country)


def decode_country(country_code: str) -> str:
    """Decode country code to country name

    Args:
        country_code (str): Country code

    Returns:
        str: Country name
    """
    global COUNTRY_CODES
    return COUNTRY_CODES.get(country_code, country_code)


def clean_cache():
    directory = CACHE_DIR
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=CACHE_VALID_DAYS)

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        if modification_time < cutoff_time:
            os.remove(file_path)


def get_url(api_key: Union[str, None] = None):
    """Get the URL for the API call"""

    if api_key == "APIKEYHERE":
        api_key = None
    if api_key is None:
        uncomtrade_url = BASE_URL_PREVIEW
    else:
        uncomtrade_url = BASE_URL_API

    # log to info
    logging.info("baseURL: %s", uncomtrade_url)

    if api_key is not None:
        logging.info("APIKEY: %s", api_key[:8])

    return uncomtrade_url


def split_period(period: str, max_periods=12):
    """Splits a period string into a list of periods of max_periods length
    Usefull to handle the limitation of the API to 12 periods per query"""

    period_list = period.split(",")
    period_list = [
        ",".join(period_list[i : i + max_periods])
        for i in range(0, len(period_list), max_periods)
    ]
    return period_list


def get_year_intervals(years):
    """Converts a list of years to a list of year intervals
    e.g. [2018,2019,2020] -> ['2018-2020']
    e.g. [2018,2019,2021] -> ['2018-2019','2021-2021']
    """
    intervals = []
    start_year = years[0]
    end_year = years[0]

    for year in years[1:]:
        if year == end_year + 1:
            end_year = year
        else:
            intervals.append(f"{start_year}-{end_year}")
            start_year = year
            end_year = year

    intervals.append(f"{start_year}-{end_year}")
    return intervals


def getFinalData(*p, **kwp):
    """
    Wrapper for comtradeapicall.getFinalData with rate limit.

    This wrapper is needed to avoid rate limit errors when calling the API.
    It also deals with requests that specify more than 12 periods by splitting
        the request in multiple calls and concatenating the results.

    For information about the base function see https://github.com/uncomtrade/comtradeapicall.

    Args:
        *args: Extra arguments for comtradeapicall.getFinalData.
        remove_world (bool, optional): Remove the world entry; defaults to False;
                                        when partnerCode is None, the API returns
                                        partnerCode = 0 for the world and
                                        partnerCode for each partner;
                                        if True, the world entry is removed.
        cache (bool, optional): Cache the results; defaults to True.
        retry_if_empty (bool, optional): Retry if the cached result is empty; defaults to True.
        period_size (int, optional): Number of periods to request in each call; defaults to 12;
        use_alternative (bool, optional): Use alternative API call. True/False.
            "Alternative functions ... returns the same data frame ....
            with query optimization by calling multiple APIs based on the periods
            (instead of single API call)" Not Tested.


    If the call does not specify partner2Code, some years produce
    more than one line per reporter/partner pair with different values.

    For example, if China is the reporter and Equatorial Guinea
    is the partner in the years 2015, 2016, 2017, it appears:

    One line per partner2Code, including a line where partner2
    is equal to partner (direct imports).
    An additional line with partner2Code equal to zero that
    contains the total aggregate of the other lines
    with explicit partner2Code.

    This means that there is duplication of the total.

    |    | reporterDesc   | partnerDesc       |   partner2Code | partner2Desc         |   refYear | cmdCode   | flowCode   | primaryValueFormated   |
    |---:|:---------------|:------------------|---------------:|:---------------------|----------:|:----------|:-----------|:-----------------------|
    |  3 | China          | Equatorial Guinea |            344 | China, Hong Kong SAR |      2015 | TOTAL     | M          | 59.0                   |
    |  1 | China          | Equatorial Guinea |             56 | Belgium              |      2015 | TOTAL     | M          | 2,435.0                |
    |  2 | China          | Equatorial Guinea |            226 | Equatorial Guinea    |      2015 | TOTAL     | M          | 1,166,493,970.0        |
    |  0 | China          | Equatorial Guinea |              0 | nan                  |      2015 | TOTAL     | M          | 1,166,496,464.0        |


    To avoid this, the API must be called with partner2Code = 0, so that the results for 2015, 2016, 2017 exclude
        the breakdown. If partner2Code=None, the additional lines appear.

    So if partner2Code is not specified in the arguments this function will add partner2Code = 0 before calling comtrade.
    """
    global RETRY

    if len(p) == 0:
        api_key = get_api_key()
        p = [api_key]
    elif len(p) == 1:
        api_key = p[0]  # currently unused
    else:
        raise ValueError("Only one positional argument is allowed, the API Key")

    cache = kwp.get("cache", True)
    # remove cache from kwp
    if "cache" in kwp:
        del kwp["cache"]

    retry_if_empty = kwp.get("retry_if_empty", True)
    # remove retry_if_empty from kwp
    if "retry_if_empty" in kwp:
        del kwp["retry_if_empty"]

    remove_world = kwp.get("remove_world", False)
    # remove remove_world from kwp
    if "remove_world" in kwp:
        del kwp["remove_world"]

    period_size = kwp.get("period_size", 12)
    # remove period_size from kwp
    if "period_size" in kwp:
        del kwp["period_size"]

    use_alternative = kwp.get("use_alternative", False)

    # check for partner2Code missing.

    # check if "partner2Code" is not in kwp
    if "partner2Code" not in kwp:
        # do something
        kwp["partner2Code"] = 0

    # get period from kwp
    period = kwp.get("period", None)
    if period is None:
        raise ValueError("Period is required")

    if cache and not os.path.exists(CACHE_DIR):
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

    subperiods = split_period(period, period_size)

    df = pd.DataFrame()
    for subperiod in subperiods:
        kwp["period"] = subperiod

        logging.info("Calling getFinalData for period %s", subperiod)

        # make a hash of the parameters for caching
        hash_updater = hashlib.md5()
        call_string = f"{str(kwp)}{use_alternative}"

        logging.debug("Call %s", call_string)
        hash_updater.update(call_string.encode("utf-8"))
        cache_file = f"{CACHE_DIR}/{hash_updater.hexdigest()}.pickle"
        used_cache = False

        if cache and os.path.exists(cache_file):

            modification_time = os.path.getmtime(cache_file)
            current_time = datetime.datetime.now().timestamp()
            days_since_modification = (current_time - modification_time) / (24 * 3600)
            if days_since_modification <= CACHE_VALID_DAYS:
                with open(cache_file, "rb") as f:
                    temp = pickle.load(f)
                    used_cache = True
                    logging.info("Using cached results for period %s", subperiod)
            else:
                os.remove(cache_file)
                used_cache = False
            if temp.size == 0 and retry_if_empty:
                os.remove(cache_file)
                logging.info(
                    "Empty result in cached result, retrying. Disable with retry_if_empty=False"
                )
                used_cache = False

        if not used_cache:
            RETRY = 0
            try:
                logging.debug("Calling comtradeapicall.getFinalData with %s", kwp)
                temp = comtradeapicall_getFinalData(*p, **kwp)
                if temp is None:
                    logging.debug("Call returned None")
                else:
                    logging.debug("Number of record in temp: %s", temp.size)
            except Exception as e:
                sleep = MAX_SLEEP * (RETRY + 1)
                logging.error(
                    f"Error in getFinalData, retrying in {MAX_SLEEP} seconds", e
                )
                time.sleep(MAX_SLEEP)
                RETRY += 1
                logging.debug("Retrying comtradeapicall.getFinalData with %s", kwp)
                temp = comtradeapicall_getFinalData(*p, **kwp)
                if temp is None:
                    logging.debug("Call returned None")
                else:
                    logging.debug("Number of record in temp: %s", temp.size)
            while temp is None and RETRY < MAX_RETRIES:
                sleep = MAX_SLEEP * (RETRY + 1)
                logging.info(
                    f"Empty result in getFinalData, retrying in {sleep} seconds"
                )
                time.sleep(sleep)
                RETRY += 1
                temp = comtradeapicall_getFinalData(*p, **kwp)
            if temp is None:
                # raise Exception(f"Empty result in getFinalData after {MAX_RETRIES} retries")
                #
                raise IOError(
                    f"Empty result in getFinalData after {MAX_RETRIES} retries"
                )
            elif cache and temp is not None:  # save in cache
                with open(cache_file, "wb") as f:
                    pickle.dump(temp, f)
        if temp is not None and temp.size > 0:
            df = pd.concat([df, temp], ignore_index=True)

    # we do some checks on the results to avoid common problems
    partnerCode = kwp.get("partnerCode", None)
    if partnerCode is None and remove_world and "partnerCode" in df.columns:
        # when partnerCode is None, the API returns partnerCode = 0 for the world
        #  and partnerCode for each partner. We remove the world entry
        df = df[df.partnerCode != 0]

    return df


@sleep_and_retry
@limits(calls=CALLS_PER_PERIOD, period=PERIOD_SECONDS)
def comtradeapicall_getFinalData(*p, **kwp):
    use_alternative = kwp.get("use_alternative", False)
    # remove use_alternative from kwp
    if "use_alternative" in kwp:
        del kwp["use_alternative"]
    if use_alternative:
        temp = comtradeapicall._getFinalData(*p, **kwp)
    else:
        logging.debug("Calling comtradeapicall.getFinalData with %s",  kwp)
        temp = comtradeapicall.getFinalData(*p, **kwp)
        if temp is not None:
            logging.debug("Number of records fetched: %s", temp.size)
        else:
            logging.debug("Call returned None")
    return temp


def subtotal(df, groupby: list, col: str):
    """Returns the sum of col for each groupby group

    Args:
        df (pd.DataFrame): DataFrame to group
        groupby (list): list of columns to group by
        col (str): column to sum
    """
    return df.groupby(groupby)[col].transform("sum")


def rank(df, rankby: list, col: str):
    """Returns the rank of col for each rankby group

    Args:
        df (pd.DataFrame): DataFrame to group
        rankby (list): list of columns to group by
        col (str): column to rank
    """
    return df.groupby(rankby)[col].rank(ascending=False, method="dense").astype(int)


def total_rank_perc(
    df: pd.DataFrame,
    groupby: list,
    col: str,
    prefix: str,
    rankby: list = None,
    percby: list = None,
    drop_duplicates: bool = True,
):
    """Returns the sum, rank and percentages of col for each groupby subset

    Args:
        df (pd.DataFrame): DataFrame to group
        groupby (list): list of columns to group by
        col (str): column to rank
        prefix (str): prefix for the new columns
        rankby (list): list of columns to rank by. Default groupby[:-1]
        drop_duplicates (bool): drop duplicates after calculating subtotal. Default True


    Returns:
        Dataframe with extra columns:
            {prefix}_sum
            {prefix}_rank
            {prefix}_perc
            {prefix}_upper_sum (sum of col for groupby[:-1])
            {prefix}_upper_perc (perc of {prefix}_upper_sum in {prefix}_sum )
    """
    subtotal_col = f"{prefix}_sum"
    if rankby is None:
        rankby = groupby[:-1]
    if percby is None:
        percby = groupby[:-1]
    df[subtotal_col] = subtotal(df, groupby, col)
    df[f"{prefix}_rank"] = rank(df, rankby, subtotal_col)
    df[f"{prefix}_perc"] = df[col] / subtotal(df, groupby[:-1], col)
    df[f"{prefix}_upper_sum"] = subtotal(df, groupby[:-1], col)
    df[f"{prefix}_upper_perc"] = df[subtotal_col] / df[f"{prefix}_upper_sum"]
    if drop_duplicates:
        df = df.drop_duplicates(groupby).copy()
    return df


def make_format(cols: list):
    f = {col: "{0:.3%}" for col in cols if col.endswith("perc")}
    f.update({col: "${0:,.0f}" for col in cols if col.endswith("sum")})
    f.update({"primaryValue": "${0:,.0f}"})
    return f


def top_commodities(
    reporterCode,
    partnerCode=0,
    years=None,
    flowCode="M,X",
    partner2Code=0,
    cmdCode="AG2",
    motCode=None,
    rank_filter=5,
    return_data=False,
    timeout=120,
    echo_url=False,
):
    """Get the top commodities (level 2 HS nomenclature) traded between countries for a given year range

    DEPRECATED
    Args:
        reporterCode (str): reporter country code, e.g. 49 for China
        partnerCode (str): partner country code, 0 for the world, None for all, code or CSV
        partner2Code (str): partner2 country code, 0 for world,
                            -1 all but World, None for all, default 0
        years (str): year range, e.g. 2010,2011,2012
        flowCode (str): flow code, e.g. M for imports, X for exports, defaults to M,X
        cmdCode (str): HS code, e.g. AG2 for all HS2 codes, AG4 for all HS4 codes,
                        TOTAL for all, defaults to AG2
        motCode (str, optional): Mode of transport code, e.g. 0 for all, 1 for sea, 2 for air.
                                    Defaults to None. If -1 is passed removes results with motCode = 0
        rank_filter (int): number of top commodities to return, default 5
        return_data (bool): return the original data before clipping, If true
                            returns a tuple (top_commodities, data)
        echo_url (bool): print the url to the console, default False


    """
    df = get_data(
        "C",  # C for commodities, S for Services
        "A",  # (freqCode) A for annual and M for monthly
        flowCode=flowCode,
        cmdCode=cmdCode,
        reporterCode=reporterCode,
        partnerCode=partnerCode,
        partner2Code=partner2Code,
        period=years,
        motCode=motCode,
        timeout=timeout,
        echo_url=echo_url,
    )

    if df is None:
        warnings.warn("No data returned, check the parameters")
        return None

    # Total value per period per flow
    df["sum_year_flow"] = df.groupby(["refYear", "flowCode"])["primaryValue"].transform(
        "sum"
    )
    df["perc_year_flow"] = df["primaryValue"] / df["sum_year_flow"]

    # Total value of commodities per HS code
    df["sum_cmd"] = df.groupby(["refYear", "flowCode", "cmdCode"])[
        "primaryValue"
    ].transform("sum")
    # Total value of commodities per partner
    df["sum_partner"] = df.groupby(["refYear", "flowCode", "partnerCode"])[
        "primaryValue"
    ].transform("sum")

    # rank of commodity per HS code
    df["rank_cmd"] = df.groupby(["reporterDesc", "refYear", "flowCode"])[
        "sum_cmd"
    ].rank(ascending=False, method="dense")
    df["rank_cmd"] = df["rank_cmd"].astype(int)

    # Total value per period per flow per reporter
    df["sum_reporter"] = df.groupby(["reporterDesc", "refYear", "flowCode"])[
        "primaryValue"
    ].transform("sum")
    df["perc_reporter"] = df["primaryValue"] / df["sum_reporter"]

    # rank of reporter
    df["rank_reporter"] = df.groupby(["partnerDesc", "refYear", "flowCode"])[
        "sum_reporter"
    ].rank(ascending=False, method="dense")
    df["rank_reporter"] = df["rank_reporter"].astype(int)

    # value of trade as percentage of total same HS code
    df[PERC_PARTNER_IN_CMD] = df["primaryValue"] / df["sum_cmd"]
    # value of trade as percentage of total same partner
    df[PERC_CMD_IN_PARTNER] = df["primaryValue"] / df["sum_partner"]

    # rank of partner per HS code
    df["rank_cmd_partner"] = df.groupby(
        ["reporterDesc", "refYear", "flowCode", "cmdCode"]
    )["primaryValue"].rank(ascending=False, method="dense")
    df["rank_cmd_partner"] = df["rank_cmd_partner"].astype(int)

    # global rank of partner
    df["rank_partner"] = df.groupby(["reporterDesc", "refYear", "flowCode"])[
        "sum_partner"
    ].rank(ascending=False, method="dense")
    df["rank_partner"] = df["rank_partner"].astype(int)

    rank_cut = (
        df["rank_cmd"] <= rank_filter
    )  # & (df['rank_cmd_partner'] <= rank_filter)
    sort_list = ["refYear", "flowCode", "rank_cmd", "rank_cmd_partner"]
    sort_order = [True, True, True, True]

    pco = df[rank_cut].sort_values(sort_list, ascending=sort_order)
    if return_data:
        return (pco, df)
    else:
        return pco


def get_trade_flows_old(
    countryOfInterest=None,
    period=None,
    typeCode="C",
    freqCode="A",
    partners=0,  # default world
    symmetric_values=True,
    timeout=120,
    echo_url=False,
):
    """
    DEPRECATED: use get_trade_flows instead
    Get the Import/Export totals for a given country and year range

    Args:
        country_of_interest (str): country of interest, e.g. 49 for China
        years (str): year range, e.g. 2010,2011,2012
        symmetric_values: if True report also exports from partner imports
                          and imports from partners exports; default True
        typeCode (str): C for commodities, S for Services, default C
        freqCode (str): A for annual and M for monthly, default A
        partners (str): 0 for the world, None for all, code or CSV, default 0
        timeout (int): timeout in seconds for the request, default 120
        echo_url (bool): print the url to the console, default False

    Returns:
        DataFrame: DataFrame with the totals for each year and flow indexed
                   by year and flow code"""

    reported_imports = get_data(
        typeCode=typeCode,
        freqCode=freqCode,
        reporterCode=countryOfInterest,
        partnerCode=partners,
        partner2Code=0,
        flowCode="M",
        period=period,
        motCode=0,
        clCode="HS",
    )
    reported_exports = get_data(
        typeCode=typeCode,
        freqCode=freqCode,
        reporterCode=countryOfInterest,
        partnerCode=partners,
        partner2Code=0,
        flowCode="X",
        period=period,
        motCode=0,
        timeout=timeout,
        echo_url=echo_url,
    )
    if symmetric_values:

        exports_from_imports = get_data(
            "C",
            "A",
            reporterCode=partners if partners != 0 else None,
            partnerCode=countryOfInterest,
            partner2Code=0,
            flowCode="M",
            period=period,
            motCode=0,
            timeout=timeout,
            echo_url=echo_url,
        )
        imports_from_exports = get_data(
            typeCode,
            freqCode,
            reporterCode=partners if partners != 0 else None,
            partnerCode=countryOfInterest,
            partner2Code=0,
            flowCode="X",
            period=period,
            motCode=0,
            timeout=timeout,
            echo_url=echo_url,
        )

    # Agregate by year and flow
    if reported_exports is not None:
        reported_exports = (
            reported_exports.groupby(["period", "reporterCode"])["primaryValue"]
            .sum()
            .reset_index()
        )
        reported_exports["flowCode"] = "X"
        reported_exports["flowDesc"] = "exports"
        # rename reporterCode to countryCode
        reported_exports.rename(columns={"reporterCode": "countryCode"}, inplace=True)
    else:
        reported_exports = pd.DataFrame(
            columns=["period", "countryCode", "primaryValue", "flowCode", "flowDesc"]
        )
    if reported_imports is not None:
        reported_imports = (
            reported_imports.groupby(["period", "reporterCode"])["primaryValue"]
            .sum()
            .reset_index()
        )
        # rename reporterCode to countryCode
        reported_imports.rename(columns={"reporterCode": "countryCode"}, inplace=True)
        reported_imports["flowCode"] = "M"
        reported_imports["flowDesc"] = "imports"
    else:
        reported_imports = pd.DataFrame(
            columns=["period", "countryCode", "primaryValue", "flowCode", "flowDesc"]
        )

    global_trade = pd.concat([reported_imports, reported_exports])

    if symmetric_values:
        if exports_from_imports is not None:
            exports_from_imports = (
                exports_from_imports.groupby(["period", "partnerCode"])["primaryValue"]
                .sum()
                .reset_index()
            )
            # rename partnerCode to countryCode
            exports_from_imports.rename(
                columns={"partnerCode": "countryCode"}, inplace=True
            )
            exports_from_imports["flowCode"] = "X<M"
            exports_from_imports["flowDesc"] = "exports(others imports)"
        else:
            exports_from_imports = pd.DataFrame(
                columns=[
                    "period",
                    "countryCode",
                    "primaryValue",
                    "flowCode",
                    "flowDesc",
                ]
            )

        if imports_from_exports is not None:
            imports_from_exports = (
                imports_from_exports.groupby(["period", "partnerCode"])["primaryValue"]
                .sum()
                .reset_index()
            )
            # rename partnerCode to countryCode
            imports_from_exports.rename(
                columns={"partnerCode": "countryCode"}, inplace=True
            )
            imports_from_exports["flowCode"] = "M<X"
            imports_from_exports["flowDesc"] = "imports(others exports)"
        else:
            imports_from_exports = pd.DataFrame(
                columns=[
                    "period",
                    "countryCode",
                    "primaryValue",
                    "flowCode",
                    "flowDesc",
                ]
            )

    global_trade = pd.concat([global_trade, exports_from_imports, imports_from_exports])

    trade_balance = pd.pivot_table(
        global_trade, index=["period"], columns="flowCode", values="primaryValue"
    ).fillna(0)
    trade_balance["trade_balance (X-M)"] = trade_balance["X"] - trade_balance["M"]
    trade_balance["trade_balance (X<M-M)"] = trade_balance["X<M"] - trade_balance["M"]
    trade_balance["trade_volume (X+M)"] = trade_balance["X"] + trade_balance["M"]
    trade_balance["trade_volume (X<M+M)"] = trade_balance["X<M"] + trade_balance["M"]
    trade_balance.reset_index()
    return trade_balance
    # .reindex(columns=['countryCode','countryDesc','exports','imports',
    # 'trade_balance','xReporterCode','xReporterDesc'])


def get_trade_flows(
    countryOfInterest=None,
    period=None,
    typeCode="C",
    freqCode="A",
    partners=0,  # default world
    symmetric_values=True,
):
    """
    Get the Import/Export totals for a given country and year range

    Args:
        country_of_interest (str): country of interest, e.g. 49 for China
        years (str): year range, e.g. 2010,2011,2012
        symmetric_values: if True report also exports from partner imports
                          and imports from partners exports; default True
        typeCode (str): C for commodities, S for Services, default C
        freqCode (str): A for annual and M for monthly, default A
        partners (str): 0 for the world, None for all, code or CSV, default 0

    Returns:
        DataFrame: DataFrame with the totals for each year and flow indexed
                   by year and flow code"""

    reported_imports = getFinalData(
        APIKEY,
        typeCode=typeCode,
        freqCode=freqCode,
        reporterCode=countryOfInterest,
        partnerCode=partners,
        partner2Code=0,
        flowCode="M",
        period=period,
        period_size=1,
        motCode=0,
        customsCode="C00",
        cmdCode="TOTAL",
        clCode="HS",
        includeDesc=True,
    )
    reported_exports = getFinalData(
        APIKEY,
        typeCode=typeCode,
        freqCode=freqCode,
        reporterCode=countryOfInterest,
        partnerCode=partners,
        partner2Code=0,
        flowCode="X",
        period=period,
        period_size=1,
        clCode="HS",
        cmdCode="TOTAL",
        customsCode="C00",
        motCode=0,
        includeDesc=True,
    )
    if symmetric_values:

        exports_from_imports = getFinalData(
            APIKEY,
            typeCode=typeCode,
            freqCode=freqCode,
            reporterCode=partners if partners != 0 else None,
            partnerCode=countryOfInterest,
            partner2Code=0,
            flowCode="M",
            period=period,
            period_size=1,
            clCode="HS",
            customsCode="C00",
            cmdCode="TOTAL",
            motCode=0,
            includeDesc=True,
        )
        imports_from_exports = getFinalData(
            APIKEY,
            typeCode=typeCode,
            freqCode=freqCode,
            reporterCode=partners if partners != 0 else None,
            partnerCode=countryOfInterest,
            partner2Code=0,
            flowCode="X",
            period=period,
            period_size=1,
            clCode="HS",
            customsCode="C00",
            cmdCode="TOTAL",
            motCode=0,
            includeDesc=True,
        )

    # Agregate by year and flow
    if reported_exports is not None:
        reported_exports = (
            reported_exports.groupby(["period", "reporterCode"])["primaryValue"]
            .sum()
            .reset_index()
        )
        reported_exports["flowCode"] = "X"
        reported_exports["flowDesc"] = "exports"
        # rename reporterCode to countryCode
        reported_exports.rename(columns={"reporterCode": "countryCode"}, inplace=True)
    else:
        reported_exports = pd.DataFrame(
            columns=["period", "countryCode", "primaryValue", "flowCode", "flowDesc"]
        )
    if reported_imports is not None:
        reported_imports = (
            reported_imports.groupby(["period", "reporterCode"])["primaryValue"]
            .sum()
            .reset_index()
        )
        # rename reporterCode to countryCode
        reported_imports.rename(columns={"reporterCode": "countryCode"}, inplace=True)
        reported_imports["flowCode"] = "M"
        reported_imports["flowDesc"] = "imports"
    else:
        reported_imports = pd.DataFrame(
            columns=["period", "countryCode", "primaryValue", "flowCode", "flowDesc"]
        )

    global_trade = pd.concat([reported_imports, reported_exports])

    if symmetric_values:
        if exports_from_imports is not None:
            exports_from_imports = (
                exports_from_imports.groupby(["period", "partnerCode"])["primaryValue"]
                .sum()
                .reset_index()
            )
            # rename partnerCode to countryCode
            exports_from_imports.rename(
                columns={"partnerCode": "countryCode"}, inplace=True
            )
            exports_from_imports["flowCode"] = "X<M"
            exports_from_imports["flowDesc"] = "exports(others imports)"
        else:
            exports_from_imports = pd.DataFrame(
                columns=[
                    "period",
                    "countryCode",
                    "primaryValue",
                    "flowCode",
                    "flowDesc",
                ]
            )

        if imports_from_exports is not None:
            imports_from_exports = (
                imports_from_exports.groupby(["period", "partnerCode"])["primaryValue"]
                .sum()
                .reset_index()
            )
            # rename partnerCode to countryCode
            imports_from_exports.rename(
                columns={"partnerCode": "countryCode"}, inplace=True
            )
            imports_from_exports["flowCode"] = "M<X"
            imports_from_exports["flowDesc"] = "imports(others exports)"
        else:
            imports_from_exports = pd.DataFrame(
                columns=[
                    "period",
                    "countryCode",
                    "primaryValue",
                    "flowCode",
                    "flowDesc",
                ]
            )

    global_trade = pd.concat([global_trade, exports_from_imports, imports_from_exports])

    trade_balance = pd.pivot_table(
        global_trade, index=["period"], columns="flowCode", values="primaryValue"
    ).fillna(0)
    trade_balance["trade_balance (X-M)"] = trade_balance["X"] - trade_balance["M"]
    trade_balance["trade_balance (X<M-M)"] = trade_balance["X<M"] - trade_balance["M"]
    trade_balance["trade_volume (X+M)"] = trade_balance["X"] + trade_balance["M"]
    trade_balance["trade_volume (X<M+M)"] = trade_balance["X<M"] + trade_balance["M"]
    trade_balance.reset_index()
    return trade_balance
    # .reindex(columns=['countryCode','countryDesc','exports','imports',
    # 'trade_balance','xReporterCode','xReporterDesc'])


def top_partners(
    reporterCode=0,
    years=None,
    cmdCode="TOTAL",
    flowCode="M,X",
    partnerCode=None,
    partner2Code=0,
    motCode=0,
    customsCode="C00",
    rank_partner_filter=None,
    rank_reporter_filter=None,
    rank_cmd_filter=None,
    rank_partner_cmd_filter=None,
    rank_cmd_partner_filter=None,
    return_data=False,
    timeout=120,
    echo_url=False,
):
    """Get the top trade partners of a country
        for a given year range

        DEPRECATED
    Args:
        reporterCode (str): reporter country code, e.g. 49 for China, or a CSV list
        years (str): year range, e.g. 2010,2011,2012
        cmdCode (str): HS code, e.g. TOTAL for all commodities, or AG2,
                        AG4 or specific code or list of
        flowCode (str): flow code, e.g. M for imports, X for exports, defaults to M,X
        partnerCode (str, optional): partner country code, e.g. 842 for USA, defaults to None (all)
        partner2Code (str, optional): second partner country code, e.g. 842 for USA,
                                    defaults to 0 (world)
                                    None for all, -1 for all but world.
        motCode (str, optional): Mode of transport code, e.g. 0 for all, 1 for sea, 2 for air.
                                    Defaults to None. If -1 is passed removes results with motCode = 0
        customsCode (str, optional): Customs procedure code, e.g. C00 for all, C05 for free zone.
        rank_filter (int): number of top commodities to return, default 5
        return_data (bool): return the DataFrame with the results and the DataFrame with the
                            full data as a tuple, default False
        echo_url (bool): print the url to the console, default False

    Returns:
        DataFrame: DataFrame with the top partners for each year and flow

        Extra cols:
        * primaryValueFormated: primaryValue formatted as a string
        * sum_cmd: total value for the commodity per year and flow
        * sum_year_flow: total value for the year and flow
        * perc_year_flow: percentage of the total value for the year and flow
        * sum_partner: total value for reporter+partner per year and flow
        * perc_partner: percentage of the total value for reporter+partner per year and flow
        * rank_partner: rank of the reporter+partner per year and flow
        * sum_reporter: total value for reporter per year and flow
        * perc_reporter: percentage of the total value for reporter per year and flow
        * rank_reporter: rank of the reporter per year and flow


    """
    df = get_data(
        "C",  # C for commodities, S for Services
        "A",  # (freqCode) A for annual and M for monthly
        flowCode=flowCode,
        cmdCode=cmdCode,
        reporterCode=reporterCode,
        partnerCode=partnerCode,
        partner2Code=partner2Code,
        period=years,
        motCode=motCode,
        customsCode=customsCode,
        timeout=timeout,
        echo_url=echo_url,
    )
    if df is None:
        warnings.warn("No data returned")
        return None

    # check if this is not beiing handled in getdata
    df = df[df["partnerCode"] != 0]

    # Total value of commodities per HS code per year and flow
    df["sum_cmd"] = df.groupby(["refYear", "flowCode", "cmdCode"])[
        "primaryValue"
    ].transform("sum")
    df["sum_reporter_cmd"] = df.groupby(
        ["refYear", "flowCode", "reporterCode", "cmdCode"]
    )["primaryValue"].transform("sum")
    df["sum_partner_cmd"] = df.groupby(
        ["refYear", "flowCode", "partnerCode", "cmdCode"]
    )["primaryValue"].transform("sum")

    # Total value per period per flow
    df["sum_year_flow"] = df.groupby(["refYear", "flowCode"])["primaryValue"].transform(
        "sum"
    )
    df["perc_year_flow"] = df["primaryValue"] / df["sum_year_flow"]

    # Total value for partner per period and flow
    df["sum_partner"] = df.groupby(["refYear", "flowCode", "partnerCode"])[
        "primaryValue"
    ].transform("sum")
    df["perc_partner"] = df["primaryValue"] / df["sum_partner"]

    # Total value for reporter+partner per period and flow
    df["sum_reporter_partner"] = df.groupby(
        ["refYear", "flowCode", "reporterCode", "partnerCode"]
    )["primaryValue"].transform("sum")
    df["perc_reporter_partner"] = df["primaryValue"] / df["sum_reporter_partner"]

    # global rank of partner
    df["rank_partner"] = df.groupby(["reporterDesc", "refYear", "flowCode"])[
        "sum_partner"
    ].rank(ascending=False, method="dense")
    df["rank_partner"] = df["rank_partner"].astype(int)

    # Total value per period per flow per reporter
    df["sum_reporter"] = df.groupby(["reporterDesc", "refYear", "flowCode"])[
        "primaryValue"
    ].transform("sum")
    df["perc_reporter"] = df["primaryValue"] / df["sum_reporter"]

    # rank of reporter
    df["rank_reporter"] = df.groupby(["reporterDesc", "refYear", "flowCode"])[
        "sum_reporter"
    ].rank(ascending=False, method="dense")
    df["rank_reporter"] = df["rank_reporter"].astype(int)

    # rank of commodity per HS code
    df["rank_cmd"] = df.groupby(["reporterDesc", "refYear", "flowCode"])[
        "sum_cmd"
    ].rank(ascending=False, method="dense")
    df["rank_cmd"] = df["rank_cmd"].astype(int)

    # rank of commodity per partner
    df["rank_partner_cmd"] = df.groupby(
        ["reporterDesc", "refYear", "flowCode", "partnerCode"]
    )["primaryValue"].rank(ascending=False, method="dense")
    df["rank_partner_cmd"] = df["rank_partner_cmd"].astype(int)

    # rank of partner per HS code
    df["rank_cmd_partner"] = df.groupby(
        ["reporterDesc", "refYear", "flowCode", "cmdCode"]
    )["primaryValue"].rank(ascending=False, method="dense")
    df["rank_cmd_partner"] = df["rank_cmd_partner"].astype(int)

    # value of trade as percentage of total same HS code
    df[PERC_PARTNER_IN_CMD] = df["primaryValue"] / df["sum_cmd"]
    # value of trade as percentage of total same partner
    df[PERC_CMD_IN_PARTNER] = df["primaryValue"] / df["sum_partner"]

    sort_list = ["refYear", "flowCode", "partnerDesc", "primaryValue"]
    sort_order = [True, True, True, False]

    pco = df
    if rank_partner_filter is not None:
        pco = pco[pco["rank_partner"] <= rank_partner_filter]
    if rank_reporter_filter is not None:
        pco = pco[pco["rank_reporter"] <= rank_reporter_filter]
    if rank_cmd_filter is not None:
        pco = pco[pco["rank_cmd"] <= rank_cmd_filter]
    if rank_cmd_partner_filter is not None:
        pco = pco[pco["rank_cmd_partner"] <= rank_cmd_partner_filter]
    if rank_partner_cmd_filter is not None:
        pco = pco[pco["rank_partner_cmd"] <= rank_partner_cmd_filter]
    pco_cut_sorted = pco.sort_values(sort_list, ascending=sort_order)

    if return_data:
        return (pco_cut_sorted, df)
    else:
        return pco_cut_sorted


def year_range(year_start=1984, year_end=2030):
    """Return a string with comma separeted list of years

    Args:
        year_start (int, optional): Start year. Defaults to 1984.
        year_end (int, optional): End year. Defaults to 2030.

    """
    period = ",".join(map(str, list(range(year_start, year_end + 1, 1))))
    return period


def excel_col_autowidth(
    data_frame: pd.DataFrame,
    excel_file: pd.ExcelWriter,
    sheet=None,
    consider_headers=True,
):
    """Set the column width in the Excel file to the maximum width of the data in the column

    Args:
        data_frame (pd.DataFrame): The DataFrame to format
        excel_file (pd.ExcelWriter): The ExcelWriter object
        sheet (str, optional): The sheet name. Defaults to first one
        consider_headers (bool, optional): If True consider the headers when setting
                                            the width. Defaults to True.

    """

    # get the name of the first sheet
    if sheet is None:
        sheet = list(excel_file.sheets.keys())[0]

    # for each level of the index
    for indx_n, index in enumerate(data_frame.index.names):
        if index is not None:
            index_col = index
        else:
            index_col = ""

        # get the max width of the index
        col_width = data_frame.index.get_level_values(indx_n).astype(str).map(len).max()
        if consider_headers:
            col_header_width = len(index_col)
            col_width = max(col_width, col_header_width)

        if col_width > 100:
            col_width = 100

        excel_file.sheets[sheet].set_column(indx_n, indx_n, col_width)

    for column in data_frame:
        # get the max width of the index
        col_width = data_frame[column].astype(str).map(len).max()
        if consider_headers:
            col_header_width = len(column)
            col_width = max(col_width, col_header_width)

        if col_width > 100:
            col_width = 100

        col_idx = data_frame.columns.get_loc(column) + indx_n + 1
        excel_file.sheets[sheet].set_column(col_idx, col_idx, col_width)


def excel_format_currency(
    data_frame: pd.DataFrame,
    excel_file: pd.ExcelWriter,
    sheet=None,
    columns=None,
    format="$#,##0",
    width=None,
):
    """Format the columns in the Excel file as currency

    Args:
        data_frame (pd.DataFrame): The DataFrame to format
        excel_file (pd.ExcelWriter): The ExcelWriter object
        sheet (str, optional): The sheet to format. Defaults to None, first sheet.
        columns (list, optional): The columns to format. Defaults to all numeric columns.
        format (str, optional): The format to use. Defaults to '$#,##0'.
    """
    workbook = excel_file.book
    currency_format = workbook.add_format({"num_format": format})
    if columns is None:
        columns = data_frame.select_dtypes(include=["number"]).columns
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


def excel_format_percent(
    data_frame: pd.DataFrame,
    excel_file: pd.ExcelWriter,
    sheet=None,
    columns=None,
    format="0.00%",
    width=None,
):
    """Format the columns in the Excel file as percentage

    Args:
        data_frame (pd.DataFrame): The DataFrame to format
        excel_file (pd.ExcelWriter): The ExcelWriter object
        sheet (str, optional): The sheet to format. Defaults to None, first sheet.
        columns (list, optional): The columns to format. Defaults to all numeric columns.
        format (str, optional): The format to use. Defaults to '0.00%'.
    """
    workbook = excel_file.book
    percent_format = workbook.add_format({"num_format": format})
    if columns is None:
        columns = data_frame.select_dtypes(include=["number"]).columns
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


def checkAggregateValues(
    df: pd.DataFrame, hcode_column: str, aggregate_column="isCmdAggregate"
):
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
            df.loc[lastIndex, aggregate_column] = True
        elif currentCode == lastCode:
            # code is the same as last row, copy the value
            df.loc[row[0], aggregate_column] = df.loc[lastIndex, aggregate_column]
            warnings.warn(
                f"Code {currentCode} is duplicated in row {row[0]} and {lastIndex}"
            )
        else:
            df.loc[lastIndex, aggregate_column] = False
        # print(df.loc[row[0]][['cmdCode','cmdDesc']])
        lastCode = currentCode
        lastIndex = row[0]
    return df


# create main function
if __name__ == "__main__":
    print("contrade.py initializing...")
    Path("support").mkdir(parents=True, exist_ok=True)
    Path("reports").mkdir(parents=True, exist_ok=True)
    fname = "config.ini"
    content = """
    # Config file
    [comtrade]
    # Add API Key. DO NOT SHARE
    key =
    """
    if not os.path.isfile(fname):
        print("Creating file config.ini")
        with open(fname, "w", encoding="utf-8") as f:
            f.write(content)
        print("Add API Key. Get one at https://comtradedeveloper.un.org/ ")
    if os.path.isfile(fname):
        config = configparser.ConfigParser()
        config.read("config.ini")
        # get API Key or set to None
        APIKEY = config["comtrade"].get("key", None)
    init(APIKEY, force_init=True)
    PERIOD_SECONDS = 7
    print("contrade.py initialized")


@sleep_and_retry
@limits(calls=CALLS_PER_PERIOD, period=PERIOD_SECONDS)
def get_data(
    typeCode: str,
    freqCode: str,
    reporterCode: str = "49",
    partnerCode: str = "024,076,132,226,624,508,620,678,626",
    partner2Code: str = 0,
    period: str = None,
    clCode: str = "HS",
    cmdCode: str = "TOTAL",
    flowCode: str = "M,X",
    customsCode: str = "C00",
    more_pars=None,
    qtyUnitCodeFilter=None,
    motCode=None,
    apiKey: Union[str, None] = None,
    cache: bool = True,
    timeout: int = 10,
    echo_url: bool = False,
) -> Union[pd.DataFrame, None]:
    """Makes a query to UN Comtrade+ API, returns a pandas DataFrame

    This is DEPRECATED. Originally the UN API did not decode results
    and this function added decoding of values using the various codebooks.

    Use comtradetools.getFinalData() instead.

    Args:
        typeCode (str): Type of data to retrieve, C for commodities, S for Services
        freqCode (str): Frequency of data, A for annual, M for monthly
        reporterCode (str, optional): Reporter country code. Defaults to '49'.
        partnerCode (str, optional): Partner country code. Defaults to
                                        '024,076,132,226,624,508,620,678,626'.
        partner2Code (str, optional): Partner2 country code. Defaults to 0 (world).
                                        Use -1 to remove 0 (world)
        period (str, optional): Period of data, e.g. 2018, 2018,2019, 2018,2019,2020.
                                Defaults to None.
        clCode (str, optional): Classification code, HS for Harmonized System,
                                SITC for Standard International Trade Classification. Defaults to "HS".
        cmdCode (str, optional): Commodity code, TOTAL for all commodities. Defaults to "TOTAL".
        flowCode (str, optional): Flow code, M for imports, X for exports. Defaults to "M,X".
        customsCode (str, optional): Customs code, C00 for all customs. Defaults to 'C00'.
        more_pars (dict, optional): Additional parameters to pass to the API.
        qtyUnitCodeFilter (str, optional): Quantity unit code, e.g. 1 for tonnes, 2 for kilograms.
                                            Defaults to None.
        motCode (str, optional): Mode of transport code, e.g. 0 for all, 1 for sea, 2 for air.
                                            Defaults to None.
                                            If -1 is passed removes results with motCode = 0,
        apiKey (str,optional): API Key for umcomtrade+
        cache (bool, optional): Cache the results. Defaults to True.
        timeout (int, optional): Timeout for the API call. Defaults to 10.
        echo_url (bool, optional): Echo the CODE_BOOK_url to the console. Defaults to False.

    """
    if apiKey is None:
        apiKey = APIKEY
    if more_pars is None:
        more_pars = {}

    base_url = f"{get_url(apiKey)}/{typeCode}/{freqCode}/{clCode}"
    if partner2Code == -1:  # -1
        partner2CodePar = None
    else:
        partner2CodePar = partner2Code

    pars = {
        "reporterCode": reporterCode,
        "period": period,
        "partnerCode": partnerCode,
        "partner2CodePar": partner2CodePar,
        "cmdCode": cmdCode,
        "flowCode": flowCode,
        "customsCode": customsCode,
        "subscription-key": apiKey,
    }

    df: pd.DataFrame | None = pd.DataFrame()

    # make a hash of the parameters for caching
    hash = hashlib.md5()
    hash.update(f"{base_url}{str(pars)}".encode("utf-8"))

    if cache and not os.path.exists(CACHE_DIR):
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

    cache_file = f"{CACHE_DIR}/{hash.hexdigest()}.pickle"
    if cache and os.path.exists(cache_file):
        modification_time = os.path.getmtime(cache_file)
        current_time = datetime.datetime.now().timestamp()
        days_since_modification = (current_time - modification_time) / (24 * 3600)
        if days_since_modification <= CACHE_VALID_DAYS:
            with open(cache_file, "rb") as f:
                df = pickle.load(f)
                return df
        else:
            os.remove(cache_file)

    error: bool = False

    global RETRY
    RETRY = 0
    while RETRY < MAX_RETRIES:
        resp = requests.get(base_url, {**pars, **more_pars}, timeout=timeout)
        if resp.status_code == 200:
            break
        elif resp.status_code == 429:
            sleep = MAX_SLEEP * (RETRY + 1)
            RETRY += 1
            errorInfo = json.loads(resp.content)
            message = errorInfo.get("message", resp.content)
            warnings.warn(
                f"Server returned HTTP Status: {str(resp.status_code)} {message} retrying in {sleep} seconds",
            )

            time.sleep(sleep)
        else:
            break

    if echo_url:
        sanitize = re.sub("subscription-key=.*", "subscription-key=HIDDEN", resp.url)
        print(sanitize)
    if resp.status_code != 200:
        warnings.warn(
            f"Server returned HTTP Status: {str(resp.status_code)}",
        )
        errorInfo = json.loads(resp.content)
        message = errorInfo.get("message", resp.content)
        warnings.warn(f"Server returned error: {message}")
        df = None
        error = True
    else:
        resp_json = json.loads(resp.content)
        error_json = resp_json.get("statusCode", None)
        if error_json is not None:
            error_message = resp_json.get("message", None)
            warnings.warn(f"Server returned JSON error: {error_json}: {error_message}")
            df = None
            error = True

    if error:
        return None
    else:
        results = json.loads(resp.content)["data"]
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

            if customsCode is not None:
                df = df[df.customsCode == customsCode]

            if motCode is not None:
                if motCode == -1:  # Remove motCode = 0
                    lenBefore = len(df)
                    df = df[df.motCode != 0]
                    lenAfter = len(df)
                    if lenBefore != lenAfter:
                        warnings.warn(
                            f"Removed {lenBefore-lenAfter} results with motCode = 0"
                        )
                else:  # Keep only specified motCode
                    df = df[df.motCode == motCode]
            else:
                motCodes = df["motCode"].unique()
                if len(motCodes) > 1 and 0 in motCodes:
                    warnings.warn(
                        "Query returned different motCodes including 0 (all), check for duplicate"
                        " results when aggregating. Use motCode = -1 to remove motCode = 0, "
                        "or motCode=0 to remove details"
                    )

            if len(df["isAggregate"].unique()) > 1:
                warnings.warn(
                    "Query returned different isAggregate values, "
                    "check for duplicate results when aggregating"
                )

            # check for multiple partner2Codes and potentially duplicate results

            if partner2Code == -1:  # Remove partner2Code = 0
                df = df[df.partner2Code != 0]
            elif partner2Code is not None:  # Keep only specified partner2Code
                df = df[df.partner2Code == partner2Code]

            partner2Codes = df["partner2Code"].unique()
            if len(partner2Codes) > 1 and 0 in partner2Codes:
                warnings.warn(
                    "Query returned different partner2Codes including 0 (all), check for duplicate results when aggregating. "
                    "Use partner2Code = -1 to remove partner2Code = 0, or partner2Code=0 to remove details"
                )

            customCodes = df["customsCode"].unique()
            if len(customCodes) > 1 and "C00" in customCodes:
                warnings.warn(
                    "Query returned different customCodes including C00 (all), check for duplicate results when aggregating. Use customsCode = C00 to remove details"
                )

            # Convert the country codes to country names
            if "reporterCode" in df.columns.values:
                df.reporterDesc = df.reporterCode.map(COUNTRY_CODES)
                # check for Nan in the result
                # and change it to the reporterCode as string
                df.reporterDesc = df.reporterDesc.fillna(df.reporterCode.astype(str))
            if "partnerCode" in df.columns.values:
                df.partnerDesc = df.partnerCode.map(COUNTRY_CODES)
                # check for Nan in the result
                # and change it to the partnerCode
                df.partnerDesc = df.partnerDesc.fillna(df.partnerCode.astype(str))
            if "partner2Code" in df.columns.values:
                df.partner2Desc = df.partner2Code.map(COUNTRY_CODES)
                # check for Nan in the result
                # and change it to the partner2Code
                df.partner2Desc = df.partner2Desc.fillna(df.partner2Code.astype(str))

            # Convert flowCode
            if "flowCode" in df.columns.values:
                df["flowDesc"] = df.flowCode.map(FLOWS_CODES)
            # Convert the HS codes
            if "cmdCode" in df.columns.values:
                df["cmdDesc"] = df.cmdCode.map(HS_CODES)

            # Convert customsCode
            if "customsCode" in df.columns.values:
                df["customsDesc"] = df.customsCode.map(CUSTOMS_CODE)

            # Convert mosCode
            if "mosCode" in df.columns.values:
                df["mosDesc"] = df.mosCode.map(MOS_CODES)

            # Convert motCode
            if "motCode" in df.columns.values:
                df["motDesc"] = df.motCode.map(MOT_CODES)

            # Convert qtyUnitCode
            if "qtyUnitCode" in df.columns.values:
                df["qtyUnitAbbr"] = df.qtyUnitCode.map(QTY_CODES)
                df["qtyUnitDesc"] = df.qtyUnitCode.map(QTY_CODES_DESC)

            # Convert altQtyUnitCode
            if "altQtyUnitCode" in df.columns.values:
                df["altQtyUnitAbbr"] = df.altQtyUnitCode.map(QTY_CODES)
                df["altQtyUnitDesc"] = df.altQtyUnitCode.map(QTY_CODES_DESC)

            # Generate a formated version of the value for readability here
            if "primaryValue" in df.columns.values:
                df["primaryValueFormated"] = df.primaryValue.map("{:,.2f}".format)

            # check to cache the results
            if cache:
                with open(cache_file, "wb") as f:
                    pickle.dump(df, f)

            # return the DataFrame
        return df


# create main function
if __name__ == "__main__":
    print("contrade.py initializing...")
    Path("support").mkdir(parents=True, exist_ok=True)
    Path("reports").mkdir(parents=True, exist_ok=True)
    fname = "config.ini"
    content = """
    # Config file
    [comtrade]
    # Add API Key. DO NOT SHARE
    key =
    """
    if not os.path.isfile(fname):
        print("Creating file config.ini")
        with open(fname, "w", encoding="utf-8") as f:
            f.write(content)
        print("Add API Key. Get one at https://comtradedeveloper.un.org/ ")
    if os.path.isfile(fname):
        config = configparser.ConfigParser()
        config.read("config.ini")
        # get API Key or set to None
        APIKEY = config["comtrade"].get("key", None)
    init(APIKEY, force_init=True)
    PERIOD_SECONDS = 7
    print("contrade.py initialized")
