# coding=gbk


class statisticsHelper:
    """github ���ݵ�ͳ�ư�����"""

    def __init__(self):
        self.usefulRequestNumber = 0  # ���õ�pull request����ȡ����
        self.commentNumber = 0
        self.usefulReviewNumber = 0  # review����ȡ����
        self.usefulReviewCommentNumber = 0  # review comment����ȡ����
        self.usefulIssueCommentNumber = 0  # issue comment ����ȡ����
        self.usefulCommitNumber = 0  # commit����ȡ����
        self.usefulCommitCommentNumber = 0  # commit comment����ȡ����
        self.startTime = None  # ��ʼʱ��
        self.endTime = None  # ����ʱ��