import requests
import pandas as pd
import time
from datetime import date, timedelta, datetime
import numpy as np
from sklearn.cluster import KMeans
import numpy as np



class PvpcPrices():

    def __init__(self, api_token, target_date, geo_id=8741):
        #Initializes PvpcPrices object ():
        #https://api.esios.ree.es/indicators/1001?geo_ids[]=8741
        self.url = 'https://api.esios.ree.es/indicators/1001'
        self.token = api_token
        self.columns = ['Hour','Price','Group','Color']
        self.data = pd.DataFrame(columns=self.columns)
        self.target_date = target_date
        self.geo_id=geo_id


    def download_data(self):
        start_date = self.target_date - timedelta(hours=1)
        end_date = self.target_date + timedelta(hours=23)
        headers={'Accept': 'application/json; application/vnd.esios-api-v1+json',
                 'Accept-Encoding': 'gzip, deflate, sdch, br',
                 'Host' : 'api.esios.ree.es',
                 'Authorization': 'Token token=' + '"' + self.token + '"'}

        query= {'geo_ids[]':[self.geo_id],
                'start_date':start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'end_date':end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                }
        responseCode = ''
        timeout = 5
        response = ''
        retries = 0

        #Intentamos hasta 3 veces descargar la pagina
        while responseCode.startswith('2') == False and retries < 3:
            response = requests.get(self.url, headers=headers, params=query, timeout=timeout)
            responseCode = str(response.status_code)
            retries += 1
            timeout = timeout**2

        return response.json()

    def parse_response(self, response_json):
        columns = ['Hour','Price']
        df = pd.DataFrame(columns=columns)
        hourly_data = response_json.get('indicator').get('values')
        for value_dict in hourly_data:
            #Convert the price to €/kWh (provided in €/MWh)
            value = value_dict.get('value') / 1000
            #Limit value to 5 decimals
            value = round(value, 5)
            #drop time zone adjustments
            time_trunc = value_dict.get('datetime').split(".")[0]
            time = datetime.strptime(time_trunc, '%Y-%m-%dT%H:%M:%S')
            df = df.append({"Hour":time.strftime("%H:%Mh"),
                            "Price":value},ignore_index=True)
        return df

    def prepare_data(self, response_df):
        #Split prices in three groups: low, mid and high
        kmeans = KMeans(n_clusters=3, random_state=0).fit(response_df.Price.values.reshape(-1,1))
        low_price_group = kmeans.cluster_centers_.tolist().index(min(kmeans.cluster_centers_))
        high_price_group = kmeans.cluster_centers_.tolist().index(max(kmeans.cluster_centers_))
        mid_price_group = np.setdiff1d(kmeans.labels_,[low_price_group, high_price_group])[0]
        color_dict = {low_price_group:'green',
                      mid_price_group:'orange',
                      high_price_group:'red'}
        response_df['Group'] = kmeans.labels_
        response_df['Color'] = response_df['Group'].apply(lambda x: color_dict.get(x))
        return response_df

    def get_data(self):
        #Main function to download and parse the data
        #Initial log
        print("Iniciem el procés per extreure les dades de: " + \
        "'" + self.url + "'...")

        #Initialization of timer and local vars
        start_time = time.time()
        retries = 0

        raw_data = self.download_data()
        initial_df = self.parse_response(raw_data)

        #re-try if data is not available in the api yet
        while initial_df.size == 0 and retries < 5:
            raw_data = self.download_data()
            initial_df = self.parse_response(raw_data)
            retries+=1
            time.sleep(600 * retries)

        #transform data
        self.data = self.prepare_data(initial_df)

        return self.data