# coding=gbk
import os
from datetime import datetime
import heapq
import time
from math import ceil

import graphviz
import numpy
import pandas
from pandas import DataFrame
from sklearn.decomposition import PCA
from sklearn.model_selection import PredefinedSplit, GridSearchCV
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.tree import export_graphviz

from source.config.projectConfig import projectConfig
from source.data.service.DataSourceHelper import processFilePathVectorByGensim, appendTextualFeatureVector, \
    appendFilePathFeatureVector
from source.scikit.ML.MultipleLabelAlgorithm import MultipleLabelAlgorithm
from source.scikit.service.DataProcessUtils import DataProcessUtils
from source.scikit.service.MLGraphHelper import MLGraphHelper
from source.scikit.service.RecommendMetricUtils import RecommendMetricUtils
from source.utils.ExcelHelper import ExcelHelper
from source.utils.StringKeyUtils import StringKeyUtils
from source.utils.pandas.pandasHelper import pandasHelper

from sklearn.impute import SimpleImputer


class MLTrain:

    @staticmethod
    def testMLAlgorithms(project, dates, algorithm):
        """
           �����㷨�ӿڣ����������Ƶ��㷨ͳһ
           algorithm : svm, dt, rf
        """

        recommendNum = 5  # �Ƽ�����
        excelName = f'output{algorithm}.xlsx'
        sheetName = 'result'

        """��ʼ��excel�ļ�"""
        ExcelHelper().initExcelFile(fileName=excelName, sheetName=sheetName, excel_key_list=['ѵ����', '���Լ�'])

        for date in dates:
            startTime = datetime.now()

            """ֱ�Ӷ�ȡ����·������Ϣ"""
            filename = projectConfig.getRootPath() + os.sep + 'data' + os.sep + 'train' + os.sep + \
                       f'ML_{project}_data_{date[0]}_{date[1]}_to_{date[2]}_{date[3]}.tsv'
            df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITHOUT_HEAD)
            print("raw df:", df.shape)

            # """��ȡ��·�����ļ���Ϣ"""
            # filename = projectConfig.getRootPath() + os.sep + r'data' + os.sep + 'train' + os.sep + \
            #            f'ML_{project}_data_{date[0]}_{date[1]}_to_{date[2]}_{date[3]}_include_filepath.csv'
            # df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD,
            #                               sep=StringKeyUtils.STR_SPLIT_SEP_CSV)

            """df��Ԥ����"""
            train_data, train_data_y, test_data, test_data_y = MLTrain.preProcessForSingleLabel(df, date, project,
                                                                                                isNOR=True)
            recommendList = None
            answerList = None
            """�����㷨����Ƽ��б�"""
            if algorithm == StringKeyUtils.STR_ALGORITHM_SVM:  # ֧��������
                recommendList, answerList = MLTrain.RecommendBySVM(train_data, train_data_y, test_data,
                                                                   test_data_y, recommendNum=recommendNum)
            elif algorithm == StringKeyUtils.STR_ALGORITHM_DT:  # ������
                recommendList, answerList = MLTrain.RecommendByDecisionTree(train_data, train_data_y, test_data,
                                                                            test_data_y, recommendNum=recommendNum)
            elif algorithm == StringKeyUtils.STR_ALGORITHM_RF:  # ���ɭ��
                recommendList, answerList = MLTrain.RecommendByRandomForest(train_data, train_data_y, test_data,
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
    def testBayesAlgorithms(project, dates):  # ����������ںͶ�Ӧ�ļ�����  ���һ�����㷨�ı���

        recommendNum = 5  # �Ƽ�����
        excelName = 'outputNB.xlsx'
        sheetName = 'result'

        """��ʼ��excel�ļ�"""
        ExcelHelper().initExcelFile(fileName=excelName, sheetName=sheetName, excel_key_list=['ѵ����', '���Լ�'])

        for i in range(1, 4):  # Bayes ������ģ��
            for date in dates:
                filename = projectConfig.getRootPath() + r'\data\train' + r'\\' \
                           + f'ML_{project}_data_{date[0]}_{date[1]}_to_{date[2]}_{date[3]}.tsv'
                df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITHOUT_HEAD)
                """df��Ԥ����"""
                isNOR = True
                if i == 1 or i == 3:
                    isNOR = False  # �Բ�Ŭ��������һ
                train_data, train_data_y, test_data, test_data_y = MLTrain.preProcessForSingleLabel(df, date, project,
                                                                                                    isNOR=isNOR)

                """�����㷨����Ƽ��б�"""
                recommendList, answerList = MLTrain.RecommendByNativeBayes(train_data, train_data_y, test_data,
                                                                           test_data_y, recommendNum, i)

                """�����Ƽ��б�������"""
                topk, mrr = DataProcessUtils.judgeRecommend(recommendList, answerList, recommendNum)

                """���д��excel"""
                DataProcessUtils.saveResult(excelName, sheetName, topk, mrr, date)

            """�ļ��ָ�"""
            content = ['']
            ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())
            content = ['ѵ����', '���Լ�']
            ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())

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
        if bayesType == 2:
            clf = GaussianNB()
        elif bayesType == 3:
            clf = MultinomialNB()
            param = {"alpha": [0.2 * x for x in range(0, 10)], "fit_prior": [False, True]}
            clf = GridSearchCV(clf, param_grid=param)
        elif bayesType == 1:
            clf = BernoulliNB()

        clf.fit(X=train_data, y=train_data_y)
        if bayesType == 3:
            print(clf.best_params_, clf.best_score_)

        """�鿴�㷨��ѧϰ����"""
        MLGraphHelper.plot_learning_curve(clf, 'Bayes', train_data, train_data_y).show()

        pre = clf.predict_proba(test_data)
        # print(clf.classes_)
        pre_class = clf.classes_

        recommendList = DataProcessUtils.getListFromProbable(pre, pre_class, recommendNum)
        # print(recommendList)
        answer = [[x] for x in test_data_y]
        # print(answer)
        return [recommendList, answer]

    @staticmethod
    def RecommendBySVM(train_data, train_data_y, test_data, test_data_y, recommendNum=5, CoreType='rbf', C=1,
                       gamma='auto',
                       decisionShip='ovo'):
        """ʹ��SVM
           recommendNum : �Ƽ�����
           CoreType : 'linear' ����
                      'rbf' ��˹
           C�� �ͷ�ϵ��
           gamma�� �˲���lambda
           decisionShip: �������
        """

        """�趨�жϲ���"""

        """ѵ��������3 7���ֳ�ѵ�����ͽ�����֤��"""

        """�Զ�����֤�� ������ʹ�ý�����֤"""

        """����ʹ�ý�����֤�����Զ�����֤��Ҫ���о�һ��  3.31"""
        test_fold = numpy.zeros(train_data.shape[0])
        test_fold[:ceil(train_data.shape[0] * 0.7)] = -1
        ps = PredefinedSplit(test_fold=test_fold)

        grid_parameters = [
            {'kernel': ['rbf'], 'gamma': [0.0005, 0.00075, 0.0001],
             'C': [100, 105, 108, 110], 'decision_function_shape': ['ovr']}]
        # {'kernel': ['linear'], 'C': [90, 95, 100],
        #  'decision_function_shape': ['ovr', 'ovo'],
        #  'class_weight': ['balanced', None]}]  # ���ڲ���

        from sklearn import svm
        from sklearn.model_selection import GridSearchCV
        clf = svm.SVC(C=C, kernel=CoreType, probability=True, gamma=gamma, decision_function_shape=decisionShip)
        """
          ��ΪREVIEW����������ʱ����ص�  ���Խ�����nfold����ʹ��
          ��Ҫ�Զ�����֤�� ���ʹ���Զ�����֤��   GridSearchCVA(CV=ps)

        """
        # clf = GridSearchCV(clf, param_grid=grid_parameters, cv=ps)  # ������������
        clf.fit(X=train_data, y=train_data_y)
        # clf.fit(X=train_features, y=train_label)

        # print(clf.best_params_)

        # clf = svm.SVC(C=100, kernel='linear', probability=True)
        # clf.fit(train_data, train_data_y)

        pre = clf.predict_proba(test_data)
        pre_class = clf.classes_
        # print(pre)
        # print(pre_class)
        """�鿴�㷨��ѧϰ����"""
        MLGraphHelper.plot_learning_curve(clf, 'SVM', train_data, train_data_y).show()

        recommendList = DataProcessUtils.getListFromProbable(pre, pre_class, recommendNum)
        # print(recommendList.__len__())
        answer = [[x] for x in test_data_y]
        # print(answer.__len__())
        return [recommendList, answer]

    @staticmethod
    def preProcessForSingleLabel(df, date, project, isSTD=False, isNOR=False):
        """����˵��
         df����ȡ��dataframe����
         testDate:��Ϊ���Ե����� (year,month)
         isSTD:�������Ƿ��׼��
         isNOR:�������Ƿ��һ��

         ֮ǰ�ĵ���ǩ���⴦��
        """

        # """����filepath��tf-idf"""
        # df = processFilePathVectorByGensim(df=df)
        # print("filepath df:", df.shape)

        # """�����ڵ�dataframe�Ļ�������׷��review��ص��ı�����Ϣ����"""
        # df = appendTextualFeatureVector(df, project, date)

        columnName = ['reviewer_reviewer', 'pr_number', 'review_id', 'commit_sha', 'author', 'pr_created_at',
                      'pr_commits', 'pr_additions', 'pr_deletions', 'pr_head_label', 'pr_base_label',
                      'review_submitted_at', 'commit_status_total', 'commit_status_additions',
                      'commit_status_deletions', 'commit_files', 'author_review_count',
                      'author_push_count', 'author_submit_gap']
        df.columns = columnName

        """��df���һ�б�ʶѵ�����Ͳ��Լ�"""
        df['label'] = df['pr_created_at'].apply(
            lambda x: (time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_year == date[2] and
                       time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_mon == date[3]))
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

        # """���ɷַ���"""
        # pca = PCA()
        # train_data = pca.fit_transform(train_data)
        # print("after pca train:", train_data.shape)
        # print(pca.explained_variance_ratio_)
        # test_data = pca.transform(test_data)
        # print("after pca test:", test_data.shape)

        """�����淶��"""
        if isSTD:
            stdsc = StandardScaler()
            train_data_std = stdsc.fit_transform(train_data)
            test_data_std = stdsc.transform(test_data)
            # print(train_data_std)
            # print(test_data_std.shape)
            return train_data_std, train_data_y, test_data_std, test_data_y
        elif isNOR:
            maxminsc = MinMaxScaler()
            train_data_std = maxminsc.fit_transform(train_data)
            test_data_std = maxminsc.transform(test_data)
            return train_data_std, train_data_y, test_data_std, test_data_y
        else:
            return train_data, train_data_y, test_data, test_data_y

    @staticmethod
    def preProcess(df, date, project, featureType, isSTD=False, isNOR=False):
        """����˵��
         df����ȡ��dataframe����
         testDate:��Ϊ���Ե����� (year,month)
         isSTD:�������Ƿ��׼��
         isNOR:�������Ƿ��һ��
        """
        print("start df shape:", df.shape)
        """����NA������"""
        df.dropna(axis=0, how='any', inplace=True)
        print("after fliter na:", df.shape)

        """��df���һ�б�ʶѵ�����Ͳ��Լ�"""
        df['label'] = df['pr_created_at'].apply(
            lambda x: (time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_year == date[2] and
                       time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_mon == date[3]))
        df.reset_index(drop=True, inplace=True)

        # """�����е�����������ı�·������"""
        """����˵��������PCA����ѵ�����Ͳ��Լ�ͬʱ��ά�������൱��ʹ���˺������Ϣ
           �������֮ǰ�������߷ֱ��� 4.13 
           append ���������ڱ���label����ʹ��"""

        if featureType == 1 or featureType == 3:
            df = appendFilePathFeatureVector(df, project, date, 'pr_number')
        """�����е����������pr����������ı�����"""
        if featureType == 2 or featureType == 3:
            df = appendTextualFeatureVector(df, project, date, 'pr_number')

        """Ƶ��ͳ��ÿһ��reviewer�Ĵ������ų��������ٵ�reviewer"""
        freq = {}
        for data in df.itertuples(index=False):
            name = data[list(df.columns).index('review_user_login')]
            if freq.get(name, None) is None:
                freq[name] = 0
            """ѵ�����û�������һ  ���Լ�ֱ�ӱ��� """
            if not data[list(df.columns).index('label')]:
                freq[name] += 1
            else:
                freq[name] += 1

        num = 5
        df['freq'] = df['review_user_login'].apply(lambda x: freq[x])
        df = df.loc[df['freq'] > num].copy(deep=True)
        df.drop(columns=['freq'], inplace=True)
        df.reset_index(drop=True, inplace=True)
        print("after lifter unexperienced user:", df.shape)

        # # # ��������������Ƶ��ͼ
        # MLTrain.getSeriesBarPlot(df['review_user_login'])

        """�������������ִ���"""
        """Ƶ�ʲ������������ڱ��֮ǰ���Ѿ������ˣ����ÿ��Ƿ��಻���������"""
        """����reviewer_user_login ���� ��һ�������Ӱ��candicateNum��������ں��������"""
        convertDict = DataProcessUtils.changeStringToNumber(df, ['review_user_login', 'pr_user_login'])
        print(df.shape)
        candicateNum = max(df.loc[df['label'] == 0]['review_user_login'])
        print("candicate Num:", candicateNum)

        """��branch������  ����base,head����� �����ֻ�"""
        df.drop(axis=1, columns=['pr_base_label'], inplace=True)  # inplace ����ֱ����������
        df['pr_head_tail'] = df['pr_head_label']
        df['pr_head_tail'] = df['pr_head_tail'].apply(lambda x: x.split(':')[1])
        df['pr_head_label'] = df['pr_head_label'].apply(lambda x: x.split(':')[0])

        df.drop(axis=1, columns=['pr_head_tail'], inplace=True)

        # MLTrain.changeStringToNumber(df, ['pr_head_tail'])
        DataProcessUtils.changeStringToNumber(df, ['pr_head_label'])

        """ʱ��תʱ�������"""
        df['pr_created_at'] = df['pr_created_at'].apply(
            lambda x: int(time.mktime(time.strptime(x, "%Y-%m-%d %H:%M:%S"))))

        """�ȶ�tag�����"""
        tagDict = dict(list(df.groupby('pr_number')))

        """���Ѿ��е����������ͱ�ǩ��ѵ�����Ĳ��"""
        train_data = df.loc[df['label'] == False].copy(deep=True)
        test_data = df.loc[df['label']].copy(deep=True)

        train_data.drop(columns=['label'], inplace=True)
        test_data.drop(columns=['label'], inplace=True)

        """����ת��Ϊ���ǩ����
            train_data_y   [{pull_number:[r1, r2, ...]}, ... ,{}]
        """
        train_data_y = {}
        pull_number_list = train_data.drop_duplicates(['pr_number']).copy(deep=True)['pr_number']
        for pull_number in pull_number_list:
            reviewers = list(tagDict[pull_number].drop_duplicates(['review_user_login'])['review_user_login'])
            train_data_y[pull_number] = reviewers

        train_data.drop(columns=['review_user_login'], inplace=True)
        train_data.drop_duplicates(inplace=True)
        """ѵ���� ����������ǩ����ͨ�õ�ģʽ"""
        train_data_y = DataProcessUtils.convertLabelListToDataFrame(train_data_y, pull_number_list, candicateNum)

        test_data_y = {}
        pull_number_list = test_data.drop_duplicates(['pr_number']).copy(deep=True)['pr_number']
        for pull_number in test_data.drop_duplicates(['pr_number'])['pr_number']:
            reviewers = list(tagDict[pull_number].drop_duplicates(['review_user_login'])['review_user_login'])
            test_data_y[pull_number] = reviewers

        test_data.drop(columns=['review_user_login'], inplace=True)
        test_data.drop_duplicates(inplace=True)
        # test_data_y = DataProcessUtils.convertLabelListToDataFrame(test_data_y, pull_number_list, candicateNum)
        test_data_y = DataProcessUtils.convertLabelListToListArray(test_data_y, pull_number_list)

        """���pr list"""
        prList = list(test_data['pr_number'])

        """ȥ��pr number"""
        test_data.drop(columns=['pr_number'], inplace=True)
        train_data.drop(columns=['pr_number'], inplace=True)

        """�����淶��"""
        if isSTD:
            stdsc = StandardScaler()
            train_data_std = stdsc.fit_transform(train_data)
            test_data_std = stdsc.transform(test_data)
            # print(train_data_std)
            # print(test_data_std.shape)
            return train_data_std, train_data_y, test_data_std, test_data_y, convertDict, prList
        elif isNOR:
            maxminsc = MinMaxScaler()
            train_data_std = maxminsc.fit_transform(train_data)
            test_data_std = maxminsc.transform(test_data)
            return train_data_std, train_data_y, test_data_std, test_data_y, convertDict, prList
        else:
            return train_data, train_data_y, test_data, test_data_y, convertDict, prList

    @staticmethod
    def changeStringToNumber(data, columns, startNum=0):  # ��dataframe��һЩ�������ı�ת����  input: dataFrame����Ҫ�����ĳЩ��
        if isinstance(data, DataFrame):
            count = startNum
            convertDict = {}  # ����ת�����ֵ�  ��ʼΪ1
            for column in columns:
                pos = 0
                for item in data[column]:
                    if convertDict.get(item, None) is None:
                        count += 1
                        convertDict[item] = count
                    data.at[pos, column] = convertDict[item]
                    pos += 1

    @staticmethod
    def RecommendByDecisionTree(train_data, train_data_y, test_data, test_data_y, recommendNum=5):
        """ʹ�þ�����
           recommendNum : �Ƽ�����
           max_depth ������������
           min_samples_split �ڲ��ڵ㻮��������С������
           min_samples_leaf Ҷ�ӽڵ���С������
           class_weight ����Ȩ��
        """

        """�趨�жϲ���"""

        """ѵ��������3 7���ֳ�ѵ�����ͽ�����֤��"""

        """�Զ�����֤�� ������ʹ�ý�����֤"""
        test_fold = numpy.zeros(train_data.shape[0])
        test_fold[:ceil(train_data.shape[0] * 0.7)] = -1
        ps = PredefinedSplit(test_fold=test_fold)

        grid_parameters = [
            {'min_samples_leaf': [2, 4, 8, 16, 32, 64], 'max_depth': [2, 4, 6, 8],
             'class_weight': [None]}]  # ���ڲ���

        # # scores = ['precision', 'recall']  # �ж�����

        from sklearn.tree import DecisionTreeClassifier
        from sklearn.model_selection import GridSearchCV
        clf = DecisionTreeClassifier()
        clf = GridSearchCV(clf, param_grid=grid_parameters, cv=ps, n_jobs=-1)
        clf.fit(train_data, train_data_y)

        print(clf.best_params_)
        # dot_data = export_graphviz(clf, out_file=None)
        # graph = graphviz.Source(dot_data)
        # graph.render("DTree")

        pre = clf.predict_proba(test_data)
        pre_class = clf.classes_
        # print(pre)
        # print(pre_class)

        recommendList = DataProcessUtils.getListFromProbable(pre, pre_class, recommendNum)
        # print(recommendList)
        answer = [[x] for x in test_data_y]
        # print(answer)
        return [recommendList, answer]

    @staticmethod
    def getSeriesBarPlot(series):
        #  ��� �������ݵ���״�ֲ�ͼ
        import matplotlib.pyplot as plt

        fig = plt.figure()
        # fig.add_subplot(2, 1, 1)
        counts = series.value_counts()
        print(counts)
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        counts.plot(kind='bar')
        plt.title('��Ŀrails����������ʷͳ��')
        plt.xlabel('��Ա')
        plt.ylabel('�������')
        plt.show()

    @staticmethod
    def RecommendByRandomForest(train_data, train_data_y, test_data, test_data_y, recommendNum=5):
        """ʹ�����ɭ��
           n_estimators : �����ѧϰ������
           recommendNum : �Ƽ�����
           max_depth ������������
           min_samples_split �ڲ��ڵ㻮��������С������
           min_samples_leaf Ҷ�ӽڵ���С������
           class_weight ����Ȩ��
        """

        """�趨�жϲ���"""

        """�Զ�����֤�� ������ʹ�ý�����֤"""
        test_fold = numpy.zeros(train_data.shape[0])
        test_fold[:ceil(train_data.shape[0] * 0.7)] = -1
        ps = PredefinedSplit(test_fold=test_fold)

        """����ģ��"""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import GridSearchCV
        clf = RandomForestClassifier(min_samples_split=100,
                                     min_samples_leaf=20, max_depth=8, max_features='sqrt', random_state=10)
        # clf = GridSearchCV(clf, param_grid=grid_parameters, cv=ps, n_jobs=-1)
        # clf.fit(train_data, train_data_y)
        #
        # print("OOB SCORE:", clf.oob_score_)

        """������������������������"""
        # param_test1 = {'n_estimators': range(10, 200, 10)}
        # clf = GridSearchCV(estimator=clf, param_grid=param_test1)
        # clf.fit(train_data, train_data_y)
        # print(clf.best_params_, clf.best_score_)

        """�Ծ������Ĳ���������"""
        param_test2 = {'max_depth': range(3, 14, 2), 'min_samples_split': range(50, 201, 20)}
        clf = GridSearchCV(estimator=clf, param_grid=param_test2, iid=False, cv=5)
        clf.fit(train_data, train_data_y)
        # gsearch2.grid_scores_, gsearch2.best_params_, gsearch2.best_score_

        """�鿴�㷨��ѧϰ����"""
        MLGraphHelper.plot_learning_curve(clf, 'RF', train_data, train_data_y).show()

        pre = clf.predict_proba(test_data)
        pre_class = clf.classes_
        # print(pre)
        # print(pre_class)

        recommendList = DataProcessUtils.getListFromProbable(pre, pre_class, recommendNum)
        # print(recommendList)
        answer = [[x] for x in test_data_y]
        # print(answer)
        return [recommendList, answer]

    @staticmethod
    def testMLAlgorithmsByMultipleLabels(projects, dates, algorithms=None):
        """
           ���ǩ�����㷨�ӿڣ����������Ƶ��㷨ͳһ
        """
        startTime = datetime.now()

        for algorithmType in algorithms:
            for project in projects:
                excelName = f'output{algorithmType}_{project}_ML.xlsx'
                recommendNum = 5  # �Ƽ�����
                sheetName = 'result'
                """��ʼ��excel�ļ�"""
                ExcelHelper().initExcelFile(fileName=excelName, sheetName=sheetName, excel_key_list=['ѵ����', '���Լ�'])
                for featureType in range(0, 1):
                    """��ʼ����Ŀ̧ͷ"""
                    content = ["��Ŀ���ƣ�", project]
                    ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())
                    content = ['�������ͣ�', str(featureType)]
                    ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())

                    """�����ۻ�����"""
                    topks = []
                    mrrs = []
                    precisionks = []
                    recallks = []
                    fmeasureks = []

                    for date in dates:
                        recommendList, answerList, prList, convertDict, trainSize = MLTrain.algorithmBody(date, project,
                                                                                               algorithmType,
                                                                                               recommendNum,
                                                                                               featureType)
                        """�����Ƽ��б�������"""
                        topk, mrr, precisionk, recallk, fmeasurek = \
                            DataProcessUtils.judgeRecommend(recommendList, answerList, recommendNum)

                        topks.append(topk)
                        mrrs.append(mrr)
                        precisionks.append(precisionk)
                        recallks.append(recallk)
                        fmeasureks.append(fmeasurek)

                        """���д��excel"""
                        DataProcessUtils.saveResult(excelName, sheetName, topk, mrr, precisionk, recallk, fmeasurek,
                                                    date)

                        """�ļ��ָ�"""
                        content = ['']
                        ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())
                        content = ['ѵ����', '���Լ�']
                        ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())

                    print("cost time:", datetime.now() - startTime)

                    """������ʷ�ۻ�����"""
                    DataProcessUtils.saveFinallyResult(excelName, sheetName, topks, mrrs, precisionks, recallks,
                                                       fmeasureks)

    @staticmethod
    def algorithmBody(date, project, algorithmType, recommendNum=5, featureType=3):
        df = None
        """�������ļ����ϲ� """
        for i in range(date[0] * 12 + date[1], date[2] * 12 + date[3] + 1):  # ��ֵ�������ƴ��
            y = int((i - i % 12) / 12)
            m = i % 12
            if m == 0:
                m = 12
                y = y - 1

            print(y, m)
            filename = projectConfig.getMLDataPath() + os.sep + f'ML_{project}_data_{y}_{m}_to_{y}_{m}.tsv'
            """�����Դ�head"""
            if df is None:
                df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD)
            else:
                temp = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD)
                df = df.append(temp)  # �ϲ�

        df.reset_index(inplace=True, drop=True)
        """df��Ԥ����"""
        """��ȡ���Ե� pull number�б�"""
        train_data, train_data_y, test_data, test_data_y, convertDict, prList = MLTrain.preProcess(df, date, project,
                                                                                                   featureType,
                                                                                                   isNOR=True)
        print("train data:", train_data.shape)
        print("test data:", test_data.shape)

        recommendList, answerList = MultipleLabelAlgorithm. \
            RecommendByAlgorithm(train_data, train_data_y, test_data, test_data_y, algorithmType)

        trainSize = (train_data.shape[0], test_data.shape[0])

        return recommendList, answerList, prList, convertDict, trainSize


if __name__ == '__main__':
    # dates = [(2018, 1, 2019, 4), (2018, 1, 2019, 5), (2018, 1, 2019, 6), (2018, 1, 2019, 7), (2018, 1, 2019, 7),
    #          (2018, 1, 2019, 8)
    #     , (2018, 1, 2019, 9), (2018, 1, 2019, 10), (2018, 1, 2019, 11), (2018, 1, 2019, 12)]
    # dates = [(2018, 1, 2019, 5), (2018, 1, 2019, 6), (2018, 1, 2019, 7), (2018, 1, 2019, 8), (2018, 1, 2019, 9)
    #     , (2018, 1, 2019, 10)]
    # dates = [(2018, 1, 2019, 12)]
    # MLTrain.testMLAlgorithms('rails', dates, StringKeyUtils.STR_ALGORITHM_DT)
    # MLTrain.testBayesAlgorithms('rails', dates)
    # projects = ['rails', 'scala', 'akka', 'bitcoin']
    dates = [(2018, 1, 2019, 1)]
    projects = ['cakephp']
    MLTrain.testMLAlgorithmsByMultipleLabels(projects, dates, [0])
