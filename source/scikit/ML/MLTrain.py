# coding=gbk
import heapq
import time

import numpy
import pandas
from pandas import DataFrame
from sklearn.preprocessing import StandardScaler, MinMaxScaler

from source.config.projectConfig import projectConfig
from source.scikit.service.RecommendMetricUtils import RecommendMetricUtils
from source.utils.ExcelHelper import ExcelHelper
from source.utils.pandas.pandasHelper import pandasHelper

from sklearn.impute import SimpleImputer


class MLTrain:

    @staticmethod
    def testAlgorithms(project, dates):  # ����������ںͶ�Ӧ�ļ�����  ���һ�����㷨�ı���

        recommendNum = 5  # �Ƽ�����
        excelName = 'output.xlsx'
        sheetName = 'result'

        """��ʼ��excel�ļ�"""
        ExcelHelper().initExcelFile(fileName=excelName, sheetName=sheetName, excel_key_list=['ѵ����', '���Լ�'])

        for i in range(1, 4):  # Bayes ������ģ��
            for date in dates:
                filename = projectConfig.getRootPath() + r'\data\train' + r'\\' \
                           + f'ML_{project}_data_{date[0]}_{date[1]}_to_{date[2]}_{date[3]}.tsv'
                df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITHOUT_HEAD)
                """df��Ԥ����"""
                train_data, train_data_y, test_data, test_data_y = MLTrain.preProcess(df, (date[2], date[3]))

                """�����㷨����Ƽ��б�"""
                recommendList, answerList = MLTrain.RecommendByNativeBayes(train_data, train_data_y, test_data,
                                                                           test_data_y, recommendNum, i)

                """�����Ƽ��б�������"""
                topk, mrr = MLTrain.judgeRecommend(recommendList, answerList, recommendNum)

                """���д��excel"""
                MLTrain.saveResult(excelName, sheetName, topk, mrr, date)

            """�ļ��ָ�"""
            content = ['']
            ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())
            content = ['ѵ����', '���Լ�']
            ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())

    @staticmethod
    def saveResult(filename, sheetName, topk, mrr, date):
        """ʱ���׼ȷ��"""
        content = None
        if date[3] == 1:
            content = [f"{date[2]}.{date[3]}", f"{date[0]}.{date[1]} - {date[2] - 1}.{12}", "TopKAccuracy"]
        else:
            content = [f"{date[2]}.{date[3]}", f"{date[0]}.{date[1]} - {date[2]}.{date[3] - 1}", "TopKAccuracy"]

        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', '', 1, 2, 3, 4, 5]
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', ''] + topk
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', '', 'MRR']
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', '', 1, 2, 3, 4, 5]
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', ''] + mrr
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())


    @staticmethod
    def RecommendByNativeBayes(train_data, train_data_y, test_data, test_data_y, recommendNum=5, bayesType=1):
        """ʹ��NB
           recommendNum : �Ƽ�����
           bayesType : 1 Bernoulli
                       2 Gaussian
                       3 Multionmial

        """
        from sklearn.naive_bayes import GaussianNB, MultinomialNB, BernoulliNB
        clf = None
        if bayesType == 3:
            clf = GaussianNB()
        elif bayesType == 2:
            clf = MultinomialNB()
        elif bayesType == 1:
            clf = BernoulliNB()

        clf.fit(X=train_data, y=train_data_y)
        pre = clf.predict_proba(test_data)
        # print(clf.classes_)
        pre_class = clf.classes_

        recommendList = MLTrain.getListFromProbable(pre, pre_class, recommendNum)
        # print(recommendList)
        answer = [[x] for x in test_data_y]
        # print(answer)
        return [recommendList, answer]

    @staticmethod
    def preProcess(df, testDate, isSTD=False, isNOR=False):
        """����˵��
         df����ȡ��dataframe����
         testDate:��Ϊ���Ե����� (year,month)
         isSTD:�������Ƿ��׼��
         isNOR:�������Ƿ��һ��
        """
        columnName = ['reviewer_reviewer', 'pr_number', 'review_id', 'commit_sha', 'author', 'pr_created_at',
                      'pr_commits', 'pr_additions', 'pr_deletions', 'pr_head_label', 'pr_base_label',
                      'review_submitted_at', 'commit_status_total', 'commit_status_additions',
                      'commit_status_deletions', 'commit_files', 'author_review_count',
                      'author_push_count', 'author_submit_gap']
        df.columns = columnName

        """��df���һ�б�ʶѵ�����Ͳ��Լ�"""
        df['label'] = df['pr_created_at'].apply(
            lambda x: (time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_year == testDate[0] and
                       time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_mon == testDate[1]))
        """�������������ִ���"""
        MLTrain.changeStringToNumber(df, ['reviewer_reviewer', 'author'])
        print(df.shape)

        """"ȥ������ʱ����֮���NAN����"""
        df = df[~df['pr_head_label'].isna()]
        df = df[~df['pr_created_at'].isna()]
        df = df[~df['review_submitted_at'].isna()]
        df.reset_index(drop=True, inplace=True)
        print(df.shape)

        """��branch������  ����base,head����� �����ֻ�"""
        df.drop(axis=1, columns=['pr_base_label'], inplace=True)  # inplace ����ֱ����������
        df['pr_head_tail'] = df['pr_head_label']
        df['pr_head_tail'] = df['pr_head_tail'].apply(lambda x: x.split(':')[1])
        df['pr_head_label'] = df['pr_head_label'].apply(lambda x: x.split(':')[0])

        MLTrain.changeStringToNumber(df, ['pr_head_tail'])
        MLTrain.changeStringToNumber(df, ['pr_head_label'])

        """ʱ��תʱ�������"""
        df['pr_created_at'] = df['pr_created_at'].apply(
            lambda x: int(time.mktime(time.strptime(x, "%Y-%m-%d %H:%M:%S"))))
        df['review_submitted_at'] = df['review_submitted_at'].apply(
            lambda x: int(time.mktime(time.strptime(x, "%Y-%m-%d %H:%M:%S"))))

        """ȥ�����õ� commit_sha, review_id �� pr_number ��review_submitted_at"""
        df.drop(axis=1, columns=['commit_sha', 'review_id', 'pr_number', 'review_submitted_at'], inplace=True)
        # inplace ����ֱ����������

        """��������ȱʡֵ"""
        df.fillna(value=999999999999, inplace=True)
        # print(df)

        """���Լ���ѵ�����ֿ�"""
        test_data = df.loc[df['label']].copy(deep=True)

        print("test:", test_data.shape)
        train_data = df[df['label'] == False].copy(deep=True)
        print("train:", train_data.shape)

        test_data.drop(axis=1, columns=['label'], inplace=True)
        train_data.drop(axis=1, columns=['label'], inplace=True)

        """�ָ� tag��feature"""

        test_data_y = test_data['reviewer_reviewer'].copy(deep=True)
        test_data.drop(axis=1, columns=['reviewer_reviewer'], inplace=True)

        train_data_y = train_data['reviewer_reviewer'].copy(deep=True)
        train_data.drop(axis=1, columns=['reviewer_reviewer'], inplace=True)

        """�����淶��"""
        if isSTD:
            stdsc = StandardScaler()
            train_data_std = stdsc.fit_transform(train_data)
            test_data_std = stdsc.transform(test_data)
            # print(train_data_std)
            # print(test_data_std.shape)
            return train_data_std, train_data_y, test_data_std, test_data
        elif isNOR:
            maxminsc = MinMaxScaler()
            train_data_std = maxminsc.fit_transform(train_data)
            test_data_std = maxminsc.transform(test_data)
            return train_data_std, train_data_y, test_data_std, test_data
        else:
            return test_data, test_data_y, train_data, train_data_y

    @staticmethod
    def judgeRecommend(recommendList, answer, recommendNum):

        """�����Ƽ�����"""
        topk = RecommendMetricUtils.topKAccuracy(recommendList, answer, recommendNum)
        print(topk)
        mrr = RecommendMetricUtils.MRR(recommendList, answer, recommendNum)
        print(mrr)

        return topk, mrr

    @staticmethod
    def getListFromProbable(probable, classList, k):  # �Ƽ�k��
        recommendList = []
        for case in probable:
            max_index_list = list(map(lambda x: numpy.argwhere(case == x), heapq.nlargest(k, case)))
            caseList = []
            for item in max_index_list:
                caseList.append(classList[item[0][0]])
            recommendList.append(caseList)
        return recommendList

    @staticmethod
    def changeStringToNumber(data, columns):  # ��dataframe��һЩ�������ı�ת����  input: dataFrame����Ҫ�����ĳЩ��
        if isinstance(data, DataFrame):
            count = 0
            convertDict = {}  # ����ת�����ֵ�  ��ʼΪ1
            for column in columns:
                pos = 0
                for item in data[column]:
                    if convertDict.get(item, None) is None:
                        count += 1
                        convertDict[item] = count
                    data.at[pos, column] = convertDict[item]
                    pos += 1


if __name__ == '__main__':
    # inputPath = projectConfig.getRootPath() + r'\data\train\ML_rails_data_2018_4_to_2019_4.tsv'
    # featureProcess.preProcess(inputPath)
    dates = [(2019, 3, 2019, 4), (2019, 1, 2019, 4), (2018, 10, 2019, 4), (2018, 7, 2019, 4), (2018, 4, 2019, 4)]
    MLTrain.testAlgorithms('rails', dates)
