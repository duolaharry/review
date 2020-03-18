# coding=gbk
from source.data.bean.Beanbase import BeanBase
from source.utils.StringKeyUtils import StringKeyUtils


class PRTimeLineRelation(BeanBase):
    """github��pull request��timeline ��ϵ"""

    def __init__(self):
        self.pullrequest_node = None
        self.timelineitem_node = None
        self.typename = None
        self.position = None

    @staticmethod
    def getIdentifyKeys():
        return [StringKeyUtils.STR_KEY_PULL_REQUEST_NODE, StringKeyUtils.STR_KEY_TIME_LINE_ITEM_NODE]

    @staticmethod
    def getItemKeyList():
        items = [StringKeyUtils.STR_KEY_PULL_REQUEST_NODE, StringKeyUtils.STR_KEY_TIME_LINE_ITEM_NODE
            , StringKeyUtils.STR_KEY_TYPE_NAME, StringKeyUtils.STR_KEY_POSITION]

        return items

    @staticmethod
    def getItemKeyListWithType():
        items = [(StringKeyUtils.STR_KEY_PULL_REQUEST_NODE, BeanBase.DATA_TYPE_STRING),
                 (StringKeyUtils.STR_KEY_TIME_LINE_ITEM_NODE, BeanBase.DATA_TYPE_STRING),
                 (StringKeyUtils.STR_KEY_TYPE_NAME, BeanBase.DATA_TYPE_STRING),
                 (StringKeyUtils.STR_KEY_POSITION, BeanBase.DATA_TYPE_INT)]

        return items

    def getValueDict(self):
        items = {StringKeyUtils.STR_KEY_PULL_REQUEST_NODE: self.pullrequest_node,
                 StringKeyUtils.STR_KEY_TIME_LINE_ITEM_NODE: self.timelineitem_node,
                 StringKeyUtils.STR_KEY_TYPE_NAME: self.typename,
                 StringKeyUtils.STR_KEY_POSITION: self.position}

        return items

    class parser(BeanBase.parser):

        @staticmethod
        def parser(src):
            resList = []  # ���ؽ��Ϊһϵ�й�ϵ
            if isinstance(src, dict):
                data = src.get(StringKeyUtils.STR_KEY_DATA, None)
                if data is not None and isinstance(data, dict):
                    nodes = data.get(StringKeyUtils.STR_KEY_NODES, None)
                    if nodes is not None:
                        for pr in nodes:
                            pr_id = pr.get(StringKeyUtils.STR_KEY_ID)
                            pos = 0
                            timelineitems = pr.get(StringKeyUtils.STR_KEY_TIME_LINE_ITEMS, None)
                            if timelineitems is not None:
                                edges = timelineitems.get(StringKeyUtils.STR_KEY_EDGES, None)
                                if edges is not None:
                                    for item in edges:
                                        item_node = item.get(StringKeyUtils.STR_KEY_NODE, None)
                                        if item_node is not None:
                                            typename = item_node.get(StringKeyUtils.STR_KEY_TYPE_NAME_JSON, None)
                                            item_id = item_node.get(StringKeyUtils.STR_KEY_ID, None)
                                            relation = PRTimeLineRelation()
                                            relation.position = pos
                                            pos += 1
                                            relation.typename = typename
                                            relation.timelineitem_node = item_id
                                            relation.pullrequest_node = pr_id
                                            resList.append(relation)
            return resList
