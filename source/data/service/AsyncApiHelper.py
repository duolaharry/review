# coding=gbk
import asyncio
import json
import random
import time
import traceback
from datetime import datetime

import aiohttp

from source.config.configPraser import configPraser
from source.data.bean.CommentRelation import CommitRelation
from source.data.bean.Commit import Commit
from source.data.bean.CommitPRRelation import CommitPRRelation
from source.data.bean.IssueComment import IssueComment
from source.data.bean.PRTimeLineRelation import PRTimeLineRelation
from source.data.bean.PullRequest import PullRequest
from source.data.bean.Review import Review
from source.data.bean.ReviewComment import ReviewComment
from source.data.service.AsyncSqlHelper import AsyncSqlHelper
from source.data.service.GraphqlHelper import GraphqlHelper
from source.data.service.PRTimeLineUtils import PRTimeLineUtils
from source.data.service.ProxyHelper import ProxyHelper
from source.utils.StringKeyUtils import StringKeyUtils


class AsyncApiHelper:
    """ʹ��aiohttp�첽ͨѶ"""

    owner = None
    repo = None

    @staticmethod
    def setRepo(owner, repo):  # ʹ��֮ǰ������Ŀ����������
        AsyncApiHelper.owner = owner
        AsyncApiHelper.repo = repo

    @staticmethod
    def getAuthorizationHeaders(header):
        if header is not None and isinstance(header, dict):
            if configPraser.getAuthorizationToken():
                header[StringKeyUtils.STR_HEADER_AUTHORIZAITON] = (StringKeyUtils.STR_HEADER_TOKEN
                                                                   + configPraser.getAuthorizationToken())
        return header

    @staticmethod
    def getUserAgentHeaders(header):
        if header is not None and isinstance(header, dict):
            # header[self.STR_HEADER_USER_AGENT] = self.STR_HEADER_USER_AGENT_SET
            header[StringKeyUtils.STR_HEADER_USER_AGENT] = random.choice(StringKeyUtils.USER_AGENTS)
        return header

    @staticmethod
    def getMediaTypeHeaders(header):
        if header is not None and isinstance(header, dict):
            header[StringKeyUtils.STR_HEADER_ACCEPT] = StringKeyUtils.STR_HEADER_MEDIA_TYPE
        return header

    @staticmethod
    async def getProxy():
        if configPraser.getProxy():
            proxy = await ProxyHelper.getAsyncSingleProxy()
            if configPraser.getPrintMode():
                print(proxy)
            if proxy is not None:
                return StringKeyUtils.STR_PROXY_HTTP_FORMAT.format(proxy)
        return None

    @staticmethod
    async def parserPullRequest(resultJson):
        try:
            if not AsyncApiHelper.judgeNotFind(resultJson):
                res = PullRequest.parser.parser(resultJson)
                if res is not None and res.base is not None:
                    res.repo_full_name = res.base.repo_full_name  # ��pull_request��repo_full_name ��һ����ȫ
                return res
        except Exception as e:
            print(e)

    @staticmethod
    def judgeNotFind(resultJson):
        if resultJson is not None and isinstance(json, dict):
            if resultJson.get(StringKeyUtils.STR_KEY_MESSAGE) == StringKeyUtils.STR_NOT_FIND:
                return True
            if resultJson.get(StringKeyUtils.STR_KEY_MESSAGE) == StringKeyUtils.STR_FAILED_FETCH:
                return True
        return False

    @staticmethod
    async def downloadInformation(pull_number, semaphore, mysql, statistic):
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                try:
                    beanList = []  # �����ռ���Ҫ�洢��bean��
                    """�Ȼ�ȡpull request��Ϣ"""
                    api = AsyncApiHelper.getPullRequestApi(pull_number)
                    json = await AsyncApiHelper.fetchBeanData(session, api)
                    pull_request = await AsyncApiHelper.parserPullRequest(json)
                    print(pull_request)
                    usefulPullRequestsCount = 0
                    usefulReviewsCount = 0
                    usefulReviewCommentsCount = 0
                    usefulIssueCommentsCount = 0
                    usefulCommitsCount = 0

                    if pull_request is not None:
                        usefulPullRequestsCount = 1
                        beanList.append(pull_request)

                        if pull_request.head is not None:
                            beanList.append(pull_request.head)
                        if pull_request.base is not None:
                            beanList.append(pull_request.base)
                        if pull_request.user is not None:
                            beanList.append(pull_request.user)

                        """��ȡreview��Ϣ"""
                        api = AsyncApiHelper.getReviewForPullRequestApi(pull_number)
                        json = await AsyncApiHelper.fetchBeanData(session, api)
                        reviews = await AsyncApiHelper.parserReview(json, pull_number)
                        if configPraser.getPrintMode():
                            print(reviews)

                        usefulReviewsCount = 0
                        if reviews is not None:
                            for review in reviews:
                                usefulReviewsCount += 1
                                beanList.append(review)
                                if review.user is not None:
                                    beanList.append(review.user)

                        """��ȡreview comment��Ϣ"""
                        api = AsyncApiHelper.getReviewCommentForPullRequestApi(pull_number)
                        json = await AsyncApiHelper.fetchBeanData(session, api, isMediaType=True)
                        reviewComments = await AsyncApiHelper.parserReviewComment(json)

                        if configPraser.getPrintMode():
                            print(reviewComments)
                        usefulReviewCommentsCount = 0
                        if reviewComments is not None:
                            for reviewComment in reviewComments:
                                usefulReviewCommentsCount += 1
                                beanList.append(reviewComment)
                                if reviewComment.user is not None:
                                    beanList.append(reviewComment.user)

                        '''��ȡ pull request��Ӧ��issue comment��Ϣ'''
                        api = AsyncApiHelper.getIssueCommentForPullRequestApi(pull_number)
                        json = await AsyncApiHelper.fetchBeanData(session, api, isMediaType=True)
                        issueComments = await  AsyncApiHelper.parserIssueComment(json, pull_number)
                        usefulIssueCommentsCount = 0
                        if issueComments is not None:
                            for issueComment in issueComments:
                                usefulIssueCommentsCount += 1
                                beanList.append(issueComment)
                                if issueComment.user is not None:
                                    beanList.append(issueComment.user)

                        '''��ȡ pull request��Ӧ��commit��Ϣ'''
                        api = AsyncApiHelper.getCommitForPullRequestApi(pull_number)
                        json = await AsyncApiHelper.fetchBeanData(session, api, isMediaType=True)
                        Commits, Relations = await AsyncApiHelper.parserCommitAndRelation(json, pull_number)
                        usefulCommitsCount = 0
                        for commit in Commits:
                            if commit is not None:
                                usefulCommitsCount += 1
                                api = AsyncApiHelper.getCommitApi(commit.sha)
                                json = await AsyncApiHelper.fetchBeanData(session, api)
                                commit = await AsyncApiHelper.parserCommit(json)
                                beanList.append(commit)

                                if commit.committer is not None:
                                    beanList.append(commit.committer)
                                if commit.author is not None:
                                    beanList.append(commit.author)
                                if commit.files is not None:
                                    for file in commit.files:
                                        beanList.append(file)
                                if commit.parents is not None:
                                    for parent in commit.parents:
                                        beanList.append(parent)
                                """��Ϊ��Դ��Լ   commit comment�����ɼ�"""

                        for relation in Relations:
                            beanList.append(relation)

                        print(beanList)

                    await AsyncSqlHelper.storeBeanDateList(beanList, mysql)

                    # ����ͬ������
                    statistic.lock.acquire()
                    statistic.usefulRequestNumber += usefulPullRequestsCount
                    statistic.usefulReviewNumber += usefulReviewsCount
                    statistic.usefulReviewCommentNumber += usefulReviewCommentsCount
                    statistic.usefulIssueCommentNumber += usefulIssueCommentsCount
                    statistic.usefulCommitNumber += usefulCommitsCount
                    print("useful pull request:", statistic.usefulRequestNumber,
                          " useful review:", statistic.usefulReviewNumber,
                          " useful review comment:", statistic.usefulReviewCommentNumber,
                          " useful issue comment:", statistic.usefulIssueCommentNumber,
                          " useful commit:", statistic.usefulCommitNumber,
                          " cost time:", datetime.now() - statistic.startTime)
                    statistic.lock.release()
                except Exception as e:
                    print(e)

    @staticmethod
    async def parserReview(resultJson, pull_number):
        try:
            if not AsyncApiHelper.judgeNotFind(resultJson):
                items = []
                for item in resultJson:
                    res = Review.parser.parser(item)
                    res.repo_full_name = AsyncApiHelper.owner + '/' + AsyncApiHelper.repo  # ��repo_full_name ��һ����ȫ
                    res.pull_number = pull_number
                    items.append(res)
                return items
        except Exception as e:
            print(e)

    @staticmethod
    def getPullRequestApi(pull_number):
        api = StringKeyUtils.API_GITHUB + StringKeyUtils.API_PULL_REQUEST
        api = api.replace(StringKeyUtils.STR_OWNER, AsyncApiHelper.owner)
        api = api.replace(StringKeyUtils.STR_REPO, AsyncApiHelper.repo)
        api = api.replace(StringKeyUtils.STR_PULL_NUMBER, str(pull_number))
        return api

    @staticmethod
    def getReviewCommentForPullRequestApi(pull_number):
        api = StringKeyUtils.API_GITHUB + StringKeyUtils.API_COMMENTS_FOR_PULL_REQUEST
        api = api.replace(StringKeyUtils.STR_OWNER, AsyncApiHelper.owner)
        api = api.replace(StringKeyUtils.STR_REPO, AsyncApiHelper.repo)
        api = api.replace(StringKeyUtils.STR_PULL_NUMBER, str(pull_number))
        return api

    @staticmethod
    def getReviewForPullRequestApi(pull_number):
        api = StringKeyUtils.API_GITHUB + StringKeyUtils.API_REVIEWS_FOR_PULL_REQUEST
        api = api.replace(StringKeyUtils.STR_OWNER, AsyncApiHelper.owner)
        api = api.replace(StringKeyUtils.STR_REPO, AsyncApiHelper.repo)
        api = api.replace(StringKeyUtils.STR_PULL_NUMBER, str(pull_number))
        return api

    @staticmethod
    def getIssueCommentForPullRequestApi(issue_number):
        api = StringKeyUtils.API_GITHUB + StringKeyUtils.API_ISSUE_COMMENT_FOR_ISSUE
        api = api.replace(StringKeyUtils.STR_OWNER, AsyncApiHelper.owner)
        api = api.replace(StringKeyUtils.STR_REPO, AsyncApiHelper.repo)
        api = api.replace(StringKeyUtils.STR_ISSUE_NUMBER, str(issue_number))
        return api

    @staticmethod
    def getCommitForPullRequestApi(pull_number):
        api = StringKeyUtils.API_GITHUB + StringKeyUtils.API_COMMITS_FOR_PULL_REQUEST
        api = api.replace(StringKeyUtils.STR_OWNER, AsyncApiHelper.owner)
        api = api.replace(StringKeyUtils.STR_REPO, AsyncApiHelper.repo)
        api = api.replace(StringKeyUtils.STR_PULL_NUMBER, str(pull_number))
        return api

    @staticmethod
    def getGraphQLApi():
        api = StringKeyUtils.API_GITHUB + StringKeyUtils.API_GRAPHQL
        return api

    @staticmethod
    def getCommitApi(commit_sha):
        api = StringKeyUtils.API_GITHUB + StringKeyUtils.API_COMMIT
        api = api.replace(StringKeyUtils.STR_OWNER, AsyncApiHelper.owner)
        api = api.replace(StringKeyUtils.STR_REPO, AsyncApiHelper.repo)
        api = api.replace(StringKeyUtils.STR_COMMIT_SHA, str(commit_sha))
        return api

    @staticmethod
    async def fetchBeanData(session, api, isMediaType=False):
        headers = {}
        headers = AsyncApiHelper.getUserAgentHeaders(headers)
        headers = AsyncApiHelper.getAuthorizationHeaders(headers)
        if isMediaType:
            headers = AsyncApiHelper.getMediaTypeHeaders(headers)
        while True:
            proxy = await AsyncApiHelper.getProxy()
            if configPraser.getProxy() and proxy is None:  # �Դ����û��ip�����������
                print('no proxy and sleep!')
                await asyncio.sleep(20)
            else:
                break

        try:
            async with session.get(api, ssl=False, proxy=proxy
                    , headers=headers, timeout=configPraser.getTimeout()) as response:
                print("rate:", response.headers.get(StringKeyUtils.STR_HEADER_RATE_LIMIT_REMIAN))
                print("status:", response.status)
                if response.status == 403:
                    await ProxyHelper.judgeProxy(proxy.split('//')[1], ProxyHelper.INT_KILL_POINT)
                    raise 403
                elif proxy is not None:
                    await ProxyHelper.judgeProxy(proxy.split('//')[1], ProxyHelper.INT_POSITIVE_POINT)
                return await response.json()
        except Exception as e:
            print(e)
            if proxy is not None:
                proxy = proxy.split('//')[1]
                await ProxyHelper.judgeProxy(proxy, ProxyHelper.INT_NEGATIVE_POINT)
            # print("judge end")
            return await AsyncApiHelper.fetchBeanData(session, api, isMediaType=isMediaType)

    @staticmethod
    async def postGraphqlData(session, api, args=None):
        """ͨ�� github graphhql�ӿ� ͨ��post����"""
        headers = {}
        headers = AsyncApiHelper.getUserAgentHeaders(headers)
        headers = AsyncApiHelper.getAuthorizationHeaders(headers)

        body = {}
        body = GraphqlHelper.getTimeLineQueryByNodes(body)
        body = GraphqlHelper.getGraphqlVariables(body, args)
        bodyJson = json.dumps(body)
        # print("bodyjson:", bodyJson)

        while True:
            proxy = await AsyncApiHelper.getProxy()
            if configPraser.getProxy() and proxy is None:  # �Դ����û��ip�����������
                print('no proxy and sleep!')
                await asyncio.sleep(20)
            else:
                break

        try:
            async with session.post(api, ssl=False, proxy=proxy,
                                    headers=headers, timeout=configPraser.getTimeout(),
                                    data=bodyJson) as response:
                print("rate:", response.headers.get(StringKeyUtils.STR_HEADER_RATE_LIMIT_REMIAN))
                print("status:", response.status)
                if response.status == 403:
                    await ProxyHelper.judgeProxy(proxy.split('//')[1], ProxyHelper.INT_KILL_POINT)
                    raise 403
                elif proxy is not None:
                    await ProxyHelper.judgeProxy(proxy.split('//')[1], ProxyHelper.INT_POSITIVE_POINT)
                return await response.json()
        except Exception as e:
            print(e)
            if proxy is not None:
                proxy = proxy.split('//')[1]
                await ProxyHelper.judgeProxy(proxy, ProxyHelper.INT_NEGATIVE_POINT)
            # print("judge end")
            return await AsyncApiHelper.postGraphqlData(session, api, args)

    @staticmethod
    async def parserReviewComment(resultJson):
        try:
            if not AsyncApiHelper.judgeNotFind(resultJson):
                items = []
                for item in resultJson:
                    res = ReviewComment.parser.parser(item)
                    items.append(res)
                return items
        except Exception as e:
            print(e)

    @staticmethod
    async def parserIssueComment(resultJson, issue_number):
        try:
            if not AsyncApiHelper.judgeNotFind(json):
                items = []
                for item in resultJson:
                    res = IssueComment.parser.parser(item)
                    """��Ϣ��ȫ"""
                    res.repo_full_name = AsyncApiHelper.owner + '/' + AsyncApiHelper.repo  # ��repo_full_name ��һ����ȫ
                    res.pull_number = issue_number

                    items.append(res)
                return items
        except Exception as e:
            print(e)

    @staticmethod
    async def parserCommitAndRelation(resultJson, pull_number):
        try:
            if not AsyncApiHelper.judgeNotFind(resultJson):
                items = []
                relations = []
                for item in resultJson:
                    res = Commit.parser.parser(item)
                    relation = CommitPRRelation()
                    relation.sha = res.sha
                    relation.pull_number = pull_number
                    relation.repo_full_name = AsyncApiHelper.owner + '/' + AsyncApiHelper.repo
                    relations.append(relation)
                    items.append(res)
                return items, relations
        except Exception as e:
            print(e)

    @staticmethod
    async def parserCommit(resultJson):
        try:
            if not AsyncApiHelper.judgeNotFind(resultJson):
                res = Commit.parser.parser(resultJson)
                return res
        except Exception as e:
            print(e)

    @staticmethod
    async def parserPRItemLine(resultJson):
        try:
            if not AsyncApiHelper.judgeNotFind(resultJson):
                res, items = PRTimeLineRelation.parser.parser(resultJson)
                return res, items
        except Exception as e:
            print(e)

    @staticmethod
    async def downloadRPTimeLine(nodeIds, semaphore, mysql, statistic):
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                try:
                    args = {"ids": nodeIds}
                    """�Ȼ�ȡpull request��Ϣ"""
                    api = AsyncApiHelper.getGraphQLApi()
                    resultJson = await AsyncApiHelper.postGraphqlData(session, api, args)
                    beanList = []
                    # pull_request = await AsyncApiHelper.parserPullRequest(json)
                    # print(pull_request)
                    print(type(resultJson))
                    print("post json:", resultJson)
                    timeLineRelations, timeLineItems = await  AsyncApiHelper.parserPRItemLine(resultJson)

                    usefulTimeLineItemCount = 0
                    usefulTimeLineCount = 0

                    beanList.extend(timeLineRelations)
                    beanList.extend(timeLineItems)
                    await AsyncSqlHelper.storeBeanDateList(beanList, mysql)

                    """���ƻ�ȡ������commit ��Ϣ"""
                    pairs = PRTimeLineUtils.splitTimeLine(timeLineRelations)
                    for pair in pairs:
                        print(pair)
                        await AsyncApiHelper.completeCommitInformation(pair, mysql, session)

                    # ����ͬ������
                    statistic.lock.acquire()
                    statistic.usefulTimeLineCount += usefulTimeLineCount
                    print(f"usefulTimeLineItemCount: {usefulTimeLineCount}",
                          f" usefulTimeLineCount:{usefulTimeLineItemCount}")
                    statistic.lock.release()
                except Exception as e:
                    print(e)

    @staticmethod
    async def completeCommitInformation(pair, mysql, session):
        """���� review������¼���ص�commit"""
        review = pair[0]
        changes = pair[1]

        for change in changes:
            commit1 = review.pullrequestReviewCommit
            commit2 = None
            if change.typename == StringKeyUtils.STR_KEY_PULL_REQUEST_COMMIT:
                commit2 = change.pullrequestCommitCommit
            elif change.typename == StringKeyUtils.STR_KEY_HEAD_REF_PUSHED_EVENT:
                commit2 = change.headRefForcePushedEventAfterCommit

            loop = 0
            if commit2 is not None and commit1 is not None:

                class CommitNode:
                    willFetch = None
                    oid = None

                """Ϊ��ͳ��ʹ�õĹ�����"""

                def isNodesContains(nodes1, nodes2):
                    isContain = True
                    for node in nodes2:
                        isFind = False
                        for node1 in nodes1:
                            if node1.oid == node.oid:
                                isFind = True
                                break
                        if not isFind and node.willFetch:
                            isContain = False
                            break
                    return isContain

                def printNodes(nodes1, nodes2):
                    print('node1')
                    for node in nodes1:
                        print(node.oid, node.willFetch)
                    print('node2')
                    for node in nodes2:
                        print(node.oid, node.willFetch)

                async def fetNotFetchedNodes(nodes, mysql, session):
                    fetchList = [node.oid for node in nodes if node.willFetch]
                    """�ȳ��Դ����ݿ��ж�ȡ"""
                    localExistList, localRelationList = await AsyncApiHelper.getCommitsFromStore(fetchList, mysql)
                    fetchList = [oid for oid in fetchList if oid not in localExistList]
                    # print("res fetch list:", fetchList)
                    webRelationList = await AsyncApiHelper.getCommitsFromApi(fetchList, mysql, session)

                    for node in nodes:
                        node.willFetch = False

                    # for node in nodes:
                    #     print("after fetched 1: " + f"{node.oid}  {node.willFetch}")

                    relationList = []
                    relationList.extend(localRelationList)
                    relationList.extend(webRelationList)
                    # print("relationList:", relationList)
                    # for relation in relationList:
                    #     print(relation.child, "    ", relation.parent)

                    addNode = []
                    for relation in relationList:
                        isFind = False
                        """ȷ���������ط���������"""
                        for node in nodes:
                            if relation.parent == node.oid:
                                isFind = True
                                break
                        for node in addNode:
                            if relation.parent == node.oid:
                                isFind = True
                                break

                        if not isFind:
                            newNode = CommitNode()
                            newNode.willFetch = True
                            newNode.oid = relation.parent
                            addNode.append(newNode)
                    nodes.extend(addNode)

                    # for node in nodes:
                    #     print("after fetched  2: " + f"{node.oid}  {node.willFetch}")

                    return nodes

                commit1Nodes = []
                commit2Nodes = []

                node1 = CommitNode()
                node1.oid = commit1
                node1.willFetch = True
                commit1Nodes.append(node1)
                node2 = CommitNode()
                node2.oid = commit2
                commit2Nodes.append(node2)
                node2.willFetch = True

                completeFetch = 0
                while loop < configPraser.getCommitFetchLoop():

                    loop += 1

                    print("loop:", loop, " 1")
                    printNodes(commit1Nodes, commit2Nodes)

                    if isNodesContains(commit1Nodes, commit2Nodes):
                        completeFetch = 2
                        break

                    if isNodesContains(commit2Nodes, commit1Nodes):
                        completeFetch = 1
                        break

                    await fetNotFetchedNodes(commit2Nodes, mysql, session)
                    print("loop:", loop, " 2")
                    printNodes(commit1Nodes, commit2Nodes)

                    if isNodesContains(commit1Nodes, commit2Nodes):
                        completeFetch = 2
                        break
                    if isNodesContains(commit2Nodes, commit1Nodes):
                        completeFetch = 1
                        break

                    await fetNotFetchedNodes(commit1Nodes, mysql, session)

                    print("loop:", loop, " 3")
                    printNodes(commit1Nodes, commit2Nodes)

                if completeFetch == 0:
                    raise Exception('out of the loop !')

                """�ҳ����鲻ͬ��node���бȽ�"""

                """�����������￪ʼ���߲��� �ҳ����߲���ĵ�  ��ɸѡ��һЩ�������������"""


    @staticmethod
    async def getCommitsFromStore(oids, mysql):

        beans = []

        existList = []  # �����б�
        relationList = []  # ��ѯ�õ��Ĺ�ϵ�б� �����б���ִ�����ϵͳ�д洢

        """�ȴ�sha(oid)ת��Ϊcommit����"""
        for oid in oids:
            bean = CommitRelation()
            bean.child = oid
            beans.append(bean)

        results = await AsyncSqlHelper.queryBeanData(beans, mysql, [[StringKeyUtils.STR_KEY_CHILD] * beans.__len__()])
        # print("result:", results)

        """�ӱ��ط��صĽ��������"""
        for relationTuple in results:
            if relationTuple.__len__() > 0:
                existList.append(relationTuple[0][0])
                for relation in relationTuple:
                    r = CommitRelation()
                    r.child = relation[0]
                    r.parent = relation[1]
                    relationList.append(r)
        """ȥ�ش���"""
        existList = list(set(existList))
        relationList = list(set(relationList))
        return existList, relationList

    @staticmethod
    async def getCommitsFromApi(oids, mysql, session):

        beanList = []
        relationList = []  # ��ѯ�õ��Ĺ�ϵ�б�

        for oid in oids:
            api = AsyncApiHelper.getCommitApi(oid)
            json = await AsyncApiHelper.fetchBeanData(session, api)
            # print(json)
            commit = await AsyncApiHelper.parserCommit(json)

            if commit.parents is not None:
                relationList.extend(commit.parents)
            if commit.files is not None:
                beanList.extend(commit.files)

            beanList.append(commit)
        beanList.extend(relationList)
        await AsyncSqlHelper.storeBeanDateList(beanList, mysql)
        return relationList
