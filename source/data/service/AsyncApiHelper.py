# coding=gbk
import asyncio
import json
import random
import time
import traceback
from datetime import datetime

import aiohttp

from source.config.configPraser import configPraser
from source.data.bean.Comment import Comment
from source.data.bean.CommentRelation import CommitRelation
from source.data.bean.Commit import Commit
from source.data.bean.CommitPRRelation import CommitPRRelation
from source.data.bean.File import File
from source.data.bean.IssueComment import IssueComment
from source.data.bean.PRTimeLine import PRTimeLine
from source.data.bean.PRTimeLineRelation import PRTimeLineRelation
from source.data.bean.PullRequest import PullRequest
from source.data.bean.Review import Review
from source.data.bean.ReviewComment import ReviewComment
from source.data.service.AsyncSqlHelper import AsyncSqlHelper
from source.data.service.BeanParserHelper import BeanParserHelper
from source.data.service.GraphqlHelper import GraphqlHelper
from source.data.service.PRTimeLineUtils import PRTimeLineUtils
from source.data.service.ProxyHelper import ProxyHelper
from source.data.service.TextCompareUtils import TextCompareUtils
from source.utils.Logger import Logger
from source.utils.StringKeyUtils import StringKeyUtils
from operator import itemgetter, attrgetter


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
        """����Github ��Token������֤"""
        if header is not None and isinstance(header, dict):
            if configPraser.getAuthorizationToken():
                header[StringKeyUtils.STR_HEADER_AUTHORIZAITON] = (StringKeyUtils.STR_HEADER_TOKEN
                                                                   + configPraser.getAuthorizationToken())
        return header

    @staticmethod
    def getUserAgentHeaders(header):
        """������ԣ� ��������agent"""
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
        """��ȡ����ip���е�ip  ��ϸ�� ProxyHelper"""
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
        """��ȡһ����Ŀ ����pull-request ��ص���Ϣ"""

        """����issue  ��Ҫ��дdownloadInformation���� 
           ֻ��pull-request�Ļ�ȡת��Ϊissue
        """
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

                        reviewCommits = []  # review���漰��Commit�ĵ�

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
                                if review.commit_id not in reviewCommits:
                                    reviewCommits.append(review.commit_id)

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

                        for commit in Commits:
                            if commit.sha in reviewCommits:
                                reviewCommits.remove(commit.sha)

                        """��Щreview�漰��commit�ĵ�û����PR�����ռ��� ��Щ����Ҫ���м�������
                        û�еĵ� ���������Ҫ��������ȡ���õ� ����Ҳ��Ҫ�ռ�"""

                        """ʣ�µĵ���Ҫ���λ�ȡ"""
                        for commit_id in reviewCommits:
                            api = AsyncApiHelper.getCommitApi(commit_id)
                            json = await AsyncApiHelper.fetchBeanData(session, api)
                            commit = await AsyncApiHelper.parserCommit(json)
                            Commits.append(commit)

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

                    """���ݿ�洢"""
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
    def getCommitApiWithProjectName(owner, repo, commit_sha):
        api = StringKeyUtils.API_GITHUB + StringKeyUtils.API_COMMIT
        api = api.replace(StringKeyUtils.STR_OWNER, owner)
        api = api.replace(StringKeyUtils.STR_REPO, repo)
        api = api.replace(StringKeyUtils.STR_COMMIT_SHA, str(commit_sha))
        return api


    @staticmethod
    async def fetchBeanData(session, api, isMediaType=False):
        """�첽��ȡ����ͨ�ýӿڣ���Ҫ��"""

        """��ʼ������ͷ"""
        headers = {}
        headers = AsyncApiHelper.getUserAgentHeaders(headers)
        headers = AsyncApiHelper.getAuthorizationHeaders(headers)
        if isMediaType:
            headers = AsyncApiHelper.getMediaTypeHeaders(headers)
        while True:
            """�Ե�������ѭ���ж� ֱ������ɹ����ߴ���"""

            """��ȡ����ip  ip��ȡ��Ҫ���д����"""
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
            """�� 403�������������  ѭ������"""
            print(e)
            if proxy is not None:
                proxy = proxy.split('//')[1]
                await ProxyHelper.judgeProxy(proxy, ProxyHelper.INT_NEGATIVE_POINT)
            # print("judge end")
            """ѭ������"""
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
            if AsyncApiHelper.judgeNotFind(resultJson):
                raise Exception("not found")

            """�����쳣���"""
            if not isinstance(resultJson, dict):
                return None
            data = resultJson.get(StringKeyUtils.STR_KEY_DATA, None)
            if data is None or not isinstance(data, dict):
                return None
            nodes = data.get(StringKeyUtils.STR_KEY_NODE, None)
            if nodes is None:
                return None

            """��ʼ����"""
            pr_timeline = PRTimeLine.Parser.parser(resultJson)
            return pr_timeline
        except Exception as e:
            print(e)

    @staticmethod
    async def downloadRPTimeLine(node_id, semaphore, mysql, statistic):
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                try:
                    args = {"id": node_id}
                    """��GitHub v4 API �л�ȡĳ��pull-request��TimeLine����"""
                    api = AsyncApiHelper.getGraphQLApi()
                    resultJson = await AsyncApiHelper.postGraphqlData(session, api, args)
                    print("timeline json:", resultJson)
                    """�ӻ�Ӧ���������prʱ���߶���"""
                    prTimeLine = await AsyncApiHelper.parserPRItemLine(resultJson)
                    prTimeLineItems = prTimeLine.timeline_items
                    """�洢���ݿ���"""
                    try:
                        await AsyncSqlHelper.storeBeanDateList(prTimeLineItems, mysql)
                    except Exception as e:
                        Logger.loge(e)
                        Logger.loge("this pr's timeline: {0} fail to insert".format(node_id))
                    # ����ͬ������
                    statistic.lock.acquire()
                    statistic.usefulTimeLineCount += 1
                    print(f" usefulTimeLineCount:{statistic.usefulTimeLineCount}",
                          f" change trigger count:{statistic.usefulChangeTrigger}",
                          f" twoParents case:{statistic.twoParentsNodeCase}",
                          f" outOfLoop case:{statistic.outOfLoopCase}")
                    statistic.lock.release()
                    return prTimeLine
                except Exception as e:
                    print(e)

    @staticmethod
    async def analyzeReviewChangeTrigger(pair, mysql, statistic):
        """����review������changes�Ƿ���trigger��ϵ"""
        """Ŀǰ�㷨��ʱ�Ȳ�����comment��change_trigger��ֻ�����ļ�����"""
        """�㷨˵����  ͨ��reviewCommit��changeCommit���Ƚ�����֮��Ĵ������"""
        """����˼·:   reviewCommit���������ڽڵ����һ��commit�ļ���reviewGroup
                      changeCommitͬ�������changeGroup

                      ��Group��ÿһ��commit�㶼��������Ϣ��
                      1. oid (commit-sha)
                      2. ���ڵ�� oid
                      3. ���commit�漰���ļ��Ķ�

                      Group�а����������ͽڵ㣬һ������Ϣ�Ѿ���ȡ������һ������Ϣ��δ��ȡ��
                      ��Ϣ�Ѿ���ȡ���������commit����������Ϣ��֪������δ��ȡ���������commit
                      ֻ��oid��Ϣ��

                      Groupһ�ε�����ָ��ÿ�λ�ȡ����Ϊδ��ȡ��Ϣ��commit�㣬������Щ�����Group�У�
                      commitָ��ĸ��ڵ�Ҳ��Ϊδ��ȡ��Ϣ�ڵ����Group�С�

                      ����commit��Ϊ��㲻��������������ֱ��ĳ��Group��δ��ȡ��Ϣ�ĵ㼯�ϰ�������
                      ����һ��Group������ڵ���

                      ��������֮��ֱ��ҵ�����Group�����commit�㼯�ϣ���Ϊ�����㷨������
        """

        """ȱ�㣺 �����㷨�޷�����commit��������������������merge�������ֵĵ�
                  �����㷨�о��ֵֹģ�Ч�ʿ��ܲ��Ǻܸ�
                  �������Ӧ����LCA����ı���
        """

        """�㷨����:  1��commit���ȡ����Խ��Խ��
                     2������commit��汾����������ʱ����Լ�⣬�����ƴ��� 
        """

        """commit node������"""
        class CommitNode:
            willFetch = None
            oid = None
            parents = None  # [sha1, sha2 ...]

            def __init__(self, will_fetch=True, oid=None, parents=None):
                self.willFetch = will_fetch
                self.oid = oid
                self.parents = parents

        """node group���߷���start"""
        def findNodes(nodes, oid):
            for node in nodes:
                if node.oid == oid:
                    return node

        def isExist(nodes, oid):
            for node in nodes:
                if node.oid == oid:
                    return True
            return False

        def isNodesContains(nodes1, nodes2):
            """nodes2����δ̽���ĵ��Ƿ�nodes1����"""
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
                print(node.oid, node.willFetch, node.parents)
            print('node2')
            for node in nodes2:
                print(node.oid, node.willFetch, node.parents)

        async def fetNotFetchedNodes(nodes, mysql):
            async with aiohttp.ClientSession() as session:
                """��ȡcommit����Ϣ �������ݿ��ȡ��GitHub API��ȡ nodes����һ��Group"""
                needFetchList = [node.oid for node in nodes if node.willFetch]
                """�ȳ��Դ����ݿ��ж�ȡ"""
                localExistList, localRelationList = await AsyncApiHelper.getCommitsFromStore(needFetchList, mysql)
                needFetchList = [oid for oid in needFetchList if oid not in localExistList]
                print("need fetch list:", needFetchList)
                webRelationList = await AsyncApiHelper.getCommitsFromApi(needFetchList, mysql, session)

                for node in nodes:
                    node.willFetch = False

                relationList = []
                relationList.extend(localRelationList)
                relationList.extend(webRelationList)

                """ԭ�е�node ��ȫparents"""
                for relation in relationList:
                    node = findNodes(nodes, relation.child)
                    if node is not None:
                        if relation.parent not in node.parents:
                            node.parents.append(relation.parent)

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
                        """�¼���Ϊ��ȡ�ĵ�"""
                        newNode = CommitNode(will_fetch=True, oid=relation.parent, parents=[])
                        addNode.append(newNode)
                nodes.extend(addNode)
                return nodes
        """node group���߷���end"""

        review = pair[0]
        changes = pair[1]

        isUsefulReview = False

        """�����ݿ��ȡreview comments(ע��һ��review ���ܻ�������comment��ÿ��comment��ָ��һ���ļ��Ͷ�Ӧ������)"""
        comments = await AsyncApiHelper.getReviewCommentsByNodeFromStore(review.timeline_item_node, mysql)
        if comments is None:
            return isUsefulReview

        twoParentsBadCase = 0  # ��¼һ��commit���������ڵ����� ����������ֱ��ֹͣ
        outOfLoopCase = 0  # ��¼Ѱ������commit���������ڽڵ� ʹ���ϼ�׷�ݵĴ��������������

        """����review֮���changes���ж��Ƿ���comment����change�����"""
        for change in changes:  # �Ժ��������Ķ����α���
            reviewCommit = review.pullrequestReviewCommit
            changeCommit = None
            if change.typename == StringKeyUtils.STR_KEY_PULL_REQUEST_COMMIT:
                changeCommit = change.pullrequestCommitCommit
            elif change.typename == StringKeyUtils.STR_KEY_HEAD_REF_PUSHED_EVENT:
                changeCommit = change.headRefForcePushedEventAfterCommit

            if changeCommit is None or reviewCommit is None:
                break
            try:
                # TODO �����о����ֱ�ӱȽ�����commit�İ汾����
                """����Group�ĵ�������"""
                reviewGroup = []
                changeGroup = []

                reviewGroupStartNode = CommitNode(oid=reviewCommit, parents=[])
                reviewGroup.append(reviewGroupStartNode)
                changeGroupStartNode = CommitNode(oid=changeCommit, parents=[])
                changeGroup.append(changeGroupStartNode)

                # ��ȫ��Fetch��group
                completeFetch = None
                loop = 0
                while loop < configPraser.getCommitFetchLoop():
                    """��������������"""
                    loop += 1
                    print("fetch nodes loop: ", loop)
                    printNodes(reviewGroup, changeGroup)

                    """�жϰ�����ϵ������ȡchangeGroup"""
                    if isNodesContains(reviewGroup, changeGroup):
                        completeFetch = 'CHANGE_GROUP'
                        break
                    if isNodesContains(changeGroup, reviewGroup):
                        completeFetch = 'REVIEW_GROUP'
                        break
                    await fetNotFetchedNodes(changeGroup, mysql)

                    """�жϰ�����ϵ������ȡchangeGroup"""
                    printNodes(reviewGroup, changeGroup)
                    if isNodesContains(reviewGroup, changeGroup):
                        completeFetch = 'CHANGE_GROUP'
                        break
                    if isNodesContains(changeGroup, reviewGroup):
                        completeFetch = 'REVIEW_GROUP'
                        break
                    await fetNotFetchedNodes(reviewGroup, mysql)

                if completeFetch is None:
                    outOfLoopCase += 1
                    raise Exception('out of the loop !')

                """�ҳ����鲻ͬ��node���бȽ�"""

                """�����������￪ʼ���߲��� �ҳ����߲���ĵ�  ��ɸѡ��һЩ�������������"""

                # ��Χ�ϴ��group
                groupInclude = None
                groupIncludeStartNode = None
                # ��������group
                groupIncluded = None
                groupIncludedStartNode = None

                """���ݰ�����ϵ ȷ�ϰ����ͱ���������"""
                if completeFetch == 'CHANGE_GROUP':
                    groupInclude = reviewGroup
                    groupIncluded = changeGroup  # 2��λΪ������
                    groupIncludeStartNode = reviewGroupStartNode.oid
                    groupIncludedStartNode = changeGroupStartNode.oid
                if completeFetch == 'REVIEW_GROUP':
                    groupInclude = changeGroup
                    groupIncluded = reviewGroup
                    groupIncludeStartNode = changeGroupStartNode.oid
                    groupIncludedStartNode = reviewGroupStartNode.oid

                # ���ڴ洢���߲
                diff_nodes1 = []
                diff_nodes2 = [x for x in groupIncluded if not findNodes(groupInclude, x.oid)]

                # diff_nodes1 �Ȱ������е㣬Ȼ���ҳ���2�������ﲻ�˵ĵ�
                diff_nodes1 = groupInclude.copy()
                for node in groupIncluded:
                    if not findNodes(groupInclude, node.oid):  # ȥ��
                        diff_nodes1.append(node)

                temp = [groupIncludedStartNode]
                while temp.__len__() > 0:
                    oid = temp.pop(0)
                    node = findNodes(diff_nodes1, oid)
                    if node is not None:
                        temp.extend(node.parents)
                    diff_nodes1.remove(node)

                for node in diff_nodes1:
                    if node.willFetch:
                        twoParentsBadCase += 1
                        raise Exception('will fetch node in set 1 !')  # ȥ���ֲ�ڵ�δ��֮ǰ���������

                """diff_node1 �� diff_node2 �ֱ�洢���ߵĲ����"""
                printNodes(diff_nodes1, diff_nodes2)

                """��ȥ������е�merge�ڵ�"""
                for node in diff_nodes1:
                    if node.parents.__len__() >= 2:
                        twoParentsBadCase += 1
                        raise Exception('merge node find in set1 !')
                for node in diff_nodes2:
                    if node.parents.__len__() >= 2:
                        twoParentsBadCase += 1
                        raise Exception('merge node find in set 2!')
                """���commit ���е�change file"""
                file1s = await AsyncApiHelper.getFilesFromStore([x.oid for x in diff_nodes1], mysql)
                file2s = await AsyncApiHelper.getFilesFromStore([x.oid for x in diff_nodes2], mysql)

                for comment in comments:  # ��ÿһ��commentͳ��change trigger
                    """comment ��Ӧ���ļ�"""
                    commentFile = comment.path
                    # TODO Ŀǰ�ݲ�����commentϸ�����е�change_trigger
                    # """comment ��Ӧ���ļ���"""
                    # commentLine = comment.original_line
                    #
                    # diff_patch1 = []  # ���߲�ͬ��patch patch���ǲ�ͬ�ı�����
                    # diff_patch2 = []

                    """ֻҪ�ڸĶ�·���ϳ��ֹ���commentFile��ͬ���ļ������϶�����comment����Ч��"""
                    startNode = [groupIncludeStartNode]  # ��commitԴͷ�ҵ�����ÿһ��commit���漰�ļ�����patch
                    while startNode.__len__() > 0:
                        """����DFS�㷨"""
                        node_oid = startNode.pop(0)
                        for node in diff_nodes1:
                            if node.oid == node_oid:
                                for file in file1s:
                                    if file.filename == commentFile and file.commit_sha == node.oid:
                                        comment.change_trigger = True
                                        # TODO Ŀǰ�ݲ�����commentϸ�����е�change_trigger
                                        # """patch��һ������ĳЩ�����仯���ı�����Ҫ���浥���Ľ���"""
                                        # diff_patch1.insert(0, file.patch)
                                startNode.extend(node.parents)

                    startNode = [groupIncludedStartNode]
                    while startNode.__len__() > 0:
                        node_oid = startNode.pop(0)
                        for node in diff_nodes2:
                            if node.oid == node_oid:
                                for file in file2s:
                                    if file.filename == commentFile and file.commit_sha == node.oid:
                                        comment.change_trigger = True
                                        # TODO Ŀǰ�ݲ�����commentϸ�����е�change_trigger
                                        # diff_patch2.insert(0, file.patch)
                                startNode.extend(node.parents)

                    # TODO Ŀǰ�ݲ�����commentϸ�����е�change_trigger
                    # """ͨ���Ƚ�commit�������������comment������ļ��仯"""
                    # closedChange = TextCompareUtils.getClosedFileChange(diff_patch1, diff_patch2, commentLine)
                    # print("closedChange :", closedChange)
                    # if comment.change_trigger is None:
                    #     comment.change_trigger = closedChange
                    # else:
                    #     comment.change_trigger = min(comment.change_trigger, closedChange)
                    """�ҵ�һ��comment��change_trigger�����϶���review��Ч, ���ټ������������comment"""
                    if comment.change_trigger:
                        isUsefulReview = True
                        break
            except Exception as e:
                print(e)
                continue

            """���ҵ�һ����comment������change���϶���review��Ч�����ټ����Һ����change"""
            if isUsefulReview:
                break

        statistic.lock.acquire()
        statistic.outOfLoopCase += outOfLoopCase
        statistic.usefulChangeTrigger += [x for x in comments if x.change_trigger is not None].__len__()
        statistic.lock.release()

        # TODO �ֶ�����comment��original_line��line����change_triggerһ��д�����ݿ���"""
        # await AsyncSqlHelper.updateBeanDateList(comments, mysql)
        return isUsefulReview

    @staticmethod
    async def getReviewCommentsByNodeFromStore(node_id, mysql):
        """�����ݿ��ж�ȡreview id ��ʱ�����ֻҪ�����ݿ������Ӿ�ok��"""

        review = Review()
        review.node_id = node_id

        reviews = await AsyncSqlHelper.queryBeanData([review], mysql, [[StringKeyUtils.STR_KEY_NODE_ID]])
        print("reviews:", reviews)
        if reviews and reviews[0] and reviews[0].__len__() > 0:
            review_id = reviews[0][0][2]
            print("review_id:", review_id)
            comment = ReviewComment()
            comment.pull_request_review_id = review_id

            result = await AsyncSqlHelper.queryBeanData([comment], mysql,
                                                        [[StringKeyUtils.STR_KEY_PULL_REQUEST_REVIEW_ID]])
            print(result)
            if result[0].__len__() > 0:
                comments = BeanParserHelper.getBeansFromTuple(ReviewComment(), ReviewComment.getItemKeyList(),
                                                              result[0])

                """��ȡcomment �Լ���Ӧ��sha ��nodeId ������,fileName"""
                for comment in comments:
                    print(comment.getValueDict())
                return comments

    @staticmethod
    async def getFilesFromStore(oids, mysql):
        """�����ݿ��ж�ȡ���oid��file changes"""

        print("query file oids:", oids)

        queryFiles = []
        for oid in oids:
            file = File()
            file.commit_sha = oid
            queryFiles.append(file)

        gitFiles = []

        if queryFiles.__len__() > 0:
            results = await AsyncSqlHelper.queryBeanData(queryFiles, mysql,
                                                         [[StringKeyUtils.STR_KEY_COMMIT_SHA]] * queryFiles.__len__())
            print("files:", results)
            for result in results:
                if result.__len__() > 0:
                    files = BeanParserHelper.getBeansFromTuple(File(), File.getItemKeyList(), result)
                    gitFiles.extend(files)

        return gitFiles

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

        results = await AsyncSqlHelper.queryBeanData(beans, mysql, [[StringKeyUtils.STR_KEY_CHILD]] * beans.__len__())
        print("result:", results)

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

    @staticmethod
    async def downloadCommits(projectName, oid, semaphore, mysql, statistic):
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                try:
                    beanList = []
                    owner, repo = projectName.split('/')
                    api = AsyncApiHelper.getCommitApiWithProjectName(owner, repo, oid)
                    json = await AsyncApiHelper.fetchBeanData(session, api)
                    # print(json)
                    commit = await AsyncApiHelper.parserCommit(json)

                    if commit.parents is not None:
                        beanList.extend(commit.parents)
                    if commit.files is not None:
                        beanList.extend(commit.files)

                    beanList.append(commit)
                    await AsyncSqlHelper.storeBeanDateList(beanList, mysql)

                    # ����ͬ������
                    statistic.lock.acquire()
                    statistic.usefulCommitNumber += 1
                    print(f" usefulCommitCount:{statistic.usefulCommitNumber}")
                    statistic.lock.release()
                except Exception as e:
                    print(e)
