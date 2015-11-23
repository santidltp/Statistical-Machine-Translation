__author__ = 'santiago'

class tokenizer:
    def __init__(self, file):
        file_object = open(file, 'r').read()
        print(file_object)
        pass
    def readFile(self):
        pass


if __name__ == '__main__':
    n = tokenizer("en.txt")
