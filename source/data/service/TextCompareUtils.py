# coding=gbk
from source.utils.pandas.pandasHelper import pandasHelper
import re


class TextCompareUtils:
    """patch���ı��Ƚ���"""

    @staticmethod
    def patchParser(text):
        """patch���ı�����"""

        """ patch �ı���ʽʾ��˵��
        
         @@ -35,9 +36,8 @@ ruby <%= \"'#{RUBY_VERSION}'\" -%>
         # gem 'rack-cors'
         
         <%- end -%>
         -# The gems below are used in development, but if they cause problems it's OK to remove them
         -
         <% if RUBY_ENGINE == 'ruby' -%>
         +# The gems below are used in development, but if they cause problems it's OK to remove them
         group :development, :test do
         # Call 'byebug' anywhere in the code to stop execution and get a debugger console
         gem 'byebug', platforms: [:mri, :mingw, :x64_mingw]
         
         
         ˵����  -35,9,+36,8  ˵������Ķ����ϸ��汾��35�п�ʼ��������9����ԭ���汾������
                                           �¸��汾36�п�ʼ������8�����°汾������
                                           "+" �����°汾���е�����
                                           "-" �����ϰ汾���е�����
                                           
                patch �ĵ�һ�в�������
        ע�� �������Լ���������� @���ݷ�
        """

        changes = []  # һ��patch���ܻ��ж���Ķ�    [(��ʼ��,��,�汾����ʼ,��) -> [+, ,-,....]]
        print(text)
        print('-' * 50)

        headMatch = re.compile(r'@@(.)+@@')
        numberMatch = re.compile(r'[^0-9]+')

        status = None
        lines = []
        for t in text.split('\n'):
            """���в��  ���ν���"""
            head = headMatch.search(t)
            if head:
                if status is not None:
                    changes.append([status, lines])
                    status = None
                    lines = []

                print(head.group())
                numbers = [int(x) for x in numberMatch.split(head.group()) if x.__len__() > 0]
                print(numbers)
                if numbers.__len__() == 4:
                    status = tuple(numbers)
                elif numbers.__len__() == 2:
                    """������ֻ���������������"""
                    numbers = (numbers[0], 1, numbers[1], 1)
                    status = numbers
            else:
                """�ռ��������� ��ÿһ���޸�״̬"""
                lines.append(t[0])
        if status is not None:
            changes.append([status, lines])
        print(changes)
        return changes

    @staticmethod
    def simulateTextChanges(patches1, patches2, targetLine):
        """ͨ����patch���ı�ģ������ñ仯�����
          ��Patch1 �ĸĶ�����ģ��
          ��Patch2 �ĸĶ�����ģ��

        """

        changes1 = []
        changes2 = []

        # minLine = float('inf')
        maxLine = 0  # ��ʡ�ռ��ѯ�漰�仯���Ͻ���
        for patch in patches1:
            change = TextCompareUtils.patchParser(patch)  # ÿһ��patch�����м����仯����ƽ�й�ϵ
            changes1.insert(0, change)

            for c in change:
                # minLine = min(minLine, c[0])
                """���޸ı��Ŀ��ܻ��漰��������� �����ı�ģ��ĸ���"""
                maxLine = max(maxLine, c[0][0] + c[1].__len__(), c[0][2] + c[1].__len__())
        for patch in patches2:
            change = TextCompareUtils.patchParser(patch)
            changes2.insert(0, change)
            for c in change:
                # minLine = min(minLine, c[0])
                maxLine = max(maxLine, c[0][0] + c[1].__len__(), c[0][2] + c[1].__len__())

        maxLine = max(maxLine + 20, targetLine + 20)
        print(maxLine)

        """ͨ��һ��������ģ���ı��ı仯"""
        text = [x for x in range(1, maxLine)]  # ����ģ���ı�
        print(text)

        """����ģ����� һ������ �����е����ִ����к�  ���������ʹ��Patch������"""

        """���ڷ���·��������  ���Ķ��м�����Ϊ������   ������Ϊ������"""
        for changes in changes1:
            """����ģ��ʱ�������ƫ��"""
            offset = 0
            for change in changes:
                cur = change[0][2] - offset
                print('start  offset:', change[0], offset)
                for c in change[1]:
                    if c == ' ':
                        cur += 1
                    elif c == '-':
                        text.insert(cur - 1, 0)
                        cur += 1
                    elif c == '+':
                        text.pop(cur - 1)
                """ɾ���е���ԭ������ʼ������λ  ��Ҫ����ƫ�Ʋ���"""

                """����ƫ��δ�ۼӵ��µ�bug"""
                offset += change[1].count('+') - change[1].count('-')

        """ǰ��·��Ϊ��"""
        for changes in changes2:
            offset = 0
            for change in changes:
                cur = change[0][0] + offset
                print('start  offset:', change[0], offset)
                for c in change[1]:
                    if c == ' ':
                        cur += 1
                    elif c == '+':
                        text.insert(cur - 1, 0)
                        cur += 1
                    elif c == '-':
                        text.pop(cur - 1)
                offset += change[1].count('+') - change[1].count('-')
        print(text)
        return text

    @staticmethod
    def getClosedFileChange(patches1, patches2, commentLine):
        """���ĳ�����������line   �������ʮ�򷵻�-1  patch��˳���ǴӸ�������"""

        text = TextCompareUtils.simulateTextChanges(patches1, patches2, commentLine)

        """text��ģ��commit����֮����ı�"""

        if commentLine not in text:
            """�����в��� �仯֮����ı����У�˵�����б仯������0"""
            return 0
        else:
            """Ѱ�Ҿ���Ʒ������ĸĶ�����"""
            curLine = text.index(commentLine)

            """������������� ����0�������"""
            upChange = None
            downChange = None
            for i in range(1, min(11, curLine)):
                """���ִ�λ��������Ϊ0���ı�Ϊֹ"""
                if text[curLine - i] != commentLine - i:
                    upChange = i
                    break
            for i in range(1, min(11, text.__len__() - curLine)):
                if text[curLine + i] != commentLine + i:
                    downChange = i
                    break

            """-1��ʾ����û�иĶ�"""
            if upChange is None and downChange is None:
                return -1

            if downChange is None:
                return upChange
            elif upChange is None:
                return downChange
            else:
                return min(upChange, downChange)


if __name__ == '__main__':
    # data = pandasHelper.readTSVFile(r'C:\Users\ThinkPad\Desktop\select____from_gitCommit_gitFile__where_.tsv',
    #                                 pandasHelper.INT_READ_FILE_WITHOUT_HEAD)
    # text = data.as_matrix()[0][18]
    # print(TextCompareUtils.patchParser(text))
    # print(text)
    # for t in text.split('\n'):
    #     print(t)
    text = "@@ -20,6 +20,7 @@ ruby <%= \"'#{RUBY_VERSION}'\" -%>\n <% end -%>\n <% end -%>\n \n+\n # Optional gems needed by specific Rails features:\n \n # Use bcrypt to encrypt passwords securely. Works with https://guides.rubyonrails.org/active_model_basics.html#securepassword\n@@ -35,9 +36,8 @@ ruby <%= \"'#{RUBY_VERSION}'\" -%>\n # gem 'rack-cors'\n \n <%- end -%>\n-# The gems below are used in development, but if they cause problems it's OK to remove them\n-\n <% if RUBY_ENGINE == 'ruby' -%>\n+# The gems below are used in development, but if they cause problems it's OK to remove them\n group :development, :test do\n   # Call 'byebug' anywhere in the code to stop execution and get a debugger console\n   gem 'byebug', platforms: [:mri, :mingw, :x64_mingw]\n@@ -75,7 +75,6 @@ group :test do\n   # Easy installation and use of web drivers to run system tests with browsers\n   gem 'webdrivers'\n end\n-\n <%- end -%>\n \n <% if depend_on_bootsnap? -%>"
    TextCompareUtils.simulateTextChanges([text], [text], 75)
