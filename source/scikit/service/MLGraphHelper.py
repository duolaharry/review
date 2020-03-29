# coding=gbk
import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_digits
from sklearn.model_selection import learning_curve, ShuffleSplit
from sklearn.naive_bayes import GaussianNB


class MLGraphHelper:
    """�ṩһЩ�滭�ӿڵİ�����"""

    @staticmethod
    def plot_learning_curve(estimator, title, X, y, ylim=None, cv=None, n_jobs=1,
                            train_sizes=np.linspace(0.1, 1.0, 20)):
        """����ѧϰ����"""
        plt.figure()
        plt.title(title)
        if ylim is not None:
            plt.ylim(*ylim)  # ����y�ķ�Χ
        plt.xlabel("Training example")
        plt.ylabel("Score")
        train_sizes, train_scores, test_scores = learning_curve(
            estimator, X, y, cv=cv, n_jobs=n_jobs, train_sizes=train_sizes)  # �ṩģ������
        """
            cv : int, ������֤��������ɵ����Ŀ�ѡ�ȷ��������֤��ֲ��ԡ�
            1 �ޣ�ʹ��Ĭ�ϵ�3��������֤��
            2 ������ָ���۵�����
            3 Ҫ����������֤�������Ķ���
            4 �ɵ�����yieldingѵ��/���Է��ѡ�
        """
        train_scores_mean = np.mean(train_scores, axis=1)
        train_scores_std = np.std(train_scores, axis=1)  # �������׼��
        test_scores_mean = np.mean(test_scores, axis=1)  # �Ը�����ƽ��ֵ
        test_scores_std = np.std(train_scores, axis=1)
        plt.grid()  # ����������

        plt.fill_between(train_sizes, train_scores_mean - train_scores_std,
                         train_scores_mean + train_scores_std, alpha=0.1,
                         color="r")
        plt.fill_between(train_sizes, test_scores_mean - test_scores_std,
                         test_scores_mean + test_scores_std, alpha=0.1, color="g")
        plt.plot(train_sizes, train_scores_mean, 'o-', color='r', label="Training score")
        plt.plot(train_sizes, test_scores_mean, '-o', color='g', label="Cross-validation score")
        plt.legend(loc="best")  # ����ͼ��
        return plt


if __name__ == "__main__":
    digits = load_digits()
    X, y = digits.data, digits.target  # ������������
    print(X)
    print(y)
    title = r"Learning Curves (Naive Bayes)"
    cv = ShuffleSplit(n_splits=100, test_size=0.2, random_state=0)  # �����ɢ�ֳ�������
    estimator = GaussianNB()
    MLGraphHelper.plot_learning_curve(estimator, title, X, y, ylim=(0.7, 1.01), cv=cv, n_jobs=1).show()
