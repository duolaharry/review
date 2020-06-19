# coding=gbk
import numpy
from pandas import DataFrame
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import RidgeClassifierCV
from sklearn.metrics import accuracy_score
from sklearn.model_selection import GridSearchCV
from sklearn.multiclass import OneVsRestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier, RadiusNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier, ExtraTreeClassifier
from skmultilearn.adapt import MLkNN
from skmultilearn.problem_transform import BinaryRelevance, ClassifierChain

from source.scikit.service.DataProcessUtils import DataProcessUtils


class MultipleLabelAlgorithm:
    """�Զ��ǩ�㷨����װ"""

    @staticmethod
    def RecommendByBinaryRelevance(train_data, train_data_y, test_data, test_data_y, recommendNum=5):
        """ʹ�ö��ǩ����� ��ֵ��� """
        classifier = BinaryRelevance(RandomForestClassifier(oob_score=True, max_depth=10, min_samples_split=20))
        classifier.fit(train_data, train_data_y)

        predictions = classifier.predict_proba(test_data)
        predictions = predictions.todense().getA()

        recommendList = DataProcessUtils.getListFromProbable(predictions, range(1, train_data_y.shape[1] + 1),
                                                             recommendNum)
        answerList = test_data_y
        print(predictions)
        print(test_data_y)
        print(recommendList)
        print(answerList)
        return [recommendList, answerList]

    @staticmethod
    def RecommendByClassifierChain(train_data, train_data_y, test_data, test_data_y, recommendNum=5):
        """��������"""
        classifier = ClassifierChain(RandomForestClassifier(oob_score=True, max_depth=10, min_samples_split=20))
        classifier.fit(train_data, train_data_y)

        predictions = classifier.predict_proba(test_data)
        predictions = predictions.todense().getA()

        recommendList = DataProcessUtils.getListFromProbable(predictions, range(1, train_data_y.shape[1] + 1),
                                                             recommendNum)
        answerList = test_data_y
        print(predictions)
        print(test_data_y)
        print(recommendList)
        print(answerList)
        return [recommendList, answerList]

    @staticmethod
    def RecommendBySVM(train_data, train_data_y, test_data, test_data_y, recommendNum=5):
        """svm һ�Զ�"""
        classifier = SVC(kernel='linear', probability=True, class_weight='balanced', C=70)
        clf = OneVsRestClassifier(classifier)
        clf.fit(train_data, train_data_y)
        predictions = clf.predict_proba(test_data)
        recommendList = DataProcessUtils.getListFromProbable(predictions, range(1, train_data_y.shape[1] + 1),
                                                             recommendNum)

        answerList = test_data_y
        # print(predictions)
        # print(test_data_y)
        # print(recommendList)
        # print(answerList)
        return [recommendList, answerList]


    @staticmethod
    def RecommendByMLKNN(train_data, train_data_y, test_data, test_data_y, recommendNum=5):
        """ML KNN�㷨"""
        classifier = MLkNN(k=train_data_y.shape[1])
        classifier.fit(train_data, train_data_y)

        predictions = classifier.predict_proba(test_data).todense()
        """Ԥ����ת��Ϊdata array"""
        predictions = numpy.asarray(predictions)

        recommendList = DataProcessUtils.getListFromProbable(predictions, range(1, train_data_y.shape[1] + 1),
                                                             recommendNum)
        answerList = test_data_y
        print(predictions)
        print(test_data_y)
        print(recommendList)
        print(answerList)
        return [recommendList, answerList]

    @staticmethod
    def RecommendByDT(train_data, train_data_y, test_data, test_data_y, recommendNum=5):

        grid_parameters = [
            {'min_samples_leaf': [2, 4, 8, 16, 32, 64], 'max_depth': [2, 4, 6, 8]}]  # ���ڲ���

        from sklearn.tree import DecisionTreeClassifier
        from sklearn.model_selection import GridSearchCV
        clf = DecisionTreeClassifier()
        clf = GridSearchCV(clf, param_grid=grid_parameters, n_jobs=-1)
        clf.fit(train_data, train_data_y)

        predictions = clf.predict_proba(test_data)
        print(clf.best_params_)
        """Ԥ����ת��Ϊdata array"""
        predictions = DataProcessUtils.convertMultilabelProbaToDataArray(predictions)
        print(predictions)

        recommendList = DataProcessUtils.getListFromProbable(predictions, range(1, train_data_y.shape[1] + 1),
                                                             recommendNum)
        answerList = test_data_y
        print(predictions)
        print(test_data_y)
        print(recommendList)
        print(answerList)
        return [recommendList, answerList]

    @staticmethod
    def RecommendByRF(train_data, train_data_y, test_data, test_data_y, recommendNum=5):
        """���ǩ����  ���ɭ��"""

        clf = RandomForestClassifier(n_estimators=50, max_depth=5, n_jobs=-1)
        """������������������������"""
        # param_test1 = {'n_estimators': range(200, 250, 10)}
        # clf = GridSearchCV(estimator=clf, param_grid=param_test1)
        # print(clf.best_params_)
        # print(clf.best_params_, clf.best_score_)
        """�Ծ������Ĳ���������"""
        # param_test2 = {'max_depth': range(6, 8, 1), 'min_samples_split': range(18, 22, 1)}
        # clf = GridSearchCV(estimator=clf, param_grid=param_test1, cv=5, n_jobs=5)

        clf.fit(train_data, train_data_y)

        predictions = clf.predict_proba(test_data)
        # print(clf.best_params_)
        # print(clf.best_score_)
        # print(clf.cv_results_)
        """Ԥ����ת��Ϊdata array"""
        predictions = DataProcessUtils.convertMultilabelProbaToDataArray(predictions)
        print(predictions)

        recommendList = DataProcessUtils.getListFromProbable(predictions, range(1, train_data_y.shape[1] + 1),
                                                             recommendNum)
        answerList = test_data_y
        print(predictions)
        print(test_data_y)
        print(recommendList)
        print(answerList)
        return [recommendList, answerList]

    @staticmethod
    def RecommendByET(train_data, train_data_y, test_data, test_data_y, recommendNum=5):
        """���ǩ����  """

        clf = ExtraTreeClassifier()
        clf.fit(train_data, train_data_y)
        predictions = clf.predict_proba(test_data)
        """Ԥ����ת��Ϊdata array"""
        predictions = DataProcessUtils.convertMultilabelProbaToDataArray(predictions)
        print(predictions)

        recommendList = DataProcessUtils.getListFromProbable(predictions, range(1, train_data_y.shape[1] + 1),
                                                             recommendNum)
        answerList = test_data_y
        print(predictions)
        print(test_data_y)
        print(recommendList)
        print(answerList)
        return [recommendList, answerList]

    @staticmethod
    def RecommendByETS(train_data, train_data_y, test_data, test_data_y, recommendNum=5):
        """���ǩ����  """

        clf = ExtraTreesClassifier(n_jobs=3, n_estimators=250)
        param_test2 = {'max_depth': range(10, 40, 10), 'min_samples_split': range(15, 30, 5)}
        clf = GridSearchCV(estimator=clf, param_grid=param_test2, iid=False, cv=10, n_jobs=2)

        clf.fit(train_data, train_data_y)
        predictions = clf.predict_proba(test_data)
        """Ԥ����ת��Ϊdata array"""
        predictions = DataProcessUtils.convertMultilabelProbaToDataArray(predictions)
        print(predictions)

        recommendList = DataProcessUtils.getListFromProbable(predictions, range(1, train_data_y.shape[1] + 1),
                                                             recommendNum)
        answerList = test_data_y
        print(predictions)
        print(test_data_y)
        print(recommendList)
        print(answerList)
        return [recommendList, answerList]

    @staticmethod
    def RecommendByKN(train_data, train_data_y, test_data, test_data_y, recommendNum=5):
        """ML  KNeighbors"""
        clf = KNeighborsClassifier()
        clf.fit(train_data, train_data_y)
        predictions = clf.predict_proba(test_data)
        """Ԥ����ת��Ϊdata array"""
        predictions = DataProcessUtils.convertMultilabelProbaToDataArray(predictions)
        print(predictions)

        recommendList = DataProcessUtils.getListFromProbable(predictions, range(1, train_data_y.shape[1] + 1),
                                                             recommendNum)
        answerList = test_data_y
        print(predictions)
        print(test_data_y)
        print(recommendList)
        print(answerList)
        return [recommendList, answerList]

    @staticmethod
    def RecommendByAlgorithm(train_data, train_data_y, test_data, test_data_y, algorithmType, recommendNum=5):
        """
        ��sklearn��֧ͬ�ֶ��ǩ������㷨����װ
        algorithmType����ͬ���㷨

        ���ڲ�������RandomForest ��  ExtraTreeClassifier����Ч
        """
        if algorithmType == 0:
            return MultipleLabelAlgorithm.RecommendByRF(train_data, train_data_y, test_data, test_data_y, recommendNum)
        elif algorithmType == 1:
            return MultipleLabelAlgorithm.RecommendByDT(train_data, train_data_y, test_data, test_data_y, recommendNum)
        elif algorithmType == 2:
            return MultipleLabelAlgorithm.RecommendByET(train_data, train_data_y, test_data, test_data_y, recommendNum)
        elif algorithmType == 3:
            return MultipleLabelAlgorithm.RecommendByETS(train_data, train_data_y, test_data, test_data_y, recommendNum)
        elif algorithmType == 4:
            return MultipleLabelAlgorithm.RecommendByKN(train_data, train_data_y, test_data, test_data_y, recommendNum)
        elif algorithmType == 5:
            return MultipleLabelAlgorithm.RecommendByBinaryRelevance(train_data, train_data_y, test_data, test_data_y,
                                                                     recommendNum)
        elif algorithmType == 6:
            return MultipleLabelAlgorithm.RecommendByClassifierChain(train_data, train_data_y, test_data, test_data_y,
                                                                     recommendNum)
        elif algorithmType == 7:
            return MultipleLabelAlgorithm.RecommendBySVM(train_data, train_data_y, test_data, test_data_y,
                                                                     recommendNum)


    @staticmethod
    def getAnswerListFromDataFrame(test_data_y):
        """Ԥ�����Ϊ˳λ 1��ʼ��������ǰ��Ԥ����֤ """
        answerList = []
        for labels in test_data_y:
            pos = 1
            answer = []
            for label in labels:
                if label == 1:
                    answer.append(pos)
                pos += 1
            answerList.append(answer)
        return answerList
