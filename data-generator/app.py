import requests
import pandas as pd
import quandl
import math
import random
import os
import numpy as np
from sklearn import preprocessing, cross_validation, svm
from sklearn.linear_model import LinearRegression
from stocks import stocks
import psycopg2
import pprint
import json
pp = pprint.PrettyPrinter(indent=4)

def getStockData(stockSymbol):
    quandl.ApiConfig.api_key = "qWcicxSctVxrP9PhyneG"
    allData = quandl.get('WIKI/'+stockSymbol)
    dataLength = 251
    allDataLength = len(allData)
    firstDataElem = math.floor(random.random()*(allDataLength-dataLength))
    mlData = allData[0:firstDataElem+dataLength]

    def FormatForModel(dataArray):
        dataArray = dataArray[['Adj. Open', 'Adj. High', 'Adj. Low', 'Adj. Close', 'Adj. Volume']]
        dataArray['HL_PCT'] = (dataArray['Adj. High'] - dataArray['Adj. Close']) / dataArray['Adj. Close'] * 100.0
        dataArray['PCT_change'] = (dataArray['Adj. Close'] - dataArray['Adj. Open']) / dataArray['Adj. Open'] * 100.0
        dataArray = dataArray[['Adj. Close', 'HL_PCT', 'PCT_change','Adj. Volume']]
        dataArray.fillna(-99999, inplace=True)
        return dataArray

    mlData = FormatForModel(mlData)

    forecast_col = 'Adj. Close'
    forecast_out = int(math.ceil(0.12*dataLength))

    mlData['label'] = mlData[forecast_col].shift(-forecast_out)
    mlData.dropna(inplace=True)

    X = np.array(mlData.drop(['label'],1))
    X = preprocessing.scale(X)
    X_data = X[-dataLength:]
    X = X[:-dataLength]
    data = mlData[-dataLength:]
    mlData = mlData[:-dataLength]
    y = np.array(mlData['label'])

    X_train, X_test, y_train, y_test = cross_validation.train_test_split(X, y, test_size=0.3)

    clf = LinearRegression()
    clf.fit(X_train, y_train)
    accuracy = clf.score(X_test, y_test)

    prediction = clf.predict(X_data)
    data = data[['Adj. Close']]
    data = data.rename(columns={'Adj. Close':'EOD'})
    data['prediction'] = prediction[:]
    # pp.pprint(data)
    data = data.to_dict(orient='index')
    returnData = []
    for key, value in data.items():
        date = key.date()
        stringDate = str(date.month) + '/' + str(date.day) + '/' + str(date.year)
        returnData.append({"date": date, "EOD": value['EOD'], "prediction": value['prediction'], "stringDate":stringDate })
    returnData = sorted(returnData, key=lambda item: item['date'])
    for i, elem in enumerate(returnData):
        returnData[i]['date'] = returnData[i]['stringDate']
        del returnData[i]['stringDate']
        
    return json.dumps(returnData)

def insertStockData(stockList):
    delete_sql = "DELETE FROM stocks"
    sql = "INSERT INTO stocks(name, symbol, data) VALUES(%s, %s, %s)"

    try:
        conn = psycopg2.connect("dbname=stockit user=" + os.environ['DB_USERNAME'] +' password=' + os.environ['DB_PASSWORD'] + ' host=austintackaberry-stockit.c3tu2houar8w.us-west-1.rds.amazonaws.com')

        # create a new cursor
        cur = conn.cursor()
        cur.execute(delete_sql)
        # execute the INSERT statement
        cur.executemany(sql,stockList)
        # commit the changes to the database
        conn.commit()
        # close communication with the database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

stockData = []
for stock in stocks:
    stockTuple = stock['name'], stock['symbol'], getStockData(stock["symbol"])
    stockData.append(stockTuple)

# pp.pprint(stockData)
# pp.pprint(stockData)
insertStockData(stockData)
