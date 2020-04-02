# coding=gbk
import os
import time
from datetime import datetime

import pandas

from source.config.projectConfig import projectConfig
from source.data.bean.PullRequest import PullRequest
from source.scikit.FPS.FPSAlgorithm import FPSAlgorithm
from source.scikit.service.BeanNumpyHelper import BeanNumpyHelper
from source.scikit.service.DataFrameColumnUtils import DataFrameColumnUtils
from source.scikit.service.DataProcessUtils import DataProcessUtils
from source.scikit.service.RecommendMetricUtils import RecommendMetricUtils
from source.utils.ExcelHelper import ExcelHelper
from source.utils.StringKeyUtils import StringKeyUtils
from source.utils.pandas.pandasHelper import pandasHelper


class FPSTrain:

    @staticmethod
    def TestAlgorithm(project, dates):
        """���� ѵ������"""
        recommendNum = 5  # �Ƽ�����
        excelName = f'outputFPS.xlsx'
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
                filename = projectConfig.getFPSDataPath() + os.sep + f'FPS_{project}_data_{y}_{m}_to_{y}_{m}.tsv'
                """�����Դ�head"""
                if df is None:
                    df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD)
                else:
                    temp = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD)
                    df = df.append(temp)  # �ϲ�

            df.reset_index(inplace=True, drop=True)
            """df��Ԥ����"""
            train_data, train_data_y, test_data, test_data_y = FPSTrain.preProcess(df, date)

            recommendList, answerList = FPSAlgorithm.RecommendByFPS(train_data, train_data_y, test_data,
                                                               test_data_y, recommendNum=recommendNum)

            # print(recommendList)
            # print(answerList)

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
            dates:��Ԫ�飬����λ��Ϊ���Ե����� (,,year,month)
           """

        """ע�⣺ �����ļ����Ѿ�����������"""

        """����NAN"""
        df.fillna(value='', inplace=True)

        """��df���һ�б�ʶѵ�����Ͳ��Լ�"""
        df['label'] = df['pr_created_at'].apply(
            lambda x: (time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_year == dates[2] and
                       time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_mon == dates[3]))
        """��reviewer�������ֻ�����"""
        DataProcessUtils.changeStringToNumber(df, ['review_user_login'])
        """�ȶ�tag�����"""
        tagDict = dict(list(df.groupby('pull_number')))

        print("before drop:", df.shape)
        df = df.copy(deep=True)
        df.drop(columns=['review_user_login', 'pr_created_at', 'repo_full_name'], inplace=True)
        df.drop_duplicates(['pull_number', 'commit_sha', 'file_filename'], inplace=True)
        print("after drop:", df.shape)

        """���Ѿ��е����������ͱ�ǩ��ѵ�����Ĳ��"""
        train_data = df.loc[df['label'] == False].copy(deep=True)
        test_data = df.loc[df['label']].copy(deep=True)

        train_data.drop(columns=['label'], inplace=True)
        test_data.drop(columns=['label'], inplace=True)

        """����ת��Ϊ���ǩ����
            train_data_y   [{pull_number:[r1, r2, ...]}, ... ,{}]
        """

        train_data_y = {}
        for pull_number in train_data.drop_duplicates(['pull_number'])['pull_number']:
            reviewers = list(tagDict[pull_number].drop_duplicates(['review_user_login'])['review_user_login'])
            train_data_y[pull_number] = reviewers

        test_data_y = {}
        for pull_number in test_data.drop_duplicates(['pull_number'])['pull_number']:
            reviewers = list(tagDict[pull_number].drop_duplicates(['review_user_login'])['review_user_login'])
            test_data_y[pull_number] = reviewers

        return train_data, train_data_y, test_data, test_data_y


if __name__ == '__main__':
    dates = [(2018, 4, 2018, 5), (2018, 4, 2018, 7), (2018, 4, 2018, 10), (2018, 4, 2019, 1),
             (2018, 4, 2019, 4)]
    # dates = [(2019, 3, 2019, 4)]
    FPSTrain.TestAlgorithm('rails', dates)
