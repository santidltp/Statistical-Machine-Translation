# -*- coding:utf-8 -*-

__author__ = 'santiago'

class tokenizer:


    def tokenizer(self, file1):
        try:
            english_input = open(file1, 'r').read()
            # foreing_input = open(file2,'r').read()
            # print(english_input)

        except:
            print("The files does not exist!")


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
    print n.tokenizer("news-commentary-v8.cs-en.en")