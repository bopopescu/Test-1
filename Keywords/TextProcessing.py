import nltk
from flask import Flask, render_template, request
from nltk.corpus import stopwords
from nltk.stem import LancasterStemmer
from nltk.stem.wordnet import WordNetLemmatizer
import string
import operator
from sklearn.feature_extraction.text import CountVectorizer
import mysql.connector
import json
app = Flask(__name__)


@app.route('/')
def index():
    """
    :return: HTML front page
    """
    return render_template('index.html')


domain = ""
text = ""
punctuation = set(string.punctuation)
stop_words = set(stopwords.words("english"))
imp_keywords = set()
imp_words = set()
imp_words_list_database = []
imp_words_list_vocabulary = []

lem = WordNetLemmatizer()  # It will find the Root form i.e Verb of a word
lancaster = LancasterStemmer()  # It will convert the word into its stemed form i.e. Root form


def get_json_data(filepathname):
    """
    Description : This function will accept the json file_path_name as a parameter
                  Read that file and return file pointer to calling function.

    Input : Json file path name
    Output : Read that file and return file pointer
    """
    with open(filepathname, 'r') as fp:
        return json.load(fp)


def remove_stopwords_puntuation(words):
    """
    Description : This function will accept the list of words as a input.
                  Remove stop_words and puntuations from it. and returns the final list.

    Input : List of words
    Output : List of words without stop_words and puntuations.
    """
    tokanize_words = [word.lower() for word in words if word not in stop_words and word not in punctuation]
    return tokanize_words


@app.route('/form1', methods=['POST'])
def find_important_keywords():
    """
    Description : This function will accept the Issue description from the from as a String.
                  Convert the text into List and Remove Stop_words and Puntuations from it.
                  Compare each word with Keywords fetched from Mysql database and checked if
                  that word or root form of that word is present in the database.
                  Also calculate list of keywords which are not present in database but
                  may be important.

    Input : Text Message (Issue description ) from user.
    Output : 1) Important Keywords fetched from Database with their count
             2) Keywords that may be important but not present in database.
    """

    global text, punctuation, stop_words, imp_words_list_vocabulary, imp_words, imp_words_list_database, imp_keywords, domain

    text = request.form['description']  # Accept issue description from user and store it in String variable.
    domain = request.form.get('Domains')  # Accept value from drop-down list
    words = nltk.word_tokenize(text)  # create tokens of words from the text
    tokanize_words = remove_stopwords_puntuation(words)  # Filter words . i.e. Remove stopwords and Puntuations.

    try:
        myobj = get_json_data('./config.json')   # pass file to function. to get file pointer.

        HOST = myobj.get("HOST")
        DATABASE = myobj.get("DATABASE")
        USERNAME = myobj.get("USERNAME")
        PASSWORD = myobj.get("PASSWORD")
        connection = mysql.connector.connect(host=HOST,
                                             database=DATABASE,
                                             user=USERNAME,
                                             password=PASSWORD)   # Connect to Mysql Database.

        mySql_select_query = "SELECT * FROM " + str(domain) + ";"

        cursor = connection.cursor()
        cursor.execute(mySql_select_query)
        records = cursor.fetchall()            # Fetch records from the Mysql table
        for row in records:
            imp_keywords.add(row[0])
        connection.commit()
        cursor.close()

    except mysql.connector.Error as error:
        print("Failed to select record from {0} table {1}".format(domain, error))

    finally:
        if (connection.is_connected()):
            connection.close()
            print("MySQL connection is closed")

    imp_words = set([word for word in tokanize_words if
                     lem.lemmatize(word.lower()) in imp_keywords or lancaster.stem(word.lower()) in imp_keywords
                     or word in imp_keywords])

    print("impwords", imp_words)
    imp_words_dict = {}
    ex=list(imp_words)

    for word in tokanize_words:
        if word in imp_words:
            if word in imp_words_dict.keys():
                imp_words_dict[word] = imp_words_dict[word] + 1
            else:
                imp_words_dict[word] = 1

    imp_words_list_database = sorted(imp_words_dict.items(), key=operator.itemgetter(1), reverse=True)

    cv = CountVectorizer(max_df=0.8, stop_words=stop_words, max_features=100, ngram_range=(1, 3))
    x = cv.fit_transform(tokanize_words)
    imp_words_list_vocabulary = [word for word in list(cv.vocabulary_.keys())[:15] if word not in imp_words]

    mylist = text.split()
    print(mylist)

    return render_template('index.html', imp_words_list_database=imp_words_list_database,
                           imp_words_list_vocabulary=imp_words_list_vocabulary, text=text, domain=domain,imp_words_dict=ex)


@app.route('/form2', methods=['POST'])
def add_keywords_database():
    """
    Description : This function will add important keywords to the mysql database.
                  This function will accept the list of checked keywords from the user.
                  Add each word of that list to the perticular table in database.

    Input : List of checked Keywords from User.
    Output : Updated important keywords fetched from database and vocabulary
    """
    check_box = request.form.getlist('check')
    try:
        myobj = get_json_data('./config.json')

        HOST = myobj.get("HOST")
        DATABASE = myobj.get("DATABASE")
        USERNAME = myobj.get("USERNAME")
        PASSWORD = myobj.get("PASSWORD")

        connection = mysql.connector.connect(host=HOST,
                                             database=DATABASE,
                                             user=USERNAME,
                                             password=PASSWORD)

        for word in check_box:
            word = lem.lemmatize(word.lower())
            mySql_insert_query = "INSERT INTO " + str(domain) + " (Keywords) VALUES ('" + str(word) + "')"
            cursor = connection.cursor()
            cursor.execute(mySql_insert_query)

        connection.commit()
        cursor.close()

    except mysql.connector.Error as error:
        print("Failed to insert record into {0} table {1}".format(domain, error))

    finally:
        if (connection.is_connected()):
            connection.close()
            print("MySQL connection is closed")

    return render_template('index.html', imp_words_list_database=imp_words_list_database,
                           imp_words_list_vocabulary=imp_words_list_vocabulary, text=text, domain=domain)


if __name__ == '__main__':
    app.run(debug=True)