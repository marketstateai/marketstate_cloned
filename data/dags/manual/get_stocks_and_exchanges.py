"""
One-off scraper to load exchange-level stock lists from Stock Analysis
into BigQuery.

What it does:
- Reads the exchanges table from https://stockanalysis.com/list/exchanges/
  (via pandas.read_html) and extracts the per-exchange list URLs.
- Visits each exchange list page in Selenium, accepts consent prompts,
  paginates through the main table using the "next" SVG icon, and gathers rows.
- Normalizes headers, adds the source page URL to each row, and merges results.
- Writes a per-exchange summary table and a per-stock table to BigQuery.
- When --urls is "all", each exchange is processed in an isolated run
  (fresh browser + per-exchange write).

Output:
- BigQuery table output for exchanges and stocks.
- Schema: columns are derived from the exchange list table headers and
  normalized to ensure every row has the same number of columns. The
  script also adds `page_url` for the source page of each row.
- Project: BigQuery output.

Required environment:
- Chrome + compatible ChromeDriver available on PATH.
- Network access to stockanalysis.com.
- Optional: set `HEADLESS=1` to run the browser headless.
- For BigQuery writes: `GOOGLE_APPLICATION_CREDENTIALS` with
  BigQuery write permissions for the target table.

Required arguments:
- --urls (whitespace-separated exchange URLs or 'all')
- --table-id (project.dataset.table or dataset.table with --project)
- --dataset (if table-id omitted; requires --project)
- --headless (true/false)

Optional arguments:
- --skip-urls (whitespace-separated exchange URLs to skip)

Skip example:
  --skip-urls "https://stockanalysis.com/list/otc-stocks/"

Example usage:
python -m dags.manual.get_stocks_and_exchanges \
  --headless false \
  --urls "https://stockanalysis.com/list/frankfurt-stock-exchange/" \
  --table-id general-428410.src_dev.exchanges \
  --project general-428410 \
  --write-disposition WRITE_APPEND


"""

import argparse
from datetime import datetime
import os
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import io

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from marketstate.marketstate_data.src.bigquery_utils import load_dataframe_to_bigquery
from marketstate.marketstate_data.src.scraping_utils.playwright_tables import PaginatedTableScraper
try:
    from airflow.sdk import Variable
except Exception:  # pragma: no cover - optional in CLI usage
    Variable = None

try:
    from marketstate.marketstate_data.dags._lib.utils import SecretManagerHelper
except Exception:  # pragma: no cover - optional outside Airflow
    SecretManagerHelper = None

os.environ.setdefault("GOOGLE_AUTH_DISABLE_GCE_METADATA", "1")
os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
os.environ.setdefault("GRPC_TRACE", "")
os.environ.setdefault("ABSL_LOGGING_MIN_SEVERITY", "2")
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("GLOG_logtostderr", "0")
os.environ.setdefault("GLOG_stderrthreshold", "2")

BQ_SECRET_RESOURCE_VAR = "BQ_SECRET_RESOURCE"
DEFAULT_BQ_SECRET_RESOURCE = "projects/318171260121/secrets/bigquery"
secret_helper = SecretManagerHelper() if SecretManagerHelper is not None else None

# Exchange Mappings
EXCHANGE_MAPPING_HEADERS = [
  'url',
  'exchange_name_local_language',
  'exchange_abbreviation',
  'yahoo_suffix',
  'exchange_name',
  'country',
  'currency',
  'market_identifier_code',
  'trade_accessibility',
]
EXCHANGE_MAPPING_ROWS = [
  ['https://stockanalysis.com/list/australian-securities-exchange/', 'Australian Securities Exchange', 'ASX', 'AX', 'Australian Securities Exchange', 'Australia', 'AUD', 'XASX', 'high'],
  ['https://stockanalysis.com/list/cboe-canada/', 'Cboe Canada', 'NEO', 'NE', 'Cboe Canada', 'Canada', 'CAD', 'NEOE', 'high'],
  ['https://stockanalysis.com/list/canadian-securities-exchange/', 'Canadian Securities Exchange', 'CSE', 'CN', 'Canadian Securities Exchange', 'Canada', 'CAD', 'XCNQ', 'high'],
  ['https://stockanalysis.com/list/toronto-stock-exchange/', 'Bourse de Toronto', 'TSX', 'TO', 'Toronto Stock Exchange', 'Canada', 'CAD', 'XTSE', 'high'],
  ['https://stockanalysis.com/list/tsx-venture-exchange/', 'TSX Venture Exchange', 'TSX', 'V', 'TSX Venture Exchange', 'Canada', 'CAD', 'XTSX', 'high'],
  ['https://stockanalysis.com/list/six-swiss-exchange/', 'Schweizer Börse', 'SIX', 'SW', 'SIX Swiss Exchange', 'Switzerland', 'CHF', 'XSWX', 'high'],
  ['https://stockanalysis.com/list/copenhagen-stock-exchange/', 'Københavns Fondsbørs', 'CPH', 'CO', 'Copenhagen Stock Exchange', 'Denmark', 'DKK', 'XCSE', 'high'],
  ['https://stockanalysis.com/list/nasdaq-tallinn/', 'Nasdaq Tallinn', 'TLN', 'TL', 'Nasdaq Tallinn', 'Estonia', 'EUR', 'XTAL', 'high'],
  ['https://stockanalysis.com/list/cboe-europe/', 'CBOE Europe', 'CHIX', 'XD', 'CBOE Europe', 'Europe', 'EUR', 'BCXE', 'high'],
  ['https://stockanalysis.com/list/euronext-brussels/', 'Euronext Brussels', 'EBR', 'BR', 'Euronext Brussels', 'Belgium', 'EUR', 'XBRU', 'high'],
  ['https://stockanalysis.com/list/euronext-amsterdam/', 'Euronext Amsterdam', 'AMS', 'AS', 'Euronext Amsterdam', 'Netherlands', 'EUR', 'XAMS', 'high'],
  ['https://stockanalysis.com/list/stuttgart-stock-exchange/', 'Boerse Stuttgart', 'BST', 'SG', 'Stuttgart Stock Exchange', 'Germany', 'EUR', 'XSTU', 'high'],
  ['https://stockanalysis.com/list/euronext-dublin/', 'Euronext Dublin', 'ISE', 'IR', 'Euronext Dublin', 'Ireland', 'EUR', 'XMSM', 'high'],
  ['https://stockanalysis.com/list/euronext-paris/', 'Euronext Paris', 'PAR', 'PA', 'Euronext Paris', 'France', 'EUR', 'XPAR', 'high'],
  ['https://stockanalysis.com/list/malta-stock-exchange/', "Borz ta' Malta", 'MSE', None, 'Malta Stock Exchange', 'Malta', 'EUR', 'XMAL', 'high'],
  ['https://stockanalysis.com/list/ljubljana-stock-exchange/', 'Ljubljanska Borza', 'LJSE', None, 'Ljubljana Stock Exchange', 'Slovenia', 'EUR', 'XLJU', 'high'],
  ['https://stockanalysis.com/list/athens-stock-exchange/', 'Chrimatistirio Athinon', 'ATH', 'AT', 'Athens Stock Exchange', 'Greece', 'EUR', 'XATH', 'high'],
  ['https://stockanalysis.com/list/nasdaq-helsinki/', 'Nasdaq Helsinki', 'HEL', 'HE', 'Nasdaq Helsinki', 'Finland', 'EUR', 'XHEL', 'high'],
  ['https://stockanalysis.com/list/cyprus-stock-exchange/', 'Kipriaki Chrematistiria', 'CYS', None, 'Cyprus Stock Exchange', 'Cyprus', 'EUR', 'XCYS', 'high'],
  ['https://stockanalysis.com/list/deutsche-boerse-xetra/', None, 'ETR', 'DE', 'Deutsche Boerse Xetra', 'Germany', 'EUR', 'XETR', 'high'],
  ['https://stockanalysis.com/list/luxembourg-stock-exchange/', 'Bourse de Luxembourg', 'LUX', None, 'Luxembourg Stock Exchange', 'Luxembourg', 'EUR', 'XLUX', 'high'],
  ['https://stockanalysis.com/list/euronext-lisbon/', 'Euronext Lisboa', 'ELI', 'LS', 'Euronext Lisbon', 'Portugal', 'EUR', 'XLIS', 'high'],
  ['https://stockanalysis.com/list/dusseldorf-stock-exchange/', 'Boerse Duesseldorf', 'DUSE', 'DU', 'Dusseldorf Stock Exchange', 'Germany', 'EUR', 'XDUS', 'high'],
  ['https://stockanalysis.com/list/borsa-italiana/', 'Borsa Italiana', 'BIT', 'MI', 'Borsa Italiana', 'Italy', 'EUR', 'XMIL', 'high'],
  ['https://stockanalysis.com/list/nasdaq-vilnius/', 'Nasdaq Vilnius', 'VSE', 'VS', 'Nasdaq Vilnius', 'Lithuania', 'EUR', 'XLIT', 'high'],
  ['https://stockanalysis.com/list/frankfurt-stock-exchange/', 'Frankfurter Wertpapierbörse', 'FRA', 'F', 'Frankfurt Stock Exchange', 'Germany', 'EUR', 'XDWZ', 'high'],
  ['https://stockanalysis.com/list/madrid-stock-exchange/', 'Bolsa de Madrid', 'BME', 'MC', 'Madrid Stock Exchange', 'Spain', 'EUR', 'XMAD', 'high'],
  ['https://stockanalysis.com/list/hamburg-stock-exchange/', 'Boerse Hamburg', 'HAM', 'HM', 'Hamburg Stock Exchange', 'Germany', 'EUR', 'HAMA', 'high'],
  ['https://stockanalysis.com/list/vienna-stock-exchange/', 'Wiener Boerse', 'VIE', 'VI', 'Vienna Stock Exchange', 'Austria', 'EUR', 'XVIE', 'high'],
  ['https://stockanalysis.com/list/nasdaq-riga/', 'Nasdaq Riga', 'RSE', 'RG', 'Nasdaq Riga', 'Latvia', 'EUR', 'XRIS', 'high'],
  ['https://stockanalysis.com/list/london-stock-exchange-aim/', 'London Stock Exchange AIM', 'AIM', 'L', 'London Stock Exchange AIM', 'United Kingdom', 'GBP', 'AIMX', 'high'],
  ['https://stockanalysis.com/list/london-stock-exchange/', 'London Stock Exchange', 'LON', 'L', 'London Stock Exchange', 'United Kingdom', 'GBP', 'XLON', 'high'],
  ['https://stockanalysis.com/list/aquis-exchange/', 'Aquis Exchange', 'AQU', 'AQ', 'Aquis Exchange', 'United Kingdom', 'GBP', 'AQXE', 'high'],
  ['https://stockanalysis.com/list/oslo-bors/', None, 'OSE', 'OL', 'Oslo Bors', 'Norway', 'NOK', 'XOSL', 'high'],
  ['https://stockanalysis.com/list/warsaw-stock-exchange/', 'Gielda Papierow Wartosciowych', 'WSE', 'WA', 'Warsaw Stock Exchange', 'Poland', 'PLN', 'XWAR', 'high'],
  ['https://stockanalysis.com/list/bucharest-stock-exchange/', 'Bursa de Valori Bucuresti', 'BVB', 'RO', 'Bucharest Stock Exchange', 'Romania', 'RON', 'XBRM', 'high'],
  ['https://stockanalysis.com/list/nasdaq-stockholm/', 'Nasdaq Stockholm', 'STO', 'ST', 'Nasdaq Stockholm', 'Sweden', 'SEK', 'XSTO', 'high'],
  ['https://stockanalysis.com/list/nordic-growth-market/', 'Nordic Growth Market', 'NGM', None, 'Nordic Growth Market', 'Sweden', 'SEK', 'XNGM', 'high'],
  ['https://stockanalysis.com/list/nyse-stocks/', 'NYSE', 'NYSE', None, 'New York Stock Exchange', 'United States', 'USD', 'XNYS', 'high'],
  ['https://stockanalysis.com/list/otc-stocks/', 'US OTC', 'OTC', None, 'US OTC', 'United States', 'USD', 'OTCM', 'high'],
  ['https://stockanalysis.com/list/nyseamerican-stocks/', 'NYSE American', 'AMEX', None, 'NYSE American', 'United States', 'USD', 'AMXO', 'high'],
  ['https://stockanalysis.com/list/nasdaq-stocks/', 'Nasdaq', 'NASDAQ', None, 'Nasdaq Stock Market', 'United States', 'USD', 'XNAS', 'high'],
  ['https://stockanalysis.com/list/dubai-financial-market/', 'Dubai Suq Al-Mali', 'DFM', 'AE', 'Dubai Financial Market', 'United Arab Emirates', 'AED', 'XDFM', 'low'],
  ['https://stockanalysis.com/list/abu-dhabi-securities-exchange/', 'Abu Dhabi Suq Al-Mali', 'ADX', None, 'Abu Dhabi Securities Exchange', 'United Arab Emirates', 'AED', 'XADS', 'low'],
  ['https://stockanalysis.com/list/buenos-aires-stock-exchange/', 'Bolsa de Comercio de Buenos Aires', 'BCBA', 'BA', 'Buenos Aires Stock Exchange', 'Argentina', 'ARS', 'XBUE', 'low'],
  ['https://stockanalysis.com/list/dhaka-stock-exchange/', 'Dhaka Stock Exchange', 'DSE', None, 'Dhaka Stock Exchange', 'Bangladesh', 'BDT', 'XDHA', 'low'],
  ['https://stockanalysis.com/list/bulgarian-stock-exchange/', 'Balgarska Fondova Borsa', 'BUL', None, 'Bulgarian Stock Exchange', 'Bulgaria', 'BGN', 'XBUL', 'low'],
  ['https://stockanalysis.com/list/bahrain-stock-exchange/', 'Bahrain Bourse', 'BAX', None, 'Bahrain Stock Exchange', 'Bahrain', 'BHD', 'XBAH', 'low'],
  ['https://stockanalysis.com/list/brazil-stock-exchange/', 'Bolsa de Valores do Brasil', 'B3', 'SA', 'Brazil Stock Exchange', 'Brazil', 'BRL', 'BVMF', 'low'],
  ['https://stockanalysis.com/list/botswana-stock-exchange/', 'Botswana Stock Exchange', 'MYX', None, 'Botswana Stock Exchange', 'Botswana', 'BWP', 'XBOT', 'low'],
  ['https://stockanalysis.com/list/santiago-stock-exchange/', 'Bolsa de Comercio de Santiago', 'SSE', 'SN', 'Santiago Stock Exchange', 'Chile', 'CLP', 'XSGO', 'low'],
  ['https://stockanalysis.com/list/shenzhen-stock-exchange/', 'Shenzhen Stock Exchange', 'SZSE', 'SZ', 'Shenzhen Stock Exchange', 'China', 'CNY', 'XSHE', 'low'],
  ['https://stockanalysis.com/list/shanghai-stock-exchange/', 'Shanghai Stock Exchange', 'SSE', 'SS', 'Shanghai Stock Exchange', 'China', 'CNY', 'XSHG', 'low'],
  ['https://stockanalysis.com/list/colombia-stock-exchange/', 'Bolsa de Valores de Colombia', 'COL', 'CL', 'Colombia Stock Exchange', 'Colombia', 'COP', 'XBOG', 'low'],
  ['https://stockanalysis.com/list/prague-stock-exchange/', 'Pražská burza', 'PSE', 'PR', 'Prague Stock Exchange', 'Czech Republic', 'CZK', 'XPRA', 'low'],
  ['https://stockanalysis.com/list/egyptian-stock-exchange/', 'Egyptian Exchange', 'EGX', 'CA', 'Egyptian Stock Exchange', 'Egypt', 'EGP', 'XCAI', 'low'],
  ['https://stockanalysis.com/list/bratislava-stock-exchange/', 'Burza cenných papierov v Bratislave', 'BSSE', None, 'Bratislava Stock Exchange', 'Slovakia', 'EUR', 'XBRA', 'low'],
  ['https://stockanalysis.com/list/belgrade-stock-exchange/', 'Beogradska Berza', 'BELEX', None, 'Belgrade Stock Exchange', 'Serbia', 'EUR', 'XBEL', 'low'],
  ['https://stockanalysis.com/list/zagreb-stock-exchange/', 'Zagrebacka Burza', 'ZSE', None, 'Zagreb Stock Exchange', 'Croatia', 'HRK', 'XZAG', 'low'],
  ['https://stockanalysis.com/list/budapest-stock-exchange/', 'Budapesti Értéktőzsde', 'BUD', 'BD', 'Budapest Stock Exchange', 'Hungary', 'HUF', 'XBUD', 'low'],
  ['https://stockanalysis.com/list/indonesia-stock-exchange/', 'Bursa Efek Indonesia', 'IDX', 'JK', 'Indonesia Stock Exchange', 'Indonesia', 'IDR', 'XIDX', 'low'],
  ['https://stockanalysis.com/list/tel-aviv-stock-exchange/', 'Tel Aviv Stock Exchange', 'TLV', 'TA', 'Tel Aviv Stock Exchange', 'Israel', 'ILS', 'XTAE', 'low'],
  ['https://stockanalysis.com/list/nse-india/', 'National Stock Exchange of India', 'NSE', 'NS', 'National Stock Exchange of India', 'India', 'INR', 'XNSE', 'low'],
  ['https://stockanalysis.com/list/bse-india/', 'Bombay Stock Exchange', 'BSE', 'BO', 'Bombay Stock Exchange', 'India', 'INR', 'XBOM', 'low'],
  ['https://stockanalysis.com/list/nasdaq-iceland/', 'Nasdaq Iceland', 'ICE', 'IC', 'Nasdaq Iceland', 'Iceland', 'ISK', 'XICE', 'low'],
  ['https://stockanalysis.com/list/jamaica-stock-exchange/', 'Jamaica Stock Exchange', 'JMSE', None, 'Jamaica Stock Exchange', 'Jamaica', 'JMD', 'XJAM', 'low'],
  ['https://stockanalysis.com/list/palestine-stock-exchange/', 'Palestine Exchange', 'PEX', None, 'Palestine Stock Exchange', 'Palestine', 'JOD', 'XPAE', 'low'],
  ['https://stockanalysis.com/list/amman-stock-exchange/', 'Amman Stock Exchange', 'ASE', None, 'Amman Stock Exchange', 'Jordan', 'JOD', 'XAMM', 'low'],
  ['https://stockanalysis.com/list/nairobi-stock-exchange/', 'Nairobi Securities Exchange', 'NASE', None, 'Nairobi Stock Exchange', 'Kenya', 'KES', 'XNAI', 'low'],
  ['https://stockanalysis.com/list/kosdaq-korea/', 'KOSDAQ', 'KOSDAQ', 'KQ', 'KOSDAQ', 'South Korea', 'KRW', 'XTAD', 'low'],
  ['https://stockanalysis.com/list/korea-new-exchange/', 'KONEX', 'XKON', None, 'Korea New Exchange', 'South Korea', 'KRW', 'XKON', 'low'],
  ['https://stockanalysis.com/list/korea-stock-exchange/', 'Korea Stock Exchange', 'KRX', 'KS', 'Korea Stock Exchange', 'South Korea', 'KRW', 'XKOR', 'low'],
  ['https://stockanalysis.com/list/kuwait-stock-exchange/', 'Boursa Kuwait', 'KWSE', 'KW', 'Kuwait Stock Exchange', 'Kuwait', 'KWD', 'XKUW', 'low'],
  ['https://stockanalysis.com/list/kazakhstan-stock-exchange/', 'Kazakhstan Stock Exchange', 'KASE', None, 'Kazakhstan Stock Exchange', 'Kazakhstan', 'KZT', 'XKAZ', 'low'],
  ['https://stockanalysis.com/list/beirut-stock-exchange/', 'Beirut Stock Exchange', 'BDB', None, 'Beirut Stock Exchange', 'Lebanon', 'LBP', 'XBEY', 'low'],
  ['https://stockanalysis.com/list/colombo-stock-exchange/', 'Colombo Stock Exchange', 'COSE', None, 'Colombo Stock Exchange', 'Sri Lanka', 'LKR', 'XCOL', 'low'],
  ['https://stockanalysis.com/list/casablanca-stock-exchange/', 'Bourse de Casablanca', 'CBSE', None, 'Casablanca Stock Exchange', 'Morocco', 'MAD', 'XCAS', 'low'],
  ['https://stockanalysis.com/list/mauritius-stock-exchange/', 'Stock Exchange of Mauritius', 'MUSE', None, 'Mauritius Stock Exchange', 'Mauritius', 'MUR', 'XMAU', 'low'],
  ['https://stockanalysis.com/list/malawi-stock-exchange/', 'Malawi Stock Exchange', 'MAL', None, 'Malawi Stock Exchange', 'Malawi', 'MWK', 'XMSW', 'low'],
  ['https://stockanalysis.com/list/mexican-stock-exchange/', 'Bolsa Mexicana de Valores', 'BMV', 'MX', 'Mexican Stock Exchange', 'Mexico', 'MXN', 'XMEX', 'low'],
  ['https://stockanalysis.com/list/bursa-malaysia/', 'Bursa Malaysia', 'KLSE', 'KL', 'Bursa Malaysia', 'Malaysia', 'MYR', 'XKLS', 'low'],
  ['https://stockanalysis.com/list/namibian-stock-exchange/', 'Namibian Stock Exchange', 'NMSE', None, 'Namibian Stock Exchange', 'Namibia', 'NAD', 'XNAM', 'low'],
  ['https://stockanalysis.com/list/nigerian-stock-exchange/', 'Nigerian Stock Exchange', 'NGX', None, 'Nigerian Stock Exchange', 'Nigeria', 'NGN', 'XNSA', 'low'],
  ['https://stockanalysis.com/list/new-zealand-stock-exchange/', 'NZX', 'NZX', 'NZ', 'New Zealand Stock Exchange', 'New Zealand', 'NZD', 'XNZE', 'low'],
  ['https://stockanalysis.com/list/muscat-securities-market/', 'Muscat Securities Market', 'MSM', None, 'Muscat Securities Market', 'Oman', 'OMR', 'XMUS', 'low'],
  ['https://stockanalysis.com/list/lima-stock-exchange/', 'Bolsa de Valores de Lima', 'BVL', None, 'Lima Stock Exchange', 'Peru', 'PEN', 'XLIM', 'low'],
  ['https://stockanalysis.com/list/philippine-stock-exchange/', 'Philippine Stock Exchange', 'PSE', 'PS', 'Philippine Stock Exchange', 'Philippines', 'PHP', 'XPHS', 'low'],
  ['https://stockanalysis.com/list/pakistan-stock-exchange/', 'Pakistan Stock Exchange', 'PSX', None, 'Pakistan Stock Exchange', 'Pakistan', 'PKR', 'XKAR', 'low'],
  ['https://stockanalysis.com/list/qatar-stock-exchange/', 'Qatar Stock Exchange', 'QSE', 'QA', 'Qatar Stock Exchange', 'Qatar', 'QAR', 'DSMD', 'low'],
  ['https://stockanalysis.com/list/moscow-stock-exchange/', 'Moscow Exchange', 'MOEX', None, 'Moscow Stock Exchange', 'Russia', 'RUB', 'MISX', 'low'],
  ['https://stockanalysis.com/list/saudi-stock-exchange/', 'Tadawul', 'TADAWUL', 'SAU', 'Saudi Stock Exchange', 'Saudi Arabia', 'SAR', 'XSAU', 'low'],
  ['https://stockanalysis.com/list/singapore-exchange/', 'Singapore Exchange Catalist', 'SGXC', 'SI', 'Singapore Exchange - Catalist', 'Singapore', 'SGD', 'XSCA', 'low'],
  ['https://stockanalysis.com/list/singapore-exchange/', 'Singapore Exchange', 'SGX', 'SI', 'Singapore Exchange', 'Singapore', 'SGD', 'XSES', 'low'],
  ['https://stockanalysis.com/list/stock-exchange-of-thailand/', 'SET', 'BKK', 'BK', 'Stock Exchange of Thailand', 'Thailand', 'THB', 'XBKK', 'low'],
  ['https://stockanalysis.com/list/tunis-stock-exchange/', 'Bourse de Tunis', 'BVMT', None, 'Tunis Stock Exchange', 'Tunisia', 'TND', 'XTUN', 'low'],
  ['https://stockanalysis.com/list/borsa-istanbul/', 'Borsa Istanbul', 'BIST', 'IS', 'Istanbul Stock Exchange', 'Turkey', 'TRY', 'XIST', 'low'],
  ['https://stockanalysis.com/list/taipei-exchange/', 'Taipei Exchange', 'TPEX', 'TWO', 'Taipei Exchange', 'Taiwan', 'TWD', 'ROCO', 'low'],
  ['https://stockanalysis.com/list/taiwan-stock-exchange/', 'Taiwan Stock Exchange', 'TPE', 'TW', 'Taiwan Stock Exchange', 'Taiwan', 'TWD', 'XTAI', 'low'],
  ['https://stockanalysis.com/list/tanzania-stock-exchange/', 'Dar es Salaam Stock Exchange', 'DAR', None, 'Tanzania Stock Exchange', 'Tanzania', 'TZS', 'XDAR', 'low'],
  ['https://stockanalysis.com/list/pfts-stock-exchange/', 'PFTS', 'UKR', None, 'PFTS Stock Exchange', 'Ukraine', 'UAH', 'PFTS', 'low'],
  ['https://stockanalysis.com/list/uganda-securities-exchange/', 'Uganda Securities Exchange', 'UGSE', None, 'Uganda Securities Exchange', 'Uganda', 'UGX', 'XUGA', 'low'],
  ['https://stockanalysis.com/list/caracas-stock-exchange/', 'Bolsa de Valores de Caracas', 'CCSE', 'CR', 'Caracas Stock Exchange', 'Venezuela', 'VES', 'XCAR', 'low'],
  ['https://stockanalysis.com/list/ho-chi-minh-stock-exchange/', 'Ho Chi Minh Stock Exchange', 'HOSE', 'VN', 'Ho Chi Minh Stock Exchange', 'Vietnam', 'VND', 'XSTC', 'low'],
  ['https://stockanalysis.com/list/ivory-coast-stock-exchange/', 'Bourse Régionale des Valeurs Mobilières', 'BRVM', None, 'Ivory Coast Stock Exchange', 'Ivory Coast', 'XOF', 'XBRV', 'low'],
  ['https://stockanalysis.com/list/johannesburg-stock-exchange/', 'Johannesburg Stock Exchange', 'JSE', 'JO', 'Johannesburg Stock Exchange', 'South Africa', 'ZAR', 'XJSE', 'low'],
  ['https://stockanalysis.com/list/lusaka-stock-exchange/', 'Lusaka Securities Exchange', 'LUSE', None, 'Lusaka Stock Exchange', 'Zambia', 'ZMW', 'XLUS', 'low'],
  ['https://stockanalysis.com/list/zimbabwe-stock-exchange/', 'Zimbabwe Stock Exchange', 'ZMSE', None, 'Zimbabwe Stock Exchange', 'Zimbabwe', 'ZWL', 'XZIM', 'low'],
  ['https://stockanalysis.com/list/hong-kong-stock-exchange/', 'Hong Kong Stock Exchange', 'HKEX', 'HK', 'Hong Kong Stock Exchange', 'Hong Kong', 'HKD', 'XHKG', 'medium'],
  ['https://stockanalysis.com/list/sapporo-stock-exchange/', 'Sapporo Stock Exchange', 'SPSE', None, 'Sapporo Stock Exchange', 'Japan', 'JPY', 'XSAP', 'medium'],
  ['https://stockanalysis.com/list/fukuoka-stock-exchange/', 'Fukuoka Stock Exchange', 'FKSE', None, 'Fukuoka Stock Exchange', 'Japan', 'JPY', 'XFKA', 'medium'],
  ['https://stockanalysis.com/list/tokyo-stock-exchange/', 'Tokyo Stock Exchange', 'TSE', 'T', 'Tokyo Stock Exchange', 'Japan', 'JPY', 'XTKS', 'medium'],
  ['https://stockanalysis.com/list/nagoya-stock-exchange/', 'Nagoya Stock Exchange', 'XNGO', None, 'Nagoya Stock Exchange', 'Japan', 'JPY', 'XNGO', 'medium'],
  ['https://stockanalysis.com/list/ghana-stock-exchange/', '', '', None, '', '', '', '', ''],
  ['https://stockanalysis.com/list/hanoi-stock-exchange/', '', '', None, '', '', '', '', ''],
  ['https://stockanalysis.com/list/munich-stock-exchange/', '', '', None, '', '', '', '', ''],
  ['https://stockanalysis.com/list/spotlight-stock-market/', '', '', None, '', '', '', '', ''],
]
EXCHANGE_MAPPINGS = [
  dict(zip(EXCHANGE_MAPPING_HEADERS, row))
  for row in EXCHANGE_MAPPING_ROWS
]

def _normalize_exchange_url(url: str) -> str:
    return url.rstrip("/")

def _exchange_metadata_keys() -> list[str]:
    keys: list[str] = []
    for entry in EXCHANGE_MAPPINGS:
        for key in entry.keys():
            if key == "url":
                continue
            if key not in keys:
                keys.append(key)
    return keys


EXCHANGE_BY_URL = {
    _normalize_exchange_url(entry["url"]): entry
    for entry in EXCHANGE_MAPPINGS
    if entry.get("url")
}

EXCHANGE_SCHEMA_FIELDS = [
    "exchange_name",
    "country",
    "market_identifier_code",
    "currency",
    "stock_count",
    "url",
    "capture_datetime",
    "exchange_abbreviation",
    "exchange_name_local_language",
    "trade_accessibility",
    "yahoo_suffix",
]
EXCHANGE_SCHEMA_DDL = """
    CREATE TABLE IF NOT EXISTS `{table_id}` (
      exchange_name STRING,
      country STRING,
      market_identifier_code STRING,
      currency STRING,
      stock_count STRING,
      url STRING,
      capture_datetime STRING,
      exchange_abbreviation STRING,
      exchange_name_local_language STRING,
      trade_accessibility STRING,
      yahoo_suffix STRING
    )
"""
EXCHANGE_BQ_SCHEMA = [
    bigquery.SchemaField("exchange_name", "STRING"),
    bigquery.SchemaField("country", "STRING"),
    bigquery.SchemaField("market_identifier_code", "STRING"),
    bigquery.SchemaField("currency", "STRING"),
    bigquery.SchemaField("stock_count", "STRING"),
    bigquery.SchemaField("url", "STRING"),
    bigquery.SchemaField("capture_datetime", "STRING"),
    bigquery.SchemaField("exchange_abbreviation", "STRING"),
    bigquery.SchemaField("exchange_name_local_language", "STRING"),
    bigquery.SchemaField("trade_accessibility", "STRING"),
    bigquery.SchemaField("yahoo_suffix", "STRING"),
]
STOCK_SCHEMA_FIELDS = [
    "row_no",
    "symbol",
    "yf_symbol",
    "company_name",
    "market_cap",
    "stock_price",
    "percent_change",
    "revenue",
    "url",
    "capture_datetime",
]
STOCK_SCHEMA_DDL = """
    CREATE TABLE IF NOT EXISTS `{table_id}` (
      row_no STRING,
      symbol STRING,
      yf_symbol STRING,
      company_name STRING,
      market_cap STRING,
      stock_price STRING,
      percent_change STRING,
      revenue STRING,
      url STRING,
      capture_datetime STRING
    )
"""
STOCK_BQ_SCHEMA = [
    bigquery.SchemaField("row_no", "STRING"),
    bigquery.SchemaField("symbol", "STRING"),
    bigquery.SchemaField("yf_symbol", "STRING"),
    bigquery.SchemaField("company_name", "STRING"),
    bigquery.SchemaField("market_cap", "STRING"),
    bigquery.SchemaField("stock_price", "STRING"),
    bigquery.SchemaField("percent_change", "STRING"),
    bigquery.SchemaField("revenue", "STRING"),
    bigquery.SchemaField("url", "STRING"),
    bigquery.SchemaField("capture_datetime", "STRING"),
]


EXCHANGES_URL = "https://stockanalysis.com/list/exchanges/"
NEXT_ICON_D = (
    "M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 "
    "011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
)
TABLE_ID = "main-table"
OUTPUT_CSV = "otc_stocks.csv"

CONSENT_XPATHS = [
    (
        "//p[contains(@class, 'fc-button-label') "
        "and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
        "'consent')]/ancestor::button[1]"
    ),
    (
        "//button["
        "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') "
        "or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree') "
        "or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'consent')"
        "]"
    ),
]


class StockAnalysisExchangeScraper(PaginatedTableScraper):
    def __init__(self) -> None:
        super().__init__(
            table_id=TABLE_ID,
            next_icon_d=NEXT_ICON_D,
            consent_xpaths=CONSENT_XPATHS,
            page_url_field="page_url",
            skip_signature_headers={"page_url"},
        )


def _normalize_headers(headers: list[str], expected_len: int) -> list[str]:
    normalized = []
    for idx, header in enumerate(headers, start=1):
        normalized.append(header or f"Column_{idx}")
    while len(normalized) < expected_len:
        normalized.append(f"Column_{len(normalized) + 1}")
    if len(normalized) > expected_len:
        normalized = normalized[:expected_len]
    return normalized


def print_page_head(headers: list[str], page_rows: list[dict], label: str, rows: int = 5) -> None:
    print(f"{label} headers: {headers}")
    for index, row in enumerate(page_rows[:rows], start=1):
        cells = [row.get(header, "") for header in headers]
        print(f"{label} row {index}: {cells}")


def _normalize_table_id(table_id: str, project: str | None) -> str:
    dot_count = table_id.count(".")
    if dot_count == 2:
        return table_id
    if dot_count == 1:
        if not project:
            raise ValueError("Project is required when table_id is dataset.table")
        return f"{project}.{table_id}"
    raise ValueError("table_id must be dataset.table or project.dataset.table")


def _stocks_table_id(table_id: str) -> str:
    parts = table_id.split(".")
    if len(parts) != 3:
        raise ValueError("table_id must be project.dataset.table")
    return f"{parts[0]}.{parts[1]}.stocks"


def _build_yf_symbol(row: pd.Series) -> str:
    symbol = str(row.get("symbol") or "").strip()
    if not symbol:
        return ""
    url = str(row.get("url") or row.get("page_url") or "").strip()
    if not url:
        return symbol
    metadata = EXCHANGE_BY_URL.get(_normalize_exchange_url(url))
    if not metadata:
        return symbol
    suffix = metadata.get("yahoo_suffix")
    if not suffix:
        return symbol
    return f"{symbol}.{suffix}"


def _add_page_url(headers: list[str], rows: list[dict], page_url: str) -> list[str]:
    if "page_url" not in headers:
        headers = headers + ["page_url"]
    for row in rows:
        row["page_url"] = page_url
    return headers


def enrich_rows_with_exchange_metadata(
    rows: list[dict], stock_count_by_url: dict[str, str]
) -> None:
    for row in rows:
        url = (row.get("page_url") or row.get("url") or "").strip()
        if not url:
            continue
        normalized_url = _normalize_exchange_url(url)
        metadata = EXCHANGE_BY_URL.get(normalized_url)
        if not metadata:
            continue
        for key, value in metadata.items():
            if key == "url":
                continue
            if row.get(key) in ("", None):
                row[key] = value
        if row.get("url") in ("", None):
            row["url"] = url
        if row.get("stock_count") in ("", None):
            stock_count = stock_count_by_url.get(normalized_url, "")
            if stock_count:
                row["stock_count"] = stock_count


def _normalize_bq_columns(headers: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: dict[str, int] = {}
    for header in headers:
        if header == "No.":
            name = "row_no"
        elif header == "% Change":
            name = "percent_change"
        elif header == "Stock Price":
            name = "stock_price"
        elif header == "Company Name":
            name = "company_name"
        elif header == "Market Cap":
            name = "market_cap"
        elif header == "Symbol":
            name = "symbol"
        elif header == "Revenue":
            name = "revenue"
        else:
            name = re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")
        if not name:
            name = "col"
        if name[0].isdigit():
            name = f"col_{name}"
        count = seen.get(name, 0)
        if count:
            name = f"{name}_{count + 1}"
        seen[name] = count + 1
        normalized.append(name)
    return normalized


def _fetch_html(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _extract_exchange_urls(html: str) -> list[str]:
    table_match = re.search(
        r'<div[^>]+class=["\'][^"\']*table-wrap[^"\']*["\'][^>]*>.*?(<table[^>]*>.*?</table>)',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not table_match:
        return []
    table_html = table_match.group(1)
    hrefs = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', table_html, flags=re.IGNORECASE)
    urls = []
    seen = set()
    for href in hrefs:
        if not href.startswith("/list/"):
            continue
        full_url = urljoin(EXCHANGES_URL, href)
        if full_url not in seen:
            seen.add(full_url)
            urls.append(full_url)
    return urls


def _df_headers(df: pd.DataFrame) -> list[str]:
    headers = [str(col).strip() for col in df.columns]
    return _normalize_headers(headers, len(headers))


def _df_rows(headers: list[str], df: pd.DataFrame) -> list[dict]:
    rows = []
    for _, row in df.iterrows():
        record = {}
        for header in headers:
            value = row.get(header, "")
            record[header] = "" if pd.isna(value) else str(value).strip()
        rows.append(record)
    return rows


def _merge_headers(existing: list[str], new_headers: list[str]) -> list[str]:
    for header in new_headers:
        if header not in existing:
            existing.append(header)
    return existing


def fetch_exchanges_list() -> tuple[pd.DataFrame, list[str]]:
    html = _fetch_html(EXCHANGES_URL)
    tables = pd.read_html(io.StringIO(html))
    if not tables:
        raise ValueError("No exchanges table found.")
    df = tables[0]
    urls = _extract_exchange_urls(html)
    return df, urls


def _build_stock_count_by_url(rows: list[dict]) -> dict[str, str]:
    counts: dict[str, int] = {}
    for row in rows:
        url = (row.get("page_url") or row.get("url") or "").strip()
        if not url:
            continue
        normalized_url = _normalize_exchange_url(url)
        counts[normalized_url] = counts.get(normalized_url, 0) + 1
    return {url: str(count) for url, count in counts.items()}


def _parse_urls(value: str) -> list[str]:
    urls = [item.strip() for item in value.split() if item.strip()]
    return urls


def _normalize_urls(urls: list[str]) -> list[str]:
    return [_normalize_exchange_url(url) for url in urls]


def _write_results(
    all_rows: list[dict],
    headers: list[str],
    table_id: str,
    project: str | None,
    write_disposition: str,
    bq_credentials: object | None,
) -> None:
    stock_count_by_url = _build_stock_count_by_url(all_rows)
    metadata_keys = _exchange_metadata_keys()
    headers = _merge_headers(headers, metadata_keys)
    headers = _merge_headers(headers, ["url"])
    enrich_rows_with_exchange_metadata(all_rows, stock_count_by_url)
    headers = _merge_headers(headers, ["capture_datetime"])
    capture_datetime = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    for row in all_rows:
        row["capture_datetime"] = capture_datetime
    df = pd.DataFrame(all_rows, columns=headers)
    bq_headers = _normalize_bq_columns(headers)
    df.columns = bq_headers
    for field in EXCHANGE_SCHEMA_FIELDS:
        if field not in df.columns:
            df[field] = ""
    exchange_rows: dict[str, dict] = {}
    for _, row in df.iterrows():
        url = str(row.get("url") or row.get("page_url") or "").strip()
        if not url:
            continue
        exchange_row = exchange_rows.get(url)
        if not exchange_row:
            exchange_row = {field: "" for field in EXCHANGE_SCHEMA_FIELDS}
            exchange_row["url"] = url
            exchange_rows[url] = exchange_row
        for field in EXCHANGE_SCHEMA_FIELDS:
            if field == "stock_count":
                continue
            value = row.get(field, "")
            if exchange_row.get(field) in ("", None) and value not in ("", None):
                exchange_row[field] = value
        exchange_row["stock_count"] = str(
            int(exchange_row.get("stock_count", "0") or "0") + 1
        )
    df_exchange = pd.DataFrame(exchange_rows.values(), columns=EXCHANGE_SCHEMA_FIELDS)
    for field in STOCK_SCHEMA_FIELDS:
        if field not in df.columns:
            df[field] = ""
    df["yf_symbol"] = df.apply(_build_yf_symbol, axis=1)
    df_stocks = df[STOCK_SCHEMA_FIELDS].copy()
    print("Stock counts by url:")
    for url, count in sorted(stock_count_by_url.items()):
        print(f"  {url}: {count}")
    load_dataframe_to_bigquery(
        df_exchange,
        table_id=table_id,
        project=project,
        write_disposition=write_disposition,
        ddl=EXCHANGE_SCHEMA_DDL,
        schema=EXCHANGE_BQ_SCHEMA,
        empty_message="No rows to write to BigQuery.",
        credentials=bq_credentials,
    )
    stocks_table_id = _stocks_table_id(table_id)
    load_dataframe_to_bigquery(
        df_stocks,
        table_id=stocks_table_id,
        project=project,
        write_disposition=write_disposition,
        ddl=STOCK_SCHEMA_DDL,
        schema=STOCK_BQ_SCHEMA,
        empty_message="No stock rows to write to BigQuery.",
        credentials=bq_credentials,
    )


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    raise ValueError("headless must be true/false or 1/0")


def _get_bq_credentials() -> tuple[object | None, str | None]:
    if secret_helper is None or Variable is None:
        return None, None
    resource = secret_helper.get_secret_resource(
        BQ_SECRET_RESOURCE_VAR, DEFAULT_BQ_SECRET_RESOURCE
    )
    sa_info = secret_helper.fetch_service_account_json(resource)
    credentials = service_account.Credentials.from_service_account_info(sa_info)
    project_id = sa_info.get("project_id")
    return credentials, project_id


def main(
    urls_arg: str | None = None,
    skip_urls_arg: str | None = None,
    table_id_arg: str | None = None,
    dataset_arg: str | None = None,
    project_arg: str | None = None,
    write_disposition_arg: str | None = None,
    headless_arg: bool | None = None,
) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--urls",
        required=urls_arg is None,
        help="Whitespace-separated exchange URLs or 'all' to process everything.",
    )
    parser.add_argument(
        "--skip-urls",
        default=skip_urls_arg or "",
        help="Whitespace-separated exchange URLs to skip.",
    )
    parser.add_argument(
        "--table-id",
        required=table_id_arg is None,
        help="Target table ID: dataset.table or project.dataset.table",
    )
    parser.add_argument(
        "--dataset",
        default=dataset_arg or "",
        help="Dataset name (used if table-id is omitted).",
    )
    parser.add_argument(
        "--project",
        default=project_arg or os.environ.get("GCP_PROJECT_ID"),
        help="GCP project ID (used if table-id omits project).",
    )
    parser.add_argument(
        "--write-disposition",
        default=write_disposition_arg or "WRITE_APPEND",
        choices=["WRITE_TRUNCATE", "WRITE_APPEND"],
        help="BigQuery write disposition. Default: WRITE_APPEND",
    )
    parser.add_argument(
        "--headless",
        type=_parse_bool,
        default=headless_arg,
        help="Run browser headless (true/false).",
    )
    args = parser.parse_args([] if urls_arg or table_id_arg else None)
    raw_urls = urls_arg if urls_arg is not None else args.urls
    raw_skip_urls = skip_urls_arg if skip_urls_arg is not None else args.skip_urls
    if not raw_urls:
        raise ValueError("urls is required (whitespace-separated URLs or 'all').")
    urls_input = raw_urls.strip()
    skip_urls = set(_normalize_urls(_parse_urls(raw_skip_urls))) if raw_skip_urls else set()

    table_id_value = table_id_arg if table_id_arg is not None else args.table_id
    dataset_value = dataset_arg if dataset_arg is not None else args.dataset
    if not table_id_value:
        if not dataset_value:
            raise ValueError("table-id or dataset is required.")
        if not args.project:
            raise ValueError("project is required when dataset is provided without table-id.")
        table_id_value = f"{args.project}.{dataset_value}.exchanges"
    bq_credentials, bq_project = _get_bq_credentials()
    if not args.project and bq_project:
        args.project = bq_project
    table_id = _normalize_table_id(table_id_value, args.project)
    exchanges_df, exchange_urls = fetch_exchanges_list()
    ex_headers = _df_headers(exchanges_df)
    ex_rows = _df_rows(ex_headers, exchanges_df)
    print_page_head(ex_headers, ex_rows, "Exchanges Head")
    print_page_head(ex_headers, list(reversed(ex_rows)), "Exchanges Tail")
    print(f"Exchange URLs: {len(exchange_urls)}")

    all_rows: list[dict] = []
    headers: list[str] = []
    write_per_url = False
    if args.headless is not None:
        os.environ["HEADLESS"] = "1" if args.headless else "0"
    driver = None
    try:
        if urls_input.lower() == "all":
            urls_to_process = [
                url
                for url in exchange_urls
                if _normalize_exchange_url(url) not in skip_urls
            ]
            write_per_url = True
            reset_driver_per_url = True
        else:
            urls_to_process = _parse_urls(urls_input)
            if skip_urls:
                urls_to_process = [
                    url
                    for url in urls_to_process
                    if _normalize_exchange_url(url) not in skip_urls
                ]
            invalid = [url for url in urls_to_process if url not in exchange_urls]
            if invalid:
                raise ValueError(f"Invalid exchange URLs: {invalid}")
            reset_driver_per_url = False
        if skip_urls:
            print(f"Skipping {len(skip_urls)} exchange URLs.")
        if write_per_url:
            print("Running per-exchange mode for urls=all.")
        first_write = True
        for url in urls_to_process:
            if write_per_url:
                all_rows = []
                headers = []
            scraper = StockAnalysisExchangeScraper()
            print(f"Scraping exchange: {url}")
            if reset_driver_per_url or driver is None:
                if driver is not None:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                driver = scraper.build_driver()
            attempts = 0
            while True:
                try:
                    page_headers, page_rows = scraper.scrape_with_driver(driver, url)
                    headers = _merge_headers(headers, page_headers)
                    all_rows.extend(page_rows)
                    break
                except Exception as exc:
                    attempts += 1
                    if attempts > 1:
                        print(f"Skipping exchange {url} after driver error: {exc}")
                        break
                    try:
                        if driver is not None:
                            driver.quit()
                    except Exception:
                        pass
                    driver = scraper.build_driver()
            if reset_driver_per_url and driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = None
            if write_per_url:
                if all_rows:
                    write_disposition = args.write_disposition
                    if write_disposition == "WRITE_TRUNCATE" and not first_write:
                        write_disposition = "WRITE_APPEND"
                    _write_results(
                        all_rows,
                        headers,
                        table_id=table_id,
                        project=args.project,
                        write_disposition=write_disposition,
                        bq_credentials=bq_credentials,
                    )
                    first_write = False
                else:
                    print(f"No rows collected for {url}; skipping BigQuery write.")
        if not write_per_url:
            if all_rows:
                _write_results(
                    all_rows,
                    headers,
                    table_id=table_id,
                    project=args.project,
                    write_disposition=args.write_disposition,
                    bq_credentials=bq_credentials,
                )
            else:
                print("No rows collected; skipping BigQuery write.")
    finally:
        if driver is not None:
            driver.quit()



if __name__ == "__main__":
    main()


try:
    from airflow import DAG
    from airflow.providers.standard.operators.python import PythonOperator

    def _run_scrape(**kwargs) -> None:
        print(f"Airflow kwargs: {kwargs}")
        dag_run = kwargs.get("dag_run")
        params = kwargs.get("params") or {}
        urls_value = ""
        table_id_value = ""
        dataset_value = ""
        project_value = ""
        write_disposition_value = ""
        headless_value = ""
        if dag_run and dag_run.conf:
            urls_value = str(dag_run.conf.get("urls") or "")
            table_id_value = str(dag_run.conf.get("table_id") or "")
            dataset_value = str(dag_run.conf.get("dataset") or "")
            project_value = str(dag_run.conf.get("project") or "")
            write_disposition_value = str(dag_run.conf.get("write_disposition") or "")
            headless_value = str(dag_run.conf.get("headless") or "")
        if not urls_value:
            urls_value = str(params.get("urls") or "")
        if not table_id_value:
            table_id_value = str(params.get("table_id") or "")
        if not dataset_value:
            dataset_value = str(params.get("dataset") or "")
        if not project_value:
            project_value = str(params.get("project") or "")
        if not write_disposition_value:
            write_disposition_value = str(params.get("write_disposition") or "")
        if not headless_value:
            headless_value = str(params.get("headless") or "")
        skip_urls_value = ""
        if dag_run and dag_run.conf:
            skip_urls_value = str(dag_run.conf.get("skip_urls") or "")
        if not skip_urls_value:
            skip_urls_value = str(params.get("skip_urls") or "")
        if not urls_value:
            raise ValueError("Airflow param 'urls' is required.")
        if not table_id_value and not dataset_value:
            raise ValueError("Airflow param 'table_id' or 'dataset' is required.")
        headless_arg = None
        if headless_value:
            headless_arg = _parse_bool(headless_value)
        main(
            urls_arg=urls_value,
            skip_urls_arg=skip_urls_value or None,
            table_id_arg=table_id_value or None,
            dataset_arg=dataset_value or None,
            project_arg=project_value or None,
            write_disposition_arg=write_disposition_value or None,
            headless_arg=headless_arg,
        )

    with DAG(
        dag_id="manual_get_stocks_and_exchanges",
        description="Manual scrape for stockanalysis.com",
        schedule=None,
        start_date=datetime(2024, 1, 1),
        catchup=False,
        params={
            "urls": "https://stockanalysis.com/list/euronext-paris/",
            "table_id": "general-428410.src_dev.exchanges",
            "dataset": "src_dev",
            "project": "general-428410",
            "write_disposition": "WRITE_APPEND",
            "headless": "true",
            "skip_urls": "https://stockanalysis.com/list/otc-stocks/",
        },
        tags=["manual", "stocks"],
    ) as dag:
        PythonOperator(
            task_id="get_stocks_and_exchanges",
            python_callable=_run_scrape,
        )
except Exception:
    pass
