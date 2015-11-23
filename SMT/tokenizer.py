__author__ = 'santiago'

class tokenizer:
    def __init__(self, file1, file2):
        try:
            english_input = open(file1, 'r').read()
            # foreing_input = open(file2,'r').read()
            # print(english_input)

        except:
            print("one of the files does not exist!")
        pass
    def tokenizer(self):

        my_string = "This is nothing but a pure test. I mean, (just a test)."
        broken = my_string.split(" ")
        newString = ""
        pstPunct = [',','.','!',')','%','\'',"\"",':',';',']','?']
        prePunct = ['¡','(','#','\'','\"','[','¿','@']

        for word in broken:
            if any(x in word for x in pstPunct):
                if ')' in word and '.' in word or ']' in word and '.' in word:
                    newString += word[:-2] + " " + word[len(word)-2:len(word)-1] + " " +word[len(word)-1:]

                else:
                    newString += word[:-1] + " " + word[len(word)-1:] + " "
            elif any(x in word for x in prePunct):
                newString += word[0] + " " + word[1:] + " "
            else:
                newString += word + " "


        return self.truecasing(newString)

    def truecasing(self, str):
        return str.lower()

if __name__ == '__main__':
    n = tokenizer("en.txt","es.txt")
    # n.tokenizer()
    print(n.tokenizer())