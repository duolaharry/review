# coding=gbk
from source.utils.StringKeyUtils import StringKeyUtils
import pandas


class pandasHelper:
    """  pandas�ӿڷ�װ������ """

    INT_READ_FILE_WITHOUT_HEAD = None
    INT_READ_FILE_WITH_HEAD = 0

    @staticmethod
    def readTSVFile(fileName, header=INT_READ_FILE_WITHOUT_HEAD, sep=StringKeyUtils.STR_SPLIT_SEP_TSV):  # ��һΪ�ޱ�ͷ
        train = pandas.read_csv(fileName, sep=sep, header=header)
        return train

    @staticmethod
    def toDataFrame(data, columns=None, dtype=None):
        return pandas.DataFrame(data, columns=columns, dtype=dtype)

    @staticmethod
    def writeTSVFile(fileName, dataFrame):  # д��tsv�ļ�
        with open(fileName, 'w', encoding='utf-8') as write_tsv:
            print(fileName)
            write_tsv.write(dataFrame.to_csv(sep=StringKeyUtils.STR_SPLIT_SEP_TSV, index=False))
