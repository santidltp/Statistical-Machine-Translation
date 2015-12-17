# -*- coding:utf-8 -*-

__author__ = 'santiago'
import sys
class tokenizer:


    def tokenizer(self, file1):
        try:
            english_input = open(file1, 'r').read()

        except:
            return("The files does not exist!")


        newString = english_input
        punctuation = [',','.','!',')','%','\'',"\"",':',';',']'
            ,'?','¡','(','#','[','¿','@','$','\xe2\x80\x99',
                       '-','_']
        for punct in punctuation:

            if punct in english_input:
               newString = newString.replace(punct, " "+punct+" ")


        with open(file1+'_tk.txt', 'w') as f:
            f.write(self.truecasing(newString))
            f.close()

        # return self.truecasing(newString)
        return "Document tokenized!"
    def truecasing(self, str):
        return str.lower()

if __name__ == '__main__':
    n = tokenizer()
    try:
        args =sys.argv[1:][0] # one file per time
        print args
        print n.tokenizer(args)
    except Exception as e:
        print e