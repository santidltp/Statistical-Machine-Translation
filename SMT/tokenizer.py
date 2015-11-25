__author__ = 'santiago'

class tokenizer:


    def tokenizer(self, file1):
        try:
            english_input = open(file1, 'r').read()
            # foreing_input = open(file2,'r').read()
            # print(english_input)

        except:
            print("The files does not exist!")

        my_string = "This is nothing but a pure test. I mean, (just a test)."
        lines = english_input.split('\n')
        words = [x.split(" ") for x in lines ]

        # words = lines.split(" ")
        newString = ""
        pstPunct = [',','.','!',')','%','\'',"\"",':',';',']','?']
        prePunct = ['¡','(','#','\'','\"','[','¿','@','$']
        for line in lines:
            ex = line.split(" ")
            for word in ex:

                if any(x in word for x in pstPunct):
                    if ')' in word and '.' in word or ']' in word and '.' in word:
                        newString += word[:-2] + " " + word[len(word)-2:len(word)-1] + " " + word[len(word)-1:]

                    else:
                        newString += word[:-1] + " " + word[len(word)-1:] + " "

                elif any(x in word for x in prePunct):
                    newString += word[0] + " " + word[1:] + " "
                else:
                    newString += word + " "
                # if '\n' in word:
            newString+='\n'


        return self.truecasing(newString)

    def truecasing(self, str):
        return str.lower()

if __name__ == '__main__':
    n = tokenizer()
    print(n.tokenizer("en.txt"))