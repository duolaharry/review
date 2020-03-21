# coding=gbk

class SqlUtils:
    """���ڴ洢��SQL���"""

    STR_SQL_CREATE_TABLE = 'create table %s'

    '''Ԥ�ƴ洢�ı�����'''
    STR_TABLE_NAME_REPOS = 'repository'
    STR_TABLE_NAME_USER = 'userList'
    STR_TABLE_NAME_PULL_REQUEST = 'pullRequest'
    STR_TABLE_NAME_BRANCH = 'branch'
    STR_TABLE_NAME_REVIEW = 'review'
    STR_TABLE_NAME_REVIEW_COMMENT = 'reviewComment'
    STR_TABLE_NAME_ISSUE_COMMENT = 'issueComment'
    STR_TABLE_NAME_COMMIT = 'gitCommit'
    STR_TABLE_NAME_FILE = 'gitFile'
    STR_TABLE_NAME_COMMIT_RELATION = 'commitRelation'
    STR_TABLE_NAME_COMMIT_PR_RELATION = 'commitPRRelation'
    STR_TABLE_NAME_COMMIT_COMMENT = 'commitComment'
    STR_TABLE_NAME_PR_TIME_LINE = 'PRTimeLine'
    STR_TABLE_NAME_HEAD_REF_FORCE_PUSHED_EVENT = 'HeadRefForcePushedEvent'
    STR_TABLE_NAME_PULL_REQUEST_COMMIT = 'pullRequestCommit'

    '''�洢�ı��е�����'''
    STR_KEY_INT = 'int'
    STR_KEY_VARCHAR_MAX = 'varchar(8000)'
    STR_KEY_VARCHAR_MIDDLE = 'varchar(5000)'
    STR_KEY_DATE_TIME = 'datatime'
    STR_KEY_TEXT = 'text'

    '''�������'''
    STR_SQL_INSERT_TABLE_UTILS = 'insert into {0} values{1}'

    '''��ѯ����'''
    STR_SQL_QUERY_TABLE_UTILS = 'select * from {0} {1}'

    '''ɾ������'''
    STR_SQL_DELETE_TABLE_UTILS = 'delete from {0} {1}'

    '''�޸Ĳ���'''
    STR_SQL_UPDATE_TABLE_UTILS = 'update {0} {1} {2}'

    @staticmethod
    def getInsertTableFormatString(tableName, items):

        '''��ȡ�������ı�ĸ�ʽ'''

        res = tableName
        if items.__len__() > 0:
            res += '('
            pos = 0
            for item in items:
                if (pos == 0):
                    res += item
                else:
                    res += ','
                    res += item
                pos += 1
            res += ')'
        return res

    @staticmethod
    def getInsertTableValuesString(number):
        """��ȡ�������ֵ�ĸ�ʽ"""

        res = '('
        pos = 0
        while pos < number:
            if pos == 0:
                res += '%s'
            else:
                res += ','
                res += '%s'
            pos += 1
        res += ')'
        return res

    @staticmethod
    def getQueryTableConditionString(items):

        """��ȡ��ѯ���ı�׼��ʽ"""
        res = ''
        pos = 0
        if items is not None and items.__len__() > 0:
            res += 'where'
            for item in items:
                if pos == 0:
                    res += ' '
                    res += item
                    res += '=%s'
                else:
                    res += ' and '
                    res += item
                    res += '=%s'
                pos += 1
        return res

    @staticmethod
    def getUpdateTableSetString(items):

        """��ȡ���±�����ı�׼��ʽ"""
        res = ''
        pos = 0
        if items is not None and items.__len__() > 0:
            res += 'set'
            for item in items:
                if pos == 0:
                    res += ' '
                    res += item
                    res += '=%s'
                else:
                    res += ','
                    res += item
                    res += '=%s'
                pos += 1
        return res
