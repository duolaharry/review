# coding=gbk
from source.utils.StringKeyUtils import StringKeyUtils
import pandas


class pandasHelper:
    """  pandas�ӿڷ�װ������ """

    INT_READ_FILE_WITHOUT_HEAD = -1
    INT_READ_FILE_WITH_HEAD = 0

    @staticmethod
    def readTSVFile(fileName, header=INT_READ_FILE_WITHOUT_HEAD, low_memory=False):  # ��һΪ�ޱ�ͷ
        train = pandas.read_csv(fileName, sep=StringKeyUtils.STR_SPLIT_SEP_TSV, header=header, low_memory=low_memory)
        return train

    @staticmethod
    def writeTSVFile(fileName, dataFrame):  # д��tsv�ļ�
        with open(fileName, 'w', encoding='utf-8') as write_tsv:
            print(fileName)
            write_tsv.write(dataFrame.to_csv(sep='\t', index=False))
