# coding=gbk

class RecommendMetricUtils:
    """�����Ƽ���׼ȷ�ʵĹ�����"""

    @staticmethod
    def topKAccuracy(recommendCase, answerCase, k):
        """top k Accuracy  �������Ϊ���Ԥ���ʵ�ʵ��Ƽ��б���б�"""
        topK = [0 for i in range(k)]
        if recommendCase.__len__() != answerCase.__len__():
            raise Exception("case is not right")
        casePos = 0
        for recommendList in recommendCase:
            # print("recommend:", recommendList)
            answerList = answerCase[casePos]
            # print("answerList:", answerList)
            casePos += 1
            listPos = 0
            firstFind = False
            for recommend in recommendList:
                if firstFind:
                    break
                index = -1
                try:
                    index = answerList.index(recommend)
                except Exception as e:
                    pass
                if index != -1:
                    for i in range(listPos, k):
                        topK[i] += 1
                    firstFind = True
                    break
                else:
                    listPos += 1
        for i in range(0, topK.__len__()):
            topK[i] /= recommendCase.__len__()
        return topK

    @staticmethod
    def MRR(recommendCase, answerCase, k=5):
        """MRR �������Ϊ���Ԥ���ʵ�ʵ��Ƽ��б���б�"""
        MMR = [0 for x in range(0, k)]
        for i in range(0, k):
            totalScore = 0
            if recommendCase.__len__() != answerCase.__len__():
                raise Exception("case is not right")
            casePos = 0
            for recommendList in recommendCase:
                # print("recommend:", recommendList)
                answerList = answerCase[casePos]
                # print("answerList:", answerList)
                recommendList = recommendList[0:i + 1]
                casePos += 1
                listPos = 0
                firstFind = False
                for recommend in recommendList:
                    if firstFind:
                        break
                    index = -1
                    try:
                        index = answerList.index(recommend)
                    except Exception as e:
                        pass
                    if index != -1:
                        totalScore += 1.0 / (listPos + 1)  # ��һ����ȷ��Ա����������
                        firstFind = True
                        break
                    else:
                        listPos += 1
                # print("score:", totalScore)
            MMR[i] = totalScore / recommendCase.__len__()
        return MMR

    @staticmethod
    def precisionK(recommendCase, answerCase, k=5):
        """top k precision
           top k recall
           top k f-measure
           �������Ϊ���Ԥ���ʵ�ʵ��Ƽ��б���б�"""
        precisonk = [0 for x in range(0, k)]
        recallk = [0 for x in range(0, k)]
        fmeasurek = [0 for x in range(0, k)]
        if recommendCase.__len__() != answerCase.__len__():
            raise Exception("case is not right")

        for i in range(0, k):
            totalPrecisionScore = 0
            totalRecallScore = 0
            casePos = 0
            for recommendList in recommendCase:
                answerList = answerCase[casePos]
                recommendList = recommendList[0:i + 1]
                casePos += 1

                precision = [x for x in recommendList if x in answerList].__len__() / recommendList.__len__()
                recall = [x for x in answerList if x in recommendList].__len__() / answerList.__len__()
                totalPrecisionScore += precision
                totalRecallScore += recall
            totalPrecisionScore /= recommendCase.__len__()
            totalRecallScore /= recommendCase.__len__()
            fmeasure = (2 * totalPrecisionScore * totalRecallScore) / (totalRecallScore + totalPrecisionScore)
            precisonk[i] = totalPrecisionScore
            recallk[i] = totalRecallScore
            fmeasurek[i] = fmeasure
        return precisonk, recallk, fmeasurek
