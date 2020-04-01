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
from source.data.service.DataSourceHelper import processFilePathVectorByGensim, appendTextualFeatureVector
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

            # """ֱ�Ӷ�ȡ����·������Ϣ"""
            # filename = projectConfig.getRootPath() + os.sep + 'data' + os.sep + 'train' + os.sep + \
            #            f'ML_{project}_data_{date[0]}_{date[1]}_to_{date[2]}_{date[3]}.tsv'
            # df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITHOUT_HEAD)
            # print("raw df:", df.shape)

            """��ȡ��·�����ļ���Ϣ"""
            filename = projectConfig.getRootPath() + os.sep + r'data' + os.sep + 'train' + os.sep + \
                       f'ML_{project}_data_{date[0]}_{date[1]}_to_{date[2]}_{date[3]}_include_filepath.csv'
            df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD,
                                          sep=StringKeyUtils.STR_SPLIT_SEP_CSV)
            """df��Ԥ����"""
            train_data, train_data_y, test_data, test_data_y = MLTrain.preProcess(df, date, project, isNOR=True)
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
                train_data, train_data_y, test_data, test_data_y = MLTrain.preProcess(df, date, project,
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

        recommendList = MLTrain.getListFromProbable(pre, pre_class, recommendNum)
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

        recommendList = MLTrain.getListFromProbable(pre, pre_class, recommendNum)
        # print(recommendList.__len__())
        answer = [[x] for x in test_data_y]
        # print(answer.__len__())
        return [recommendList, answer]

    @staticmethod
    def preProcess(df, date, project, isSTD=False, isNOR=False):
        """����˵��
         df����ȡ��dataframe����
         testDate:��Ϊ���Ե����� (year,month)
         isSTD:�������Ƿ��׼��
         isNOR:�������Ƿ��һ��
        """

        """����filepath��tf-idf"""
        df = processFilePathVectorByGensim(df=df)
        print("filepath df:", df.shape)

        # """�����ڵ�dataframe�Ļ�������׷��review��ص��ı�����Ϣ����"""
        # df = appendTextualFeatureVector(df, project, date)

        # columnName = ['reviewer_reviewer', 'pr_number', 'review_id', 'commit_sha', 'author', 'pr_created_at',
        #               'pr_commits', 'pr_additions', 'pr_deletions', 'pr_head_label', 'pr_base_label',
        #               'review_submitted_at', 'commit_status_total', 'commit_status_additions',
        #               'commit_status_deletions', 'commit_files', 'author_review_count',
        #               'author_push_count', 'author_submit_gap']
        # df.columns = columnName

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

        recommendList = MLTrain.getListFromProbable(pre, pre_class, recommendNum)
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
        counts.plot(kind='bar')
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

        recommendList = MLTrain.getListFromProbable(pre, pre_class, recommendNum)
        # print(recommendList)
        answer = [[x] for x in test_data_y]
        # print(answer)
        return [recommendList, answer]


if __name__ == '__main__':
    dates = [(2019, 3, 2019, 4), (2019, 1, 2019, 4), (2018, 10, 2019, 4), (2018, 7, 2019, 4)]
    # dates = [(2018, 7, 2019, 4)]
    MLTrain.testMLAlgorithms('rails', dates, StringKeyUtils.STR_ALGORITHM_RF)
    # MLTrain.testBayesAlgorithms('akka', dates)
