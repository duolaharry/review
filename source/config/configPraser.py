# coding=gbk
import os
import random

from source.config.projectConfig import projectConfig
import configparser


class configPraser:  # 用于解析config。ini文件

    STR_TOKEN = 'token'
    STR_AUTHORIZATION = 'authorization'
    STR_DATABASE = 'database'
    STR_DEBUG = 'debug'
    STR_PROJECT = 'project'
    STR_NETWORK = 'network'

    STR_USERNAME = 'username'
    STR_PASSWORD = 'password'
    STR_HOST = 'host'
    STR_PRINT = 'print'
    STR_TRUE = 'True'
    STR_RETRY = 'retry'
    STR_OWNER = 'owner'
    STR_REPO = 'repo'
    STR_LIMIT = 'limit'
    STR_PROXY = 'proxy'
    STR_START = 'start'
    STR_TIMEOUT = 'timeout'
    STR_SEMAPHORE = 'semaphore'

    @staticmethod
    def getAuthorizationToken():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        tokenList = cp.get(configPraser.STR_AUTHORIZATION, configPraser.STR_TOKEN).split(',')
        return tokenList[random.randint(0, tokenList.__len__() - 1)]

    @staticmethod
    def getDataBaseUserName():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        return cp.get(configPraser.STR_DATABASE, configPraser.STR_USERNAME)

    @staticmethod
    def getDataBasePassword():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        return cp.get(configPraser.STR_DATABASE, configPraser.STR_PASSWORD)

    @staticmethod
    def getDataBaseHost():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        return cp.get(configPraser.STR_DATABASE, configPraser.STR_HOST)

    @staticmethod
    def getPrintMode():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        return cp.get(configPraser.STR_DEBUG, configPraser.STR_PRINT) == configPraser.STR_TRUE

    @staticmethod
    def getProxy():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        return cp.get(configPraser.STR_NETWORK, configPraser.STR_PROXY) == configPraser.STR_TRUE

    @staticmethod
    def getRetryTime():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        return int(cp.get(configPraser.STR_NETWORK, configPraser.STR_RETRY))

    @staticmethod
    def getOwner():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        return cp.get(configPraser.STR_PROJECT, configPraser.STR_OWNER)

    @staticmethod
    def getRepo():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        return cp.get(configPraser.STR_PROJECT, configPraser.STR_REPO)

    @staticmethod
    def getLimit():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        return int(cp.get(configPraser.STR_PROJECT, configPraser.STR_LIMIT))

    @staticmethod
    def getStart():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        return int(cp.get(configPraser.STR_PROJECT, configPraser.STR_START))

    @staticmethod
    def getTimeout():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        return int(cp.get(configPraser.STR_NETWORK, configPraser.STR_TIMEOUT))

    @staticmethod
    def getSemaphore():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        return int(cp.get(configPraser.STR_NETWORK, configPraser.STR_SEMAPHORE))

    @staticmethod
    def getDataBase():
        cp = configparser.ConfigParser()
        cp.read(projectConfig.getConfigPath())
        return cp.get(configPraser.STR_DATABASE, configPraser.STR_DATABASE)


if __name__ == '__main__':
    print(configPraser.getLimit())

