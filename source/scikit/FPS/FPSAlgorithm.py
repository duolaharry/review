# coding=gbk
from datetime import datetime

from source.config.configPraser import configPraser
from source.scikit.service.BeanNumpyHelper import BeanNumpyHelper
from source.scikit.service.SortAlgorithmUtils import SortAlgorithmUtils
from source.utils.StringKeyUtils import StringKeyUtils


class FPSAlgorithm:
    """File Path Similarity �㷨ʵ����"""

    @staticmethod
    def reviewerRecommend(pullrequests, pullrequestsIndex, reviews, reviewsIndex, commits,
                          commitsIndex, files, filesIndex, pullRequestreviewIndex,
                          reviewCommitIndex, commitFileIndex, targetReviewPos, reviewerNumber):
        """input: review���ݣ�commit���ݣ�file����, ��Ҫ�Ƽ���review�� review�Ƽ�������
           output: reviewers �Ƽ�list ����ȷ��list"""

        """��review�����ڵ�������  ʱ�䵹��"""
        FPSAlgorithm.sortReviews(reviews, reviewsIndex)

        reviewerList = []  # reviewer�Ƽ��ߵ��б�

        """����Ŀ��review֮ǰ��review�������"""
        LCPScoreDict, LCSScoreDict, LCSubstrScoreDict, LCSubseqScoreDict \
            = FPSAlgorithm.judgeReviewerScore(reviews, reviewsIndex, commits, commitsIndex,
                                              files, filesIndex, reviewCommitIndex,
                                              commitFileIndex, targetReviewPos)

        print(LCPScoreDict)
        print(LCSScoreDict)
        print(LCSubstrScoreDict)
        print(LCSubseqScoreDict)

        LCPScoreList = SortAlgorithmUtils.dictScoreConvertToList(LCPScoreDict)
        LCSScoreList = SortAlgorithmUtils.dictScoreConvertToList(LCSScoreDict)
        LCSubstrScoreList = SortAlgorithmUtils.dictScoreConvertToList(LCSubstrScoreDict)
        LCSubseqScoreList = SortAlgorithmUtils.dictScoreConvertToList(LCSubseqScoreDict)

        print(LCPScoreList)
        print(LCSScoreList)
        print(LCSubstrScoreList)
        print(LCSubseqScoreList)

        candicateList = SortAlgorithmUtils.BordaCountSort([LCPScoreList, LCSScoreList,
                                                           LCSubstrScoreList, LCSubseqScoreList])
        print(candicateList)

        print(reviews[targetReviewPos].getValueDict())

        author = \
            pullrequests[pullrequestsIndex[(reviews[targetReviewPos].repo_full_name,
                                            reviews[targetReviewPos].pull_number)]].user_login

        if configPraser.getFPSRemoveAuthor():
            """�Լ���ķ��������򣬳�ȥ�Լ���Ӱ��"""
            if candicateList.index(author):
                print("remove review author:", author)
                candicateList.remove(author)
        reviewerNumber = min(reviewerNumber, candicateList.__len__())
        answerList = [author]
        return candicateList[:reviewerNumber], answerList

    @staticmethod
    def judgeReviewerScore(reviews, reviewsIndex, commits, commitsIndex, files, filesIndex,
                           reviewCommitIndex, commitFileIndex, targetReviewPos):
        LCPScoreDict = {}  # Longest Common Prefix �㷨����
        LCSScoreDict = {}  # Longest Common Suffix �㷨����
        LCSubstrScoreDict = {}  # Longest Common Substring �㷨����
        LCSubseqScoreDict = {}  # Longest Common Subsequence �㷨����

        targetReview = reviews[targetReviewPos]

        targetFilenameList = FPSAlgorithm.getReviewFileList(targetReview, reviewsIndex, commits, commitsIndex,
                                                            files, filesIndex, reviewCommitIndex, commitFileIndex)

        print(reviews.__len__())

        # time1 = datetime.now()

        t1 = 0
        t2 = 0
        t3 = 0
        t4 = 0

        for pos in range(targetReviewPos + 1, reviews.__len__()):

            # time2 = datetime.now()
            # print("pos:", pos, "cost time:", time2 - time1)

            review = reviews[pos]
            """��¼��reviewer������"""
            if LCPScoreDict.get(review.user_login, None) is None:
                LCPScoreDict[review.user_login] = 0
                LCSScoreDict[review.user_login] = 0
                LCSubstrScoreDict[review.user_login] = 0
                LCSubseqScoreDict[review.user_login] = 0

            filenameList = FPSAlgorithm.getReviewFileList(review, reviewsIndex, commits, commitsIndex,
                                                          files, filesIndex, reviewCommitIndex, commitFileIndex)

            scores = [0, 0, 0, 0]  # �ĸ���ͬ�����
            """��review���ļ����������"""
            for targetFilename in targetFilenameList:
                for filename in filenameList:
                    # if configPraser.getPrintMode():
                    #     print(targetFilename, filename)
                    time1 = datetime.now()
                    scores[0] += FPSAlgorithm.LCP(targetFilename, filename)
                    time2 = datetime.now()
                    scores[1] += FPSAlgorithm.LCS(targetFilename, filename)
                    time3 = datetime.now()
                    scores[2] += FPSAlgorithm.LCSubstr(targetFilename, filename)
                    time4 = datetime.now()
                    scores[3] += FPSAlgorithm.LCSubseq(targetFilename, filename)
                    time5 = datetime.now()
                    t1 += (time2 - time1).microseconds
                    t2 += (time3 - time2).microseconds
                    t3 += (time4 - time3).microseconds
                    t4 += (time5 - time4).microseconds

            for i in range(0, 4):  # ������һ��
                scores[i] = scores[i] / (targetFilenameList.__len__() * filenameList.__len__())

            LCPScoreDict[review.user_login] += scores[0]
            LCSScoreDict[review.user_login] += scores[1]
            LCSubstrScoreDict[review.user_login] += scores[2]
            LCSubseqScoreDict[review.user_login] += scores[3]

        print(t1)
        print(t2)
        print(t3)
        print(t4)

        return LCPScoreDict, LCSScoreDict, LCSubstrScoreDict, LCSubseqScoreDict

    @staticmethod
    def sortReviews(reviews, reviewsIndex):
        # print(reviews)
        # print(reviewsIndex.__len__())
        reviews.sort(key=lambda review: review.submitted_at, reverse=True)
        # print(reviews)
        pos = 0
        for review in reviews:
            identifyTuple = BeanNumpyHelper.getBeanIdentifyTuple(review)
            reviewsIndex[identifyTuple] = pos
            pos += 1

    @staticmethod
    def getReviewFileList(review, reviewsIndex, commits, commitsIndex
                          , files, filesIndex, reviewCommitIndex, commitFileIndex):
        res = []
        reviewTuple = BeanNumpyHelper.getBeanIdentifyTuple(review)
        commitsSHAList = reviewCommitIndex[reviewTuple]
        for commitsSHA in commitsSHAList:
            commit = commits[commitsIndex[commitsSHA]]
            commitTuple = BeanNumpyHelper.getBeanIdentifyTuple(commit)
            fileIndexList = commitFileIndex[commitTuple]
            for index in fileIndexList:
                res.append(files[filesIndex[index]].filename)
        return res

    @staticmethod
    def getSplitFilePath(path, sep=StringKeyUtils.STR_SPLIT_SEP_TWO):
        return path.split(sep)

    @staticmethod
    def LCP(path1, path2):
        """�����ǰ׺"""
        list1 = FPSAlgorithm.getSplitFilePath(path1)
        list2 = FPSAlgorithm.getSplitFilePath(path2)
        pre = 0
        length = min(list1.__len__(), list2.__len__())
        for i in range(0, length):
            if list1[i] == list2[i]:
                pre += 1
            else:
                break
        # if configPraser.getPrintMode():
        #     print("Longest common pre:", pre)
        return pre

    @staticmethod
    def LCS(path1, path2):
        """�������׺"""
        list1 = FPSAlgorithm.getSplitFilePath(path1)
        list2 = FPSAlgorithm.getSplitFilePath(path2)
        suf = 0
        length = min(list1.__len__(), list2.__len__())
        for i in range(0, length):
            if list1[list1.__len__() - 1 - i] == list2[list2.__len__() - 1 - i]:
                suf += 1
            else:
                break
        # if configPraser.getPrintMode():
        #     print("Longest common suffix:", suf)
        return suf

    @staticmethod
    def LCSubstr(path1, path2):
        """���������������ִ�"""
        list1 = FPSAlgorithm.getSplitFilePath(path1)
        list2 = FPSAlgorithm.getSplitFilePath(path2)
        com = 0
        dp = [[0 for i in range(0, list2.__len__() + 1)] for i in range(0, list1.__len__() + 1)]
        for i in range(1, list1.__len__() + 1):
            for j in range(1, list2.__len__() + 1):
                if list1[i - 1] == list2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                    com = max(com, dp[i][j])
                else:
                    dp[i][j] = 0
        # if configPraser.getPrintMode():
        #     print("Longest common subString", com)
        return com

    @staticmethod
    def LCSubseq(path1, path2):
        """������󹫹����ִ�"""
        list1 = FPSAlgorithm.getSplitFilePath(path1)
        list2 = FPSAlgorithm.getSplitFilePath(path2)

        com = 0
        dp = [[0 for i in range(0, list2.__len__() + 1)] for i in range(0, list1.__len__() + 1)]
        for i in range(1, list1.__len__() + 1):
            for j in range(1, list2.__len__() + 1):
                if list1[i - 1] == list2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        com = dp[list1.__len__()][list2.__len__()]
        # if configPraser.getPrintMode():
        #     print("Longest common subString", com)
        return com

    @staticmethod
    def LCS_2(path1, path2):
        """�������׺"""
        list1 = FPSAlgorithm.getSplitFilePath(path1)
        list2 = FPSAlgorithm.getSplitFilePath(path2)
        suf = 0
        length = min(list1.__len__(), list2.__len__())
        for i in range(0, length):
            if list1[list1.__len__() - 1 - i] == list2[list2.__len__() - 1 - i]:
                suf += 1
            else:
                break
        score = suf / max(list1.__len__(), list2.__len__())
        return score

    @staticmethod
    def LCP_2(path1, path2):
        """�����ǰ׺"""
        list1 = FPSAlgorithm.getSplitFilePath(path1)
        list2 = FPSAlgorithm.getSplitFilePath(path2)
        pre = 0
        length = min(list1.__len__(), list2.__len__())
        for i in range(0, length):
            if list1[i] == list2[i]:
                pre += 1
            else:
                break
        # if configPraser.getPrintMode():
        #     print("Longest common pre:", pre)
        return pre / max(list1.__len__(), list2.__len__())

    @staticmethod
    def LCSubseq_2(path1, path2):
        """������󹫹����ִ�"""
        list1 = FPSAlgorithm.getSplitFilePath(path1)
        list2 = FPSAlgorithm.getSplitFilePath(path2)

        com = 0
        dp = [[0 for i in range(0, list2.__len__() + 1)] for i in range(0, list1.__len__() + 1)]
        for i in range(1, list1.__len__() + 1):
            for j in range(1, list2.__len__() + 1):
                if list1[i - 1] == list2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        com = dp[list1.__len__()][list2.__len__()]
        # if configPraser.getPrintMode():
        #     print("Longest common subString", com)
        return com / max(list1.__len__(), list2.__len__())

    @staticmethod
    def LCSubstr_2(path1, path2):
        """���������������ִ�"""
        list1 = FPSAlgorithm.getSplitFilePath(path1)
        list2 = FPSAlgorithm.getSplitFilePath(path2)
        com = 0
        dp = [[0 for i in range(0, list2.__len__() + 1)] for i in range(0, list1.__len__() + 1)]
        for i in range(1, list1.__len__() + 1):
            for j in range(1, list2.__len__() + 1):
                if list1[i - 1] == list2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                    com = max(com, dp[i][j])
                else:
                    dp[i][j] = 0
        # if configPraser.getPrintMode():
        #     print("Longest common subString", com)
        return com / max(list1.__len__(), list2.__len__())

    @staticmethod
    def reviewerRecommendByNumpy(trainData, targetData, review_size, k=2):
        """input: ��ʷ���ݣ�Ŀ��review����, ��ʷ����ÿһ��reivew���ļ������� review�Ƽ�������  Ĭ��targetData��id����һ��
           output: reviewers �Ƽ�list ����ȷ��list"""

        scores = {}  # ��¼�Ƽ��ߵĵ÷�

        answerList = []  # �����б�

        targetFileCount = targetData.shape[0]  # ���review���ļ����� fixbug

        print(trainData.shape)
        print(targetData.shape)

        for target in targetData.itertuples():
            answer = getattr(target, StringKeyUtils.STR_KEY_USER_LOGIN)
            filename1 = getattr(target, StringKeyUtils.STR_KEY_FILENAME)
            if answer not in answerList:
                answerList.append(answer)
            for data in trainData.itertuples():
                """���ļ���������"""
                reviewer = getattr(data, StringKeyUtils.STR_KEY_USER_LOGIN)
                review_id = getattr(data, StringKeyUtils.STR_KEY_ID)
                # dataFileCount = trainData.loc[trainData[StringKeyUtils.STR_KEY_ID] == review_id].shape[0]
                dataFileCount = review_size[review_id]

                if scores.get(reviewer, None) is None:
                    scores[reviewer] = 0
                filename2 = getattr(data, StringKeyUtils.STR_KEY_FILENAME)
                # print("filename1:", filename1, " filename2:", filename2)
                # print(f"dataFileCount:{dataFileCount}, targetFileCount:{targetFileCount}")
                scores[reviewer] += (FPSAlgorithm.LCSubseq_2(filename1, filename2)) / (dataFileCount * targetFileCount)
                # + FPSAlgorithm.LCP_2(filename1, filename2)
                # + FPSAlgorithm.LCSubseq_2(filename1, filename2)
                # + FPSAlgorithm.LCSubstr_2(filename1, filename2)) / (dataFileCount * targetFileCount)

        # print(scores)
        return [x[0] for x in sorted(scores.items(), key=lambda d: d[1], reverse=True)[0:k - 1]], answerList

    @staticmethod
    def RecommendByFPS(train_data, train_data_y, test_data, test_data_y, recommendNum=5):
        """���ǩ�����FPS"""

        recommendList = []
        answerList = []
        testDict = dict(list(test_data.groupby('pull_number')))
        trainDict = dict(list(train_data.groupby('pull_number')))

        for test_pull_number, test_df in testDict.items():
            scores = {}  # ��ʼ�������ֵ�
            """�����ȷ��"""
            answerList.append(test_data_y[test_pull_number])
            for train_pull_number, train_df in trainDict.items():
                paths1 = list(train_df['file_filename'])
                paths2 = list(test_df['file_filename'])
                score = 0
                for filename1 in paths1:
                    for filename2 in paths2:
                        score += FPSAlgorithm.LCS_2(filename1, filename2) + \
                                 FPSAlgorithm.LCSubseq_2(filename1, filename2) +\
                                 FPSAlgorithm.LCP_2(filename1, filename2) +\
                                 FPSAlgorithm.LCSubstr_2(filename1, filename2)
                score /= paths1.__len__() * paths2.__len__()
                for reviewer in train_data_y[train_pull_number]:
                    if scores.get(reviewer, None) is None:
                        scores[reviewer] = 0
                    scores[reviewer] += score
            recommendList.append([x[0] for x in sorted(scores.items(),
                                                       key=lambda d: d[1], reverse=True)[0:recommendNum - 1]])

        return [recommendList, answerList]

















