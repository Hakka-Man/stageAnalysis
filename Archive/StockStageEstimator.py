from sklearn.base import BaseEstimator
from stage import getIndustryStage
import pandas as pd
import numpy as np
from datetime import timedelta
from sklearn.model_selection import train_test_split

## CONSTANTS
HOLDING = 0
TOTAL = 1

class StockStageEstimator(BaseEstimator):
    def __init__(self, paramList = [0.20, 1.39, 0.35, 0.93, 1.09, 1.22, 0.98, 0.98, 1.38, 0.99, -0.01, 0.97, 0.99, 0.96, 0.98], goodSectorDf = pd.DataFrame, sets = [[]]):
        self.paramList = paramList
        self.goodSectorDf = goodSectorDf
        self.returns = [[0,0],[0,0],[0,0],[0,0],[0,0],[0,0]]
        self.sets = pd.read_pickle("testSetPickle/trainSet.pkl")
        self.scores = [[0,0,0],[0,0,0]]
        # self.ratio = pd.read_pickle("testSetPickle/trainSetRatio.pkl")
    
    ## Calculate Returns base
    def evalFit(self, industries, goodSectorDf):
        transactionFit = pd.read_pickle("transactionTemplate.pkl")
        transactionFit['holding'] = np.empty((len(transactionFit), 0)).tolist()
        #print("Reach #1")
        for industry in industries:
            df = getIndustryStage(industry,self.paramList,goodSectorDf)
            symbol = industry[1]
            inStage = False
            buyTwice = False
            if df.empty:
                continue
            for index, element in df.iterrows():
                open = 0
                i = transactionFit.index.get_loc(index)
                if element.Stage == "Stage 2" or element.Stage == "Buy":
                    open = element.Close
                    #delete
                    transactionFit.iat[int(i),HOLDING].append((symbol,open,0))
                    if buyTwice:
                        transactionFit.iat[i, HOLDING].append((symbol,open,0))
                    if element.Stage == "Buy" and inStage:
                        transactionFit.iat[i, HOLDING].append((symbol,open,0))
                        buyTwice = True
                    inStage = True
                    continue
                if "Sell" == element.Stage[0:4]:
                    open = element.Close
                    transactionFit.iat[i, HOLDING].append((symbol,open,-1))
                    if buyTwice:
                        transactionFit.iat[i, HOLDING].append((symbol,open,-1))
                    inStage = False
                    buyTwice = False
        #print("Reach #2")
        total = 100
        first = True
        transactionFitCopy = transactionFit
        transactionFitCopy['total'] = 0
        transactionFitCopy.to_csv("onlyShare.csv")
        noBearishCount = 0
        #print("Reach #3")
        for index, element in transactionFitCopy.iterrows():
            indexNum = transactionFitCopy.index.get_loc(index)
            if first:
                first = False
                transactionFitCopy.iat[indexNum,1] = 100
                # print(i,transactionFitCopy.iat[i,1],"#1")
                continue
            if len(element.holding) == 0:
                transactionFitCopy.iat[indexNum,1] = transactionFitCopy.iat[indexNum-1,1]
                # print(i,transactionFitCopy.iat[i,1],"#2")
                continue
            else:
                noBearishCount = noBearishCount + 1
                prevData = transactionFitCopy.iat[indexNum-1, 0]
                if len(prevData):
                    total = 0
                    removeList = []
                    close = 0
                    for i in range(len(prevData)):
                        for j in range(len(element.holding)):
                            if element.holding[j][0] == prevData[i][0]:
                                close = element.holding[j][1]
                                if element.holding[j][2] == -1:
                                    removeList.append(element.holding[j])
                                break
                        total += close*prevData[i][2]
                    transactionFitCopy.iat[indexNum,1] = total
                    # print(i,transactionFitCopy.iat[indexNum,1],"#3")
                    for delete in removeList:
                        if delete in element.holding:
                            element.holding.remove(delete)
                else:
                    transactionFitCopy.iat[indexNum,1] = transactionFitCopy.iat[indexNum-1,1]
                    # print(i,transactionFitCopy.iat[i,1],"#4")
            if len(element.holding):
                allocation = total/len(element.holding)
            for i in range(len(element.holding)):
                element.holding[i] = (element.holding[i][0],element.holding[i][1],allocation/element.holding[i][1])
        stockHolding  = 0
        transactionFitCopy.to_csv("estimatorTest.csv")
        for i in transactionFitCopy.iterrows():
            stockHolding += len(i[1]['holding'])
        transactionFitCopy.to_pickle("transactionDfs/transactionDf"+str(self.paramList[0])+".pkl")
        transactionFitCopy = transactionFitCopy[transactionFitCopy.index - pd.to_datetime('1999-06-01') > timedelta(0)]
        dailyRet = transactionFitCopy.loc[:, 'total'].pct_change()
        dailyRet[dailyRet == 0] = 0.04/52
        excessRet = dailyRet - 0.04/52
        sharpeRatio = np.sqrt(52)*np.mean(excessRet) / np.std(excessRet)
        print(self.paramList)
        if transactionFitCopy.iloc[-1]['total'] != 100:
            transactionFitCopy.to_pickle('test.pkl')
        return transactionFitCopy.iloc[-1]['total'], sharpeRatio
        if noBearishCount == 0:
            return -1
        if noBearishCount != 0:
            print(stockHolding/noBearishCount)
        print(transactionFitCopy.iloc[-1]['total'])
        print(sharpeRatio)
        if (stockHolding/noBearishCount)<(len(industries)/1000) or transactionFitCopy.iat[-1,TOTAL]<=5000 or sharpeRatio < 0.5:
            return -1
        return transactionFitCopy.iloc[-1]['total'], sharpeRatio

    def fit(self):
        for i in range(3):
            setsCombined = np.concatenate((self.sets[(i+1)%3],self.sets[(i+2)%3]))
            self.returns[i*2] = self.evalFit(setsCombined, self.goodSectorDf)
            if self.returns[i*2] == -1:
                return -1
            self.returns[i*2+1] = self.evalFit(self.sets[i%4], self.goodSectorDf)
            if self.returns[i*2+1] == -1:
                return -1
        return 0
    
    def score(self):
        if self.fit() == -1:
            return -1
        for i in range(3):
            self.scores[0][i] = np.absolute(((self.returns[i*2][0])/100)**(1/22)-((self.returns[i*2+1][0])/100)**(1/22))
            self.scores[1][i] = max(self.returns[i*2][1], self.returns[i*2+1][1]) / min(self.returns[i*2][1], self.returns[i*2+1][1])
        return self.scores
    
    def result(self):
        totalReturn = 0
        totalSharpRatio = 0
        for i in range(6):
            totalReturn += self.returns[i][0]
            totalSharpRatio += self.returns[i][1]
        return [totalReturn/6,totalSharpRatio/6]
    def getReturns(self):
        return self.returns