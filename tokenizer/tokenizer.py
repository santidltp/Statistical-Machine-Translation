# -*- coding:utf-8 -*-

__author__ = 'santiago'
import sys
class tokenizer:


    def tokenizer(self, file1, file2):
        try:
            ffile = open(file1, 'r').read()
            sfile = open(file2, 'r').read()

        except:
            print("The files do not exist!")
            return None


        fileOne = self.truecasing(ffile)
        fileTwo=self.truecasing(sfile)

        punctuation = [',','.','!',')','%','\'',"\"",':',';',']'
            ,'?','¡','(','#','[','¿','@','$','\xe2\x80\x99',
                       '-','_']
        for punct in punctuation:

            if punct in ffile:
               fileOne = fileOne.replace(punct, " "+punct+" ")
            if punct in sfile:
               fileTwo = fileTwo.replace(punct, " "+punct+" ")

        breakerOne = fileOne.split('\n')
        breakerTwo = fileTwo.split('\n')
        newerStringOne=[]
        newerStringTwo=[]
        if len(breakerOne) != len(breakerTwo):
            print "Error, both of files have different number of lines"
            return None
        else:
            for line in range(0,len(breakerOne)):
                if len(breakerOne[line])<=146 and len(breakerTwo[line])<=146:
                    newerStringOne.append(breakerOne[line])
                    newerStringTwo.append(breakerTwo[line])

        with open(file1+'_tk.txt', 'w') as f:
            f.writelines('\n'.join(newerStringOne))
            f.close()
        with open(file2+'_tk.txt', 'w') as per:
            per.writelines('\n'.join(newerStringTwo))
            per.close()


        # return self.truecasing(fileOne)
        return "Documents tokenized!"
    def truecasing(self, str):
        return str.lower()

if __name__ == '__main__':
    n = tokenizer()
    try:
        print sys.argv[1:]
        first_file =sys.argv[1:][0] # one file per time
        second_file=sys.argv[1:][1]

        print n.tokenizer(first_file, second_file)
    except Exception as e:
        print e