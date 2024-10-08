import requests
import os
import zipfile
import io
import csv
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = 'data' # Change this to create / use a different directory
START_DAY = "2024-09-01" # Adjust date in this same format as needed
END_DAY = "2024-09-20" # Adjust date in this same format as needed
INTERVALS = ["1m", "30m", "1h"] # Add or remove intervals as needed
OUTPUT_FORMAT = 'json'  # Change to 'csv' to save in CSV format
NUM_THREADS = 5  # Number of threads to use


def fetch_trading_symbols():
    """
    Fetch trading symbols from Binance Futures exchange.
    Returns a list of symbols that are currently trading.
    """
    url = 'https://fapi.binance.com/fapi/v1/exchangeInfo'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        symbols = [s['symbol'] for s in data.get('symbols', []) if s.get('status') == 'TRADING']
        logger.info(f"Fetched {len(symbols)} trading symbols.")
        return symbols
    except requests.RequestException as e:
        logger.error(f"Error fetching trading symbols: {e}")
        return []


def download_candle_data(symbols, start_day, end_day, interval):
    """
    Download candle data for the given symbols, date range, and interval.
    Returns the list of download items from Binance API.
    """
    url = 'https://www.binance.com/bapi/bigdata/v1/public/bigdata/finance/exchange/listDownloadData2'

    headers = {
        'Referer': 'https://www.binance.com/en/landing/data',
        'User-Agent': 'Mozilla/5.0',
        'Content-Type': 'application/json',
    }

    payload = {
        "bizType": "FUTURES_UM",
        "productName": "klines",
        "symbolRequestItems": [
            {
                "endDay": end_day,
                "granularityList": [interval],
                "interval": "daily",
                "startDay": start_day,
                "symbol": symbol
            } for symbol in symbols
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get('code') == "000000":
            download_items = data.get('data', {}).get('downloadItemList', [])
            logger.info(f"Successfully requested download links for {len(symbols)} symbols.")
            return download_items
        else:
            logger.error(f"Error fetching candle data: {data.get('message')}")
            return []
    except requests.RequestException as e:
        logger.error(f"HTTP request failed: {e}")
        return []


def process_download_item(download_item, interval):
    """
    Downloads and processes candle data from the given download item.
    Returns the processed data.
    """
    url = download_item.get('url')
    symbol = download_item.get('symbol')

    if not url or not symbol:
        logger.error("Invalid download item: missing 'url' or 'symbol'.")
        return None, None, None

    try:
        # Download the zip file
        response = requests.get(url)
        response.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(response.content))
    except requests.RequestException as e:
        logger.error(f"Failed to download data for {symbol}: {e}")
        return None, None, None
    except zipfile.BadZipFile as e:
        logger.error(f"Failed to unzip data for {symbol}: {e}")
        return None, None, None

    if OUTPUT_FORMAT.lower() == 'csv':
        # Return the zip file for later processing
        return symbol, interval, z
    elif OUTPUT_FORMAT.lower() == 'json':
        # Process the CSV files in the zip
        rows = []
        for file_name in z.namelist():
            with z.open(file_name) as csvfile:
                reader = csv.reader(io.TextIOWrapper(csvfile))
                headers = next(reader, None)  # Skip header
                for row in reader:
                    try:
                        formatted_row = [
                            int(row[0]),     # Open time
                            row[1],          # Open
                            row[2],          # High
                            row[3],          # Low
                            row[4],          # Close
                            row[5],          # Volume
                            int(row[6]),     # Close time
                            row[7],          # Quote asset volume
                            int(row[8]),     # Number of trades
                            row[9],          # Taker buy base asset volume
                            row[10],         # Taker buy quote asset volume
                            row[11]          # Ignore
                        ]
                        rows.append(formatted_row)
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Skipping invalid row in {symbol}: {e}")
                        continue
        if rows:
            logger.info(f"Processed data for {symbol} at interval {interval}.")
            return symbol, interval, rows
        else:
            logger.warning(f"No data rows found for {symbol}.")
            return None, None, None
    else:
        logger.error(f"Unsupported OUTPUT_FORMAT: {OUTPUT_FORMAT}")
        return None, None, None


def save_all_data(collected_data):
    """
    Saves all collected data to files.
    """
    if OUTPUT_FORMAT.lower() == 'json':
        for (symbol, interval), candles in collected_data.items():
            save_data_to_json(symbol, interval, candles)
    elif OUTPUT_FORMAT.lower() == 'csv':
        for (symbol, interval), zip_file in collected_data.items():
            save_csv_files(symbol, interval, zip_file)
    else:
        logger.error(f"Unsupported OUTPUT_FORMAT: {OUTPUT_FORMAT}")


def save_data_to_json(symbol, interval, candles):
    """
    Saves the candle data to a JSON file, combining with existing data if present.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    json_filename = os.path.join(DATA_DIR, f'{symbol}_{interval}.json')

    existing_data = []

    # Read existing data if the file exists
    if os.path.exists(json_filename):
        try:
            with open(json_filename, 'r') as jsonfile:
                existing_data = json.load(jsonfile)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON for {symbol} at interval {interval}: {e}")
            logger.info(f"Overwriting {json_filename} due to JSON decode error.")
            existing_data = []
        except Exception as e:
            logger.error(f"Unexpected error reading {json_filename}: {e}")
            existing_data = []

    # Combine and deduplicate data using open_time as the unique key
    combined_data = {candle[0]: candle for candle in existing_data}
    for candle in candles:
        combined_data[candle[0]] = candle

    # Convert back to list and sort
    combined_list = list(combined_data.values())
    combined_list.sort(reverse=True, key=lambda x: x[0])

    # Save back to the JSON file
    try:
        with open(json_filename, 'w') as jsonfile:
            json.dump(combined_list, jsonfile, indent=4)
        logger.info(f"Saved JSON data for {symbol} at interval {interval}.")
    except Exception as e:
        logger.error(f"Failed to save JSON for {symbol} at interval {interval}: {e}")


def save_csv_files(symbol, interval, zip_file):
    """
    Saves the CSV files from the zip file directly to the output directory.
    """
    # Create the directory structure: DATA_DIR/symbol/interval/
    output_dir = os.path.join(DATA_DIR, symbol, interval)
    os.makedirs(output_dir, exist_ok=True)

    for file_name in zip_file.namelist():
        try:
            # Read the file from the zip
            with zip_file.open(file_name) as source_file:
                content = source_file.read()

            # Save the file to the output directory
            output_file_path = os.path.join(output_dir, file_name)
            with open(output_file_path, 'wb') as output_file:
                output_file.write(content)

            logger.info(f"Saved CSV file {output_file_path}")
        except Exception as e:
            logger.error(f"Failed to save CSV file {file_name} for {symbol}: {e}")


def main():
    # Fetch ALL trading symbols
    # trading_symbols = fetch_trading_symbols() 

    # or just target the symbols like:
    trading_symbols = ['BTCUSDT', 'ETHUSDT']

    if not trading_symbols:
        logger.error("No trading symbols fetched. Exiting.")
        return

    # Loop through each interval
    for interval in INTERVALS:
        logger.info(f"Processing interval: {interval}")
        # Collect data for all symbols
        batch_symbols = []
        for symbol in trading_symbols:
            # Check if the data already exists
            if OUTPUT_FORMAT.lower() == 'json':
                data_filename = os.path.join(DATA_DIR, f'{symbol}_{interval}.json')
                if os.path.exists(data_filename):
                    logger.info(f"File {data_filename} already exists. Skipping download.")
                    continue
            elif OUTPUT_FORMAT.lower() == 'csv':
                # Assume data exists if the directory for the symbol and interval exists
                data_dir = os.path.join(DATA_DIR, symbol, interval)
                if os.path.exists(data_dir) and os.listdir(data_dir):
                    logger.info(f"Data for {symbol} at interval {interval} already exists. Skipping download.")
                    continue
            else:
                logger.error(f"Unsupported OUTPUT_FORMAT: {OUTPUT_FORMAT}")
                return

            batch_symbols.append(symbol)

        if not batch_symbols:
            continue  # Skip the fetch if all files exist

        # Download data for the batch of symbols
        download_items = download_candle_data(batch_symbols, START_DAY, END_DAY, interval)
        if not download_items:
            logger.error(f"No download items returned for symbols: {batch_symbols}")
            continue

        # Use ThreadPoolExecutor for multithreading
        collected_data = {}
        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = []
            for item in download_items:
                future = executor.submit(process_download_item, item, interval)
                futures.append(future)

            for future in as_completed(futures):
                symbol, interval_key, data = future.result()
                if symbol and interval_key and data:
                    key = (symbol, interval_key)
                    if OUTPUT_FORMAT.lower() == 'json':
                        if key not in collected_data:
                            collected_data[key] = []
                        collected_data[key].extend(data)
                    elif OUTPUT_FORMAT.lower() == 'csv':
                        collected_data[key] = data  # data is the zip file
                else:
                    logger.error("An error occurred during processing.")

        # Save all collected data
        save_all_data(collected_data)

    logger.info("Data fetching completed.")


if __name__ == "__main__":
    main()
