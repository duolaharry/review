# coding=gbk
import math
import os
import time
from datetime import datetime

from source.config.projectConfig import projectConfig
from source.scikit.FPS.FPSAlgorithm import FPSAlgorithm
from source.scikit.HG.Edge import Edge
from source.scikit.HG.HyperGraph import HyperGraph
from source.scikit.HG.Node import Node
from source.scikit.service.DataProcessUtils import DataProcessUtils
from source.utils.ExcelHelper import ExcelHelper
from source.utils.Gexf import Gexf
from source.utils.pandas.pandasHelper import pandasHelper
import numpy as np


class HGTrain:

    """��ͼ�����������������Ƽ�"""

    @staticmethod
    def TestAlgorithm(project, dates, alpha=0.8, K=20, c=1, tempMap=None):
        """���� ѵ������"""
        recommendNum = 5  # �Ƽ�����
        excelName = f'outputHG_{project}_{alpha}_{K}_{c}.xlsx'
        sheetName = 'result'

        """�����ۻ�����"""
        topks = []
        mrrs = []
        precisionks = []
        recallks = []
        fmeasureks = []

        """��ʼ��excel�ļ�"""
        ExcelHelper().initExcelFile(fileName=excelName, sheetName=sheetName, excel_key_list=['ѵ����', '���Լ�'])
        for date in dates:
            startTime = datetime.now()
            recommendList, answerList, prList, convertDict, trainSize = HGTrain.algorithmBody(date, project,
                                                                                              recommendNum,
                                                                                              alpha=alpha, K=K,
                                                                                              c=c, tempMap=tempMap)
            """�����Ƽ��б�������"""
            topk, mrr, precisionk, recallk, fmeasurek = \
                DataProcessUtils.judgeRecommend(recommendList, answerList, recommendNum)

            topks.append(topk)
            mrrs.append(mrr)
            precisionks.append(precisionk)
            recallks.append(recallk)
            fmeasureks.append(fmeasurek)

            """���д��excel"""
            DataProcessUtils.saveResult(excelName, sheetName, topk, mrr, precisionk, recallk, fmeasurek, date)

            """�ļ��ָ�"""
            content = ['']
            ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())
            content = ['ѵ����', '���Լ�']
            ExcelHelper().appendExcelRow(excelName, sheetName, content, style=ExcelHelper.getNormalStyle())

            print("cost time:", datetime.now() - startTime)

        """������ʷ�ۻ�����"""
        DataProcessUtils.saveFinallyResult(excelName, sheetName, topks, mrrs, precisionks, recallks,
                                           fmeasureks)

    @staticmethod
    def preProcess(df, dates):
        """����˵��
           df����ȡ��dataframe����
           dates:��Ԫ�飬����λ��Ϊ���Ե����� (,,year,month)
        """

        """ע�⣺ �����ļ����Ѿ�����������"""

        """��comment��review����nan��Ϣ������Ϊ����������õģ�����ֻ��ѵ����ȥ��na"""
        # """����NAN"""
        # df.dropna(how='any', inplace=True)
        # df.reset_index(drop=True, inplace=True)
        # df.fillna(value='', inplace=True)

        """��df���һ�б�ʶѵ�����Ͳ��Լ�"""
        df['label'] = df['pr_created_at'].apply(
            lambda x: (time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_year == dates[2] and
                       time.strptime(x, "%Y-%m-%d %H:%M:%S").tm_mon == dates[3]))
        """��reviewer�������ֻ����� �洢����ӳ���ֵ�������"""
        convertDict = DataProcessUtils.changeStringToNumber(df, ['author_user_login', 'review_user_login'])

        """���Ѿ��е����������ͱ�ǩ��ѵ�����Ĳ��"""
        train_data = df.loc[df['label'] == False].copy(deep=True)
        test_data = df.loc[df['label']].copy(deep=True)

        train_data.drop(columns=['label'], inplace=True)
        test_data.drop(columns=['label'], inplace=True)

        """����NAN"""
        train_data.dropna(how='any', inplace=True)
        train_data.reset_index(drop=True, inplace=True)
        train_data.fillna(value='', inplace=True)

        """�ȶ�tag�����"""
        trainDict = dict(list(train_data.groupby('pr_number')))
        testDict = dict(list(test_data.groupby('pr_number')))

        """ע�⣺ train_data �� test_data ���ж��comment��filename�����"""
        test_data_y = {}
        for pull_number in test_data.drop_duplicates(['pr_number'])['pr_number']:
            reviewers = list(testDict[pull_number].drop_duplicates(['review_user_login'])['review_user_login'])
            test_data_y[pull_number] = reviewers

        train_data_y = {}
        for pull_number in train_data.drop_duplicates(['pr_number'])['pr_number']:
            reviewers = list(trainDict[pull_number].drop_duplicates(['review_user_login'])['review_user_login'])
            train_data_y[pull_number] = reviewers

        return train_data, train_data_y, test_data, test_data_y, convertDict

    @staticmethod
    def algorithmBody(date, project, recommendNum=5, alpha=0.98, K=20, c=1, tempMap=None):

        """�ṩ�������ں���Ŀ����
           �����Ƽ��б�ʹ�
           ����ӿڿ��Ա�����㷨����
        """
        print(date)
        df = None
        for i in range(date[0] * 12 + date[1], date[2] * 12 + date[3] + 1):  # ��ֵ�������ƴ��
            y = int((i - i % 12) / 12)
            m = i % 12
            if m == 0:
                m = 12
                y = y - 1

            # print(y, m)
            filename = projectConfig.getHGDataPath() + os.sep + f'HG_ALL_{project}_data_{y}_{m}_to_{y}_{m}.tsv'
            """�����Դ�head"""
            if df is None:
                df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD)
            else:
                temp = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD)
                df = df.append(temp)  # �ϲ�

        df.reset_index(inplace=True, drop=True)
        """df��Ԥ����"""
        """��������ӳ���ֵ�"""
        train_data, train_data_y, test_data, test_data_y, convertDict = HGTrain.preProcess(df, date)

        prList = list(set(test_data['pr_number']))
        prList.sort()

        recommendList, answerList, authorList = HGTrain.RecommendByHG(train_data, train_data_y, test_data,
                                                          test_data_y, date, project, convertDict, recommendNum=recommendNum,
                                                          alpha=alpha, K=K, c=c, useLocalPrDis=True,tempMap=tempMap)

        """�����Ƽ������������ͳ��"""
        DataProcessUtils.saveRecommendList(prList, recommendList, answerList, convertDict, key=project + str(date),
                                           authorList=authorList)

        """��������ѵ���� ���Լ���С"""
        trainSize = (train_data.shape[0], test_data.shape[0])
        print(trainSize)

        return recommendList, answerList, prList, convertDict, trainSize

    @staticmethod
    def createTrainDataGraph(train_data, train_data_y, trainPrDis, prToRevMat, authToRevMat, reviewerFreqDict, c):
        """ͨ��ѵ�����������ͼ ���Զ���Ķ���ı���Ҫ�������"""

        graph = HyperGraph()

        """�����PR�Ķ���"""
        prList = list(set(train_data['pr_number']))
        prList.sort()  # ��С��������
        prList = tuple(prList)
        for pr in prList:
            graph.add_node(nodeType=Node.STR_NODE_TYPE_PR, contentKey=pr, description=f"pr:{pr}")

        """����author�Ķ���"""
        authorList = list(set(train_data['author_user_login']))
        for author in authorList:
            graph.add_node(nodeType=Node.STR_NODE_TYPE_AUTHOR, contentKey=author, description=f"author:{author}")

        """����reviewer�Ķ���"""
        reviewerList = list(set(train_data['review_user_login']))
        for reviewer in reviewerList:
            graph.add_node(nodeType=Node.STR_NODE_TYPE_REVIEWER, contentKey=reviewer, description=f"reviewer:{reviewer}")

        """����pr֮��ı�"""
        for p1 in prList:
            node_1 = graph.get_node_by_content(Node.STR_NODE_TYPE_PR, p1)
            for p2 in prList:
                weight = trainPrDis.get((p1, p2), None)
                if weight is not None:
                    node_2 = graph.get_node_by_content(Node.STR_NODE_TYPE_PR, p2)
                    graph.add_edge(nodes=[node_1.id, node_2.id], edgeType=Edge.STR_EDGE_TYPE_PR_DIS,
                                   weight=weight * c, description=f"pr distance between {p1} and {p2}",
                                   queryBeforeAdd=True)

        """����pr��reviewer�ı�  ������ʱreviewer���ϲ���һ�� weight��Ҫ����"""
        for pr in prList:
            reviewers = train_data_y[pr]
            for reviewer in reviewers:
                pr_node = graph.get_node_by_content(Node.STR_NODE_TYPE_PR, pr)
                reviewer_node = graph.get_node_by_content(Node.STR_NODE_TYPE_REVIEWER, reviewer)
                # Ȩ�زο�CF�İ汾
                graph.add_edge(nodes=[pr_node.id, reviewer_node.id], edgeType=Edge.STR_EDGE_TYPE_PR_REVIEW_RELATION,
                               weight=prToRevMat[pr][reviewer], description=f" pr review relation between pr {pr} and reviewer {reviewer}",                                   nodeObjects=[pr_node, reviewer_node])

        # """����pr �� author�ı�"""
        for pr in prList:
            author = list(set(train_data.loc[train_data['pr_number'] == pr]['author_user_login']))[0]
            pr_node = graph.get_node_by_content(Node.STR_NODE_TYPE_PR, pr)
            author_node = graph.get_node_by_content(Node.STR_NODE_TYPE_AUTHOR, author)
            graph.add_edge(nodes=[pr_node.id, author_node.id], edgeType=Edge.STR_EDGE_TYPE_PR_AUTHOR_RELATION,
                           weight=1, description=f" pr author relation between pr {pr} and author {author}",
                           nodeObjects=[pr_node, author_node])

        # """���� author �� reviewer �ı�"""
        # Ȩ�ؾ�Ϊ1�İ汾
        # userList = [x for x in authorList if x in reviewerList]
        # for user in userList:
        #     author_node = graph.get_node_by_content(Node.STR_NODE_TYPE_AUTHOR, user)
        #     reviewer_node = graph.get_node_by_content(Node.STR_NODE_TYPE_REVIEWER, user)
        #     graph.add_edge(nodes=[author_node.id, reviewer_node.id], edgeType=Edge.STR_EDGE_TYPE_AUTHOR_REVIEWER_RELATION,
        #                    weight=1, description=f"author reviewer relation for {user}",
        #                    nodeObjects=[author_node, reviewer_node])

        # # Ȩ�زο�CN�İ汾
        # for author, relations in authToRevMat.items():
        #     for reviewer, weight in relations.items():
        #         author_node = graph.get_node_by_content(Node.STR_NODE_TYPE_AUTHOR, author)
        #         reviewer_node = graph.get_node_by_content(Node.STR_NODE_TYPE_REVIEWER, reviewer)
        #         graph.add_edge(nodes=[author_node.id, reviewer_node.id], edgeType=Edge.STR_EDGE_TYPE_AUTHOR_REVIEWER_RELATION,
        #                        weight=weight, description=f"author reviewer relation for {author}",
        #                        nodeObjects=[author_node, reviewer_node])

        # """����ͼ�ļ�������"""
        # graph.updateMatrix()
        return graph

    @staticmethod
    def getTrainDataPrDistance(train_data, K, pathDict, date, prCreatedTimeMap, disMapList, useLocalPrDis):
        """������trainData�и��� pr ֮��ľ��� ͨ��·�����ƶȱȽ�
           {(num1, num2) -> s1}  ����num1 < num2
           ÿ������ȡ�����Ƶ� K ����Ϊ���Ӷ��󣬽�Լ�ռ�
           ע��  ������Щ������г���K����
        """
        trainPrDis = {}  # ���ڼ�¼pr�ľ���
        # ��ʼʱ�䣺���ݼ���ʼʱ���ǰһ��
        start_time = time.strptime(str(date[0]) + "-" + str(date[1]) + "-" + "01 00:00:00", "%Y-%m-%d %H:%M:%S")
        start_time = int(time.mktime(start_time) - 86400)
        # ����ʱ�䣺���ݼ������һ��
        end_time = time.strptime(str(date[2]) + "-" + str(date[3]) + "-" + "01 00:00:00", "%Y-%m-%d %H:%M:%S")
        end_time = int(time.mktime(end_time) - 1)

        print(train_data.shape)
        data = train_data[['pr_number', 'filename']].copy(deep=True)
        data.drop_duplicates(inplace=True)
        data.reset_index(inplace=True, drop=True)
        prList = list(set(data['pr_number']))
        prList.sort()  # ��С��������
        scoreMap = {}  # ͳ������pr֮�����ƶȵķ���

        for index, p1 in enumerate(prList):
            scores = {}  # ��¼
            print("now pr:", index, " all:", prList.__len__())
            for p2 in prList:
                if p1 < p2:
                    if p1 == 7960 and p2 == 8296:
                        print(p1)
                    score = 0
                    if not useLocalPrDis:
                        paths1 = list(pathDict[p1]['filename'])
                        paths2 = list(pathDict[p2]['filename'])
                        score = 0
                        for filename1 in paths1:
                            for filename2 in paths2:
                                # score += FPSAlgorithm.LCP_2(filename1, filename2)
                                score += FPSAlgorithm.LCS_2(filename1, filename2) + \
                                     FPSAlgorithm.LCSubseq_2(filename1, filename2) +\
                                     FPSAlgorithm.LCP_2(filename1, filename2) +\
                                     FPSAlgorithm.LCSubstr_2(filename1, filename2)
                        score /= paths1.__len__() * paths2.__len__()
                    else:
                        for i in range(0, 4):
                            score += disMapList[i][(p1, p2)] / 8
                        score += disMapList[-1][(p1, p2)] / 2
                    # t1 = list(train_data.loc[train_data['pr_number'] == p1]['pr_created_at'])[0]
                    # t2 = list(train_data.loc[train_data['pr_number'] == p2]['pr_created_at'])[0]
                    # t1 = time.strptime(t1, "%Y-%m-%d %H:%M:%S")
                    # t1 = int(time.mktime(t1))
                    # t2 = time.strptime(t2, "%Y-%m-%d %H:%M:%S")
                    # t2 = int(time.mktime(t2))
                    t1 = prCreatedTimeMap[p1]
                    t2 = prCreatedTimeMap[p2]
                    t = math.fabs(t1 - t2) / (end_time - start_time)

                    score = score * math.exp(t-1)

                    # TODO Ŀ�����ǳ��ĺ�ʱ�䣬 ����Ѱ���Ż��ķ���
                    scores[p2] = score
                    scoreMap[(p1, p2)] = score
                    scoreMap[(p2, p1)] = score
                elif p1 > p2:
                    score = scoreMap[(p1, p2)]
                    scores[p2] = score
            """�ҳ�K�������pr"""
            KNN = [x[0] for x in sorted(scores.items(), key=lambda d: d[1], reverse=True)[0:K]]
            for p2 in KNN:
                trainPrDis[(p1, p2)] = scores[p2]  # p1,p2��˳����ܻ����Ӱ��
        return trainPrDis

    @staticmethod
    def RecommendByHG(train_data, train_data_y, test_data, test_data_y, date, project, convertDict, recommendNum=5,
                      K=20, alpha=0.8, c=1, useLocalPrDis=False, tempMap=None):
        """���ڳ�ͼ�����Ƽ��㷨
           K �����������Ƕ����ڽ���pr
           alpha �������� �����������
           c �������� ���ڵ���pr���Ʊߵ����Ȩֵ����
        """
        recommendList = []
        answerList = []
        testDict = dict(list(test_data.groupby('pr_number')))
        authorList = []

        print("start building hypergraph....")
        start = datetime.now()

        """����ѵ������pr�Ĵ���ʱ��"""
        prCreatedTimeMap = {}
        for pr, temp_df in dict(list(train_data.groupby('pr_number'))).items():
            t1 = list(temp_df['pr_created_at'])[0]
            t1 = time.strptime(t1, "%Y-%m-%d %H:%M:%S")
            t1 = int(time.mktime(t1))
            prCreatedTimeMap[pr] = t1

        """����ѵ������pr�ľ���"""

        """���Զ�ȡ֮ǰ����Ľ��"""
        disMapList = None
        if useLocalPrDis:
            # disMapList = HGTrain.loadLocalPrDistance(project)
            disMapList = tempMap

        tempData = train_data[['pr_number', 'filename']].copy(deep=True)
        tempData.drop_duplicates(inplace=True)
        tempData.reset_index(inplace=True, drop=True)
        pathDict = dict(list(tempData.groupby('pr_number')))
        trainPrDis = HGTrain.getTrainDataPrDistance(train_data, K, pathDict, date, prCreatedTimeMap, disMapList, useLocalPrDis)
        print(" pr distance cost time:", datetime.now() - start)

        """����ѵ������reviewer�� review ����
           CN �㷨��review����С�����ε����ų�����  HG����Ҳ��������
        """
        tempData = train_data[['pr_number', 'review_user_login']].copy(deep=True)
        tempData.drop_duplicates(inplace=True)
        reviewerFreqDict = {}
        for r, temp_df in dict(list(tempData.groupby('review_user_login'))).items():
            reviewerFreqDict[r] = temp_df.shape[0]

        """����review -> requestȨ��"""
        prToRevMat = HGTrain.buildPrToRevRelation(train_data)

        """����author -> reviewerȨ��"""
        authToRevMat = HGTrain.buildAuthToRevRelation(train_data, date)

        """������ͼ"""
        graph = HGTrain.createTrainDataGraph(train_data, train_data_y, trainPrDis, prToRevMat, authToRevMat,
                                             reviewerFreqDict, c)
        # HGTrain.toGephiData(project, date, convertDict, graph)
        # graph.drawGraphByNetworkX()

        prList = list(set(train_data['pr_number']))
        prList.sort()  # ��С��������
        prList = tuple(prList)

        startTime = datetime.now()

        pr_created_time_data = train_data['pr_created_at'].apply(
            lambda x: time.mktime(time.strptime(x, "%Y-%m-%d %H:%M:%S")))
        start_time = min(pr_created_time_data.to_list())
        # ����ʱ�䣺���ݼ�pr����Ĵ���ʱ��
        pr_created_time_data = train_data['pr_created_at'].apply(
            lambda x: time.mktime(time.strptime(x, "%Y-%m-%d %H:%M:%S")))
        end_time = max(pr_created_time_data.to_list())

        pos = 0
        now = datetime.now()
        for test_pull_number, test_df in testDict.items():
            """��ÿһ������������  ���pr�ڵ��K���ߣ��Լ�������ӵ����߽ڵ�
               ���Ƽ�����֮��  ɾ��pr�ڵ��pr�ı� ������ӵ����߽ڵ�Ҳ����ɾ��
            """
            print("now:", pos, ' all:', testDict.items().__len__(), '  cost time:', datetime.now() - now)
            test_df.reset_index(drop=True, inplace=True)
            pos += 1

            """���pr�ڵ�"""
            pr_num = list(test_df['pr_number'])[0]
            paths2 = list(set(test_df['filename']))
            node_1 = graph.add_node(nodeType=Node.STR_NODE_TYPE_PR, contentKey=pr_num, description=f"pr:{pr_num}")

            """����K�� pr�ڵ�������ڵ����ӵı�"""
            scores = {}  # ��¼
            for p1 in prList:
                paths1 = list(pathDict[p1]['filename'])
                score = 0
                if not useLocalPrDis:
                    for filename1 in paths1:
                        for filename2 in paths2:
                            score += FPSAlgorithm.LCS_2(filename1, filename2) + \
                                     FPSAlgorithm.LCSubseq_2(filename1, filename2) +\
                                     FPSAlgorithm.LCP_2(filename1, filename2) +\
                                     FPSAlgorithm.LCSubstr_2(filename1, filename2)
                            # score += FPSAlgorithm.LCP_2(filename1, filename2)
                    score /= paths1.__len__() * paths2.__len__()
                else:
                    for i in range(0, 4):
                        score += disMapList[i][(pr_num, p1)] / 8
                    score += disMapList[-1][(pr_num, p1)] / 2
                # t2 = list(train_data.loc[train_data['pr_number'] == p1]['pr_created_at'])[0]
                # t2 = time.strptime(t2, "%Y-%m-%d %H:%M:%S")
                # t2 = int(time.mktime(t2))
                t2 = prCreatedTimeMap[p1]
                t = math.fabs(t2 - start_time) / (end_time - start_time)
                # TODO Ŀ�����ǳ��ĺ�ʱ�䣬 ����Ѱ���Ż��ķ���
                scores[p1] = score * math.exp(t - 1)
                # scores[p1] = score * t
                # scores[p1] = score
            """�ҳ�K�������pr"""
            KNN = [x[0] for x in sorted(scores.items(), key=lambda d: d[1], reverse=True)[0:K]]
            # """�ҳ���K������ص�pr���ӱ�"""
            for p2 in KNN:
                node_2 = graph.get_node_by_content(Node.STR_NODE_TYPE_PR, p2)
                graph.add_edge(nodes=[node_1.id, node_2.id], edgeType=Edge.STR_EDGE_TYPE_PR_DIS,
                               weight=c * scores[p2], description=f"pr distance between {pr_num} and {p2}",
                               nodeObjects=[node_1, node_2])

            """�����û�����߽ڵ� �������"""
            author = test_df['author_user_login'][0]
            authorList.append(author)

            if author == 237:
                print(test_pull_number)
            if author == 18:
                print(test_pull_number)

            authorNode = graph.get_node_by_content(Node.STR_NODE_TYPE_AUTHOR, author)
            needAddAuthorNode = False  # ���ΪTrue��������Ҫ�����߽ڵ�Ҳɾ��
            if authorNode is None:
                needAddAuthorNode = True
                authorNode = graph.add_node(nodeType=Node.STR_NODE_TYPE_AUTHOR, contentKey=author, description=f"author:{author}")
            """�������ߺ�pr֮��ı�"""
            graph.add_edge(nodes=[node_1.id, authorNode.id], edgeType=Edge.STR_EDGE_TYPE_PR_AUTHOR_RELATION,
                           weight=0.00001, description=f" pr author relation between pr {pr_num} and author {author}",
                           nodeObjects=[node_1, authorNode])

            start_temp_time = datetime.now()
            """���¼������A"""
            graph.updateMatrix()
            print("matrix update cost:", datetime.now() - start_temp_time)

            """�½���ѯ����"""
            y = np.zeros((graph.num_nodes, 1))
            """�������ߺ��Ƽ�pr��λ��Ϊ1 �ο���ֵ�ĵ����ַ�ʽ"""
            nodeInverseMap = {v: k for k, v in graph.node_id_map.items()}
            # y[nodeInverseMap[node_1.id]][0] = 1
            y[nodeInverseMap[authorNode.id]][0] = 1

            """����˳���б�f"""
            I = np.identity(graph.num_nodes)
            f = np.dot(np.linalg.inv(I - alpha * graph.A), y)

            """�Լ��������� �ҵ������ϸߵļ�λ"""
            if author == 18:
                print(18)
            scores = {}
            for i in range(0, graph.num_nodes):
                node_id = graph.node_id_map[i]
                node = graph.get_node_by_key(node_id)
                if node.type == Node.STR_NODE_TYPE_REVIEWER and reviewerFreqDict[node.contentKey] >= 2:
                    if node.contentKey != author:  # �����߹���
                        scores[node.contentKey] = f[i][0]

            answer = answer = test_data_y[pr_num]
            answerList.append(answer)
            recommendList.append([x[0] for x in sorted(scores.items(),
                                                       key=lambda d: d[1], reverse=True)[0:recommendNum]])

            """������߽ڵ���������ӵ�  ��ɾ��"""
            if needAddAuthorNode:
                graph.remove_node_by_key(authorNode.id)
            """ɾ�� pr �ڵ�"""
            graph.remove_node_by_key(node_1.id)

        print("total query cost time:", datetime.now() - startTime)
        return recommendList, answerList, authorList

    @staticmethod
    def buildPrToRevRelation(train_data):
        print("start building request -> reviewer relations....")
        start = datetime.now()
        # ��ʼʱ�䣺���ݼ�pr����Ĵ���ʱ��
        pr_created_time_data = train_data['pr_created_at'].apply(lambda x: time.mktime(time.strptime(x, "%Y-%m-%d %H:%M:%S")))
        start_time = min(pr_created_time_data.to_list())
        # ����ʱ�䣺���ݼ�pr����Ĵ���ʱ��
        pr_created_time_data = train_data['pr_created_at'].apply(lambda x: time.mktime(time.strptime(x, "%Y-%m-%d %H:%M:%S")))
        end_time = max(pr_created_time_data.to_list())
        prToRevMat = {}
        grouped_train_data = train_data.groupby([train_data['pr_number'], train_data['review_user_login']])
        max_weight = 0
        for relation, group in grouped_train_data:
            group.reset_index(drop=True, inplace=True)
            weight = HGTrain.caculateRevToPrWeight(group, start_time, end_time)
            max_weight = max(weight, max_weight)
            if not prToRevMat.__contains__(relation[0]):
                prToRevMat[relation[0]] = {}
            prToRevMat[relation[0]][relation[1]] = weight

        # ��һ��
        for pr, relations in prToRevMat.items():
            for rev, weight in relations.items():
                prToRevMat[pr][rev] = weight/max_weight
        print("finish building request -> reviewer relations. cost time: {0}s".format(datetime.now() - start))
        return prToRevMat

    @staticmethod
    def caculateRevToPrWeight(comment_records, start_time, end_time):
        """����reviewer��pr֮���Ȩ��"""
        weight_lambda = 0.0
        weight = 0
        comment_records = comment_records.copy(deep=True)
        comment_records.drop(columns=['filename'], inplace=True)
        comment_records.drop_duplicates(inplace=True)
        comment_records.reset_index(inplace=True, drop=True)
        """����ÿ�����ۣ�����Ȩ��"""
        for cm_idx, cm_row in comment_records.iterrows():
            cm_timestamp = time.strptime(cm_row['review_created_at'], "%Y-%m-%d %H:%M:%S")
            cm_timestamp = int(time.mktime(cm_timestamp))
            """����tֵ: the element t(ij,r,n) is a time-sensitive factor """
            t = (cm_timestamp - start_time) / (end_time - start_time)
            cm_weight = math.pow(weight_lambda, cm_idx) * math.exp(t-1)
            weight += cm_weight
        return weight

    @staticmethod
    def loadLocalPrDistance(project):
        prDisDf_LCP = pandasHelper.readTSVFile(projectConfig.getPullRequestDistancePath() + os.sep +
                                               f"pr_distance_{project}_LCP.tsv",
                                               header=pandasHelper.INT_READ_FILE_WITH_HEAD)
        prDisDf_LCS = pandasHelper.readTSVFile(projectConfig.getPullRequestDistancePath() + os.sep +
                                               f"pr_distance_{project}_LCS.tsv",
                                               header=pandasHelper.INT_READ_FILE_WITH_HEAD)
        prDisDf_LCSubseq = pandasHelper.readTSVFile(projectConfig.getPullRequestDistancePath() + os.sep +
                                                    f"pr_distance_{project}_LCSubseq.tsv",
                                                    header=pandasHelper.INT_READ_FILE_WITH_HEAD)
        prDisDf_LCSubstr = pandasHelper.readTSVFile(projectConfig.getPullRequestDistancePath() + os.sep +
                                                    f"pr_distance_{project}_LCSubstr.tsv",
                                                    header=pandasHelper.INT_READ_FILE_WITH_HEAD)
        prDisDf_IR = pandasHelper.readTSVFile(projectConfig.getPullRequestDistancePath() + os.sep +
                                                    f"pr_distance_{project}_IR.tsv",
                                                    header=pandasHelper.INT_READ_FILE_WITH_HEAD)

        DisMapLCP = {}
        DisMapLCS = {}
        DisMapLCSubseq = {}
        DisMapLCSubstr = {}
        DisMapIR = {}
        for row in prDisDf_LCP.itertuples(index=False, name='Pandas'):
            p1 = row[0]
            p2 = row[1]
            dis = row[2]
            DisMapLCP[(p1, p2)] = dis
            DisMapLCP[(p2, p1)] = dis

        for row in prDisDf_LCS.itertuples(index=False, name='Pandas'):
            p1 = row[0]
            p2 = row[1]
            dis = row[2]
            DisMapLCS[(p1, p2)] = dis
            DisMapLCS[(p2, p1)] = dis

        for row in prDisDf_LCSubseq.itertuples(index=False, name='Pandas'):
            p1 = row[0]
            p2 = row[1]
            dis = row[2]
            DisMapLCSubseq[(p1, p2)] = dis
            DisMapLCSubseq[(p2, p1)] = dis

        for row in prDisDf_LCSubstr.itertuples(index=False, name='Pandas'):
            p1 = row[0]
            p2 = row[1]
            dis = row[2]
            DisMapLCSubstr[(p1, p2)] = dis
            DisMapLCSubstr[(p2, p1)] = dis

        for row in prDisDf_IR.itertuples(index=False, name='Pandas'):
            p1 = row[0]
            p2 = row[1]
            dis = row[2]
            DisMapIR[(p1, p2)] = dis
            DisMapIR[(p2, p1)] = dis

        return [DisMapLCS, DisMapLCP, DisMapLCSubseq, DisMapLCSubstr, DisMapIR]
        # return [DisMapIR]


    @staticmethod
    def buildAuthToRevRelation(train_data, date):
        print("start building reviewer -> reviewer relations....")
        start = datetime.now()

        # ��ʼʱ�䣺���ݼ���ʼʱ���ǰһ��
        start_time = time.strptime(str(date[0]) + "-" + str(date[1]) + "-" + "01 00:00:00", "%Y-%m-%d %H:%M:%S")
        start_time = int(time.mktime(start_time) - 86400)
        # ����ʱ�䣺���ݼ������һ��
        end_time = time.strptime(str(date[2]) + "-" + str(date[3]) + "-" + "01 00:00:00", "%Y-%m-%d %H:%M:%S")
        end_time = int(time.mktime(end_time) - 1)

        authToRevMat = {}
        grouped_train_data = train_data.groupby([train_data['author_user_login'], train_data['review_user_login']])
        max_weight = 0
        for relation, group in grouped_train_data:
            group.reset_index(drop=True, inplace=True)
            weight = HGTrain.caculateAuthToRevWeight(group, start_time, end_time)
            max_weight = max(weight, max_weight)
            if not authToRevMat.__contains__(relation[0]):
                authToRevMat[relation[0]] = {}
            authToRevMat[relation[0]][relation[1]] = weight

        # ��һ��
        for auth, relations in authToRevMat.items():
            for rev, weight in relations.items():
                authToRevMat[auth][rev] = weight/max_weight

        print("finish building comments networks! ! ! cost time: {0}s".format(datetime.now() - start))
        return authToRevMat

    @staticmethod
    def caculateAuthToRevWeight(comment_records, start_time, end_time):
        """����author��reviewer��Ȩ��"""
        weight_lambda = 0.8
        weight = 0

        comment_records = comment_records.copy(deep=True)
        comment_records.drop(columns=['filename'], inplace=True)
        comment_records.drop_duplicates(inplace=True)
        comment_records.reset_index(inplace=True, drop=True)

        grouped_comment_records = comment_records.groupby(comment_records['pr_number'])
        for pr, comments in grouped_comment_records:
            comments.reset_index(inplace=True, drop=True)
            """����ÿ�����ۣ�����Ȩ��"""
            for cm_idx, cm_row in comments.iterrows():
                cm_timestamp = time.strptime(cm_row['review_created_at'], "%Y-%m-%d %H:%M:%S")
                cm_timestamp = int(time.mktime(cm_timestamp))
                """����tֵ: the element t(ij,r,n) is a time-sensitive factor """
                t = (cm_timestamp - start_time) / (end_time - start_time)
                cm_weight = math.pow(weight_lambda, cm_idx) * t
                weight += cm_weight
        return weight

    @staticmethod
    def toGephiData(project, date, convertDict, hyper_graph):
        file_name = f'{os.curdir}/gephi/{project}_{date[0]}_{date[1]}_{date[2]}_{date[3]}_network'

        gexf = Gexf("reviewer_recommend", file_name)
        gexf_graph = gexf.addGraph("directed", "static", file_name)
        gexf_graph.addNodeAttribute("type", 'unknown', type='string')
        gexf_graph.addNodeAttribute("description", '', type='string')
        gexf_graph.addEdgeAttribute("type", 'unknown', type='string')
        gexf_graph.addEdgeAttribute("description", '', type='string')

        tempDict = {k: v for v, k in convertDict.items()}
        edges = hyper_graph.edge_list
        for key, edge in edges.items():
            """�����ϵĵ���뵽ͼ��"""
            nodes = edge.connectedTo
            for node in nodes:
                node = hyper_graph.get_node_by_key(node)
                if node.type == Node.STR_NODE_TYPE_PR:
                    gexf_graph.addNode(id=str(node.contentKey), label=node.description,
                                       attrs=[{'id': 0, 'value': node.type},
                                              {'id': 1, 'value': node.description}])
                if node.type == Node.STR_NODE_TYPE_REVIEWER or node.type == Node.STR_NODE_TYPE_AUTHOR:
                    gexf_graph.addNode(id=str(node.contentKey), label=tempDict[node.contentKey],
                                       attrs=[{'id': 0, 'value': node.type},
                                              {'id': 1, 'value': node.description}])
            """���߼���ͼ��"""
            source = hyper_graph.get_node_by_key(edge.connectedTo[0])
            target = hyper_graph.get_node_by_key(edge.connectedTo[1])
            gexf_graph.addEdge(id=edge.id, source=str(source.contentKey), target=str(target.contentKey),
                               weight=edge.weight, attrs=[{'id': 2, 'value': edge.type},
                                      {'id': 3, 'value': edge.description}])
        output_file = open(file_name + ".gexf", "wb")
        gexf.write(output_file)
        output_file.close()
        return file_name + ".gexf"

if __name__ == '__main__':
    dates = [(2017, 1, 2018, 1), (2017, 1, 2018, 2), (2017, 1, 2018, 3), (2017, 1, 2018, 4), (2017, 1, 2018, 5),
             (2017, 1, 2018, 6), (2017, 1, 2018, 7), (2017, 1, 2018, 8), (2017, 1, 2018, 9), (2017, 1, 2018, 10),
             (2017, 1, 2018, 11), (2017, 1, 2018, 12)]
    # projects = ['opencv', 'cakephp', 'yarn', 'akka', 'django', 'react']
    # projects = ['babel', 'xbmc']
    # dates = [(2017, 1, 2018, 1), (2017, 1, 2018, 2), (2017, 1, 2018, 3), (2017, 1, 2018, 4)]
    projects = ['opencv']
    for p in projects:
        disMapList = HGTrain.loadLocalPrDistance(p)
        HGTrain.TestAlgorithm(p, dates, alpha=0.98, K=20, c=0.1, tempMap=disMapList)
