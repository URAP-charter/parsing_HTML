#pip install gensim
#pip install nltk
#pip install tqdm

#!/usr/bin/env python
# -*- coding: UTF-8

# Word Embedding Models: Preprocessing and Model Training
# Project title: Charter school identities 
# Creator: Jaren Haber, PhD Candidate
# Institution: Department of Sociology, University of California, Berkeley
# Date created: July 20, 2018
# Date last edited: November 8, 2018

# ## Initialize

# Import general packages
import imp, importlib # For working with modules
import nltk # for natural language processing tools
import pandas as pd # for working with dataframes
#from pandas.core.groupby.groupby import PanelGroupBy # For debugging
import numpy as np # for working with numbers
import pickle # For working with .pkl files
from tqdm import tqdm # Shows progress over iterations, including in pandas via "progress_apply"
import sys # For terminal tricks
import _pickle as cPickle # Optimized version of pickle
import gc # For managing garbage collector
import timeit # For counting time taken for a process
import datetime # For working with dates & times

# Import packages for cleaning, tokenizing, and stemming text
import re # For parsing text
from unicodedata import normalize # for cleaning text by converting unicode character encodings into readable format
from nltk import word_tokenize, sent_tokenize # widely used text tokenizer
from nltk.stem.porter import PorterStemmer # an approximate method of stemming words (it just cuts off the ends)
from nltk.stem.porter import PorterStemmer # approximate but effective (and common) method of normalizing words: stems words by implementing a hierarchy of linguistic rules that transform or cut off word endings
stem = PorterStemmer().stem # Makes stemming more accessible
from nltk.corpus import stopwords # for eliminating stop words
import gensim # For word embedding models
from gensim.models.phrases import Phrases # Makes word2vec more robust: Looks not just at  To look for multi-word phrases within word2vec

# Import packages for multiprocessing
import os # For navigation
numcpus = len(os.sched_getaffinity(0)) # Detect and assign number of available CPUs
from multiprocessing import Pool # key function for multiprocessing, to increase processing speed
pool = Pool(processes=numcpus) # Pre-load number of CPUs into pool function
import Cython # For parallelizing word2vec
mpdo = False # Set to 'True' if using multiprocessing--faster for creating words by sentence file, but more complicated
nltk.download('stopwords')
nltk.download('punkt')

# For loading functions from files in data_tools directory:
import sys; sys.path.insert(0, "../../data_tools/")
from clean_text import clean_sentence, stopwords_make, punctstr_make, unicode_make
import clean_text

# ## Create lists of stopwords, punctuation, and unicode characters
stop_words_list = stopwords_make() # Define old vocab file path if you want to remove first, dirty elements
unicode_list = unicode_make()
punctstr = punctstr_make()

print("Sentence cleaning preliminaries complete...")


# ## Prepare to read data

# Define file paths
if mpdo:
    wordsent_path = "../../Charter-school-identities/data/wem_wordsent_data_train250_nostem_unlapped_clean2.txt"
else:
    wordsent_path = "../../Charter-school-identities/data/wem_wordsent_data_train250_nostem_unlapped_clean2.pkl"
charters_path = "../../nowdata/traincf_2015.pkl" # All text data; only charter schools (regardless if open or not)
phrasesent_path = "../../Charter-school-identities/data/wem_phrasesent_data_train250_nostem_unlapped_clean2.pkl"
#wemdata_path = "../data/wem_data.pkl"
model_path = "../../Charter-school-identities/data/wem_model_train250_nostem_unlapped_300d_clean2.bin"
vocab_path = "../../Charter-school-identities/data/wem_vocab_train250_nostem_unlapped_300d_clean2.txt"
vocab_path_old = "../../Charter-school-identities/data/wem_vocab_train250_nostem_unlapped_300d_clean.txt"

# Check if sentences data already exists, to save time
try:
    if (os.path.exists(wordsent_path)) and (os.path.getsize(wordsent_path) > 10240): # Check if file not empty (at least 10K)
        print("Existing sentence data detected at " + str(os.path.abspath(wordsent_path)) + ", skipping preprocessing sentences.")
        sented = True
    else:
        sented = False
except FileNotFoundError or OSError: # Handle common errors when calling os.path.getsize() on non-existent files
    sented = False

# Check if sentence phrases data already exists, to save time
try:
    if (os.path.exists(phrasesent_path)) and (os.path.getsize(phrasesent_path) > 10240): # Check if file not empty (at least 10K)
        print("Existing sentence + phrase data detected at " + str(os.path.abspath(phrasesent_path)) + ", skipping preprocessing sentence phrases.")
        phrased = True
    else:
        phrased = False
except FileNotFoundError or OSError: # Handle common errors when calling os.path.getsize() on non-existent files
    phrased = False
    

# ## Define helper functions

def quickpickle_load(picklepath):
    '''Very time-efficient way to load pickle-formatted objects into Python.
    Uses C-based pickle (cPickle) and gc workarounds to facilitate speed. 
    Input: Filepath to pickled (*.pkl) object.
    Output: Python object (probably a list of sentences or something similar).'''

    with open(picklepath, 'rb') as loadfile:
        
        gc.disable() # disable garbage collector
        outputvar = cPickle.load(loadfile) # Load from picklepath into outputvar
        gc.enable() # enable garbage collector again
    
    return outputvar


def quickpickle_dump(dumpvar, picklepath):
    '''Very time-efficient way to dump pickle-formatted objects from Python.
    Uses C-based pickle (cPickle) and gc workarounds to facilitate speed. 
    Input: Python object (probably a list of sentences or something similar).
    Output: Filepath to pickled (*.pkl) object.'''

    with open(picklepath, 'wb') as destfile:
        
        gc.disable() # disable garbage collector
        cPickle.dump(dumpvar, destfile) # Dump dumpvar to picklepath
        gc.enable() # enable garbage collector again
    
    
def write_list(file_path, textlist):
    """Writes textlist to file_path. Useful for recording output of parse_school()."""
    
    with open(file_path, 'w') as file_handler:
        
        for elem in textlist:
            file_handler.write("{}\n".format(elem))
    
    return    


def load_list(file_path):
    """Loads list into memory. Must be assigned to object."""
    
    textlist = []
    with open(file_path) as file_handler:
        line = file_handler.readline()
        while line:
            textlist.append(line)
            line = file_handler.readline()
    return textlist
    
    
def write_sentence(sentence, file_path):
    """Writes sentence to file at file_path.
    Useful for recording first row's output of preprocess_wem() one sentence at a time.
    Input: Sentence (list of strings), path to file to save it
    Output: Nothing (saves to disk)"""
    
    with open(file_path, 'w+') as file_handler:
        for word in sentence: # Iterate over words in sentence
            if word == "":
                pass
            else:
                file_handler.write(word + " ") # Write each word on same line, followed by space
            
        file_handler.write("\n") # After sentence is fully written, close line (by inserting newline)
            
    return


def append_sentence(sentence, file_path):
    """Appends sentence to file at file_path. 
    Useful for recording each row's output of preprocess_wem() one sentence at a time.
    Input: Sentence (list of strings), path to file to save it
    Output: Nothing (saves to disk)"""

    with open(file_path, 'a+') as file_handler:
        for word in sentence: # Iterate over words in sentence
            if word == "":
                pass
            else:
                file_handler.write(word + " ") # Write each word on same line, followed by space
            
        file_handler.write("\n") # After sentence is fully written, close line (by inserting newline)
            
    return

    
def load_tokslist(file_path):
    """Loads from file and word-tokenizes list of "\n"-separated, possibly multi-word strings (i.e., sentences). 
    Output must be assigned to object.
    Input: Path to file with list of strings
    Output: List of word-tokenized strings, i.e. sentences"""
    
    textlist = []
    
    with open(file_path) as file_handler:
        line = file_handler.readline() # Read first line
        
        while line: # Continue while there's still a line to read
            textlist.append(word for word in word_tokenize(line)) # Tokenize each line by word while loading in
            line = file_handler.readline() # Read next line
            
    return textlist


# ## Preprocessing I: Tokenize web text by sentences

df = quickpickle_load(charters_path) # Load charter data into DF
print("DF loaded from " + str(charters_path) + "...")

if phrased: 
    pass # If parsed sentence phrase data exists, don't bother with tokenizing sentences

elif sented: # Check if tokenized sentence data already exists. If so, don't bother reparsing it
    words_by_sentence = []
    
    # Load data back in for parsing phrases and word embeddings model:
    if mpdo:
        words_by_sentence = load_tokslist(wordsent_path) 
    else:
        words_by_sentence = quickpickle_load(wordsent_path) 

else:
    
    words_by_sentence = [] # Initialize variable to hold list of lists of words (sentences)
    pcount=0 # Initialize preprocessing counter
    df["WEBTEXT"] = df["WEBTEXT"].astype(list) # Coerce these to lists in order to avoid type errors

    # Convert DF into list (of lists of tuples) and call preprocess_wem on element each using Pool():
    try:
        tqdm.pandas(desc="Tokenizing sentences") # To show progress, create & register new `tqdm` instance with `pandas`

        # WITH multiprocessing (faster):
        if mpdo:
            weblist = df["WEBTEXT"].tolist() # Convert DF into list to pass to Pool()

            # Use multiprocessing.Pool(numcpus) to run preprocess_wem:
            print("Preprocessing web text into list of sentences...")
            if __name__ == '__main__':
                with Pool(numcpus) as p:
                    p.map(preprocess_wem, tqdm(weblist, desc="Tokenizing sentences")) 

        # WITHOUT multiprocessing (much slower):
        else:
            df["WEBTEXT"].progress_apply(lambda tups: preprocess_wem(tups))

            # Save data for later
            try: # Use quickpickle to dump data into pickle file
                if __name__ == '__main__': 
                    print("Saving list of tokenized sentences to file...")
                    t = timeit.Timer(stmt="quickpickle_dump(words_by_sentence, wordsent_path)", globals=globals())
                    print("Time elapsed saving data: " + str(round(t.timeit(1),4)),'\n')

                '''with open(wordsent_path, 'wb') as destfile:
                    gc.disable() # Disable garbage collector to increase speed
                    cPickle.dump(words_by_sentence, destfile)
                    gc.enable() # Enable garbage collector again'''

            except Exception as e:
                print(str(e), "\nTrying backup save option...")
                try:
                    # Slower way to save data:
                    with open(wordsent_path, 'wb') as destfile:
                        t = timeit.Timer(stmt="pickle.dump(words_by_sentence, destfile)", globals=globals())
                        print("Success! Time elapsed saving data: " + str(round(t.timeit(1),4)),'\n')

                except Exception as e:
                    print("Failed to save sentence data: " + str(e))

    except Exception as e:
        print("Failed to tokenize sentences: " + str(e))
        sys.exit()
        
    
# ## Preprocessing II: Detect and parse common phrases in words_by_sentence

if phrased: # Check if phrased data already exists. If so, don't bother recalculating it
    words_by_sentence = []
    words_by_sentence = quickpickle_load(phrasesent_path) # Load data back in, for word embeddings model

else:
    tqdm.pandas(desc="Parsing phrases") # Change title of tqdm instance

    try:
        print("Detecting and parsing phrases in list of sentences...")
        # Threshold represents a threshold for forming the phrases (higher means fewer phrases). A phrase of words a and b is accepted if (cnt(a, b) - min_count) * N / (cnt(a) * cnt(b)) > threshold, where N is the total vocabulary size. By default this value is 10.0
        phrases = Phrases(words_by_sentence, min_count=3, delimiter=b'_', common_terms=stop_word_list, threshold=8) # Detect phrases in sentences based on collocation counts
        words_by_sentence = [phrases[sent] for sent in tqdm(words_by_sentence, desc="Parsing phrases")] # Apply phrase detection model to each sentence in data

    except Exception as e:
        print("Failed to parse sentence phrases: " + str(e))
        sys.exit()
    
    # Save data for later
    try: # Use quickpickle to dump data into pickle file
        if __name__ == '__main__': 
            print("Saving list of tokenized, phrased sentences to file...")
            t = timeit.Timer(stmt="quickpickle_dump(words_by_sentence, phrasesent_path)", globals=globals())
            print("Time elapsed saving data: " + str(round(t.timeit(1),4)),'\n')
                                         
        '''with open(phrasesent_path, 'wb') as destfile:
            gc.disable() # Disable garbage collector to increase speed
            cPickle.dump(words_by_sentence, destfile)
            gc.enable() # Enable garbage collector again'''

    except Exception as e:
        print(str(e), "\nTrying backup save option...")
        try:
            # Slower way to save data:
            with open(phrasesent_path, 'wb') as destfile:
                t = timeit.Timer(stmt="pickle.dump(words_by_sentence, destfile)", globals=globals())
                print("Success! Time elapsed saving data: " + str(round(t.timeit(1),4)),'\n')

        except Exception as e:
            print("Failed to save parsed sentence phrases: " + str(e))
        

# Take a look at the data 
print("Sample of the first 10 sentences:")
print(words_by_sentence[:10])

school_sentslist = [] # Initialize variable to hold list of lists of words (sentences)
def preprocess_wem(tuplist): # inputs were formerly: (tuplist, start, limit)
    
    '''This function cleans and tokenizes sentences, removing punctuation and numbers and making words into lower-case stems.
    Inputs: list of four-element tuples, the last element of which holds the long string of text we care about;
        an integer limit (bypassed when set to -1) indicating the DF row index on which to stop the function (for testing purposes),
        and similarly, an integer start (bypassed when set to -1) indicating the DF row index on which to start the function (for testing purposes).
    This function loops over five nested levels, which from high to low are: row, tuple, chunk, sentence, word.
    Note: This approach maintains accurate semantic distances by keeping stopwords.'''
        
    global mpdo # Check if we're doing multiprocessing. If so, then mpdo=True
    global sents_combined # Grants access to variable holding a list of lists of words, where each list of words represents a sentence in its original order (only relevant for this function if we're not using multiprocessing)
    global pcount # Grants access to preprocessing counter
    
    known_pages = set() # Initialize list of known pages for a school
    sents_combined = [] # Initialize list of all school's sentences

    if type(tuplist)==float:
        return # Can't iterate over floats, so exit
    
    #print('Parsing school #' + str(pcount)) # Print number of school being parsed

    for tup in tuplist: # Iterate over tuples in tuplist (list of tuples)
        if tup[3] in known_pages or tup=='': # Could use hashing to speed up comparison: hashlib.sha224(tup[3].encode()).hexdigest()
            continue # Skip this page if exactly the same as a previous page on this school's website

        for chunk in tup[3].split('\n'): 
            for sent in sent_tokenize(chunk): # Tokenize chunk by sentences (in case >1 sentence in chunk)
                sent = clean_sentence(sent, remove_stopwords=True) # Clean and tokenize sentence
                
                if ((sent == []) or (len(sent) == 0)): # If sentence is empty, continue to next sentence without appending
                    continue
                
                
                # TO DO: Chunk this by school, not just sentence
                # TO DO: Now that sentences are parsed and cleaned by spaces, 
                # recombine and then parse more accurately using spacy word tokenizer
                
                # Save preprocessing sentence to object (if not multiprocessing)
                sents_combined.extend(sent) # add sent to object
                    
        known_pages.add(tup[3])
        
    #school_sentslist.append(sents_combined) # add sent to object
    
    #pcount += 1 # Add to counter
    
    return sents_combined

docs_tagged = []
for school in df['WEBTEXT']:
    doc = preprocess_wem(school)
    T = gensim.models.doc2vec.TaggedDocument(doc,[doc])
    docs_tagged.append(T)
    
#setting up multiprocessing
import multiprocessing
cores = multiprocessing.cpu_count()

# Train the model with above parameters:
print("Training doc2vec model...")
model_dbow = gensim.models.Doc2Vec(dm=0, vector_size=300, negative=5, hs=0, min_count=2, sample = 0, workers=cores)
model_dbow.build_vocab(docs_tagged)
print("doc2vec model TRAINED successfully!")


#saving the model 
from gensim.test.utils import get_tmpfile
fname = get_tmpfile("my_doc2vec_model")
model_dbow.save(fname)
#for loading
#model = Doc2Vec.load(fname)
