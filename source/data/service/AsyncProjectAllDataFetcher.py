# coding=gbk
import asyncio
import os
import time
from datetime import datetime
import random

from pandas import DataFrame

from source.config.configPraser import configPraser
from source.config.projectConfig import projectConfig
from source.data.service.ApiHelper import ApiHelper
from source.data.service.AsyncApiHelper import AsyncApiHelper
from source.data.service.AsyncSqlHelper import AsyncSqlHelper
from source.data.service.PRTimeLineUtils import PRTimeLineUtils
from source.database.AsyncSqlExecuteHelper import getMysqlObj
from source.database.SqlUtils import SqlUtils
from source.utils.pandas.pandasHelper import pandasHelper
from source.utils.statisticsHelper import statisticsHelper


class AsyncProjectAllDataFetcher:
    # ��ȡ��Ŀ��������Ϣ ������Ϣ�����첽��ȡ

    @staticmethod
    def getPullRequestNodes(repo_full_name, pr_numbers):
        loop = asyncio.get_event_loop()
        coro = AsyncProjectAllDataFetcher.fetchPullRequestNodes(loop, repo_full_name, pr_numbers)
        task = loop.create_task(coro)
        loop.run_until_complete(task)
        return task.result()

    @staticmethod
    async def fetchPullRequestNodes(loop, repo_full_name, pr_numbers):
        mysql = await getMysqlObj(loop)
        print("mysql init success")

        sql = "select distinct node_id from pullRequest where state = 'closed' and repo_full_name = %s and number in %s"
        results = await AsyncSqlHelper.query(mysql, sql, [repo_full_name, pr_numbers])

        return results

    @staticmethod
    def getPullRequestTimeLine(owner, repo, nodes):
        # ��ȡ�����pull request��ʱ�����������Ϣ ���������comment��ƴ��
        AsyncApiHelper.setRepo(owner, repo)
        t1 = datetime.now()

        statistic = statisticsHelper()
        statistic.startTime = t1

        semaphore = asyncio.Semaphore(configPraser.getSemaphore())  # ���ٶ���������
        loop = asyncio.get_event_loop()
        coro = getMysqlObj(loop)
        task = loop.create_task(coro)
        loop.run_until_complete(task)
        mysql = task.result()

        tasks = [asyncio.ensure_future(AsyncApiHelper.downloadRPTimeLine(nodeId, semaphore, mysql, statistic))
                 for nodeId in nodes]  # ����ͨ��nodes �����Ƕ�׽�ʡ��������
        tasks = asyncio.gather(*tasks)
        loop.run_until_complete(tasks)
        print('cost time:', datetime.now() - t1)
        return tasks.result()

    @staticmethod
    def analyzePullRequestReview(owner, repo, prTimeLine):
        AsyncApiHelper.setRepo(owner, repo)
        statistic = statisticsHelper()
        statistic.startTime = datetime.now()

        loop = asyncio.get_event_loop()
        coro = AsyncProjectAllDataFetcher.analyzePRTimeline(prTimeLine, loop, statistic)
        task = loop.create_task(coro)
        loop.run_until_complete(task)
        return task.result()

    @staticmethod
    async def analyzePRTimeline(prTimeLine, loop, statistic):
        """����prʱ���ߣ��ҳ�������change_trigger���û�"""

        """��ʼ�����ݿ�"""
        mysql = await getMysqlObj(loop)
        """����review->changes�����ó�pr->reviewer����Ч�Թ�ϵ"""
        prUsefulReviewers = []
        pairs = PRTimeLineUtils.splitTimeLine(prTimeLine)
        for pair in pairs:
            review = pair[0]
            changes = pair[1]
            """��issueComment�Һ����н����ŵ�change������Ϊ���û���������Чreview"""
            if (review.typename == StringKeyUtils.STR_KEY_ISSUE_COMMENT) and changes:
                prUsefulReviewers.append(review.user_login)
                break
            """��Ϊ��ͨreview���򿴺�������ŵ�commit�Ƿ��reviewCommit���ļ��غϵĸĶ�"""
            isUsefulReview = await AsyncApiHelper.analyzeReviewChangeTrigger(pair, mysql, statistic)
            if isUsefulReview:
                prUsefulReviewers.append(review.user_login)
        return prUsefulReviewers

    @staticmethod
    def getDataForRepository(owner, repo, limit=-1, start=-1):
        """ָ��Ŀ��owner/repo ��ȡstart��  start - limit��ŵ�pull-request���������Ϣ"""

        """�趨start �� limit"""
        if start == -1:
            # ��ȡ��Ŀpull request������ ����ʹ��ͬ��������ȡ
            requestNumber = ApiHelper(owner, repo).getMaxSolvedPullRequestNumberForProject()
            print("total pull request number:", requestNumber)

            startNumber = requestNumber
        else:
            startNumber = start

        if limit == -1:
            limit = startNumber

        """��ȡrepo��Ϣ"""
        AsyncApiHelper.setRepo(owner, repo)
        t1 = datetime.now()

        statistic = statisticsHelper()
        statistic.startTime = t1

        """�첽��Э��������ȡpull-request��Ϣ"""
        loop = asyncio.get_event_loop()
        task = [asyncio.ensure_future(AsyncProjectAllDataFetcher.preProcess(loop, limit, start, statistic))]
        tasks = asyncio.gather(*task)
        loop.run_until_complete(tasks)

        print("useful pull request:", statistic.usefulRequestNumber,
              " useful review:", statistic.usefulReviewNumber,
              " useful review comment:", statistic.usefulReviewCommentNumber,
              " useful issue comment:", statistic.usefulIssueCommentNumber,
              " useful commit:", statistic.usefulCommitNumber,
              " cost time:", datetime.now() - statistic.startTime)

    @staticmethod
    async def preProcess(loop, limit, start, statistic):
        """׼������"""
        semaphore = asyncio.Semaphore(configPraser.getSemaphore())  # ���ٶ���������
        """��ʼ�����ݿ�"""
        mysql = await getMysqlObj(loop)

        if configPraser.getPrintMode():
            print("mysql init success")

        """��Э��"""
        tasks = [asyncio.ensure_future(AsyncApiHelper.downloadInformation(pull_number, semaphore, mysql, statistic))
                 for pull_number in range(start, max(start - limit, 0), -1)]
        await asyncio.wait(tasks)

    @staticmethod
    def getUnmatchedCommits():
        # ��ȡ ���ݿ���û�л�õ�commit�㣬һ�����2000��
        t1 = datetime.now()

        statistic = statisticsHelper()
        statistic.startTime = t1

        loop = asyncio.get_event_loop()
        task = [asyncio.ensure_future(AsyncProjectAllDataFetcher.preProcessUnmatchCommits(loop, statistic))]
        tasks = asyncio.gather(*task)
        loop.run_until_complete(tasks)

        print('cost time:', datetime.now() - t1)

    @staticmethod
    async def preProcessUnmatchCommits(loop, statistic):

        semaphore = asyncio.Semaphore(configPraser.getSemaphore())  # ���ٶ���������
        mysql = await getMysqlObj(loop)

        if configPraser.getPrintMode():
            print("mysql init success")

        res = await AsyncSqlHelper.query(mysql, SqlUtils.STR_SQL_QUERY_UNMATCH_COMMITS, None)
        print(res)

        tasks = [asyncio.ensure_future(AsyncApiHelper.downloadCommits(item[0], item[1], semaphore, mysql, statistic))
                 for item in res]  # ����ͨ��nodes �����Ƕ�׽�ʡ��������
        await asyncio.wait(tasks)

    @staticmethod
    def getPRTimeLinesByTrainData():
        date = (2018, 1, 2019, 12)
        """�����ȡ��Ҫfetch��PR"""
        df = None
        for i in range(date[0] * 12 + date[1], date[2] * 12 + date[3] + 1):  # ��ֵ�������ƴ��
            y = int((i - i % 12) / 12)
            m = i % 12
            if m == 0:
                m = 12
                y = y - 1
            filename = projectConfig.getFPSDataPath() + os.sep + f'FPS_{configPraser.getRepo()}_data_{y}_{m}_to_{y}_{m}.tsv'
            df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD)
            df.reset_index(inplace=True, drop=True)
            pr_node_numbers = list(set(df['pull_number'].tolist()))
            # ����ÿ��fetch������
            prFetchLimit = 30
            pos = 0
            size = pr_node_numbers.__len__()
            beginTime = datetime.now()
            while pos < size:
                Logger.logi("--------------begin to fetch {0} pr_timeline---------------".format(filename))
                loop_begin_time = datetime.now()
                Logger.logi("start: {0}, end: {1}, all: {2}".format(pos, pos + prFetchLimit, size))
                sub_pr_node_numbers = pr_node_numbers[pos:pos + prFetchLimit]
                pr_nodes = AsyncProjectAllDataFetcher.getPullRequestNodes(
                    configPraser.getOwner() + "/" + configPraser.getRepo(), sub_pr_node_numbers)
                pr_nodes = list(pr_nodes)
                pr_nodes = [node[0] for node in pr_nodes]
                pr_timelines = AsyncProjectAllDataFetcher.getPullRequestTimeLine(owner=configPraser.getOwner(),
                                                                                 repo=configPraser.getRepo(),
                                                                                 nodes=pr_nodes)
                Logger.logi("fetched {0} pr_timelines, cost time: {1}".format(pr_timelines.__len__(),
                                                                              datetime.now() - loop_begin_time))
                Logger.logi("--------------end---------------")
                pos += prFetchLimit
                sleepSec = random.randint(10, 20)
                Logger.logi("sleep {0}s...".format(sleepSec))
                time.sleep(sleepSec)

    @staticmethod
    def getPRUsefulReviewer(pr_timelines):
        """����pr_timeline�����й��׵�reviewer�����������й�change_trigger���û���"""
        pr_useful_reviewer_relation = DataFrame(
            columns=[StringKeyUtils.STR_KEY_PULL_NUMBER, StringKeyUtils.STR_KEY_USER_LOGIN])
        for pr_timeline in pr_timelines:
            """����pr_timeline���ҳ��й��׵�reviewer�б�"""
            pr_useful_reviewers = AsyncProjectAllDataFetcher.analyzePullRequestReview(pr_timeline)
            for reviewer in pr_useful_reviewers:
                pr_useful_reviewer_relation.append({StringKeyUtils.STR_KEY_PULL_NUMBER: pr_timeline.pull_request_id,
                                                    StringKeyUtils.STR_KEY_USER_LOGIN: reviewer}, ignore_index=True)


        """��pr->�й��׵�reviewer��ϵ������У���FPS��IR���㷨ʹ��"""
        # filename = projectConfig.getFPSDataPath() + os.sep + f'FPS_{configPraser.getRepo()}_data_{y}_{m}_to_{y}_{m}_userful_reviewer.tsv'
        # pandasHelper.writeTSVFile(filename, pr_useful_reviewer_relation)


if __name__ == '__main__':
    pr_nodes = ["MDExOlB1bGxSZXF1ZXN0MTY3MjI1ODU5"]
    AsyncProjectAllDataFetcher.getPullRequestTimeLine(owner=configPraser.getOwner(), repo=configPraser.getRepo(),
                                                      nodes=pr_nodes)
    # data = pandasHelper.readTSVFile(projectConfig.getChangeTriggerPRPath(), pandasHelper.INT_READ_FILE_WITHOUT_HEAD)
    # print(data.values.shape)
    # node_to = configPraser.getStart()
    # node_from = max(configPraser.getStart() - configPraser.getLimit(), 0)
    # data.drop([0])
    # pr_nodes = data.iloc[1:, 3].tolist()
    #
    # AsyncProjectAllDataFetcher.getUnmatchedCommits()
