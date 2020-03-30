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

        df = None

        for date in dates:
            startTime = datetime.now()
            for i in range(date[0] * 12 + date[1], date[2] * 12 + date[3] + 1):  # ��ֵ�������ƴ��
                y = int((i - i % 12) / 12)
                m = i % 12
                if m == 0:
                    m = 12
                    y = y - 1

                print(y, m)

                filename = projectConfig.getRootPath() + r'\data\train\all' + \
                           os.sep + f'ALL_{project}_data_{y}_{m}_to_{y}_{m}.tsv'
                if df is None:
                    df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD)
                else:
                    temp = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD)
                    df = df.append(temp)  # �ϲ�

            df.reset_index(inplace=True, drop=True)
            """df��Ԥ����"""
            train_data, train_data_y, test_data, test_data_y = IRTrain.preProcess(df, (date[2], date[3]))

            print("train data:", train_data.__len__())
            # print("traindatay:", train_data_y)
            print("test data:", test_data.__len__())
            # print("testdatay:", test_data_y)

            """�����㷨����Ƽ��б�"""
            recommendList, answerList = IRTrain.RecommendByIR(train_data, train_data_y, test_data,
                                                              test_data_y, recommendNum=recommendNum)

            """�����Ƽ��б�������"""
            topk, mrr = DataProcessUtils.judgeRecommend(recommendList, answerList, recommendNum)

            """���д��excel"""
            DataProcessUtils.saveResult(excelName, sheetName, topk, mrr, date)

            """�ļ��ָ�"""
            content = ['']
            ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())
            content = ['ѵ����', '���Լ�']
            ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())

            print("cost time:", datetime.now() - startTime)

    @staticmethod
    def preProcess(df, testDate):
        """����˵��
         df����ȡ��dataframe����
         testDate:��Ϊ���Ե����� (year,month)
        """

        """ע�⣺ �����ļ����Ѿ�����������"""

        """����NAN"""
        df.fillna(value='', inplace=True)

        """��df���һ�б�ʶѵ�����Ͳ��Լ�"""
        df['label'] = df['pr_created_at'].apply(
            lambda x: (time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_year == testDate[0] and
                       time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_mon == testDate[1]))

        """�ȶ��������������� ֻ���¸���Ȥ������"""
        df = df[['pr_number', 'review_id', 'review_comment_id', 'pr_title', 'pr_body',
                 'commit_commit_message', 'review_comment_body', 'review_user_login', 'label']].copy(deep=True)

        print("before filter:", df.shape)
        df.drop_duplicates(['pr_number', 'review_id', 'review_comment_id'], inplace=True)
        print("after filter:", df.shape)
        # print(df)

        """����һ��review�ж��comment�ĳ���  ��comment���ϲ���һ��"""

        comments = df['review_comment_body'].groupby(df['review_id']).sum()  # һ��review�����������ַ�������
        print(comments.index)

        """����ȥ��comment֮�����Ϣ ȥ��"""
        df = df[['pr_number', 'review_id', 'pr_title', 'pr_body', 'review_user_login',
                 'commit_commit_message', 'label']].copy(deep=True)
        print(df.shape)
        df.drop_duplicates(inplace=True)
        print(df.shape)

        df = (df.join(comments, on=['review_id'], how='inner')).copy(deep=True).reset_index(drop=True)
        print(df)

        """�������������ִ���"""
        DataProcessUtils.changeStringToNumber(df, ['review_user_login'])
        print(df)


        """�ȳ���������Ϣ����һ��"""

        """�����ռ������ı������ִ�"""
        stopwords = SplitWordHelper().getEnglishStopList()  # ��ȡͨ��Ӣ��ͣ�ô�

        textList = []
        for row in df.itertuples(index=True, name='Pandas'):
            """��ȡpull request�ı���"""
            pr_title = getattr(row, 'pr_title')
            pr_title_word_list = [x for x in FleshReadableUtils.word_list(pr_title) if x not in stopwords]

            """����������ȡ�ʸ�Ч�������½��� ��������"""

            # """�Ե�������ȡ�ʸ�"""
            # pr_title_word_list = nltkFunction.stemList(pr_title_word_list)
            textList.append(pr_title_word_list)

            """pull request��body"""
            pr_body = getattr(row, 'pr_body')
            pr_body_word_list = [x for x in FleshReadableUtils.word_list(pr_body) if x not in stopwords]
            # """�Ե�������ȡ�ʸ�"""
            # pr_body_word_list = nltkFunction.stemList(pr_body_word_list)
            textList.append(pr_body_word_list)

            """review ��comment"""
            review_comment = getattr(row, 'review_comment_body')
            review_comment_word_list = [x for x in FleshReadableUtils.word_list(review_comment) if x not in stopwords]
            # """�Ե�������ȡ�ʸ�"""
            # review_comment_word_list = nltkFunction.stemList(review_comment_word_list)
            textList.append(review_comment_word_list)

            """review��commit�� message"""
            commit_message = getattr(row, 'commit_commit_message')
            commit_message_word_list = [x for x in FleshReadableUtils.word_list(commit_message) if x not in stopwords]
            # """�Ե�������ȡ�ʸ�"""
            # commit_message_word_list = nltkFunction.stemList(commit_message_word_list)
            textList.append(commit_message_word_list)

        print(textList.__len__())

        """�Էִ��б����ֵ� ����ȡ������"""
        dictionary = corpora.Dictionary(textList)
        print('�ʵ䣺', dictionary)

        feature_cnt = len(dictionary.token2id)
        print("�ʵ���������", feature_cnt)

        """���ݴʵ佨�����Ͽ�"""
        corpus = [dictionary.doc2bow(text) for text in textList]
        print('���Ͽ�:', corpus)

        """���Ͽ�ѵ��TF-IDFģ��"""
        tfidf = models.TfidfModel(corpus)

        """�ٴα������ݣ��γ�������������ϡ��������ʽ"""
        wordVectors = []
        for i in range(0, df.shape[0]):
            words = []
            for j in range(0, 4):
                words.extend(textList[4 * i + j])
            # print(words)
            wordVectors.append(dict(tfidf[dictionary.doc2bow(words)]))
        print(wordVectors)

        """���Ѿ��еı������������ͱ�ǩ��ѵ�����Ͳ��Լ��Ĳ��"""

        train_data_y = df.loc[df['label'] == False]['review_user_login'].copy(deep=True)
        test_data_y = df.loc[df['label']]['review_user_login'].copy(deep=True)

        """ѵ����"""
        print(train_data_y.index)
        train_data = [wordVectors[x] for x in train_data_y.index]
        train_data_y.reset_index(drop=True, inplace=True)

        """���Լ�"""
        print(test_data_y.index)
        test_data = [wordVectors[x] for x in test_data_y.index]
        test_data_y.reset_index(drop=True, inplace=True)

        """����������һ��ϡ�������ֵ�"""

        return train_data, train_data_y, test_data, test_data_y

    @staticmethod
    def RecommendByIR(train_data, train_data_y, test_data, test_data_y, recommendNum=5):
        """ʹ����Ϣ����

        """""
        initScore = {}  # ���������ֵ�
        recommendList = []  # �����case�Ƽ��б�
        for y in train_data_y:
            if initScore.get(y, None) is None:
                initScore[y] = 0

        for targetData in test_data:  # ��ÿһ��case���Ƽ�
            recommendScore = initScore.copy()  # �����ظ�����
            pos = 0
            for trainData in train_data:
                reviewer = train_data_y[pos]
                pos += 1
                #
                # print("targetData:", targetData)
                # print("trainData:", trainData)
                score = IRTrain.cos(targetData, trainData)
                # print("score:", score)
                recommendScore[reviewer] += score

            targetRecommendList = [x[0] for x in
                                   sorted(recommendScore.items(), key=lambda d: d[1], reverse=True)[0:recommendNum]]
            # print(targetRecommendList)
            recommendList.append(targetRecommendList)
        # print(recommendList)
        answer = [[x] for x in test_data_y]
        # print(answer)
        return [recommendList, answer]

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
            return mul / (sqrt(l1) * sqrt(l2))


if __name__ == '__main__':
    dates = [(2018, 4, 2019, 4), (2018, 4, 2019, 3), (2018, 4, 2019, 2), (2018, 4, 2019, 1),
             (2018, 4, 2018, 12), (2018, 4, 2018, 11), (2018, 4, 2018, 10)]
    IRTrain.testIRAlgorithm('scala', dates)
