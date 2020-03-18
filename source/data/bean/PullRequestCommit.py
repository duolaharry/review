# coding=gbk
from source.data.bean.Beanbase import BeanBase
from source.utils.StringKeyUtils import StringKeyUtils


class PullRequestCommit(BeanBase):
    """github��pull request timeline de pushrequest commit�¼�"""

    def __init__(self):
        self.node_id = None
        self.oid = None

    @staticmethod
    def getIdentifyKeys():
        return [StringKeyUtils.STR_KEY_NODE_ID]

    @staticmethod
    def getItemKeyList():
        items = [StringKeyUtils.STR_KEY_NODE_ID, StringKeyUtils.STR_KEY_OID]

        return items

    @staticmethod
    def getItemKeyListWithType():
        items = [(StringKeyUtils.STR_KEY_NODE_ID, BeanBase.DATA_TYPE_STRING),
                 (StringKeyUtils.STR_KEY_OID, BeanBase.DATA_TYPE_STRING)]

        return items

    def getValueDict(self):
        items = {StringKeyUtils.STR_KEY_NODE_ID: self.node_id,
                 StringKeyUtils.STR_KEY_OID: self.oid}

        return items

    class parser(BeanBase.parser):

        @staticmethod
        def parser(src):
            # resList = []  # ���ؽ��Ϊһϵ�й�ϵ
            # if isinstance(src, dict):
            #     data = src.get('data', None)
            #     if data is not None and isinstance(data, dict):
            #         nodes = data.get('nodes', None)
            #         if nodes is not None:
            #             for pr in nodes:
            #                 pr_id = pr.get('id')
            #                 pos = 0
            #                 timelineitems = pr.get('timelineItems', None)
            #                 if timelineitems is not None:
            #                     edges = timelineitems.get('edges', None)
            #                     if edges is not None:
            #                         for item in edges:
            #                             item_node = item.get('node', None)
            #                             if item_node is not None:
            #                                 typename = item_node.get('__typename', None)
            #                                 item_id = item_node.get('id', None)
            #                                 relation = PRTimeLineRelation()
            #                                 relation.position = pos
            #                                 pos += 1
            #                                 relation.typename = typename
            #                                 relation.timelineitem_node = item_id
            #                                 relation.pullrequest_node = pr_id
            #                                 resList.append(relation)
            return resList
