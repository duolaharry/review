# coding=gbk
from datetime import datetime

from source.config.configPraser import configPraser
from source.scikit.service.BeanNumpyHelper import BeanNumpyHelper
from source.scikit.service.SortAlgorithmUtils import SortAlgorithmUtils
from source.utils.StringKeyUtils import StringKeyUtils


class FPSAlgorithm:
    """File Path Similarity 算法实现类"""

    @staticmethod
    def reviewerRecommend(pullrequests, pullrequestsIndex, reviews, reviewsIndex, commits,
                          commitsIndex, files, filesIndex, pullRequestreviewIndex,
                          reviewCommitIndex, commitFileIndex, targetReviewPos, reviewerNumber):
        """input: review数据，commit数据，file数据, 需要推荐的review， review推荐的数量
           output: reviewers 推荐list 和正确答案list"""

        """对review做日期的排序处理  时间倒序"""
        FPSAlgorithm.sortReviews(reviews, reviewsIndex)

        reviewerList = []  # reviewer推荐者的列表

        """根据目标review之前的review计算分数"""
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
            """对计算的分数做排序，出去自己的影响"""
            if candicateList.index(author):
                print("remove review author:", author)
                candicateList.remove(author)
        reviewerNumber = min(reviewerNumber, candicateList.__len__())
        answerList = [author]
        return candicateList[:reviewerNumber], answerList

    @staticmethod
    def judgeReviewerScore(reviews, reviewsIndex, commits, commitsIndex, files, filesIndex,
                           reviewCommitIndex, commitFileIndex, targetReviewPos):
        LCPScoreDict = {}  # Longest Common Prefix 算法分数
        LCSScoreDict = {}  # Longest Common Suffix 算法分数
        LCSubstrScoreDict = {}  # Longest Common Substring 算法分数
        LCSubseqScoreDict = {}  # Longest Common Subsequence 算法分数

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
            """先录入reviewer的名单"""
            if LCPScoreDict.get(review.user_login, None) is None:
                LCPScoreDict[review.user_login] = 0
                LCSScoreDict[review.user_login] = 0
                LCSubstrScoreDict[review.user_login] = 0
                LCSubseqScoreDict[review.user_login] = 0

            filenameList = FPSAlgorithm.getReviewFileList(review, reviewsIndex, commits, commitsIndex,
                                                          files, filesIndex, reviewCommitIndex, commitFileIndex)

            scores = [0, 0, 0, 0]  # 四个不同的算分
            """对review的文件做两两算分"""
            for targetFilename in targetFilenameList:
                for filename in filenameList:
                    if configPraser.getPrintMode():
                        print(targetFilename, filename)
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

            for i in range(0, 4):  # 分数归一化
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
        """计算最长前缀"""
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
        """计算最长后缀"""
        list1 = FPSAlgorithm.getSplitFilePath(path1)
        list2 = FPSAlgorithm.getSplitFilePath(path2)
        suf = 0
        length = min(list1.__len__(), list2.__len__())
        for i in range(0, length):
            if list1[list1.__len__() - 1 - i] == list2[list2.__len__() - 1 - i]:
                suf += 1
            else:
                break
        if configPraser.getPrintMode():
            print("Longest common suffix:", suf)
        return suf

    @staticmethod
    def LCSubstr(path1, path2):
        """计算连续公共子字串"""
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
        if configPraser.getPrintMode():
            print("Longest common subString", com)
        return com

    @staticmethod
    def LCSubseq(path1, path2):
        """计算最大公共子字串"""
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
        if configPraser.getPrintMode():
            print("Longest common subString", com)
        return com
