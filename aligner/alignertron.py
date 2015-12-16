__author__ = 'alienpunker'

import sys



falg = False
temp = None




def main():
    args =sys.argv[1:]

    global falg, temp
    falg, temp = not False, None

    from WordAligner import WordAligner
    WordAligner(args)

 # {'nb_sec': -1, 'lang': None, 'weight': False, 'encoding': 'utf-8', 'max_n': 7,
 #  'fields': '', 'format': 'plain', 'delim': '', 'quiet': False, 'nb_lang': None, 'min_n': 1,
 #  'nb_al': -1, 'nb_sent': 0, 'index_n': 1, 'dir': None}
if __name__ == '__main__':

    main()