# coding=gbk
from source.utils.StringKeyUtils import StringKeyUtils
import pandas


class pandasHelper:
    """  pandas�ӿڷ�װ������ """

    INT_READ_FILE_WITHOUT_HEAD = -1
    INT_READ_FILE_WITH_HEAD = 0

    @staticmethod
    def readTSVFile(fileName, header=INT_READ_FILE_WITHOUT_HEAD):  # ��һΪ�ޱ�ͷ
        train = pandas.read_csv(fileName, sep=StringKeyUtils.STR_SPLIT_SEP_TSV, header=header)
        return train
