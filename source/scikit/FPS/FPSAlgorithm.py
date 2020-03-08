# coding=gbk
from source.config.configPraser import configPraser
from source.scikit.service.BeanNumpyHelper import BeanNumpyHelper
from source.utils.StringKeyUtils import StringKeyUtils


class FPSAlgorithm:
    """File Path Similarity �㷨ʵ����"""

    @staticmethod
    def reviewerRecommend(reviews, reviewsIndex, commits, commitsIndex, files, filesIndex,
                          reviewCommitIndex, commitFileIndex, targetReviewPos, reviewerNumber):
        """input: review���ݣ�commit���ݣ�file����, ��Ҫ�Ƽ���review�� review�Ƽ�������
           output: reviewers �Ƽ�list"""

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

        for pos in range(targetReviewPos + 1, reviews.__len__()):

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
                    print(targetFilename, filename)
                    scores[0] += FPSAlgorithm.LCP(targetFilename, filename)
                    scores[1] += FPSAlgorithm.LCS(targetFilename, filename)
                    scores[2] += FPSAlgorithm.LCSubstr(targetFilename, filename)
                    scores[3] += FPSAlgorithm.LCSubseq(targetFilename, filename)

            for i in range(0, 4):  # ������һ��
                scores[i] = scores[i]/(targetFilenameList.__len__()*filenameList.__len__())

            LCPScoreDict[review.user_login] += scores[0]
            LCSScoreDict[review.user_login] += scores[1]
            LCSubstrScoreDict[review.user_login] += scores[2]
            LCSubseqScoreDict[review.user_login] += scores[3]

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
        if configPraser.getPrintMode():
            print("Longest common pre:", pre)
        return pre

    @staticmethod
    def LCS(path1, path2):
        """�������׺"""
        list1 = FPSAlgorithm.getSplitFilePath(path1)
        list2 = FPSAlgorithm.getSplitFilePath(path2)
        suf = 0
        length = min(list1.__len__(), list2.__len__())
        for i in range(0, length):
            if list1[list1.__len__()-1-i] == list2[list2.__len__()-1-i]:
                suf += 1
            else:
                break
        if configPraser.getPrintMode():
            print("Longest common suffix:", suf)
        return suf

    @staticmethod
    def LCSubstr(path1, path2):
        """���������������ִ�"""
        list1 = FPSAlgorithm.getSplitFilePath(path1)
        list2 = FPSAlgorithm.getSplitFilePath(path2)
        print(list1.__len__(), list2.__len__())

        com = 0
        dp = [[0 for i in range(0, list2.__len__() + 1)] for i in range(0, list1.__len__() + 1)]
        for i in range(1, list1.__len__() + 1):
            for j in range(1, list2.__len__() + 1):
                if list1[i-1] == list2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                    com = max(com, dp[i][j])
                else:
                    dp[i][j] = 0
        if configPraser.getPrintMode():
            print("Longest common subString", com)
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
                if list1[i-1] == list2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        com = dp[list1.__len__()][list2.__len__()]
        if configPraser.getPrintMode():
            print("Longest common subString", com)
        return com
