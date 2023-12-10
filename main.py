import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import requests
import numpy as np
import yfinance as yf
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from openai import OpenAI
from scipy.interpolate import interp1d


def get_company_name(ticker_symbol_name):
    ticker_name = yf.Ticker(ticker_symbol_name)
    info = ticker_name.info
    company_name = info.get('longName', None)
    return company_name
def on_button_click():
    start_process()


def start_process():
    Headers = {"x-api-key": ""}
    categorii = category_textbox.get("1.0", "end-1c").split(',')
    produse = products_textbox.get("1.0", "end-1c").split(',')
    industrie = industries_textbox.get("1.0", "end-1c").split(',')
    locatie = country_textbox.get("1.0", "end-1c")
    keywords_plus = keywords_textbox.get("1.0", "end-1c").split(',')
    keywords_minus = keywords_textbox_exclude.get("1.0", "end-1c").split(',')

    payload_nou = {
        "filters":
            {
                "and":
                    [
                    ]
            }
    }

    if categorii != ['']:
        payload_nou["filters"]["and"].append({"attribute": "company_category", "relation": "in", "value": categorii})
    if produse != ['']:
        payload_nou["filters"]["and"].append({"attribute": "company_products", "relation": "match_expression", "value":
            {
                "match": {"operator": "or", "operands": produse}
            }
                                              })
    if industrie != ['']:
        payload_nou["filters"]["and"].append({"attribute": "company_industry", "relation": "in", "value": industrie})
    if locatie:
        payload_nou["filters"]["and"].append(
            {"attribute": "company_location", "relation": "equals", "value": {"country": locatie}})
    keywords = {"attribute": "company_keywords", "relation": "match_expression", "value":
        {

        }
                }
    if keywords_plus != ['']:
        keywords["value"].update({"match": {"operator": "and", "operands": keywords_plus}})
    if keywords_minus != ['']:
        keywords["value"].update({"exclude": {"operator": "or", "operands": keywords_minus}})

    if keywords["value"] != {}:
        payload_nou["filters"]["and"].append(keywords)

    r = requests.post("https://data.veridion.com/search/v2/companies", headers=Headers, json=payload_nou)

    json = r.json()
    nume_companii = []
    try:
        while json["pagination"]["next"]:
            for companie in json["result"]:
                nume_companii.append(companie["company_name"].lower())
            # print(nume_companii)
            pagination_id = json["pagination"]["next"]
            # print(pagination_id)
            y = requests.post("https://data.veridion.com/search/v2/companies", headers=Headers, json=payload_nou,
                              params={'pagination_token': pagination_id})
            json = y.json()
            time.sleep(0.5)
    except:
        pass
    stock_prices = pd.read_csv("World-Stock-Prices-Dataset.csv")

    stock_prices.drop(["Dividends", "Stock Splits"], axis=1, inplace=True)
    ani_de_sters = [str(x + 2000) for x in range(18)]
    stock_prices = stock_prices[~stock_prices['Date'].str.contains('|'.join(ani_de_sters))]
    stock_prices = stock_prices.sort_values(by=['Ticker', 'Date'])
    stock_prices = stock_prices[stock_prices['Brand_Name'].isin(nume_companii)]

    ticker_array = stock_prices['Ticker'].unique()

    # risk free variable taken from the 3 month t-bill rate
    free_risk_rate = 0.0524

    # stock_prices['daily_return_rate']=(stock_prices['Close']-stock_prices['Open'])/(stock_prices['High']-stock_prices['Low'])
    stock_prices['daily_return_rate'] = np.where(
        (stock_prices['High'] - stock_prices['Low']) != 0,
        (stock_prices['Close'] - stock_prices['Open']) / (stock_prices['High'] - stock_prices['Low']),
        0
    )

    ticker_array_info = []

    for ticker in ticker_array:
        stock_prices_bit = stock_prices[stock_prices['Ticker'] == ticker]
        x_array = [x for x in range(len(stock_prices_bit))]
        y_array = stock_prices_bit['daily_return_rate']
        m, b = np.polyfit(x_array, y_array, 1)
        trend_line = [m * x + b for x in x_array]
        distances = [abs(y_array.iloc[i] - trend_line[i]) for i in range(len(y_array))]
        nr_years = len(stock_prices_bit) / 365
        yearly_profit = (stock_prices_bit['Close'].iloc[-1] - stock_prices_bit['Open'].iloc[0]) / (
                stock_prices_bit['Open'].iloc[0] * nr_years)
        if yearly_profit > 0:
            ticker_array_info.append((ticker, sum(distances) / len(distances), yearly_profit))
    print("Getting information about the recent news on your chosen company: ")
    print(get_news(get_company_name(ticker_array_info[0][0])))
    ticker_array_info.sort(key=lambda x: x[2], reverse=True)
    print(get_company_name(ticker_array_info[0][0]), " Risk: ", ticker_array_info[0][1], " Profit: ",ticker_array_info[0][2])
    stock_prices_bit = stock_prices[stock_prices['Ticker'] == ticker_array_info[0][0]]
    x_array = [x for x in range(len(stock_prices_bit))]
    y_array = stock_prices_bit['daily_return_rate']
    cubic_interp = interp1d(x_array, y_array, kind='cubic')
    x_smooth = np.linspace(0, len(stock_prices_bit) - 1)
    y_smooth = cubic_interp(x_smooth)
    plt.scatter(x_array, y_array)
    plt.plot(x_smooth, y_smooth, '-', color='red')
    plt.show()


def get_news(company):
    url = 'https://www.cnbc.com/search/?query='+company+'&qsearchterm='+company
    vector_stiri=[]
    # Function to wait for the page to load

    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run Chrome in headless mode (no GUI)

    # Create a new instance of the Chrome driver
    driver = webdriver.Chrome(options=chrome_options)

    # Navigate to the URL using Selenium
    driver.get(url)

    # Wait for the page to load (you might need to adjust the sleep time or use more sophisticated waiting techniques)
    time.sleep(17)

    # Get the page source after it has loaded
    page_source = driver.page_source

    # Close the Selenium-driven browser
    driver.quit()

    # Now you can use BeautifulSoup to parse the loaded HTML content
    soup = BeautifulSoup(page_source, 'html.parser')

    # Extract data from the loaded page using BeautifulSoup
    # For example, let's find all the links on the page
    links = soup.find_all('a', attrs={'class': 'resultlink'})
    contor_nr_articole_citite = 0
    new_links=[]
    for link in links:
        if link.text and contor_nr_articole_citite<3:
            new_links.append(link.get('href'))
            #print(link.get('href'))
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(str(link.get('href')))
            time.sleep(5)
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            article_title=soup.find('h1',attrs={'class':'ArticleHeader-headline'})
            #print(company,article_title.text)
            if company.lower() in article_title.text.lower():
                #print("a intrat")
                contor_nr_articole_citite+=1
                client = OpenAI(api_key="")
                stream = client.chat.completions.create(
                    model="gpt-4-1106-preview",
                    messages=[
                        {"role": "user", "content": article_title.text + "\nReview this headline and give a rating ranging from -100 to 100 on the impact this headline will have on the company, negative meaning bad impact and positive meaning good impact. Explain the rating in just a few words. IMPORTANT: first write the grade with the format 'Grade: your_grade'"}],
                    stream=True,
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        print(chunk.choices[0].delta.content,end="")
                print()
            driver.quit()

root = tk.Tk()
root.title("GUI")
width = 800
height = 600
root.geometry(f"{width}x{height}")
background_image = Image.open("images/background.jpg")
background_image = background_image.resize((width, height))
bk_image = ImageTk.PhotoImage(background_image)
background_label = tk.Label(root, image=bk_image)
background_label.place(x=0, y=0, relwidth=1, relheight=1)
root.resizable(False, False)
logo = tk.PhotoImage(file="images/logo.png")
root.iconphoto(False, logo)
big_logo = logo.subsample(3, 3)
photo_label = tk.Label(root, image=big_logo,bg="#22222e")
photo_label.pack()
category_label = tk.Label(root, text="Insert category here:", font=("Helvetica", 12, "bold"), bg="#22212f", fg="#ffffff")
category_label.pack()
category_textbox = tk.Text(root, height=1, width=20)
category_textbox.pack()
products_label = tk.Label(root, text="Insert products here:", font=("Helvetica", 12, "bold"), bg="#22212f", fg="#ffffff")
products_label.pack()
products_textbox = tk.Text(root, height=1, width=20)
products_textbox.pack()
industries_label = tk.Label(root, text="Insert industries here:", font=("Helvetica", 12, "bold"), bg="#22212f", fg="#ffffff")
industries_label.pack()
industries_textbox = tk.Text(root, height=1, width=20)
industries_textbox.pack()
country_label = tk.Label(root, text="Country:", font=("Helvetica", 12, "bold"), bg="#22212f", fg="#ffffff")
country_label.pack()
country_textbox = tk.Text(root, height=1, width=20)
country_textbox.pack()
keywords_label = tk.Label(root, text="Keywords to include\nSeparated by commas:", font=("Helvetica", 12, "bold"), bg="#22212f", fg="#ffffff")
keywords_label.pack()
keywords_textbox = tk.Text(root, height=1, width=20)
keywords_textbox.pack()
keywords_label_exclude = tk.Label(root, text="Keywords to exclude\nSeparated by commas:", font=("Helvetica", 12, "bold"), bg="#22212f", fg="#ffffff")
keywords_label_exclude.pack()
keywords_textbox_exclude = tk.Text(root, height=1, width=20)
keywords_textbox_exclude.pack()
button = tk.Button(root, text="Click me!", command=on_button_click)
button.pack()
root.mainloop()