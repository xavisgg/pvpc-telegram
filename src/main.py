#!/usr/bin/python3
import requests
import plotly.graph_objects as go
from datetime import date, timedelta, datetime
import sys
import json
from pvpc_api import PvpcPrices

#CONSTANTS
URL = 'https://api.telegram.org/bot'

#FUNCTIONS
def send_telegram_message(text_msg, bot_url, chat_id):

    url = bot_url + 'sendMessage'
    params = {'chat_id': chat_id, 'text': text_msg}
    response = requests.get(url, params=params)
    responseCode = str(response.status_code)

    return responseCode

def send_telegram_image(image_file_name, image_path, bot_url, chat_id):
    
    url = bot_url + 'sendPhoto'
    files = {'photo': (image_file_name, open(image_path, 'rb'))}
    params={'chat_id': chat_id}
    response = requests.post(url, params=params, files=files)
    responseCode = str(response.status_code)

    return responseCode

#MAIN

if len(sys.argv) > 1:
  try:
    target_date = datetime.strptime(sys.argv[1], '%Y-%m-%d')
  except:
      print("incorrect date format, use YYYY-MM-DD")
      sys.exit()
else:
  target_date = datetime.combine(datetime.today(), datetime.min.time()) + timedelta(days=1)

#1-Read setup from file to get the Telegram Token and the CHAT IDs to be notified
with open("./../data/setup.json", "r") as content:
  setup = json.load(content)

bot_url = URL + setup.get('BOT_TOKEN') + "/"
chat_ids = setup.get('CHAT_IDS')
api_token = setup.get('API_TOKEN')

if len(chat_ids) == 0:
  print("No bot chats registered, leaving process")
  sys.exit()

#2-Get price data
price_scraper = PvpcPrices(api_token, target_date)
data = price_scraper.get_data()
if data.size == 0:
  sys.exit()

#3-Prepare data visualization
fig = go.Figure(data=[go.Table(
  columnorder = [1,2,3,4,5],
  columnwidth = [80,100,40,80,100],
  header=dict(
    values=['<b>Hora</b>', '<b>Preu €/kWh</b>', '', '<b>Hora</b>', '<b>Preu €/kWh</b>' ],
    line_color='white', fill_color='white',
    align='center',font=dict(color='black', size=12)
  ),
  cells=dict(
    values=[data['Hour'][0:12], data['Price'][0:12], ['']*12, data['Hour'][12:24],data['Price'][12:24]],
    line_color=[data.Color[0:12], data.Color[0:12],['white']*12, data.Color[12:24], data.Color[12:24]], 
    fill_color=[data.Color[0:12], data.Color[0:12], ['white']*12, data.Color[12:24], data.Color[12:24]],
    align='center', font=dict(color='black', size=11)
    ))
                      
])

fig.write_image("./../img/fig1.png")

#4-Send Information to bot subscribers
#truncate HH:MM part
target_date = date(target_date.year, target_date.month, target_date.day)
text = "Preus de la llum pel dia " + str(target_date)
for chat_id in chat_ids:
    status_send = send_telegram_message(text, bot_url, chat_id)
    status_send = send_telegram_image("fig1.png", "./../img/fig1.png" , bot_url, chat_id) 