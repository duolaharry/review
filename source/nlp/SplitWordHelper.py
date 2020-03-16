#coding=gbk
from source.config.projectConfig import projectConfig
import jieba
import jieba.posseg

class SplitWordHelper:
    '''�ִ�����
    
    '''
    
    def getGHDStopWordList(self):
        ''' ��ȡ������ͨ��ͣ�ô� '''
        
        file = open(projectConfig.getStopWordHGDPath() ,mode = 'r+',encoding = 'utf-8')
        content = file.read() 
        print(content)
        return content.split('\n')

    def getEnglishStopList(self):
        file = open(projectConfig.getStopWordEnglishPath() ,mode = 'r+',encoding = 'utf-8')
        content = file.read()
        return content.split('\n')


    def getSplitWordListFromListData(self,dataList,cut_all = False,filter = False):
        '''��ȡ���������б�ķִ�ͳ��Ԫ�� 
            cut_all ��ģʽ����
            filter �Ƿ���ͣ�ôʹ���
        '''
        
        stopWordList = self.getGHDStopWordList()
        tf_dict = {}
        for line in dataList:
            print(line)
            seg_list = jieba.cut(line,cut_all = cut_all)
            for w in seg_list:
#                 print(w)
                if(filter):
                    if(w in stopWordList):
                        print('filter:',w)
                        continue
                tf_dict[w] = tf_dict.get(w, 0) + 1
        print("�ռ��ִ�����",tf_dict.__len__())
        sorted_list = sorted(tf_dict.items(), key = lambda x:x[1],reverse = True)
        return sorted_list
    
    def getPartOfSpeechTaggingFromListData(self,sent):
        ''' ��ȡ����ĳ�����ӵĴ��Ա�ע
        
        '''
        seg_list = jieba.posseg.cut(sent)
        result = []
        for w,t in seg_list:
            result.append((w,t))
        return result
