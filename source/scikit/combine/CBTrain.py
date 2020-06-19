# coding=gbk
from math import floor

from source.scikit.FPS.FPSTrain import FPSTrain
from source.scikit.IR.IRTrain import IRTrain
from source.scikit.ML.MLTrain import MLTrain
from source.scikit.service.DataProcessUtils import DataProcessUtils
from source.scikit.service.SortAlgorithmUtils import SortAlgorithmUtils
from source.utils.ExcelHelper import ExcelHelper
from source.utils.StringKeyUtils import StringKeyUtils


class CBTrain:
    """���ʽ�㷨 �ṩ���и����㷨���������"""

    @staticmethod
    def testCBAlgorithmsByMultipleLabels(projects, dates, algorithms):
        """
             algorithm : ����㷨���ṩ�㷨���������
             ��Ŀ -> ���� -> �㷨�������
             ÿһ����Ŀռһ���ļ�λ��  ÿһ���㷨���ռһҳ
          """
        recommendNum = 5  # �Ƽ�����
        for project in projects:
            excelName = f'outputCB_{project}.xlsx'
            sheetName = 'result'

            """��ʼ��excel�ļ�"""
            ExcelHelper().initExcelFile(fileName=excelName, sheetName=sheetName, excel_key_list=['ѵ����', '���Լ�'])

            """�Բ�ͬʱ����һ���ۺ�ͳ��
               ��ϵ�int -> [[],[]....]
            """
            topks = {}
            mrrs = {}
            precisionks = {}
            recallks = {}
            fmeasureks = {}
            """��ʼ��"""
            for i in range(1, 2 ** algorithms.__len__()):
                topks[i] = []
                mrrs[i] = []
                precisionks[i] = []
                recallks[i] = []
                fmeasureks[i] = []

            for date in dates:
                """��ò�ͬ�㷨���Ƽ��б��𰸺�pr�б�"""
                """��ͬ�㷨Ԥ������ܻ�ɸȥһЩpr  pr�б�������ͳһ"""
                prs = []
                recommendLists = []
                answerLists = []

                """���㲻ͬ��֮ǰ��ѵ����review�Ĵ��� ��Ϊ�����ۺ�ͳ�Ƶĵڶ�����"""
                reviewerFreq = DataProcessUtils.getReviewerFrequencyDict(project, date)

                for algorithm in algorithms:
                    print(f"project:{project},  date:{date}, algorithm:{algorithm}")
                    """�����㷨����Ƽ��б�"""
                    recommendList, answerList, prList, convertDict, trainSize = CBTrain.algorithmBody(date, project, algorithm,
                                                                                           recommendNum)
                    # print(recommendList)
                    print("trainSize:", trainSize)

                    """������ԭ"""
                    recommendList, answerList = CBTrain.recoverName(recommendList, answerList, convertDict)

                    # print(recommendList)

                    prs.append(prList)
                    recommendLists.append(recommendList)
                    answerLists.append(answerList)

                """��ͬ�㷨���չ��е�pr ˳�����"""
                prs, recommendLists, answerLists = CBTrain.normList(prs, recommendLists, answerLists)

                """ò���Ƽ�������Ҳ������Ч������ ��ʱ��ת��"""
                # CBTrain.convertNameToNumber(recommendLists, answerLists)

                """�Բ�ͬ�㷨���������"""
                for i in range(1, 2 ** algorithms.__len__()):
                    tempRecommendList = []
                    """��ͬ�㷨���Ե� answer�б���ͬ��ȡһ������"""
                    answer = answerLists[0]

                    involve = [0] * algorithms.__len__()
                    k = i
                    for j in range(0, algorithms.__len__()):
                        involve[algorithms.__len__() - j - 1] = k % 2
                        k = floor(k / 2)
                    """����㷨labelΪexcel sheetName"""
                    label = ''
                    for j in range(0, algorithms.__len__()):
                        if involve[j] == 1:
                            if label != '':
                                label = label + '_'
                            label = label + algorithms[j]
                            tempRecommendList.append(recommendLists[j])
                    sheetName = label
                    ExcelHelper().addSheet(filename=excelName, sheetName=sheetName)
                    """������� ��ϲ�ͬͶƱѡ����������"""
                    finalRecommendList = []
                    for j in range(0, answer.__len__()):
                        recommendList = SortAlgorithmUtils.BordaCountSortWithFreq([x[j] for x in tempRecommendList],
                                                                                  reviewerFreq)
                        finalRecommendList.append(recommendList)

                    """����ָ��"""
                    topk, mrr, precisionk, recallk, fmeasurek = \
                        DataProcessUtils.judgeRecommend(finalRecommendList, answer, recommendNum)

                    """���д��excel"""
                    DataProcessUtils.saveResult(excelName, sheetName, topk, mrr, precisionk, recallk, fmeasurek, date)

                    """�ۻ�����ָ��"""
                    topks[i].append(topk)
                    mrrs[i].append(mrr)
                    precisionks[i].append(precisionk)
                    recallks[i].append(recallk)
                    fmeasureks[i].append(fmeasurek)

            """��ָ�����ۺ�����"""
            for i in range(1, 2 ** algorithms.__len__()):
                involve = [0] * algorithms.__len__()
                k = i
                for j in range(0, algorithms.__len__()):
                    involve[algorithms.__len__() - j - 1] = k % 2
                    k = floor(k / 2)
                """����㷨labelΪexcel sheetName"""
                label = ''
                for j in range(0, algorithms.__len__()):
                    if involve[j] == 1:
                        if label != '':
                            label = label + '_'
                        label = label + algorithms[j]
                sheetName = label
                DataProcessUtils.saveFinallyResult(excelName, sheetName, topks[i], mrrs[i], precisionks[i], recallks[i],
                                                   fmeasureks[i])

    @staticmethod
    def algorithmBody(date, project, algorithmName, recommendNum=5):
        if algorithmName == StringKeyUtils.STR_ALGORITHM_FPS:
            return FPSTrain.algorithmBody(date, project, recommendNum)
        elif algorithmName == StringKeyUtils.STR_ALGORITHM_IR:
            return IRTrain.algorithmBody(date, project, recommendNum)
        elif algorithmName == StringKeyUtils.STR_ALGORITHM_RF_M:
            return MLTrain.algorithmBody(date, project, algorithmType=0, recommendNum=recommendNum, featureType=1)
        elif algorithmName == StringKeyUtils.STR_ALGORITHM_SVM:
            return MLTrain.algorithmBody(date, project, algorithmType=7, recommendNum=recommendNum, featureType=1)

    @staticmethod
    def recoverName(recommendList, answerList, convertDict):
        """ͨ��ӳ���ֵ��������ԭ"""
        tempDict = {k: v for v, k in convertDict.items()}
        recommendList = [[tempDict[i] for i in x] for x in recommendList]
        answerList = [[tempDict[i] for i in x] for x in answerList]
        return recommendList, answerList

    @staticmethod
    def convertNameToNumber(recommendLists, answerLists):
        pass

    @staticmethod
    def normList(prs, recommendLists, answerLists):
        """��ͬ���Ƽ�����Ԥ�����ԭ�򣬿��ܲ��Ե�pr��case��˳��ͬ���Է���һ���淶��"""

        """�������벻�ù淶"""
        if prs.__len__() == 1:
            return prs, recommendLists, answerLists

        normRecommendLists = []
        normAnswerLists = []
        normPrs = []

        """������pr���ҳ����е�"""
        normPrs = prs[0].copy()
        for prList in prs:
            normPrs = [i for i in normPrs if i in prList]

        """���ݹ��е�pr�б�Դ��������ɸѡ"""
        pos = -1
        for prList in prs:
            pos += 1
            recommendList = []
            answerList = []
            originRecommendList = recommendLists[pos]
            originAnswerList = answerLists[pos]
            for pr in normPrs:
                index = prList.index(pr)
                recommendList.append(originRecommendList[index])
                answerList.append(originAnswerList[index])
            normRecommendLists.append(recommendList)
            normAnswerLists.append(answerList)
        return normPrs, normRecommendLists, normAnswerLists


if __name__ == '__main__':
    # dates = [(2018, 1, 2019, 11), (2018, 1, 2019, 12)]
    # dates = [(2018, 1, 2019, 5), (2018, 1, 2019, 6), (2018, 1, 2019, 7), (2018, 1, 2019, 8), (2018, 1, 2019, 9)]
    # dates = [(2019, 1, 2019, 8), (2019, 1, 2019, 9)]
    # dates = [(2018, 1, 2019, 3)]
    dates = [(2018, 1, 2019, 1)]
    projects = ['cakephp']
    # projects = ['bitcoin']
    algorithms = [StringKeyUtils.STR_ALGORITHM_RF_M]
    # algorithms = [StringKeyUtils.STR_ALGORITHM_SVM]
    CBTrain.testCBAlgorithmsByMultipleLabels(projects, dates, algorithms)
