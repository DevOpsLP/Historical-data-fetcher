# Multithreaded Binance Data Fetcher Documentation

This guide will explain how to use the multithreaded Binance data fetcher, including installation instructions, usage, and an overview of the output data formats (JSON and CSV). Additionally, we will showcase examples of how the output data is formatted.

## Prerequisites

To use this script, you need to have Python installed (Python 3.7 or later is recommended). You also need to install the `requests` library, which is used for making HTTP requests to the Binance API.

### Installing Required Libraries

You can install the required library using `pip`:

```sh
pip install requests
```

## How to Use the Script

1. **Clone or download the script**: Copy the script to your local machine.

2. **Adjust the configuration**: You can modify the following variables at the top of the script to suit your requirements:

   - `DATA_DIR`: The directory where the fetched data will be saved.
   - `START_DAY` and `END_DAY`: The date range for fetching data in the format "YYYY-MM-DD".
   - `INTERVALS`: The time intervals for the candlestick data (e.g., `"1m"`, `"30m"`, `"1h"`).
   - `OUTPUT_FORMAT`: Set to `'json'` or `'csv'` depending on how you want the data saved.
   - `NUM_THREADS`: The number of threads to use for fetching data concurrently.

3. **Run the script**:

```sh
python app.py
```

The script will fetch data for the specified trading symbols and save it in the desired format (JSON or CSV).

### Important Variables

- **`trading_symbols`**: You can manually specify which symbols to fetch or use the `fetch_trading_symbols()` function to automatically get the list of available symbols from Binance.
- **`NUM_THREADS`**: Adjust this value based on your system's capability and the number of concurrent requests you want to make.

## Output Directory Structure

The script saves data in the `DATA_DIR` directory, organized by symbol and interval.

### JSON Output

For JSON output, the data will be saved in files named as `<symbol>_<interval>.json`. The directory structure looks like:

```
data/
  BTCUSDT_1m.json
  ETHUSDT_1m.json
  BTCUSDT_30m.json
  ETHUSDT_30m.json
  ...
```

### CSV Output

For CSV output, the data will be saved in folders for each symbol and interval, with each CSV file containing data for a specific date range.

```
data/
  BTCUSDT/
    1m/
      BTCUSDT-1m-2024-09-01.csv
      BTCUSDT-1m-2024-09-02.csv
      ...
    30m/
      BTCUSDT-30m-2024-09-01.csv
      ...
  ETHUSDT/
    1m/
      ETHUSDT-1m-2024-09-01.csv
      ETHUSDT-1m-2024-09-02.csv
      ...
```

## JSON Data Format Example

>[!NOTE]
>The candlestick data in **JSON** format is sorted from the **newest** to the **oldest**.

Below is an example of how the JSON data is formatted. Each entry represents a candlestick and is sorted from the newest candle to the oldest candle.

```json
[
  [
    1499040000000,      // Open time
    "0.01634790",       // Open
    "0.80000000",       // High
    "0.01575800",       // Low
    "0.01577100",       // Close
    "148976.11427815",  // Volume
    1499644799999,       // Close time
    "2434.19055334",    // Quote asset volume
    308,                // Number of trades
    "1756.87402397",    // Taker buy base asset volume
    "28.46694368",      // Taker buy quote asset volume
    "17928899.62484339" // Ignore
  ],
  ...
]
```

### Explanation of Fields:

- **Open time**: The start time of the candlestick in milliseconds since the Unix epoch.
- **Open, High, Low, Close**: Prices during the candlestick period.
- **Volume**: The trading volume.
- **Close time**: The end time of the candlestick.
- **Quote asset volume**: Volume in quote asset.
- **Number of trades**: The number of trades during the period.
- **Taker buy base asset volume**: Volume of buy orders executed by the taker.
- **Taker buy quote asset volume**: Volume of the quote asset bought by the taker.

## CSV Data Format Example

>[!NOTE]
>The candlestick data in **CSV** format is sorted from the **newest** to the **oldest**.

Below is an example of how the CSV data is formatted. Each row represents a candlestick, and the data is also sorted from the newest candle to the oldest candle.

```
open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore
1726444800000,59100.50,59182.20,58575.80,58641.70,15325.206,1726448399999,901113091.93640,193903,7713.277,453602861.02090,0
1726448400000,58641.60,58777.00,58396.50,58578.00,14942.560,1726451999999,875141904.08100,194610,7318.353,428703773.73460,0
```

### Explanation of Columns:

- **open\_time**: The start time of the candlestick in milliseconds since the Unix epoch.
- **open, high, low, close**: Prices during the candlestick period.
- **volume**: The trading volume.
- **close\_time**: The end time of the candlestick.
- **quote\_volume**: Volume in quote asset.
- **count**: The number of trades during the period.
- **taker\_buy\_volume**: Volume of buy orders executed by the taker.
- **taker\_buy\_quote\_volume**: Volume of the quote asset bought by the taker.
- **ignore**: Additional field, often set to zero.

## Notes

- **Concurrent Fetching**: The script uses multithreading to speed up data fetching. You can adjust `NUM_THREADS` to balance performance and system resource usage.
- **Data Consistency**: By collecting all data in memory first and writing it to files later, the script ensures data consistency and avoids file corruption.

Feel free to modify the script as per your needs and explore the Binance API to add more features. If you encounter any issues, check the log messages for details on errors or potential issues.

