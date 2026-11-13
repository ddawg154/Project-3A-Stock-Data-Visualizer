
import os
import csv
import requests
import pygal
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request

app = Flask(__name__)

def load_stocks():
    stocks = []
    csv_path = Path(__file__).resolve().parent / 'stocks.csv'

    with open(csv_path, newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            stocks.append({
                'symbol': row['Symbol'],
                'name': row['Name']
            })

    return stocks


def generate_chart(symbol, chart_type, time_series, start, end):
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    if not api_key:
        raise ValueError("Alpha Vantage API key is missing.")

    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")

    if start_date > end_date:
        raise ValueError("Start date cannot be after end date.")

    functions = {
        "1": ("TIME_SERIES_INTRADAY", "Time Series (5min)"),
        "2": ("TIME_SERIES_DAILY", "Time Series (Daily)"),
        "3": ("TIME_SERIES_WEEKLY", "Weekly Time Series"),
        "4": ("TIME_SERIES_MONTHLY", "Monthly Time Series")
    }

    if time_series not in functions:
        raise ValueError("Invalid time series selected.")

    function, data_key = functions[time_series]

    params = {
        "function": function,
        "symbol": symbol,
        "apikey": api_key
    }

    if time_series == "1":
        params["interval"] = "5min"

    if time_series == "2":
        params["outputsize"] = "full"

    response = requests.get(
        "https://www.alphavantage.co/query",
        params=params,
        timeout=30
    )
    response.raise_for_status()
    data = response.json()

    if data_key not in data:
        raise ValueError(
            data.get("Information") or
            data.get("Note") or
            data.get("Error Message") or
            "No stock data available."
        )

    stock_data = []

    for date, values in data[data_key].items():
        current_date = datetime.strptime(date[:10], "%Y-%m-%d")

        if start_date <= current_date <= end_date:
            stock_data.append((
                date,
                float(values["1. open"]),
                float(values["2. high"]),
                float(values["3. low"]),
                float(values["4. close"])
            ))

    if not stock_data:
        raise ValueError("No stock data found for those dates.")

    stock_data.sort()

    dates, open_prices, high_prices, low_prices, close_prices = map(
        list, zip(*stock_data)
    )

    if chart_type == "bar":
        chart = pygal.Bar(x_label_rotation=45)
    elif chart_type == "line":
        chart = pygal.Line(x_label_rotation=45)
    else:
        raise ValueError("Invalid chart type.")

    chart.title = f"Stock Data for {symbol}: {start} to {end}"
    chart.x_labels = dates

    chart.add("Open", open_prices)
    chart.add("High", high_prices)
    chart.add("Low", low_prices)
    chart.add("Close", close_prices)

    return chart.render(is_unicode=True)


@app.route('/', methods=['GET', 'POST'])
def home():
    stocks = load_stocks()
    chart = None
    error = None

    if request.method == 'POST':
        symbol = request.form.get('symbol', '')
        chart_type = request.form.get('chart_type', '')
        time_series = request.form.get('time_series', '')
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')

        try:
            if symbol not in {stock['symbol'] for stock in stocks}:
                raise ValueError("Please select a valid stock.")

            chart = generate_chart(
                symbol, chart_type, time_series,
                start_date, end_date
            )
        except (ValueError, requests.RequestException) as e:
            error = str(e)

    return render_template(
        'index.html',
        stocks=stocks,
        chart=chart,
        error=error
    )


if __name__ == '__main__':
    app.run(debug=True)