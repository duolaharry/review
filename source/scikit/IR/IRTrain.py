# coding=gbk
import os
import time
from datetime import datetime
from math import sqrt

import pandas
from gensim import corpora, models

from source.config.projectConfig import projectConfig
from source.nlp.FleshReadableUtils import FleshReadableUtils
from source.nlp.SplitWordHelper import SplitWordHelper
from source.nltk import nltkFunction
from source.scikit.ML.MLTrain import MLTrain
from source.scikit.service.DataProcessUtils import DataProcessUtils
from source.utils.ExcelHelper import ExcelHelper
from source.utils.pandas.pandasHelper import pandasHelper


class IRTrain:
    """��Ϊ������Ϣ������reviewer�Ƽ�"""

    @staticmethod
    def testIRAlgorithm(project, dates):  # ���case, Ԫ������ܹ���ʱ����,���һ�������ڲ���
        """
           algorithm : ������Ϣ����
        """

        recommendNum = 5  # �Ƽ�����
        excelName = f'outputIR.xlsx'
        sheetName = 'result'

        """��ʼ��excel�ļ�"""
        ExcelHelper().initExcelFile(fileName=excelName, sheetName=sheetName, excel_key_list=['ѵ����', '���Լ�'])
        for date in dates:
            df = None
            startTime = datetime.now()
            for i in range(date[0] * 12 + date[1], date[2] * 12 + date[3] + 1):  # ��ֵ�������ƴ��
                y = int((i - i % 12) / 12)
                m = i % 12
                if m == 0:
                    m = 12
                    y = y - 1

                print(y, m)

                filename = projectConfig.getIRDataPath() + os.sep \
                           + f'IR_{project}_data_{y}_{m}_to_{y}_{m}.tsv'
                if df is None:
                    df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD)
                else:
                    temp = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD)
                    df = df.append(temp)  # �ϲ�

            df.reset_index(inplace=True, drop=True)
            """df��Ԥ����"""
            train_data, train_data_y, test_data, test_data_y = IRTrain.preProcess(df, date)

            """�����㷨����Ƽ��б�"""
            recommendList, answerList = IRTrain.RecommendByIR(train_data, train_data_y, test_data,
                                                              test_data_y, recommendNum=recommendNum)
            """�����Ƽ��б�������"""
            topk, mrr, precisionk, recallk, fmeasurek = \
                DataProcessUtils.judgeRecommend(recommendList, answerList, recommendNum)

            """���д��excel"""
            DataProcessUtils.saveResult(excelName, sheetName, topk, mrr, precisionk, recallk, fmeasurek, date)

            """�ļ��ָ�"""
            content = ['']
            ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())
            content = ['ѵ����', '���Լ�']
            ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())
            print("cost time:", datetime.now() - startTime)

    @staticmethod
    def preProcess(df, dates):
        """����˵��
         df����ȡ��dataframe����
         dates:��Ϊ���Ե�������Ԫ��
        """
        """ע�⣺ �����ļ����Ѿ�����������"""

        """����NAN"""
        df.fillna(value='', inplace=True)

        """��df���һ�б�ʶѵ�����Ͳ��Լ�"""
        df['label'] = df['pr_created_at'].apply(
            lambda x: (time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_year == dates[2] and
                       time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_mon == dates[3]))

        """�ȶ��������������� ֻ���¸���Ȥ������"""
        df = df[['pr_number', 'pr_title', 'pr_body', 'review_user_login', 'label']].copy(deep=True)

        print("before filter:", df.shape)
        df.drop_duplicates(inplace=True)
        print("after filter:", df.shape)
        """�������������ִ���"""
        DataProcessUtils.changeStringToNumber(df, ['review_user_login'])
        """�ȶ�tag�����"""
        tagDict = dict(list(df.groupby('pr_number')))
        """�ȳ���������Ϣ����һ��"""
        df = df[['pr_number', 'pr_title', 'pr_body', 'label']].copy(deep=True)
        df.drop_duplicates(inplace=True)
        df.reset_index(drop=True, inplace=True)

        """�����ռ������ı������ִ�"""
        stopwords = SplitWordHelper().getEnglishStopList()  # ��ȡͨ��Ӣ��ͣ�ô�

        textList = []
        for row in df.itertuples(index=True, name='Pandas'):
            tempList = []
            """��ȡpull request�ı���"""
            pr_title = getattr(row, 'pr_title')
            pr_title_word_list = [x for x in FleshReadableUtils.word_list(pr_title) if x not in stopwords]

            """����������ȡ�ʸ�Ч�������½��� ��������"""

            """�Ե�������ȡ�ʸ�"""
            pr_title_word_list = nltkFunction.stemList(pr_title_word_list)
            tempList.extend(pr_title_word_list)

            """pull request��body"""
            pr_body = getattr(row, 'pr_body')
            pr_body_word_list = [x for x in FleshReadableUtils.word_list(pr_body) if x not in stopwords]
            """�Ե�������ȡ�ʸ�"""
            pr_body_word_list = nltkFunction.stemList(pr_body_word_list)
            tempList.extend(pr_body_word_list)
            textList.append(tempList)

        print(textList.__len__())
        """�Էִ��б����ֵ� ����ȡ������"""
        dictionary = corpora.Dictionary(textList)
        print('�ʵ䣺', dictionary)

        feature_cnt = len(dictionary.token2id)
        print("�ʵ���������", feature_cnt)

        """���ݴʵ佨�����Ͽ�"""
        corpus = [dictionary.doc2bow(text) for text in textList]
        # print('���Ͽ�:', corpus)
        """���Ͽ�ѵ��TF-IDFģ��"""
        tfidf = models.TfidfModel(corpus)

        """�ٴα������ݣ��γ�������������ϡ��������ʽ"""
        wordVectors = []
        for i in range(0, df.shape[0]):
            wordVectors.append(dict(tfidf[dictionary.doc2bow(textList[i])]))

        """���Ѿ��еı������������ͱ�ǩ��ѵ�����Ͳ��Լ��Ĳ��"""

        trainData_index = df.loc[df['label'] == False].index
        testData_index = df.loc[df['label'] == True].index

        """ѵ����"""
        train_data = [wordVectors[x] for x in trainData_index]
        """���Լ�"""
        test_data = [wordVectors[x] for x in testData_index]
        """���Ϊ����"""
        train_data = DataProcessUtils.convertFeatureDictToDataFrame(train_data, featureNum=feature_cnt)
        test_data = DataProcessUtils.convertFeatureDictToDataFrame(test_data, featureNum=feature_cnt)
        train_data['pr_number'] = list(df.loc[df['label'] == False]['pr_number'])
        test_data['pr_number'] = list(df.loc[df['label'] == True]['pr_number'])

        """����ת��Ϊ���ǩ����
            train_data_y   [{pull_number:[r1, r2, ...]}, ... ,{}]
        """

        train_data_y = {}
        for pull_number in df.loc[df['label'] == False]['pr_number']:
            reviewers = list(tagDict[pull_number].drop_duplicates(['review_user_login'])['review_user_login'])
            train_data_y[pull_number] = reviewers

        test_data_y = {}
        for pull_number in df.loc[df['label'] == True]['pr_number']:
            reviewers = list(tagDict[pull_number].drop_duplicates(['review_user_login'])['review_user_login'])
            test_data_y[pull_number] = reviewers

        return train_data, train_data_y, test_data, test_data_y

    @staticmethod
    def RecommendByIR(train_data, train_data_y, test_data, test_data_y, recommendNum=5):
        """ʹ����Ϣ����  
           �����Ƕ��ǩ����
        """""

        recommendList = []  # �����case�Ƽ��б�
        answerList = []

        for targetData in test_data.itertuples():  # ��ÿһ��case���Ƽ�
            """itertuples ���д����е�ʱ�򷵻س���Ԫ�� >255"""
            targetNum = targetData[-1]
            recommendScore = {}
            for trainData in train_data.itertuples(index=True, name='Pandas'):
                trainNum = trainData[-1]
                reviewers = train_data_y[trainNum]

                score = IRTrain.cos2(targetData[0:targetData.__len__()-2], trainData[0:trainData.__len__()-2])
                for reviewer in reviewers:
                    if recommendScore.get(reviewer, None) is None:
                        recommendScore[reviewer] = 0
                    recommendScore[reviewer] += score

            targetRecommendList = [x[0] for x in
                                   sorted(recommendScore.items(), key=lambda d: d[1], reverse=True)[0:recommendNum]]
            # print(targetRecommendList)
            recommendList.append(targetRecommendList)
            answerList.append(test_data_y[targetNum])

        return [recommendList, answerList]

    @staticmethod
    def cos(dict1, dict2):
        """������������ϡ������ֵ�ļ�������"""
        if isinstance(dict1, dict) and isinstance(dict2, dict):
            """�ȼ���ģ��"""
            l1 = 0
            for v in dict1.values():
                l1 += v * v
            l2 = 0
            for v in dict2.values():
                l2 += v * v

            mul = 0
            """�����������"""
            for key in dict1.keys():
                if dict2.get(key, None) is not None:
                    mul += dict1[key] * dict2[key]

            if mul == 0:
                return 0
            return mul / (sqrt(l1) * sqrt(l2))

    @staticmethod
    def cos2(tuple1, tuple2):
        if tuple1.__len__() != tuple2.__len__():
            raise Exception("tuple length not equal!")
        """��������Ԫ�������"""
        """�ȼ���ģ��"""
        l1 = 0
        for v in tuple1:
            l1 += v * v
        l2 = 0
        for v in tuple2:
            l2 += v * v
        mul = 0
        """�����������"""
        len = tuple1.__len__()
        for i in range(0, len):
            mul += tuple1[i] * tuple2[i]
        if mul == 0:
            return 0
        return mul / (sqrt(l1) * sqrt(l2))


if __name__ == '__main__':
    # dates = [(2018, 4, 2018, 5), (2018, 4, 2018, 7), (2018, 4, 2018, 10), (2018, 4, 2019, 1),
    #          (2018, 4, 2019, 4)]
    dates = [(2018, 1, 2019, 5), (2018, 1, 2019, 6), (2018, 1, 2019, 7), (2018, 1, 2019, 8)]
    IRTrain.testIRAlgorithm('bitcoin', dates)
