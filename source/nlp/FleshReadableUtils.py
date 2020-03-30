# coding=gbk
import math
import re

import numpy
import pronouncing
import matplotlib.pyplot as plt
from gensim import corpora
from gensim.models import TfidfModel
from gensim.similarities import SparseMatrixSimilarity
from pandas import Series

from source.config.projectConfig import projectConfig
from source.nlp import LanguageKeyWordHelper
from source.nlp.SplitWordHelper import SplitWordHelper
from source.utils.pandas.pandasHelper import pandasHelper


class FleshReadableUtils:

    # @staticmethod
    # def word_list(comment):
    #
    #     word_re = re.compile(r'[^A-Za-z\']+')
    #     words = [x for x in word_re.split(comment.lower()) if x.__len__() != 0]
    #     # print("������:" + str(len(words)))
    #     # print(words)
    #     return words

    @staticmethod
    def word_list(comment):
        """�ִ�����ȥ���˴����ŵĳ���"""
        word_re = re.compile(r'[^A-Za-z]+')
        words = [x for x in word_re.split(comment.lower()) if x.__len__() != 0]
        # print("������:" + str(len(words)))
        # print(words)
        return words

    @staticmethod
    def sentence(comment):
        point_re = re.compile(r'\.|\?|\!')
        point = [x for x in point_re.split(comment) if x.__len__() != 0]
        print("���ӳ���:" + str(len(point)))
        print(point)
        return point

    @staticmethod
    def sentenceQuestionCount(comment):
        point_re = re.compile(r'\?+')
        point = point_re.findall(comment)
        print("�ʾ�����:" + str(len(point)))
        print(point)
        return len(point)

    @staticmethod
    def CodeElement(comment):
        code_re = re.compile("```[^`]*```|`[^`]+`")
        codes = re.findall(code_re, comment)
        print("codes:")
        print(codes)
        return codes

    @staticmethod
    def get_pronouncing_num(word):
        try:
            pronunciating_list = pronouncing.phones_for_word(word)
            num = pronouncing.syllable_count(pronunciating_list[0])
        except Exception as e:
            print("���ڼ����쳣���쳣���ʣ�" + word)
            return math.ceil(2)
        else:
            return num

    @staticmethod
    def get_pronouncing_nums(words):
        counts = 0
        for word in words:
            counts += FleshReadableUtils.get_pronouncing_num(word)
        print('����������', str(counts))
        return counts


if __name__ == "__main__":

    data = pandasHelper.readTSVFile(projectConfig.getReviewCommentTestData())
    comments = data.as_matrix()[:, (2, 4)]
    print(comments.shape)

    readable = []  # �ɶ���
    stopWordRate = []  # ͣ����
    questionRatio = []  # ������
    codeElementRatio = []  # ����Ԫ����
    stopKeyRatio = []  # �ؼ�����
    conceptualSimilarity = []  # �������ƶ�
    badCase = []

    stopwords = SplitWordHelper().getEnglishStopList()
    languageKeyWords = LanguageKeyWordHelper.LanguageKeyWordLanguage.getRubyKeyWordList()

    for line in comments:

        # if '??' in comment:
        #     print(comment)
        #     print("-" * 200)
        code_diff = line[1].strip()
        comment = line[0].strip()
        print("comment:")
        print(comment)

        word_list = FleshReadableUtils.word_list(comment)
        sentence = FleshReadableUtils.sentence(comment)
        # ASL ������/������
        word_num = len(word_list)
        sentence_num = len(sentence)

        if word_num == 0 or sentence_num == 0:  # ���������������
            # readable.append(None)
            # stopWordRate.append(None)
            # questionRatio.append(None)
            print("bad case")
            print(comment)
            continue

        """���ɶ��Եļ���"""
        ASL = word_num / sentence_num

        # ASW ������/������
        pronouncing_nums = FleshReadableUtils.get_pronouncing_nums(word_list)
        ASW = pronouncing_nums / word_num

        RE = 206.835 - (1.015 * ASL) - (84.6 * ASW)
        print("RE:", RE)
        readable.append(RE)

        if RE > 100 or RE < 0:
            badCase.append((comment, RE))

        """��stop word ratio�ļ���"""
        stopwordsInComments = [x for x in word_list if x in stopwords]
        print("word list:")
        print(word_list.__len__())
        print("stop words:")
        print(stopwordsInComments.__len__())
        stopWordRate.append(stopwordsInComments.__len__() / word_list.__len__())

        """��question ratio����"""  # ͨ��������ʽ���Ӳ�ּ�ȥ�����ʺŵľ��Ӳ������
        questionsCount = FleshReadableUtils.sentenceQuestionCount(comment)
        print("questions count")
        questionRatio.append(questionsCount / sentence.__len__())

        """��Code Element Ratio����"""
        codes = FleshReadableUtils.CodeElement(comment)
        codeElementCount = 0
        for code in codes:
            codeElementCount += len(FleshReadableUtils.word_list(code))
        print("code Element count")
        print(codeElementCount)
        codeElementRatio.append(codeElementCount / word_num)

        """���������ƶȼ���"""
        print("diff")
        print(code_diff)

        """�ѸĶ������ÿһ����Ϊһ���ı� �ִʣ�ȥͣ�ô�"""
        diff_word_list = []
        for code in code_diff.split('\n'):
            diff_word_list.append([x for x in FleshReadableUtils.word_list(code) if x not in stopwords])
            # print([x for x in FleshReadableUtils.word_list(code) if x not in stopwords])
        diff_word_list = [x for x in diff_word_list if x.__len__() != 0]

        if diff_word_list.__len__() == 0:
            conceptualSimilarity.append(0)  # �ԸĶ��ı�Ϊ�����⴦��
        else:
            """�����ʵ�  ���������"""
            dictionary = corpora.Dictionary(diff_word_list)
            feature_cnt = len(dictionary.token2id.keys())
            """���ڴʵ�  �ִ��б�תϡ��������"""
            corpus = [dictionary.doc2bow(codes) for codes in diff_word_list]
            # print("key")
            # print([x for x in word_list if x not in stopwords])
            kw_vector = dictionary.doc2bow([x for x in word_list if x not in stopwords])
            """����tf-idfģ��   �������Ͽ�ѵ��"""
            tfidf = TfidfModel(corpus)
            """ѵ���õ�tf-idfģ�ʹ�������ı���������"""
            tf_texts = tfidf[corpus]
            tf_kw = tfidf[kw_vector]
            """���ƶȼ���"""
            sparse_matrix = SparseMatrixSimilarity(tf_texts, feature_cnt)
            similarities = sparse_matrix.get_similarities(tf_kw)
            # print("similarities")
            # print(similarities)
            # for e, s in enumerate(similarities, 1):
            #     print('kw �� text%d ���ƶ�Ϊ��%.2f' % (e, s))
            conceptualSimilarity.append(max(similarities))

        """key word ratio"""
        keywordsInComments = [x for x in word_list if x in languageKeyWords]
        stopKeyRatio.append(keywordsInComments.__len__() / word_list.__len__())


    print(readable)
    print(max(readable), min(readable))

    fig = plt.figure()
    fig.add_subplot(2, 1, 1)
    s = Series(readable)
    s.plot(kind='kde')
    plt.title('readable')
    plt.show()

    # for case in badCase:
    #     print(case[1], case[0])
    print(badCase.__len__() / comments.shape[0])

    print(stopWordRate)
    fig = plt.figure()
    fig.add_subplot(2, 1, 1)
    s = Series(stopWordRate)
    s.plot(kind='kde')
    plt.title('stopwordRate')
    plt.show()

    print(questionRatio)
    fig = plt.figure()
    fig.add_subplot(2, 1, 1)
    s = Series(questionRatio)
    s.plot(kind='kde')
    plt.title('questionRatio')
    plt.show()

    print(codeElementRatio)
    fig = plt.figure()
    fig.add_subplot(2, 1, 1)
    s = Series(codeElementRatio)
    plt.title('codeElementRatio')
    s.plot(kind='kde')
    plt.show()

    print(conceptualSimilarity)
    fig = plt.figure()
    fig.add_subplot(2, 1, 1)
    s = Series(conceptualSimilarity)
    plt.title('conceptualSimilarity')
    s.plot(kind='kde')
    plt.show()

    print(stopKeyRatio)
    fig = plt.figure()
    fig.add_subplot(2, 1, 1)
    s = Series(stopKeyRatio)
    plt.title('stopKeyRatio')
    s.plot(kind='kde')
    plt.show()
