
# coding: utf-8

# In[1]:


import sqlite3
import csv
import pandas as pd
import os
import re

import math
from tqdm import tqdm
import multiprocessing as mp
import time
import sched
import ast
import logging



from difflib import SequenceMatcher as SeqMatcher
import numpy as np

# Import packages for multiprocessing
import os # For navigation


folder_prefix = '/vol_b/data/'

logging.basicConfig(filename="CMO_WEBTEXT_2.log", level=logging.INFO)

# In[ ]:

#is originally charters_full_2015_15_250.pkl for xxl vm , but is nowdata/charters_full_2015_250_new.pkl in large vm for testing purposes

#full_250_df = pd.read_pickle(folder_prefix + "nowdata/charters_full_2015_250_new.pkl")
next_df = pd.read_csv(folder_prefix + "nowdata/parsing/cmo_left.csv", sep="\t", low_memory=False, encoding="utf-8")

# In[ ]:


def create_first_cut(pages):
    

    final_cut_strings = pages.copy() #copy of pages
   
    for a in range(len(pages)):
        
        for b in range(len(pages)):
    
            if a < b : #a and b are not the same
            #we're iterating from a = 0 to len(pages) - 1, so we've already seen 0,1 compared and cut down strings when 0 is 
            #compared to 1. Now we don't need to do anything to compare 1 to 0 and cut down again, cuz final_cut_strings[1]
            #should already have cut down version of 1 when it was previously compared with 0

                #get similarity ratio between a and b
                list_a = pages[a].split() #splits string_a by whitespace
                list_b = pages[b].split()

                #already compared 1,2 , don't need to compare 2,1 - you already know it's added so you have indices of overlap
                if (len(pages) <= 20):
                    #don't call get ratio
                    #go ahead and directly call get_matching_blocks
                    
                    list_of_triples = SeqMatcher(None, list_a, list_b).get_matching_blocks()
                    zeroth_triple = list_of_triples[0] #first triple, most likely in beginning, most likely a header
                    last_triple = list_of_triples[len(list_of_triples) - 2] #2nt to last triple is the footer indices

                    z_n = zeroth_triple[2] #j to j+n are the indices of the overlapping part
                    l_n = last_triple[2]

                    orig_string_a = pages[a]
                    split_li_a = orig_string_a[:zeroth_triple[0]] + " " + (orig_string_a[zeroth_triple[0] + z_n: last_triple[0]])+" " + (orig_string_a[last_triple[0] + l_n:]) 
                    #removes overlapping part in string a, removes header and footer
                    #keeps cut down part
                    cut_down_string_a = " ".join(split_li_a)


                    orig_string_b = pages[b]
                    split_li_b = orig_string_b[:zeroth_triple[1]] + " " + (orig_string_b[zeroth_triple[1] + z_n: last_triple[1]])+" " + (orig_string_b[last_triple[1] + l_n:]) 
                    #removes overlapping part in string a
                    cut_down_string_b = " ".join(split_li_b)

                    if (len(cut_down_string_a) < len(final_cut_strings[a])):
                        # this is our new low, cut down string, replace what's in fianal cut strings[a] with new version
                        final_cut_strings[a] = cut_down_string_a

                    if len(cut_down_string_b) < len(final_cut_strings[b]):
                        final_cut_strings[b] = cut_down_string_b
                    
                   
                else: 
                    quick_ratio = SeqMatcher(None, pages[a], pages[b]).quick_ratio()
                
                    if (quick_ratio >= 0.7) & (quick_ratio <  1.0):

                        list_of_triples = SeqMatcher(None, list_a, list_b).get_matching_blocks()
                        zeroth_triple = list_of_triples[0] #first triple, most likely in beginning, most likely a header
                        last_triple = list_of_triples[len(list_of_triples) - 2] #2nt to last triple is the footer indices

                        z_n = zeroth_triple[2] #j to j+n are the indices of the overlapping part
                        l_n = last_triple[2]

                        orig_string_a = pages[a]
                        split_li_a = orig_string_a[:zeroth_triple[0]] +" " + (orig_string_a[zeroth_triple[0] + z_n: last_triple[0]]) + " " +(orig_string_a[last_triple[0] + l_n:]) 
                        #removes overlapping part in string a, removes header and footer
                        #keeps cut down part
                        cut_down_string_a = " ".join(split_li_a)


                        orig_string_b = pages[b]
                        split_li_b = orig_string_b[:zeroth_triple[1]] +" " + (orig_string_b[zeroth_triple[1] + z_n: last_triple[1]])+ " " +(orig_string_b[last_triple[1] + l_n:]) 
                        #removes overlapping part in string a
                        cut_down_string_b = " ".join(split_li_b)

                        if (len(cut_down_string_a) < len(final_cut_strings[a])):
                            # this is our new low, cut down string, replace what's in fianal cut strings[a] with new version
                            final_cut_strings[a] = cut_down_string_a

                        if len(cut_down_string_b) < len(final_cut_strings[b]):
                            final_cut_strings[b] = cut_down_string_b

    #final_cut strings should be cut down 
    return final_cut_strings


# In[ ]:


def create_second_header_cut(first_header_cut):
    
    super_final_strings = []
    for s in first_header_cut:
        s_new = ""
        if(s is None):
            s_new = ""
        else:
            s_new = s
        use_punc = False
        use_sev = False
        punc = [",", ".", ":", ";"]
        p_list = []
        for p in punc:
            if (s_new.find(p) != -1):
                p_list.append(s_new.find(p))
            else:
                p_list.append(len(s_new))

        punc_ind = min(p_list)

        n_list = [index for index, k in enumerate(s_new) if k=='\n']
        start_punc = len(s_new)
        for i in n_list:
            if(i < punc_ind):
                start_punc = i # start_punc equals the largest index of \n that's less than index of first punctuation

        start = 0
        end = 0
        total = ""
        list_totals = []
        st_en = []
        for c in s_new:
            if (c not in ['\n', '\t']):
                total+=(c)
                end+=1
            else :
                if(len(total.split()) >= 7): # we hit 7 words or more, wipe everything before start index
                    #list_totals.append(total)
                    st_en.append((start, end))

                total= ""
                start = end
        start_sev = len(s_new)-1 #len(s)-1 #make it huge by default; if there's no group of 7, then start punc will be the smallest
        if len(st_en) > 0:
            start_sev = st_en[0][0] #index of first group of words that's >= 7 words; 0th tuple's start value


        #take smaller of the two indices, since we want to use the property which occurs first
        if start_punc < start_sev:
            #if start of sentence which ends in/contains puncuation occurs earlier, wipe eveything before that index
            #only take that index +1 and on, start right after the new line
            new_string = s_new[start_punc+1:] 
            super_final_strings.append(new_string)

        else:
            #if start of group of words that >= 7 occurs earlier than a sentence with punctuation, wipe eveything before that index
            #only take that index and on, statr using that begining of the group of 7+ words
            new_string = s_new[start_sev:] 
            super_final_strings.append(new_string)
        
    return super_final_strings


# In[ ]:

k = 0
def remove_string_overlaps(tuplist):
    global k

    unique_tuplist = []
    seen_pages = set() # Initialize list of known pages for a school
    unique_pages=[]
    tup_indices = []

    cleaned_strings = []
    new_list = []
    
    if (str(tuplist) == 'nan') or (len(tuplist) == 0):
        return new_list
    else :
        
        for tup in tuplist:
            if (tup is not None) and (len(tup) > 3):
                seen_pages.add(tup[3])

        for i in range(len(tuplist)):
            if (len(tuplist[i]) > 3) and (tuplist[i][3] in seen_pages) and (tuplist[i][3]  not in unique_pages):
                unique_tuplist.append(tuplist[i])
                unique_pages.append(tuplist[i][3])
                tup_indices.append(i)
                #print("unique page : " + str(i))

        #now compare all pages with each other 
        #final cut strings already should have supposed "headers" and "footers" removed
        final_cut_strings = create_first_cut(unique_pages)

        #first removal of headers in final_cut_strings currently, but now we want to cut down headers more
        #take out text before the first sentence or text before the first group of 7+ words  
        cleaned_strings = create_second_header_cut(final_cut_strings)

        #then iterate through cleaned_strings and insert into each tuple
        logging.info("insert: " + str(k))
        for count in range(len(cleaned_strings)):
            new_tup = (tuplist[tup_indices[count]][0], tuplist[tup_indices[count]][1], tuplist[tup_indices[count]][2], cleaned_strings[count])
            new_list.append(new_tup)
        
        k+=1
        return new_list


# In[ ]:


#apply remove_string_overlaps on each school, aka on each row of new_data
#since pages of a school will likely be similar to the other pages within that school own

def parse_df(old_list):
    
#     print("INSIDE PARSE_DF, list is : " + old_list)
    
    new_list = remove_string_overlaps(old_list)
    return new_list


# In[ ]:


#full_250_df['WEBTEXT'] = full_250_df['WEBTEXT'].fillna("0")
#full_250_df['WEBTEXT'] = full_250_df['WEBTEXT'].apply(ast.literal_eval) don't need

next_df['CMO_WEBTEXT'] = next_df['CMO_WEBTEXT'].fillna("[]")
next_df['CMO_WEBTEXT'] = next_df['CMO_WEBTEXT'].apply(ast.literal_eval) 

# lookup = pd.read_csv(folder_prefix + "nowdata/parsing/lookup.csv", sep="\t", low_memory=False, encoding="utf-8") #fix lookup csv

# unseen_df = lookup[lookup['OVERLAPS_REMOVED'] == 0]
# unseen_list = list(set(unseen_df['NCESSCH'].tolist()))

# new_data = full_250_df[full_250_df['NCESSCH'].isin(unseen_list)]

arr_of_dfs = np.array_split(next_df, next_df.shape[0]) #gives you a list of dataframes, each dataframe has 1 rows


# In[ ]:


def chunk_assign(df_chunk): #Jaren chunk by chunk 
    
#     print("TYPE of DF CHUNK in chunk_assign : " + str(type(df_chunk)))
    
    df_chunk['CMO_WEBTEXT'] = df_chunk['CMO_WEBTEXT'].apply(parse_df)
    
    #print("TYPE of DF_CHUNK : " + str(type(df_chunk)))
   
    
    
    return df_chunk


# In[ ]:


global num
num = 0
numcpus = len(os.sched_getaffinity(0)) # Detect and assign number of available CPUs
#p = mp.Pool(numcpus)


# indices_arr = np.arange(len(arr_of_dfs))
# ind_subarrays = np.array_split(indices_arr, ten_count) #np.array_split gives you a list

for chunk in arr_of_dfs:
#     print("TYPE of arr_of_dfs[0] : " + str(type(arr_of_dfs[0])))
    with mp.Pool(processes = numcpus) as p:
        chunk_arr = np.array_split(chunk, chunk.shape[0]) #split chunk into an array of dfs,
        #p.map takes in an iterable and applies function on each element of array
        #now chunk_arr is an array of 10 dataframes (each of which was a row previously in chunk)
        list_of_dfs = p.map(chunk_assign, chunk_arr)
        temp_df = pd.concat(list_of_dfs, ignore_index = True) 
    #     for i in temp_df:
    #         print("TYPE of i in TEMP_DF : " + str(type(i)))
    #     print("TYPE of TEMP_DF : " + str(type(temp_df)))
        num +=1
        if  num == 1: # Save first slice to new file (overwriting if needed)
            #print("NUM  is 1 : " + str(num))
            logging.info("df chunk # " + str(num))
            temp_df.to_csv(folder_prefix + "nowdata/parsing/CMO_WEBTEXT_2.csv", mode="w", index=False, header=temp_df.columns.values, sep="\t", encoding="utf-8")


        else:
            #print("NUM is actually : " + str(num))
            logging.info("df chunk # " + str(num))
            temp_df.to_csv(folder_prefix + "nowdata/parsing/CMO_WEBTEXT_2.csv", mode="a", index=False, header=False, sep="\t", encoding="utf-8")



# for sub_array in ind_subarrays:
#     arr_dfs_chunk = arr_of_dfs[sub_array[0]: sub_array[len(sub_array) -1] +1]
#     temp_df = p.map(chunk_assign, arr_dfs_chunk)
    
#     if  num == 1: # Save first slice to new file (overwriting if needed)
#         temp_df.to_csv(folder_prefix + "nowdata/parsing/parsed_df_7.csv", mode="w", index=False, header=temp_df.columns.values, sep="\t", encoding="utf-8")
        
#     else:
#         temp_df.to_csv(folder_prefix + "nowdata/parsing/parsed_df_7.csv", mode="a", index=False, header=False, sep="\t", encoding="utf-8")

    

p.close()

