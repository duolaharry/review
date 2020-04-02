# coding=gbk
import os
import time
from datetime import datetime

import numpy
import pandas
from pandas import DataFrame

from source.config.projectConfig import projectConfig
from source.scikit.service.RecommendMetricUtils import RecommendMetricUtils
from source.utils.ExcelHelper import ExcelHelper
from source.utils.pandas.pandasHelper import pandasHelper


class DataProcessUtils:
    """���ڴ�����Ŀ����һЩͨ�õķ���������"""

    """������Щ���������غϣ�����������"""
    COLUMN_NAME_ALL = ['pr_repo_full_name', 'pr_number', 'pr_id', 'pr_node_id',
                       'pr_state', 'pr_title', 'pr_user_login', 'pr_body',
                       'pr_created_at',
                       'pr_updated_at', 'pr_closed_at', 'pr_merged_at', 'pr_merge_commit_sha',
                       'pr_author_association', 'pr_merged', 'pr_comments', 'pr_review_comments',
                       'pr_commits', 'pr_additions', 'pr_deletions', 'pr_changed_files',
                       'pr_head_label', 'pr_base_label',
                       'review_repo_full_name', 'review_pull_number',
                       'review_id', 'review_user_login', 'review_body', 'review_state', 'review_author_association',
                       'review_submitted_at', 'review_commit_id', 'review_node_id',

                       'commit_sha',
                       'commit_node_id', 'commit_author_login', 'commit_committer_login', 'commit_commit_author_date',
                       'commit_commit_committer_date', 'commit_commit_message', 'commit_commit_comment_count',
                       'commit_status_total', 'commit_status_additions', 'commit_status_deletions',

                       'file_commit_sha',
                       'file_sha', 'file_filename', 'file_status', 'file_additions', 'file_deletions', 'file_changes',
                       'file_patch',

                       'review_comment_id', 'review_comment_user_login', 'review_comment_body',
                       'review_comment_pull_request_review_id', 'review_comment_diff_hunk', 'review_comment_path',
                       'review_comment_commit_id', 'review_comment_position', 'review_comment_original_position',
                       'review_comment_original_commit_id', 'review_comment_created_at', 'review_comment_updated_at',
                       'review_comment_author_association', 'review_comment_start_line',
                       'review_comment_original_start_line',
                       'review_comment_start_side', 'review_comment_line', 'review_comment_original_line',
                       'review_comment_side', 'review_comment_in_reply_to_id', 'review_comment_node_id',
                       'review_comment_change_trigger']

    """ ����col��ԴSQL��䣺
            select *
        from pullRequest, review, gitCommit, gitFile, reviewComment
        where pullRequest.repo_full_name = 'scala/scala' and
          review.repo_full_name = pullRequest.repo_full_name
        and pullRequest.number = review.pull_number and
          gitCommit.sha = review.commit_id and gitFile.commit_sha = gitCommit.sha
        and reviewComment.pull_request_review_id = review.id
    """

    """
     ���ҵ��� ��������©��������û��reviewcomment�����ݱ����ӵ�����Ҫreviewcomment����������
    """

    COLUMN_NAME_PR_REVIEW_COMMIT_FILE = ['pr_repo_full_name', 'pr_number', 'pr_id', 'pr_node_id',
                                         'pr_state', 'pr_title', 'pr_user_login', 'pr_body',
                                         'pr_created_at',
                                         'pr_updated_at', 'pr_closed_at', 'pr_merged_at', 'pr_merge_commit_sha',
                                         'pr_author_association', 'pr_merged', 'pr_comments', 'pr_review_comments',
                                         'pr_commits', 'pr_additions', 'pr_deletions', 'pr_changed_files',
                                         'pr_head_label', 'pr_base_label',
                                         'review_repo_full_name', 'review_pull_number',
                                         'review_id', 'review_user_login', 'review_body', 'review_state',
                                         'review_author_association',
                                         'review_submitted_at', 'review_commit_id', 'review_node_id',

                                         'commit_sha',
                                         'commit_node_id', 'commit_author_login', 'commit_committer_login',
                                         'commit_commit_author_date',
                                         'commit_commit_committer_date', 'commit_commit_message',
                                         'commit_commit_comment_count',
                                         'commit_status_total', 'commit_status_additions', 'commit_status_deletions',

                                         'file_commit_sha',
                                         'file_sha', 'file_filename', 'file_status', 'file_additions', 'file_deletions',
                                         'file_changes',
                                         'file_patch']

    COLUMN_NAME_REVIEW_COMMENT = [
        'review_comment_id', 'review_comment_user_login', 'review_comment_body',
        'review_comment_pull_request_review_id', 'review_comment_diff_hunk', 'review_comment_path',
        'review_comment_commit_id', 'review_comment_position', 'review_comment_original_position',
        'review_comment_original_commit_id', 'review_comment_created_at', 'review_comment_updated_at',
        'review_comment_author_association', 'review_comment_start_line',
        'review_comment_original_start_line',
        'review_comment_start_side', 'review_comment_line', 'review_comment_original_line',
        'review_comment_side', 'review_comment_in_reply_to_id', 'review_comment_node_id',
        'review_comment_change_trigger']

    COLUMN_NAME_COMMIT_FILE = [
        'commit_sha',
        'commit_node_id', 'commit_author_login', 'commit_committer_login',
        'commit_commit_author_date',
        'commit_commit_committer_date', 'commit_commit_message',
        'commit_commit_comment_count',
        'commit_status_total', 'commit_status_additions', 'commit_status_deletions',
        'file_commit_sha',
        'file_sha', 'file_filename', 'file_status', 'file_additions', 'file_deletions',
        'file_changes',
        'file_patch'
    ]

    COLUMN_NAME_PR_COMMIT_RELATION = [
        'repo_full_name', 'pull_number', 'sha'
    ]

    @staticmethod
    def splitDataByMonth(filename, targetPath, targetFileName, dateCol, dataFrame=None, hasHead=False,
                         columnsName=None):
        """���ṩ��filename �е����ݰ������ڷ��ಢ�з����ɲ�ͬ�ļ�
            targetPath: �з��ļ�Ŀ��·��
            targetFileName: �ṩ�洢���ļ�����
            dateCol: ���ڷ�ʱ�������
            dataFrame: �����ṩ���ݼ����򲻶��ļ�
            columnsName�� ��û�ж�ȡ�ļ�head��ʱ������ṩcolumnsName
        """
        df = None
        if dataFrame is not None:
            df = dataFrame
        elif not hasHead:
            df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITHOUT_HEAD, low_memory=False)
            if columnsName is None:
                raise Exception("columnName is None without head")
            df.columns = columnsName
        else:
            df = pandasHelper.readTSVFile(filename, pandasHelper.INT_READ_FILE_WITH_HEAD, low_memory=False)
        # print(df[dateCol])

        df['label'] = df[dateCol].apply(lambda x: (time.strptime(x, "%Y-%m-%d %H:%M:%S")))
        df['label_y'] = df['label'].apply(lambda x: x.tm_year)
        df['label_m'] = df['label'].apply(lambda x: x.tm_mon)
        print(max(df['label']), min(df['label']))

        maxYear = max(df['label']).tm_year
        maxMonth = max(df['label']).tm_mon
        minYear = min(df['label']).tm_year
        minMonth = min(df['label']).tm_mon
        print(maxYear, maxMonth, minYear, minMonth)

        start = minYear * 12 + minMonth
        end = maxYear * 12 + maxMonth
        for i in range(start, end + 1):
            y = int((i - i % 12) / 12)
            m = i % 12
            if m == 0:
                m = 12
                y = y - 1
            print(y, m)
            subDf = df.loc[(df['label_y'] == y) & (df['label_m'] == m)].copy(deep=True)
            subDf.drop(columns=['label', 'label_y', 'label_m'], inplace=True)
            # print(subDf)
            print(subDf.shape)
            # targetFileName = filename.split(os.sep)[-1].split(".")[0]
            sub_filename = f'{targetFileName}_{y}_{m}_to_{y}_{m}.tsv'
            pandasHelper.writeTSVFile(os.path.join(targetPath, sub_filename), subDf)

    @staticmethod
    def changeStringToNumber(data, columns):  # ��dataframe��һЩ�������ı�ת����  input: dataFrame����Ҫ�����ĳЩ��
        if isinstance(data, DataFrame):  # ע�⣺ dataframe֮ǰ��Ҫresetindex
            count = 0
            convertDict = {}  # ����ת�����ֵ�  ��ʼΪ1
            for column in columns:
                pos = 0
                for item in data[column]:
                    if convertDict.get(item, None) is None:
                        count += 1
                        convertDict[item] = count
                    data.at[pos, column] = convertDict[item]
                    pos += 1

    @staticmethod
    def judgeRecommend(recommendList, answer, recommendNum):

        """�����Ƽ�����"""
        topk = RecommendMetricUtils.topKAccuracy(recommendList, answer, recommendNum)
        print(topk)
        mrr = RecommendMetricUtils.MRR(recommendList, answer, recommendNum)
        print(mrr)
        precisionk, recallk, fmeasurek = RecommendMetricUtils.precisionK(recommendList, answer, recommendNum)

        return topk, mrr, precisionk, recallk, fmeasurek

    @staticmethod
    def saveResult(filename, sheetName, topk, mrr, precisionk, recallk, fmeasurek, date):
        """ʱ���׼ȷ��"""
        content = None
        if date[3] == 1:
            content = [f"{date[2]}.{date[3]}", f"{date[0]}.{date[1]} - {date[2] - 1}.{12}", "TopKAccuracy"]
        else:
            content = [f"{date[2]}.{date[3]}", f"{date[0]}.{date[1]} - {date[2]}.{date[3] - 1}", "TopKAccuracy"]

        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', '', 1, 2, 3, 4, 5]
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', ''] + topk
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', '', 'MRR']
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', '', 1, 2, 3, 4, 5]
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', ''] + mrr
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', '', 'precisionK']
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', '', 1, 2, 3, 4, 5]
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', ''] + precisionk
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', '', 'recallk']
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', '', 1, 2, 3, 4, 5]
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', ''] + recallk
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', '', 'F-Measure']
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', '', 1, 2, 3, 4, 5]
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())
        content = ['', ''] + fmeasurek
        ExcelHelper().appendExcelRow(filename, sheetName, content, style=ExcelHelper.getNormalStyle())

    @staticmethod
    def convertFeatureDictToDataFrame(dicts, featureNum):
        """ͨ��ת�� feature����ʽ����tf-idf ģ�����ɵ����ݿ���ת��������"""
        ar = numpy.zeros((dicts.__len__(), featureNum))
        result = pandas.DataFrame(ar)
        pos = 0
        for d in dicts:
            for key in d.keys():
                result.loc[pos, key] = d[key]
            pos = pos + 1

        return result

    @staticmethod
    def contactReviewCommentData(projectName):
        """����ƴ����Ŀ�����ݲ�����  ֮ǰ��SQL���������̫��ʱ����"""

        pr_review_file_name = os.path.join(projectConfig.getRootPath() + os.sep + 'data' + os.sep + 'train'
                                           , f'ALL_{projectName}_data_pr_review_commit_file.tsv')
        review_comment_file_name = os.path.join(projectConfig.getRootPath() + os.sep + 'data' + os.sep + 'train'
                                                , f'ALL_data_review_comment.tsv')

        out_put_file_name = os.path.join(projectConfig.getRootPath() + os.sep + 'data' + os.sep + 'train'
                                         , f'ALL_{projectName}_data.tsv')

        reviewData = pandasHelper.readTSVFile(pr_review_file_name, pandasHelper.INT_READ_FILE_WITHOUT_HEAD)
        reviewData.columns = DataProcessUtils.COLUMN_NAME_PR_REVIEW_COMMIT_FILE
        print(reviewData.shape)

        commentData = pandasHelper.readTSVFile(review_comment_file_name, pandasHelper.INT_READ_FILE_WITHOUT_HEAD)
        commentData.columns = DataProcessUtils.COLUMN_NAME_REVIEW_COMMENT
        print(commentData.shape)

        result = reviewData.join(other=commentData.set_index('review_comment_pull_request_review_id')
                                 , on='review_id', how='left')

        print(result.loc[result['review_comment_id'].isna()].shape)
        pandasHelper.writeTSVFile(out_put_file_name, result)

    @staticmethod
    def splitProjectCommitFileData(projectName):
        """���ܵ�commit file�����������зֳ�ĳ����Ŀ�����ݣ�������������Լʱ��"""

        """��ȡ��Ϣ"""
        time1 = datetime.now()
        data_train_path = projectConfig.getDataTrainPath()
        target_file_path = projectConfig.getCommitFilePath()
        pr_commit_relation_path = projectConfig.getPrCommitRelationPath()
        target_file_name = f'ALL_{projectName}_data_commit_file.tsv'

        prReviewData = pandasHelper.readTSVFile(
            os.path.join(data_train_path, f'ALL_{projectName}_data_pr_review_commit_file.tsv'),
            pandasHelper.INT_READ_FILE_WITHOUT_HEAD)
        print(prReviewData.shape)
        prReviewData.columns = DataProcessUtils.COLUMN_NAME_PR_REVIEW_COMMIT_FILE

        commitFileData = pandasHelper.readTSVFile(
            os.path.join(data_train_path, 'ALL_data_commit_file.tsv'), pandasHelper.INT_READ_FILE_WITHOUT_HEAD)
        commitFileData.columns = DataProcessUtils.COLUMN_NAME_COMMIT_FILE
        print(commitFileData.shape)

        commitPRRelationData = pandasHelper.readTSVFile(
            os.path.join(pr_commit_relation_path, f'ALL_{projectName}_data_pr_commit_relation.tsv'),
            pandasHelper.INT_READ_FILE_WITHOUT_HEAD
        )
        print(commitPRRelationData.shape)
        print("read file cost time:", datetime.now() - time1)

        """���ռ�pr��ص�commit"""
        commitPRRelationData.columns = ['repo_full_name', 'pull_number', 'sha']
        commitPRRelationData = commitPRRelationData['sha'].copy(deep=True)
        commitPRRelationData.drop_duplicates(inplace=True)
        print(commitPRRelationData.shape)

        prReviewData = prReviewData['commit_sha'].copy(deep=True)
        prReviewData.drop_duplicates(inplace=True)
        print(prReviewData.shape)

        needCommits = prReviewData.append(commitPRRelationData)
        print("before drop duplicates:", needCommits.shape)
        needCommits.drop_duplicates(inplace=True)
        print("actually need commit:", needCommits.shape)
        needCommits = list(needCommits)

        """���ܵ�commit file��Ϣ��ɸѡ����Ҫ����Ϣ"""
        print(commitFileData.columns)
        commitFileData = commitFileData.loc[commitFileData['commit_sha'].
            apply(lambda x: x in needCommits)].copy(deep=True)
        print(commitFileData.shape)

        pandasHelper.writeTSVFile(os.path.join(target_file_path, target_file_name), commitFileData)
        print(f"write over: {target_file_name}, cost time:", datetime.now() - time1)

    @staticmethod
    def contactFPSData(projectName):
        """
        ͨ�� ALL_{projectName}_data_pr_review_commit_file
             ALL_commit_file
             ALL_data_review_comment �����ļ�ƴ�ӳ�FPS������Ϣ�����ļ�
        """

        """��ȡ��Ϣ  fps ֻ��Ҫcommit_file��pr_review��relation����Ϣ"""
        time1 = datetime.now()
        data_train_path = projectConfig.getDataTrainPath()
        commit_file_data_path = projectConfig.getCommitFilePath()
        pr_commit_relation_path = projectConfig.getPrCommitRelationPath()
        prReviewData = pandasHelper.readTSVFile(
            os.path.join(data_train_path, f'ALL_{projectName}_data_pr_review_commit_file.tsv'), low_memory=False)
        prReviewData.columns = DataProcessUtils.COLUMN_NAME_PR_REVIEW_COMMIT_FILE
        print("raw pr review :", prReviewData.shape)

        """commit file ��Ϣ��ƴ�ӳ����� ������̧ͷ"""
        commitFileData = pandasHelper.readTSVFile(
            os.path.join(commit_file_data_path, f'ALL_{projectName}_data_commit_file.tsv'), low_memory=False,
            header=pandasHelper.INT_READ_FILE_WITH_HEAD)
        print("raw commit file :", commitFileData.shape)

        commitPRRelationData = pandasHelper.readTSVFile(
            os.path.join(pr_commit_relation_path, f'ALL_{projectName}_data_pr_commit_relation.tsv'),
            pandasHelper.INT_READ_FILE_WITHOUT_HEAD, low_memory=False
        )
        commitPRRelationData.columns = DataProcessUtils.COLUMN_NAME_PR_COMMIT_RELATION
        print("pr_commit_relation:", commitPRRelationData.shape)

        print("read file cost time:", datetime.now() - time1)

        """����״̬�ǹرյ�pr review"""
        prReviewData = prReviewData.loc[prReviewData['pr_state'] == 'closed'].copy(deep=True)
        print("after fliter closed pr:", prReviewData.shape)

        """���˲���Ҫ���ֶ�"""
        prReviewData = prReviewData[['pr_number', 'review_user_login', 'pr_created_at']].copy(deep=True)
        prReviewData.drop_duplicates(inplace=True)
        prReviewData.reset_index(drop=True, inplace=True)
        print("after fliter pr_review:", prReviewData.shape)

        commitFileData = commitFileData[['commit_sha', 'file_filename']].copy(deep=True)
        commitFileData.drop_duplicates(inplace=True)
        commitFileData.reset_index(drop=True, inplace=True)
        print("after fliter commit_file:", commitFileData.shape)

        """����������"""
        data = pandas.merge(prReviewData, commitPRRelationData, left_on='pr_number', right_on='pull_number')
        print("merge relation:", data.shape)
        data = pandas.merge(data, commitFileData, left_on='sha', right_on='commit_sha')
        data.reset_index(drop=True, inplace=True)
        data.drop(columns=['sha'], inplace=True)
        data.drop(columns=['pr_number'], inplace=True)
        print("����λ��")
        order = ['repo_full_name', 'pull_number', 'pr_created_at', 'review_user_login', 'commit_sha', 'file_filename']
        data = data[order]
        # print(data.columns)
        print("after merge:", data.shape)

        """����ʱ��ֳ�СƬ"""
        DataProcessUtils.splitDataByMonth(filename=None, targetPath=projectConfig.getFPSDataPath(),
                                          targetFileName=f'FPS_{projectName}_data', dateCol='pr_created_at',
                                          dataFrame=data)


if __name__ == '__main__':
    # DataProcessUtils.splitDataByMonth(projectConfig.getRootPath() + r'\data\train\ALL_rails_data.tsv',
    #                                   projectConfig.getRootPath() + r'\data\train\all' + os.sep, hasHead=True)
    #
    # print(pandasHelper.readTSVFile(
    #     projectConfig.getRootPath() + r'\data\train\all\ALL_scala_data_2012_6_to_2012_6.tsv', ))
    #
    # DataProcessUtils.contactReviewCommentData('rails')
    #
    # DataProcessUtils.splitProjectCommitFileData('rails')
    DataProcessUtils.contactFPSData('rails')
