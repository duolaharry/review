# coding=gbk
import asyncio
import time
from datetime import datetime

from source.config.configPraser import configPraser
from source.config.projectConfig import projectConfig
from source.data.service.ApiHelper import ApiHelper
from source.data.service.AsyncApiHelper import AsyncApiHelper
from source.data.service.AsyncSqlHelper import AsyncSqlHelper
from source.database.AsyncSqlExecuteHelper import getMysqlObj
from source.database.SqlUtils import SqlUtils
from source.utils.pandas.pandasHelper import pandasHelper
from source.utils.statisticsHelper import statisticsHelper


class AsyncProjectAllDataFetcher:
    # ��ȡ��Ŀ��������Ϣ ������Ϣ�����첽��ȡ

    @staticmethod
    def getPullRequestTimeLine(owner, repo, nodes):
        # ��ȡ�����pull request��ʱ�����������Ϣ ���������comment��ƴ��
        AsyncApiHelper.setRepo(owner, repo)
        t1 = datetime.now()

        statistic = statisticsHelper()
        statistic.startTime = t1

        loop = asyncio.get_event_loop()
        task = [asyncio.ensure_future(AsyncProjectAllDataFetcher.preProcessTimeLine(loop, nodes, statistic))]
        tasks = asyncio.gather(*task)
        loop.run_until_complete(tasks)

        print('cost time:', datetime.now() - t1)

    @staticmethod
    async def preProcessTimeLine(loop, node, statistic):

        semaphore = asyncio.Semaphore(configPraser.getSemaphore())  # ���ٶ���������
        mysql = await getMysqlObj(loop)

        if configPraser.getPrintMode():
            print("mysql init success")

        tasks = [asyncio.ensure_future(AsyncApiHelper.downloadRPTimeLine(nodeIds, semaphore, mysql, statistic))
                 for nodeIds in node]  # ����ͨ��nodes �����Ƕ�׽�ʡ��������
        await asyncio.wait(tasks)

    @staticmethod
    def getDataForRepository(owner, repo, limit=-1, start=-1):

        if start == -1:
            # ��ȡ��Ŀpull request������ ����ʹ��ͬ��������ȡ
            requestNumber = ApiHelper(owner, repo).getMaxSolvedPullRequestNumberForProject()
            print("total pull request number:", requestNumber)

            startNumber = requestNumber
        else:
            startNumber = start

        if limit == -1:
            limit = startNumber

        AsyncApiHelper.setRepo(owner, repo)
        t1 = datetime.now()

        statistic = statisticsHelper()
        statistic.startTime = t1

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

        semaphore = asyncio.Semaphore(configPraser.getSemaphore())  # ���ٶ���������
        mysql = await getMysqlObj(loop)

        if configPraser.getPrintMode():
            print("mysql init success")

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


if __name__ == '__main__':
    # AsyncProjectAllDataFetcher.getDataForRepository(owner=configPraser.getOwner(), repo=configPraser.getRepo()
    #                                                 , start=configPraser.getStart(), limit=configPraser.getLimit())

    # data = pandasHelper.readTSVFile(projectConfig.getChangeTriggerPRPath(), pandasHelper.INT_READ_FILE_WITHOUT_HEAD)
    # print(data.as_matrix().shape)
    # node_to = configPraser.getStart()
    # node_from = max(configPraser.getStart() - configPraser.getLimit(), 0)
    # pr_nodes = data.as_matrix()[node_from:node_to, 3]
    # print(pr_nodes.__len__())
    #
    # AsyncProjectAllDataFetcher.getPullRequestTimeLine(owner=configPraser.getOwner(), repo=configPraser.getRepo(),
    #                                                   nodes=[[x] for x in pr_nodes])

    AsyncProjectAllDataFetcher.getUnmatchedCommits()