# coding=gbk
import asyncio
import difflib
import json
import random
import time
import traceback
from datetime import datetime

import aiohttp

from source.config.configPraser import configPraser
from source.data.bean.Blob import Blob
from source.data.bean.Comment import Comment
from source.data.bean.CommentRelation import CommitRelation
from source.data.bean.Commit import Commit
from source.data.bean.CommitPRRelation import CommitPRRelation
from source.data.bean.File import File
from source.data.bean.IssueComment import IssueComment
from source.data.bean.PRChangeFile import PRChangeFile
from source.data.bean.PRTimeLine import PRTimeLine
from source.data.bean.PRTimeLineRelation import PRTimeLineRelation
from source.data.bean.PullRequest import PullRequest
from source.data.bean.Review import Review
from source.data.bean.ReviewComment import ReviewComment
from source.data.bean.TreeEntry import TreeEntry
from source.data.bean.User import User
from source.data.bean.UserFollowRelation import UserFollowRelation
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
    async def parserPullRequest(resultJson, pull_number=None, rawData=None):
        try:
            res = None
            if configPraser.getApiVersion() == StringKeyUtils.API_VERSION_RESET:
                if not AsyncApiHelper.judgeNotFind(resultJson):
                    res = PullRequest.parser.parser(resultJson)
            elif configPraser.getApiVersion() == StringKeyUtils.API_VERSION_GRAPHQL:
                res = PullRequest.parserV4.parser(resultJson)
                if res is not None:
                    res.repo_full_name = AsyncApiHelper.owner + '/' + AsyncApiHelper.repo
                """����v4�ӿ� pr��ȡ��������������ȷ�ϲ����ڣ�������Ϊ��issue�����"""
                """��ȡerrors ��Ϣ"""
                if res is None:
                    errorMessage = rawData.get(StringKeyUtils.STR_KEY_ERRORS)[0]. \
                        get(StringKeyUtils.STR_KEY_MESSAGE)
                    if errorMessage.find(StringKeyUtils.STR_KEY_ERRORS_PR_NOT_FOUND) != -1:
                        res = PullRequest()
                        res.repo_full_name = AsyncApiHelper.owner + '/' + AsyncApiHelper.repo
                        res.number = pull_number
                        res.is_pr = False
            if res is not None:
                res.repo_full_name = AsyncApiHelper.owner + '/' + AsyncApiHelper.repo
                return res
        except Exception as e:
            print(e)

    @staticmethod
    async def parserUserFollowingList(resultJson):
        try:
            res = None
            res = UserFollowRelation.parserV4.parser(resultJson)
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
    def judgeNotFindV4(resultJson):
        """v4 �ӿڵ�not find�жϺ�v3�Ĳ�����ͬ"""
        if resultJson is not None and isinstance(json, dict):
            if resultJson.get(StringKeyUtils.STR_KEY_ERRORS) is not None:
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
                                """��ȫ reivew comment �� pull_request_review_node_id"""
                                for r in reviews:
                                    if r.id == reviewComment.pull_request_review_id:
                                        reviewComment.pull_request_review_node_id = r.node_id

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
    async def downloadInformationByV4(pull_number, semaphore, mysql, statistic):
        """��ȡһ����Ŀ ����pull-request ��ص���Ϣ
           ��Ҫ�ӿ�����Ǩ�Ƶ�GraphQl��v4�ӿ���   ��������һ���Ի�ȡpr��Ϣ
           ��֤��pr��Ϣ��������
           ����commit�ľ�����Ϣ�޷���ȡ  ���׼��������������ȡ

           ��gitFile����Ϣ��������Ϣ��ȡ����
        """
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                try:
                    beanList = []  # �����ռ���Ҫ�洢��bean��
                    """�Ȼ�ȡpull request��Ϣ"""
                    args = {"number": pull_number, "owner": AsyncApiHelper.owner, "name": AsyncApiHelper.repo}
                    api = AsyncApiHelper.getGraphQLApi()
                    query = GraphqlHelper.getPrInformationByNumber()
                    resultJson = await AsyncApiHelper.postGraphqlData(session, api, query, args)
                    print(resultJson)

                    """����pull request"""
                    allData = resultJson.get(StringKeyUtils.STR_KEY_DATA, None)
                    if allData is not None and isinstance(allData, dict):
                        repoData = allData.get(StringKeyUtils.STR_KEY_REPOSITORY, None)
                        if repoData is not None and isinstance(repoData, dict):
                            prData = repoData.get(StringKeyUtils.STR_KEY_ISSUE_OR_PULL_REQUEST, None)

                            pull_request = await AsyncApiHelper.parserPullRequest(prData, pull_number, resultJson)

                            usefulPullRequestsCount = 0
                            usefulReviewsCount = 0
                            usefulReviewCommentsCount = 0
                            usefulIssueCommentsCount = 0
                            usefulCommitsCount = 0

                            """���pul request �� branch"""
                            if pull_request is not None:
                                usefulPullRequestsCount = 1
                                beanList.append(pull_request)
                                if pull_request.head is not None:
                                    beanList.append(pull_request.head)
                                if pull_request.base is not None:
                                    beanList.append(pull_request.base)

                            if pull_request is not None and pull_request.is_pr:
                                users = []
                                """���� user ֱ�Ӵ�pr��participate��ȡ"""
                                user_list = prData.get(StringKeyUtils.STR_KEY_PARTICIPANTS, None)
                                if user_list is not None and isinstance(user_list, dict):
                                    user_list_nodes = user_list.get(StringKeyUtils.STR_KEY_NODES, None)
                                    if user_list_nodes is not None and isinstance(user_list_nodes, list):
                                        for userData in user_list_nodes:
                                            user = User.parserV4.parser(userData)
                                            if user is not None:
                                                users.append(user)
                                """����û�"""
                                beanList.extend(users)

                                """���� review, review comment, review �漰�� commit ��Ϣ"""
                                reviews = []
                                reviewComments = []
                                commits = []
                                review_list = prData.get(StringKeyUtils.STR_KEY_REVIEWS, None)
                                if review_list is not None and isinstance(review_list, dict):
                                    review_list_nodes = review_list.get(StringKeyUtils.STR_KEY_NODES, None)
                                    if review_list_nodes is not None and isinstance(review_list_nodes, list):
                                        for reviewData in review_list_nodes:
                                            review = Review.parserV4.parser(reviewData)
                                            if review is not None:
                                                review.repo_full_name = pull_request.repo_full_name
                                                review.pull_number = pull_number
                                                reviews.append(review)

                                            if reviewData is not None and isinstance(reviewData, dict):
                                                comment_list = reviewData.get(StringKeyUtils.STR_KEY_COMMENTS, None)
                                                if comment_list is not None and isinstance(comment_list, dict):
                                                    comment_list_nodes = comment_list.get(StringKeyUtils.STR_KEY_NODES
                                                                                          , None)
                                                    if comment_list_nodes is not None and isinstance(comment_list_nodes
                                                            , list):
                                                        for commentData in comment_list_nodes:
                                                            commentData[StringKeyUtils.STR_KEY_REPO_FULL_NAME] = AsyncApiHelper.owner + "/" + AsyncApiHelper.repo
                                                            comment = ReviewComment.parserV4.parser(commentData)
                                                            comment.pull_request_review_id = review.id
                                                            comment.pull_request_review_node_id = review.node_id
                                                            reviewComments.append(comment)

                                                commitData = reviewData.get(StringKeyUtils.STR_KEY_COMMIT, None)
                                                if commitData is not None and isinstance(commitData, dict):
                                                    commit = Commit.parserV4.parser(commitData)
                                                    commit.has_file_fetched = False
                                                    isFind = False
                                                    for c in commits:
                                                        if c.sha == commit.sha:
                                                            isFind = True
                                                            break
                                                    if not isFind:
                                                        commits.append(commit)

                                """����2016��֮ǰ������  û��review�������PullRequestReviewThread
                                   ���Ի�ȡ��Ӧ review��review comment�� commit
                                """
                                itemLineItem_list = prData.get(StringKeyUtils.STR_KEY_TIME_LINE_ITEMS, None)
                                if itemLineItem_list is not None and isinstance(itemLineItem_list, dict):
                                    itemLineItem_list_edges = itemLineItem_list.get(StringKeyUtils.STR_KEY_EDGES, None)
                                    if itemLineItem_list_edges is not None and isinstance(itemLineItem_list_edges,
                                                                                          list):
                                        for itemLineItem_list_edge_node in itemLineItem_list_edges:
                                            if itemLineItem_list_edge_node is not None and \
                                                    isinstance(itemLineItem_list_edge_node, dict):
                                                itemLineItem_list_edge_node = itemLineItem_list_edge_node. \
                                                    get(StringKeyUtils.STR_KEY_NODE, None)
                                                typename = itemLineItem_list_edge_node.get(
                                                    StringKeyUtils.STR_KEY_TYPE_NAME_JSON, None)
                                                if typename == StringKeyUtils.STR_KEY_PULL_REQUEST_REVIEW_THREAD:
                                                    """ReviewThread ��ΪReview �洢�����ݿ���  ����ֻ��node_id ��Ϣ"""
                                                    review = Review()
                                                    review.pull_number = pull_request
                                                    review.repo_full_name = pull_request.repo_full_name
                                                    review.node_id = itemLineItem_list_edge_node.get(
                                                        StringKeyUtils.STR_KEY_ID, None)
                                                    reviews.append(review)

                                                    """���� review �漰��review comment"""
                                                    comment_list = itemLineItem_list_edge_node.get(
                                                        StringKeyUtils.STR_KEY_COMMENTS, None)
                                                    if comment_list is not None and isinstance(comment_list, dict):
                                                        comment_list_nodes = comment_list.get(
                                                            StringKeyUtils.STR_KEY_NODES
                                                            , None)
                                                        if comment_list_nodes is not None and isinstance(
                                                                comment_list_nodes
                                                                , list):
                                                            for commentData in comment_list_nodes:
                                                                comment = ReviewComment.parserV4.parser(commentData)
                                                                comment.pull_request_review_id = review.id
                                                                comment.pull_request_review_node_id = review.node_id
                                                                reviewComments.append(comment)

                                                                """"��commentData ���� original commit"""
                                                                commitData = commentData.get(
                                                                    StringKeyUtils.STR_KEY_ORIGINAL_COMMIT, None)
                                                                if commitData is not None and isinstance(commitData,
                                                                                                         dict):
                                                                    commit = Commit.parserV4.parser(commitData)
                                                                    commit.has_file_fetched = False
                                                                    isFind = False
                                                                    for c in commits:
                                                                        if c.sha == commit.sha:
                                                                            isFind = True
                                                                            break
                                                                    if not isFind:
                                                                        commits.append(commit)

                                if configPraser.getPrintMode():
                                    print(reviews)
                                    print(reviewComments)

                                usefulReviewsCount += reviews.__len__()
                                usefulReviewCommentsCount += reviewComments.__len__()

                                """���review reviewComments"""
                                beanList.extend(reviews)
                                beanList.extend(reviewComments)

                                """issue comment ��Ϣ��ȡ"""
                                issueComments = []
                                issue_comment_list = prData.get(StringKeyUtils.STR_KEY_COMMENTS, None)
                                if issue_comment_list is not None and isinstance(issue_comment_list, dict):
                                    issue_comment_list_nodes = issue_comment_list.get(StringKeyUtils.STR_KEY_NODES,
                                                                                      None)
                                    if issue_comment_list_nodes is not None and isinstance(issue_comment_list_nodes,
                                                                                           list):
                                        for commentData in issue_comment_list_nodes:
                                            issueComment = IssueComment.parserV4.parser(commentData)
                                            issueComment.pull_number = pull_number
                                            issueComment.repo_full_name = pull_request.repo_full_name
                                            issueComments.append(issueComment)

                                if configPraser.getPrintMode():
                                    print(issueComments)
                                usefulIssueCommentsCount += issueComments.__len__()
                                beanList.extend(issueComments)

                                """��ȡ pr ��ֱ�ӹ����� commit ��Ϣ"""
                                commit_list = prData.get(StringKeyUtils.STR_KEY_COMMITS, None)
                                if commit_list is not None and isinstance(commit_list, dict):
                                    commit_list_nodes = commit_list.get(StringKeyUtils.STR_KEY_NODES, None)
                                    if commit_list_nodes is not None and isinstance(commit_list_nodes, list):
                                        for commitData in commit_list_nodes:
                                            if commitData is None:
                                                continue
                                            commitData = commitData.get(StringKeyUtils.STR_KEY_COMMIT, None)
                                            commit = Commit.parserV4.parser(commitData)
                                            commit.has_file_fetched = False
                                            isFind = False
                                            for c in commits:
                                                if c.sha == commit.sha:
                                                    isFind = True
                                                    break
                                            if not isFind:
                                                commits.append(commit)

                                """���� commitPrRelation �� commitRelation"""
                                CommitPrRelations = []
                                CommitRelations = []
                                for commit in commits:
                                    relation = CommitPRRelation()
                                    relation.repo_full_name = pull_request.repo_full_name
                                    relation.pull_number = pull_number
                                    relation.sha = commit.sha
                                    CommitPrRelations.append(relation)
                                    CommitRelations.extend(commit.parents)

                                usefulCommitsCount += commits.__len__()
                                beanList.extend(CommitPrRelations)
                                beanList.extend(CommitRelations)
                                beanList.extend(commits)

                                """���� pull request �漰���ļ��䶯��������commit�ļ��䶯���ۼ�"""
                                files = []
                                files_list = prData.get(StringKeyUtils.STR_KEY_FILES, None)
                                if files_list is not None and isinstance(files_list, dict):
                                    files_list_nodes = files_list.get(StringKeyUtils.STR_KEY_NODES, None)
                                    if files_list_nodes is not None and isinstance(files_list_nodes, list):
                                        for fileData in files_list_nodes:
                                            file = PRChangeFile.parserV4.parser(fileData)
                                            file.pull_number = pull_number
                                            file.repo_full_name = pull_request.repo_full_name
                                            files.append(file)

                                if configPraser.getPrintMode():
                                    print(files)

                                beanList.extend(files)

                            """beanList ��Ӹ���������"""

                            """���ݿ�洢"""
                            if beanList.__len__() > 0:
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
    def getSingleReviewCommentApiWithProjectName(owner, repo, comment_id):
        api = StringKeyUtils.API_GITHUB + StringKeyUtils.API_COMMENT_FOR_REVIEW_SINGLE
        api = api.replace(StringKeyUtils.STR_OWNER, owner)
        api = api.replace(StringKeyUtils.STR_REPO, repo)
        api = api.replace(StringKeyUtils.STR_COMMENT_ID, str(comment_id))
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
    async def postGraphqlData(session, api, query=None, args=None):
        """ͨ�� github graphhql�ӿ� ͨ��post����"""
        headers = {}
        headers = AsyncApiHelper.getUserAgentHeaders(headers)
        headers = AsyncApiHelper.getAuthorizationHeaders(headers)

        body = {}
        body = GraphqlHelper.getGraphlQuery(body, query)
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
            print("judge end")
            return await AsyncApiHelper.postGraphqlData(session, api, query, args)

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
                """v3 �ӿ���Ϊ��gitFile��Ϣ"""
                res.has_file_fetched = True
                return res
        except Exception as e:
            print(e)

    @staticmethod
    async def parserSingleReviewComment(resultJson):
        try:
            if not AsyncApiHelper.judgeNotFind(resultJson):
                res = ReviewComment.parser.parser(resultJson)
                return res
        except Exception as e:
            print(e)

    @staticmethod
    async def downloadRPTimeLine(node_ids, semaphore, mysql, statistic):
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                try:
                    args = {"ids": node_ids}
                    """��GitHub v4 API �л�ȡ���pull-request��TimeLine����"""
                    api = AsyncApiHelper.getGraphQLApi()
                    query = GraphqlHelper.getTimeLineQueryByNodes()
                    resultJson = await AsyncApiHelper.postGraphqlData(session, api, query, args)
                    print("successfully fetched Json! nodeIDS: {0}".format(json.dumps(node_ids)))
                    """���� ���۹۲� 403 ���� rate����� = ="""
                    print(resultJson)

                    if AsyncApiHelper.judgeNotFindV4(resultJson):
                        Logger.loge("not found")
                        raise Exception("not found")

                    """�����쳣���"""
                    if not isinstance(resultJson, dict):
                        return None
                    data = resultJson.get(StringKeyUtils.STR_KEY_DATA, None)
                    if data is None or not isinstance(data, dict):
                        return None
                    nodes = data.get(StringKeyUtils.STR_KEY_NODES, None)
                    if nodes is None:
                        return None

                    prTimeLines = []
                    for node in nodes:
                        """�ӻ�Ӧ���������prʱ���߶���"""
                        node[StringKeyUtils.STR_KEY_REPO_FULL_NAME] = AsyncApiHelper.repo + "/" + AsyncApiHelper.owner
                        prTimeLine = PRTimeLine.Parser.parser(node)
                        if prTimeLine is None:
                            continue
                        prTimeLineItems = prTimeLine.timeline_items
                        """�洢���ݿ���"""
                        try:
                            await AsyncSqlHelper.storeBeanDateList(prTimeLineItems, mysql)
                        except Exception as e:
                            Logger.loge(json.dumps(e.args))
                            Logger.loge(
                                "this pr's timeline: {0} fail to insert".format(node.get(StringKeyUtils.STR_KEY_ID)))
                        # ��ͬ������
                        statistic.lock.acquire()
                        statistic.usefulTimeLineCount += 1
                        print(f" usefulTimeLineCount:{statistic.usefulTimeLineCount}",
                              f" change trigger count:{statistic.usefulChangeTrigger}",
                              f" twoParents case:{statistic.twoParentsNodeCase}",
                              f" outOfLoop case:{statistic.outOfLoopCase}")
                        statistic.lock.release()
                        prTimeLines.append(prTimeLine)
                    return prTimeLines
                except Exception as e:
                    print(e)

    @staticmethod
    async def analyzeReviewChangeTrigger(pr_node_id, pair, mysql, statistic):
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
        if changes is None or changes.__len__() == 0:
            return None

        """�����ݿ��ȡreview comments(ע��һ��review ���ܻ�������comment��ÿ��comment��ָ��һ���ļ��Ͷ�Ӧ������)"""
        comments = await AsyncApiHelper.getReviewCommentsByNodeFromStore(review.timeline_item_node, mysql)
        if comments is None:
            return None
        """ͨ��comment�� position��originalPosition��Ϣ��ȫoriginalLine, side ��Ҫ��Ӧcommit��file��patch"""
        oids = [comment.original_commit_id for comment in comments]
        """��ȡ��Щ��changes files"""
        files = await AsyncApiHelper.getFilesFromStore(oids, mysql)
        """���β�ȫ"""
        for comment in comments:
            """commentĬ��δ����change_trigger"""
            comment.change_trigger = -1
            for file in files:
                if file.commit_sha == comment.original_commit_id and file.filename == comment.path:
                    """���� line �� origin line"""
                    original_line, side = TextCompareUtils.getStartLine(file.patch, comment.original_position)
                    comment.side = side
                    comment.original_line = original_line

                    """line �ǸĶ����ı�����ָ��������� original line �ǸĶ�ǰ���ı�����ָ������
                       �� line �ͱ��� original line
                    """

        twoParentsBadCase = 0  # ��¼һ��commit���������ڵ����� ����������ֱ��ֹͣ
        outOfLoopCase = 0  # ��¼Ѱ������commit���������ڽڵ� ʹ���ϼ�׷�ݵĴ��������������

        """����review֮���changes���ж��Ƿ���comment����change�����"""
        change_trigger_comments = []
        for change in changes:  # �Ժ��������Ķ����α���
            reviewCommit = review.pull_request_review_commit
            changeCommit = None
            if change.typename == StringKeyUtils.STR_KEY_PULL_REQUEST_COMMIT:
                changeCommit = change.pull_request_commit
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

                    """�жϰ�����ϵ������ȡreviewGroup"""
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

                """�ļ�����"""
                changed_files = file1s.copy()
                changed_files.extend(file2s)
                for comment in comments:  # ��ÿһ��commentͳ��change trigger
                    """comment ��Ӧ���ļ�"""
                    commentFile = comment.path
                    for file in changed_files:
                        if file.filename == commentFile:
                            comment.change_trigger = 1
                    # TODO Ŀǰ�ݲ�����commentϸ�����е�change_trigger
                    # """comment ��Ӧ���ļ���"""
                    # commentLine = comment.original_line
                    #
                    # diff_patch1 = []  # ���߲�ͬ��patch patch���ǲ�ͬ�ı�����
                    # diff_patch2 = []

                    # """ֻҪ�ڸĶ�·���ϳ��ֹ���commentFile��ͬ���ļ������϶�����comment����Ч��"""
                    # startNode = [groupIncludeStartNode]  # ��commitԴͷ�ҵ�����ÿһ��commit���漰�ļ�����patch
                    # while startNode.__len__() > 0:
                    #     """����DFS�㷨"""
                    #     node_oid = startNode.pop(0)
                    #     for node in diff_nodes1:
                    #         if node.oid == node_oid:
                    #             for file in file1s:
                    #                 if file.filename == commentFile and file.commit_sha == node.oid:
                    #                     comment.change_trigger = 1
                    #                     # TODO Ŀǰ�ݲ�����commentϸ�����е�change_trigger
                    #                     # """patch��һ������ĳЩ�����仯���ı�����Ҫ���浥���Ľ���"""
                    #                     # diff_patch1.insert(0, file.patch)
                    #             startNode.extend(node.parents)
                    #
                    # startNode = [groupIncludedStartNode]
                    # while startNode.__len__() > 0:
                    #     node_oid = startNode.pop(0)
                    #     for node in diff_nodes2:
                    #         if node.oid == node_oid:
                    #             for file in file2s:
                    #                 if file.filename == commentFile and file.commit_sha == node.oid:
                    #                     comment.change_trigger = 1
                    #                     # TODO Ŀǰ�ݲ�����commentϸ�����е�change_trigger
                    #                     # diff_patch2.insert(0, file.patch)
                    #             startNode.extend(node.parents)
                    # TODO Ŀǰ�ݲ�����commentϸ�����е�change_trigger
                    # """ͨ���Ƚ�commit�������������comment������ļ��仯"""
                    # closedChange = TextCompareUtils.getClosedFileChange(diff_patch1, diff_patch2, commentLine)
                    # print("closedChange :", closedChange)
                    # if comment.change_trigger is None:
                    #     comment.change_trigger = closedChange
                    # else:
                    #     comment.change_trigger = min(comment.change_trigger, closedChange)
            except Exception as e:
                print(e)
                continue
        for comment in comments:
            change_trigger_comments.append({
                "pullrequest_node": pr_node_id,
                "user_login": comment.user_login,
                "comment_node": comment.node_id,
                "comment_type": StringKeyUtils.STR_LABEL_REVIEW_COMMENT,
                "change_trigger": comment.change_trigger,
                "filepath": comment.path
            })
        statistic.lock.acquire()
        statistic.outOfLoopCase += outOfLoopCase
        statistic.usefulChangeTrigger += [x for x in comments if x.change_trigger > 0].__len__()
        statistic.lock.release()

        # ����comments��change_trigger, line, original_line��Ϣ"""
        await AsyncSqlHelper.updateBeanDateList(comments, mysql)
        return change_trigger_comments

    @staticmethod
    async def analyzeReviewChangeTriggerByBlob(pr_node_id, pair, mysql, statistic):

        review = pair[0]
        changes = pair[1]
        t1 = datetime.now()
        """�����ݿ��ȡreview comments(ע��һ��review ���ܻ�������comment��ÿ��comment��ָ��һ���ļ��Ͷ�Ӧ������)"""
        comments = await AsyncApiHelper.getReviewCommentsByNodeFromStore(review.timeline_item_node, mysql)
        if comments is None:
            print("comment is None! review id:", review.timeline_item_node)
            return None

        """ʱ���������ȡ��comment���ǳ�ʼreview��comment����ϵ�еĻظ�comment��Ҫ�����ݿ��"""
        commentList = []
        for comment in comments:
            bean = ReviewComment()
            bean.in_reply_to_id = comment.id
            commentList.append(bean)
        results = await AsyncSqlHelper.queryBeanData(commentList, mysql,
                                                     [[StringKeyUtils.STR_KEY_IN_REPLY_TO_ID]] * commentList.__len__())
        # print(results)
        """commentMap ���� comment�Ĳ��ȡ����ڻظ���comment���һ��commentָ����ͬ�������ظ���"""
        commentMap = {}
        for index, result in enumerate(results):
            commentMap[comments[index].id] = BeanParserHelper.getBeansFromTuple(ReviewComment(),
                                                                                ReviewComment.getItemKeyList(),
                                                                                result)

        """����review֮���changes���ж��Ƿ���comment����change�����"""
        change_trigger_comments = []

        if changes is None or changes.__len__() == 0:
            """ȱʧ��review comment �ֲ�"""
            for comment in comments:
                change_trigger_comments.append({
                    "pullrequest_node": pr_node_id,
                    "user_login": comment.user_login,
                    "comment_node": comment.node_id,
                    "comment_type": StringKeyUtils.STR_LABEL_REVIEW_COMMENT,
                    "change_trigger": -1,
                    "filepath": comment.path
                })
                for c in commentMap[comment.id]:
                    change_trigger_comments.append({
                        "pullrequest_node": pr_node_id,
                        "user_login": c.user_login,
                        "comment_node": c.node_id,
                        "comment_type": StringKeyUtils.STR_LABEL_REVIEW_COMMENT,
                        "change_trigger": -1,
                        "filepath": c.path
                    })

            return change_trigger_comments

        # """��ʱ  ������changetrigger �� comment���������"""
        # for comment in comments:
        #     if comment.change_trigger is not None:
        #         change_trigger_comments.append({
        #             "pullrequest_node": pr_node_id,
        #             "user_login": comment.user_login,
        #             "comment_node": comment.node_id,
        #             "comment_type": StringKeyUtils.STR_LABEL_REVIEW_COMMENT,
        #             "change_trigger": comment.change_trigger,
        #             "filepath": comment.path
        #         })
        #         for c in commentMap[comment.id]:
        #             change_trigger_comments.append({
        #                 "pullrequest_node": pr_node_id,
        #                 "user_login": c.user_login,
        #                 "comment_node": c.node_id,
        #                 "comment_type": StringKeyUtils.STR_LABEL_REVIEW_COMMENT,
        #                 "change_trigger": comment.change_trigger,
        #                 "filepath": c.path
        #             })
        #         comments.remove(comment)
        #         print("skip now comment len:", comments.__len__())
        #
        # if comments.__len__() == 0:
        #     return change_trigger_comments

        # """ͨ��comment�� position��originalPosition��Ϣ��ȫline, originalLine ��Ҫ��Ӧcommit��file��patch"""

        isFileNeedFetched = False
        """����comment ���û��LEFT�򲻻�ȡ"""
        for comment in comments:
            if comment.side == 'LEFT':
                isFileNeedFetched = True
                break

        oids = list(set([comment.original_commit_id for comment in comments]))
        """��ȡ��Щ��changes files"""

        files = []
        if isFileNeedFetched:
            files = await AsyncApiHelper.getFilesFromStore(oids, mysql)
        # t21 = datetime.now()
        # print("get file cost:", t21-t11, " total:", t21 - t1)
        # """���β�ȫ"""
        #
        # needFetch = False
        for comment in comments:
            """commentĬ��δ����change_trigger"""
            comment.change_trigger = -1
        #     # if comment.original_line is None:
        #     #     needFetch = True
        #     #     break
        #     if comment.original_line is not None and comment.side is not None:
        #         continue
        #
        #     for file in files:
        #         if file.commit_sha == comment.original_commit_id and file.filename == comment.path:
        #             """����origin line �� side"""
        #             original_line, side = TextCompareUtils.getStartLine(file.patch, comment.original_position)
        #
        #             """���Patch������ ��patch ��ɣ��������ȡ"""
        #             try:
        #                 if TextCompareUtils.patchParser(file.patch).__len__() >= 2:
        #                     needFetch = True
        #             except Exception as e:
        #                 print("parser patch fail!")
        #                 print(e)
        #
        #             """
        #              ע �� 2020.07.09 ��patch�Ƕ��patch��ϵ�ʱ�� �Լ����������original_line ���ܻ���1�е����
        #                    ����ԭ����  �Ա�����: https://github.com/gib94927855/Review/pull/3#pullrequestreview-445279262
        #                                           https://github.com/yarnpkg/yarn/pull/2723
        #             """
        #
        #             comment.side = side
        #             comment.original_line = original_line
        #
        #             """line �ǸĶ����ı�����ָ��������� original line �ǸĶ�ǰ���ı�����ָ������
        #                �� line �ͱ��� original line
        #             """
        #
        #             """�������֮����Ϊ�� ��������ȡ"""
        #             if comment.side is None or comment.original_line is None:
        #                 needFetch = True
        #
        # """"�ֽ׶���Э  �ȿ�comment ��û�� original_line �ֶΣ� û�еĻ�comment ���»�ȡ��ȫ"""
        # if needFetch:
        #     statistic.lock.acquire()
        #     statistic.needFetchCommentForLineCount += 1
        #     statistic.lock.release()
        #     print("now needFetchCommentForLine Count:", statistic.needFetchCommentForLineCount, ' not need:',
        #           statistic.notNeedFetchCommentForLineCount)
        #
        #     async with aiohttp.ClientSession() as session:
        #         """���ݿ��ȡ pr"""
        #         tempPR = PullRequest()
        #         tempPR.node_id = pr_node_id
        #         pr_number = None
        #         result = await AsyncSqlHelper.queryBeanData([tempPR], mysql, [[StringKeyUtils.STR_KEY_NODE_ID]])
        #         if result[0].__len__() > 0:
        #             pr_number = result[0][0][PullRequest.getItemKeyList().index(StringKeyUtils.STR_KEY_NUMBER)]
        #         """v3 ��ȡcomments"""
        #         if pr_number is not None:
        #             """��ȡreview comment��Ϣ"""
        #             api = AsyncApiHelper.getReviewCommentForPullRequestApi(pr_number)
        #             json = await AsyncApiHelper.fetchBeanData(session, api, isMediaType=True)
        #             reviewComments = await AsyncApiHelper.parserReviewComment(json)
        #             await AsyncSqlHelper.updateBeanDateList(reviewComments, mysql)
        #             for comment in comments:
        #                 for comment_t in reviewComments:
        #                     if comment.node_id == comment_t.node_id:
        #                         comment.side = comment_t.side
        #                         comment.original_line = comment_t.original_line
        # else:
        #     statistic.lock.acquire()
        #     statistic.notNeedFetchCommentForLineCount += 1
        #     statistic.lock.release()
        #     print("now needFetchCommentForLine Count:", statistic.needFetchCommentForLineCount, ' not need:',
        #           statistic.notNeedFetchCommentForLineCount)

        """����entry����  ���ӱ��ػ���"""
        treeEntryLocalList = []

        """storeBeanList �����ռ���Ҫ�洢��bean ���ͳһ����, updateBeanList ͬ��"""
        storeBeanList = []
        updateBeanList = []

        """comment ��blob��ǰ��ȡ����Ҫ�ڴ�ѭ�����淴����ȡ"""
        """��ȡtree_id"""
        commitTreeList = await AsyncApiHelper.getCommitsByCheckTreeOID(oids, mysql, pr_node_id,
                                                                       storeBeanList, updateBeanList)

        if (None, None) in commitTreeList:
            """�쳣ֱ�ӷ���"""
            print("commit Tree fetch failed for oids:", oids, '  pr:', pr_node_id, " count:",
                  statistic.commitNotFoundErrorCount)
            statistic.lock.acquire()
            statistic.commitNotFoundErrorCount += 1
            statistic.lock.release()
            for comment in comments:
                change_trigger_comments.append({
                    "pullrequest_node": pr_node_id,
                    "user_login": comment.user_login,
                    "comment_node": comment.node_id,
                    "comment_type": StringKeyUtils.STR_LABEL_REVIEW_COMMENT,
                    "change_trigger": -1,
                    "filepath": comment.path
                })
                for c in commentMap[comment.id]:
                    change_trigger_comments.append({
                        "pullrequest_node": pr_node_id,
                        "user_login": c.user_login,
                        "comment_node": c.node_id,
                        "comment_type": StringKeyUtils.STR_LABEL_REVIEW_COMMENT,
                        "change_trigger": -1,
                        "filepath": c.path
                    })

            return change_trigger_comments

        reviewCommentTreeOidMap = {}
        for t in commitTreeList:
            reviewCommentTreeOidMap[t[0]] = t[1]

        blobMap = {}
        for comment in comments:
            blobMap[comment.id] = await AsyncApiHelper.getBlob(reviewCommentTreeOidMap[comment.original_commit_id]
                                                               , comment.path, mysql, pr_node_id, storeBeanList,
                                                               treeEntryLocalList)

        """����ʱ����Ҫ��֤ reviewComment��orignal_line �� side���� 
           ��AsyncProjectAllDataFetcher.getNoOriginLineReviewComment"""

        """����comment������comment��side�� LEFT �ĳ�������Ҫ���������ת���� RIGHT �������汾
            LEFT ���ֻ�� 3% ��������Ӧ�ÿ��Խ���
        """
        for comment in comments:
            if comment.side == 'LEFT':
                for file in files:
                    if file.commit_sha == comment.original_commit_id and file.filename == comment.path:
                        comment.temp_original_line = TextCompareUtils.ConvertLeftToRight(file.patch,
                                                                                         comment.original_position)
            else:
                comment.temp_original_line = comment.original_line

        t2 = datetime.now()
        print("update comment cost time:", t2 - t1, '  total:', t2 - t1)

        for change in changes:  # �Ժ��������Ķ����α���
            reviewCommit = review.pull_request_review_commit
            changeCommit = None
            if change.typename == StringKeyUtils.STR_KEY_PULL_REQUEST_COMMIT:
                changeCommit = change.pull_request_commit
            elif change.typename == StringKeyUtils.STR_KEY_HEAD_REF_PUSHED_EVENT:
                changeCommit = change.headRefForcePushedEventAfterCommit

            if changeCommit is None or reviewCommit is None:
                break
            try:
                """��ȡ����commit ��Ӧ�� tree_id"""
                commitTreeList = await AsyncApiHelper.getCommitsByCheckTreeOID([changeCommit], mysql,
                                                                               pr_node_id, storeBeanList,
                                                                               updateBeanList)
                print("commitTreeList", commitTreeList, " changecommit:", changeCommit, 'reviewCommit:', reviewCommit)
                changeCommitTreeOid = None
                for oid, tree_oid in commitTreeList:
                    if oid == changeCommit:
                        changeCommitTreeOid = tree_oid

                for comment in comments:

                    t3 = datetime.now()

                    """���α���ÿһ�� comment, Ѱ�� comment ��Ӧ���ļ���blob
                       ������commit�汾�е��ı�
                    """
                    if comment.temp_original_line is None or comment.side is None:
                        comment.change_trigger = -1
                        continue

                    fileName = comment.path
                    reviewBlob = blobMap.get(comment.id)
                    changeBlob = await AsyncApiHelper.getBlob(changeCommitTreeOid, fileName, mysql, pr_node_id
                                                              , storeBeanList, treeEntryLocalList)

                    if reviewBlob == changeBlob:
                        comment.change_trigger = -1
                        continue

                    if reviewBlob is None or changeBlob is None:
                        print("--" * 50)
                        print("blob is None!")
                        print(fileName)
                        print(comment.getValueDict())
                        print([reviewCommit, changeCommit])
                        print("--" * 50)
                        continue

                    print("review blob len:", reviewBlob.__len__(), ' changeblob len:', changeBlob.__len__())

                    t4 = datetime.now()
                    print("fetch blob cost time:", t4 - t3, '  total:', t4 - t1)

                    if not configPraser.getIsChangeTriggerByLine():
                        """���ڲ�ϸ�µ�ChangeTrigger�汾  �������ݲ���ͬ����"""
                        if reviewBlob != changeBlob:
                            comment.change_trigger = 1
                        else:
                            if comment.change_trigger == -1:
                                comment.change_trigger = -1
                    else:
                        """��ȡ����Blob���ı�����֮�󣬱Ƚϲ���"""
                        review_text_lines = reviewBlob.splitlines()
                        change_text_lines = changeBlob.splitlines()

                        diff = difflib.unified_diff(
                            review_text_lines,
                            change_text_lines,
                            lineterm='',
                        )

                        patch = '\n'.join(diff)
                        # print(patch)
                        """���� patch"""
                        """patch ��ǰ����  
                           --- 
                           +++
                        ȥ��"""
                        textChanges = TextCompareUtils.patchParser(patch[10:])
                        dis = 10000000
                        """���α���ÿ��patch �ҵ�ÿ��patch �о��� original_line ����ĸĶ�����"""
                        for textChange in textChanges:
                            start_left, _, start_right, _ = textChange[0]
                            status = textChange[1]
                            """curPos ѡȡ left�� ��Ϊ���ڱ䶯��comment �����������ϰ汾"""
                            curPos = start_left - 1
                            for s in status:
                                if s != '+':
                                    curPos += 1
                                if s != ' ':
                                    dis = min(dis, abs(comment.temp_original_line - curPos))
                        if dis <= 10:
                            if comment.change_trigger == -1:
                                comment.change_trigger = dis
                            else:
                                comment.change_trigger = min(comment.change_trigger, dis)
                        else:
                            if comment.change_trigger == -1:
                                comment.change_trigger = -1

                        t5 = datetime.now()
                        print("compare comment cost time:", t5 - t4, '  total:', t5 - t1)
            except Exception as e:
                print(e)
                continue
        for comment in comments:
            change_trigger_comments.append({
                "pullrequest_node": pr_node_id,
                "user_login": comment.user_login,
                "comment_node": comment.node_id,
                "comment_type": StringKeyUtils.STR_LABEL_REVIEW_COMMENT,
                "change_trigger": comment.change_trigger,
                "filepath": comment.path
            })
            for c in commentMap[comment.id]:
                change_trigger_comments.append({
                    "pullrequest_node": pr_node_id,
                    "user_login": c.user_login,
                    "comment_node": c.node_id,
                    "comment_type": StringKeyUtils.STR_LABEL_REVIEW_COMMENT,
                    "change_trigger": comment.change_trigger,
                    "filepath": c.path
                })
        statistic.lock.acquire()
        statistic.usefulChangeTrigger += [x for x in comments if x.change_trigger > 0].__len__()
        statistic.lock.release()

        updateBeanList.extend(comments)

        # ����comments��change_trigger, line, original_line��Ϣ"""
        await AsyncSqlHelper.storeBeanDateList(storeBeanList, mysql)
        await AsyncSqlHelper.updateBeanDateList(updateBeanList, mysql)
        t6 = datetime.now()
        print("single pair all total:", t6 - t1)
        return change_trigger_comments

    @staticmethod
    async def getReviewCommentsByNodeFromStore(node_id, mysql):
        """�����ݿ��ж�ȡreview id ��ʱ�����ֻҪ�����ݿ������Ӿ�ok��"""

        review = Review()
        review.node_id = node_id

        reviews = await AsyncSqlHelper.queryBeanData([review], mysql, [[StringKeyUtils.STR_KEY_NODE_ID]])
        # print("reviews:", reviews)
        if reviews is not None and reviews[0] is not None and reviews[0].__len__() > 0:
            review_id = reviews[0][0][2]
            # print("review_id:", review_id)
            comment = ReviewComment()
            comment.pull_request_review_id = review_id

            result = await AsyncSqlHelper.queryBeanData([comment], mysql,
                                                        [[StringKeyUtils.STR_KEY_PULL_REQUEST_REVIEW_ID]])
            # print(result)
            if result is not None and result[0] is not None and result[0].__len__() > 0:
                comments = BeanParserHelper.getBeansFromTuple(ReviewComment(), ReviewComment.getItemKeyList(),
                                                              result[0])

                """��ȡcomment �Լ���Ӧ��sha ��nodeId ������,fileName"""
                for comment in comments:
                    pass
                    # print(comment.getValueDict())
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

        if queryFiles is not None and queryFiles.__len__() > 0:
            results = await AsyncSqlHelper.queryBeanData(queryFiles, mysql,
                                                         [[StringKeyUtils.STR_KEY_COMMIT_SHA]] * queryFiles.__len__())
            print("files:", results)
            for result in results:
                if result is not None and result.__len__() > 0:
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
            if relationTuple is not None and relationTuple.__len__() > 0:
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
    async def getCommitsByCheckTreeOID(oids, mysql, pr_node_id, storeBeanList_all, updateBeanList_all):
        """��ȡ oids �б��commit
           ע�� 2020.7.8 commit�����ֶ� tree_oid ��Ϊcommit�������ݿ��� 22W+
                һ���Ը��±Ƚ�����  ������
                �ȴӱ������ݿ��ȡ������е���û��tree_oid ��Ҳ���»�ȡ
                
                ����û�л������ݿ�û��tree_oid�ֶε�commitҲ���»�ȡ
                û�еĵ���store ���Ѿ��еĵ��� update
        """

        """�ȴӱ��ض�ȡ"""
        beans = []
        needUpdateList = []
        needFetchList = oids.copy()
        resultCommitList = []

        """update �� fetch һ�� update,һ��store ʹ�ò�ͬsql"""
        updateBeanList = []
        fetchBeanList = []
        for oid in oids:
            bean = Commit()
            bean.sha = oid
            beans.append(bean)

        results = await AsyncSqlHelper.queryBeanData(beans, mysql, [[StringKeyUtils.STR_KEY_SHA]] * beans.__len__())
        # print("result:", results)
        treeOidPos = Commit.getItemKeyList().index(StringKeyUtils.STR_KEY_TREE_OID)
        shaPos = Commit.getItemKeyList().index(StringKeyUtils.STR_KEY_SHA)

        for pos, result in enumerate(results):
            if result.__len__() > 0:
                sha = result[0][shaPos]
                treeOid = result[0][treeOidPos]
                print("query commit for tree:", pos, " sha:", sha, " tree:", treeOid, ' all:', oids, ' pr:', pr_node_id)

                """���ݽ�������б�"""
                needFetchList.remove(sha)
                if treeOid is None:
                    needUpdateList.append(sha)
                else:
                    resultCommitList.append((sha, treeOid))

        print("need update:", needUpdateList)
        print("need fetched:", needFetchList)

        async with aiohttp.ClientSession() as session:
            """��api ��ȡ commit ��Ϣ�����ڸ���"""
            for oid in needUpdateList:
                api = AsyncApiHelper.getCommitApi(oid)
                json = await AsyncApiHelper.fetchBeanData(session, api)
                print("fetch data v3 for commit tree oid for update:", oid, ' all:', oids, ' pr:', pr_node_id)
                commit = await AsyncApiHelper.parserCommit(json)
                commit.has_file_fetched = True
                resultCommitList.append((commit.sha, commit.tree_oid))

                if commit.parents is not None:
                    updateBeanList.extend(commit.parents)
                if commit.files is not None:
                    updateBeanList.extend(commit.files)

                updateBeanList.append(commit)
            # await AsyncSqlHelper.updateBeanDateList(updateBeanList, mysql)
            updateBeanList_all.extend(updateBeanList)

            for oid in needFetchList:
                api = AsyncApiHelper.getCommitApi(oid)
                json = await AsyncApiHelper.fetchBeanData(session, api)
                print("fetch data v3 for commit tree oid for store:", oid, ' all:', oids, ' pr:', pr_node_id)
                commit = await AsyncApiHelper.parserCommit(json)
                commit.has_file_fetched = True
                resultCommitList.append((commit.sha, commit.tree_oid))

                if commit.parents is not None:
                    fetchBeanList.extend(commit.parents)
                if commit.files is not None:
                    fetchBeanList.extend(commit.files)

                fetchBeanList.append(commit)
            # await AsyncSqlHelper.storeBeanDateList(fetchBeanList, mysql)
            storeBeanList_all.extend(fetchBeanList)

        return resultCommitList

    @staticmethod
    async def getBlob(tree_oid, path, mysql, pr_node_id, beanList, treeEntryLocalList):
        """��ȡ ���� Tree��Ӧ�� path��blob����
           ·������ ѭ����ȡ�����ߵݹ�
        """
        async with aiohttp.ClientSession() as session:
            """�ָ�·��"""
            t1 = datetime.now()
            paths = path.split('/')
            print(paths, ' pr_node_id:', pr_node_id, ' tree:', tree_oid)
            blobText = None

            """�Ȼ�ȡtree�ĸ��ڵ�"""
            curOid = tree_oid
            curPos = 0
            isBlobFind = False  # ȷ��blob�Ƿ��ȡ
            isEntryBroken = False  # ȷ��TreeEntry�Ƿ��ж�

            while curPos < paths.__len__():
                treeEntryList = []
                isEntryFind = False

                """�ȳ��Ա��ػ����"""
                for entry in treeEntryLocalList:
                    if entry.child_path == paths[curPos] and entry.parent_oid == curOid:
                        curOid = entry.child_oid
                        childType = entry.child_type
                        curPos += 1
                        isEntryFind = True
                        if curPos == paths.__len__() and childType == StringKeyUtils.STR_KEY_BLOB:
                            isBlobFind = True
                        break

                if not isEntryFind:
                    """�ȳ������ݿ��ж�ȡ"""
                    tempEntry = TreeEntry()
                    tempEntry.repository = AsyncApiHelper.owner + '/' + AsyncApiHelper.repo
                    tempEntry.parent_oid = curOid
                    results = await AsyncSqlHelper.queryBeanData([tempEntry], mysql, [[StringKeyUtils.STR_KEY_REPOSITORY,
                                                                                       StringKeyUtils.STR_KEY_PARENT_OID]])

                    """�������ػ���"""
                    if results[0] is not None:
                        entrys = BeanParserHelper.getBeansFromTuple(TreeEntry(), TreeEntry.getItemKeyList(), results[0])
                        treeEntryLocalList.extend(entrys)

                    """��ѯ��Ϊ����Entry ��ѯ"""
                    isFind = False
                    for result in results[0]:
                        if result[TreeEntry.getItemKeyList().index(StringKeyUtils.STR_KEY_CHILD_PATH)] == paths[curPos]:
                            curOid = result[TreeEntry.getItemKeyList().index(StringKeyUtils.STR_KEY_CHILD_OID)]
                            childType = result[TreeEntry.getItemKeyList().index(StringKeyUtils.STR_KEY_CHILD_TYPE)]
                            curPos += 1
                            isFind = True
                            isEntryFind = True
                            if curPos == paths.__len__() and childType == StringKeyUtils.STR_KEY_BLOB:
                                isBlobFind = True
                            break

                    if results[0].__len__() > 0 and not isFind:
                        print("not find in database for fetched entrys!", tree_oid, '  path:', path)
                        isEntryBroken = True
                        break

                if isEntryBroken:
                    isBlobFind = False
                    break

                if not isEntryFind:
                    """��v4�ӿڻ��tree ��ϵ"""
                    args = {"expression": "", "owner": AsyncApiHelper.owner,
                            "name": AsyncApiHelper.repo, "oid": curOid}
                    api = AsyncApiHelper.getGraphQLApi()
                    query = GraphqlHelper.getTreeByOid()
                    resultJson = await AsyncApiHelper.postGraphqlData(session, api, query, args)
                    print("fetch from v4 relation:", curOid, 'treeOid:', tree_oid, ' pr:', pr_node_id)
                    print("relation result:", resultJson)

                    if isinstance(resultJson, dict):
                        rawData = resultJson.get(StringKeyUtils.STR_KEY_DATA, None)
                        if isinstance(rawData, dict):
                            repoData = rawData.get(StringKeyUtils.STR_KEY_REPOSITORY, None)
                            if isinstance(repoData, dict):
                                objectData = repoData.get(StringKeyUtils.STR_KEY_OBJECT, None)
                                treeEntryList = TreeEntry.parserV4.parser(objectData)
                                beanList.extend(treeEntryList)
                                treeEntryLocalList.extend(treeEntryList)

                    isFind = False
                    for entry in treeEntryList:
                        if entry.child_path == paths[curPos]:
                            curPos += 1
                            curOid = entry.child_oid
                            isFind = True

                            if curPos == paths.__len__() and entry.child_type == StringKeyUtils.STR_KEY_BLOB:
                                isBlobFind = True
                            break

                    if not isFind:
                        """tree ��ɾ��"""
                        isBlobFind = False
                        isEntryBroken = True
                        break

            if isBlobFind:
                """curOid ����Ŀ���blob����"""
                print('blob curoid:', curOid)

                """�ȴ����ݿ��ȡblob"""
                tempBlob = Blob()
                tempBlob.repository = AsyncApiHelper.owner + '/' + AsyncApiHelper.repo
                tempBlob.oid = curOid
                result = await AsyncSqlHelper.queryBeanData([tempBlob], mysql, [[StringKeyUtils.STR_KEY_REPOSITORY,
                                                                                 StringKeyUtils.STR_KEY_OID]])
                if result[0].__len__() > 0:
                    blobText = result[0][0][Blob.getItemKeyList().index(StringKeyUtils.STR_KEY_TEXT)]

                if blobText is None:
                    """��api��ȡBlob����"""
                    args = {"expression": "", "owner": AsyncApiHelper.owner,
                            "name": AsyncApiHelper.repo, "oid": curOid}
                    api = AsyncApiHelper.getGraphQLApi()
                    query = GraphqlHelper.getTreeByOid()
                    resultJson = await AsyncApiHelper.postGraphqlData(session, api, query, args)
                    print(resultJson)
                    print("fetch from v4 blob:", curOid, ' treeOid:', tree_oid, ' pr:', pr_node_id)

                    if isinstance(resultJson, dict):
                        rawData = resultJson.get(StringKeyUtils.STR_KEY_DATA, None)
                        if isinstance(rawData, dict):
                            repoData = rawData.get(StringKeyUtils.STR_KEY_REPOSITORY, None)
                            if isinstance(repoData, dict):
                                objectData = repoData.get(StringKeyUtils.STR_KEY_OBJECT, None)
                                blob = Blob.parserV4.parser(objectData)
                                blobText = blob.text
                                beanList.append(blob)

            # await  AsyncSqlHelper.storeBeanDateList(beanList, mysql)

            print("blob cost time:", datetime.now() - t1)

            return blobText

    @staticmethod
    async def downloadUserFollowList(userLogin, semaphore, mysql, statistic):
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                try:
                    beanList = []  # �����ռ���Ҫ�洢��bean��
                    """�Ȼ�ȡpull request��Ϣ"""
                    args = {"login": userLogin}
                    api = AsyncApiHelper.getGraphQLApi()
                    query = GraphqlHelper.getFollowingListByLogin()
                    resultJson = await AsyncApiHelper.postGraphqlData(session, api, query, args)
                    print(resultJson)

                    followingList = await AsyncApiHelper.parserUserFollowingList(resultJson)
                    beanList.extend(followingList)

                    await AsyncSqlHelper.storeBeanDateList(beanList, mysql)
                    # ����ͬ������
                    statistic.lock.acquire()
                    statistic.usefulCommitNumber += 1
                    print(f" usefulCommitCount:{statistic.usefulCommitNumber}")
                    statistic.lock.release()
                except Exception as e:
                    print(e)

    @staticmethod
    async def downloadCommits(projectName, oid, semaphore, mysql, statistic):
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                try:
                    beanList = []
                    owner, repo = projectName.split('/')
                    api = AsyncApiHelper.getCommitApiWithProjectName(owner, repo, oid)
                    json = await AsyncApiHelper.fetchBeanData(session, api)
                    print(json)
                    commit = await AsyncApiHelper.parserCommit(json)
                    """��v3�Ľӿ���Ϊ��GitFile"""
                    commit.has_file_fetched = True

                    if commit.parents is not None:
                        beanList.extend(commit.parents)
                    if commit.files is not None:
                        beanList.extend(commit.files)

                    # beanList.append(commit)
                    await AsyncSqlHelper.storeBeanDateList(beanList, mysql)
                    """commit ��Ϣ����"""
                    await AsyncSqlHelper.updateBeanDateList([commit], mysql)

                    # ����ͬ������
                    statistic.lock.acquire()
                    statistic.usefulCommitNumber += 1
                    print(f" usefulCommitCount:{statistic.usefulCommitNumber}")
                    statistic.lock.release()
                except Exception as e:
                    print(e)

    @staticmethod
    async def downloadSingleReviewComment(projectName, comment_id, semaphore, mysql, statistic):
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                try:
                    beanList = []
                    owner, repo = projectName.split('/')
                    api = AsyncApiHelper.getSingleReviewCommentApiWithProjectName(owner, repo, comment_id)
                    json = await AsyncApiHelper.fetchBeanData(session, api)
                    print(json)
                    comment = await AsyncApiHelper.parserSingleReviewComment(json)

                    await AsyncSqlHelper.updateBeanDateList([comment], mysql)

                    # ����ͬ������
                    statistic.lock.acquire()
                    statistic.usefulReviewCommentNumber += 1
                    print(f" usefulReviewCommentCount:{statistic.usefulReviewCommentNumber}")
                    statistic.lock.release()
                except Exception as e:
                    print(e)
