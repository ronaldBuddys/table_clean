'''
Created on Oct 23, 2017

@author: ronaldmaceachern

modules for methods to clean dirty .csv  using a set of rules
'''


import re
import os
import numpy as np
import pandas as pd

from difflib import SequenceMatcher


def makeRowDf( x, desc_name = '', cols = None):
    '''a wrapper function to make it neater to make a row table for column summary
    '''
    ncol = len(cols)
    return pd.DataFrame( np.array([desc_name] + x).reshape(1,ncol), columns = cols)

def checkIfColLikeRow(df, n = 5):
    
    cols = list(df.columns)
    
    #increment down a few rows
    out = []
    for i in np.arange(n):
        #extract a row and convert to str
        rw = np.array([ str(x) for x in df.iloc[i,:].values])
        
        #see how similar to columns
        sim = np.array([ SequenceMatcher(None, rw[i], cols[i]).ratio() for i in np.arange(df.shape[1])])

        out += [sim.reshape(1, len(sim))]
    
    #stack the results
    out = np.concatenate(out, axis = 0)

    #average over the rows
    out = np.mean(out, axis =  0)
    
    return out


def checkIfColInFirstRow(df):
    '''
    check if columns are in first rows 
    '''
    res = None
    
    ## column fix -  could be a class
    ##rule1: check if first row belongs as column name
    r1 = df.iloc[0,:]
    #drop the NaN's
    r1 = r1.dropna()
    #check if non NaNs are strings
    #are they all?
    allStr = np.array([isinstance(x,str) for x in r1]).all()
    
    #if they're all str, combine with column  names - this is 
    if allStr:
        print('column names found in first row, putting into columns')
        cols = list(r1.index)
        oldCol = np.array(df.columns)
        newcol = df.columns[df.columns.isin(cols)] +'_' +r1.values
        oldCol[df.columns.isin(cols)] = newcol
        res = oldCol
        #drop row with bad values
        #df = df.drop(0)
        
    return res    
    
def checkForExpression(df, expression = '', return_bool = False):
    '''check each element to see if matches a regular expression 
        if return_bool is True return an array of bools (same size as df)
        other wise return percentages that matched
        if an element is null (according to pd.isnull()) False is given
        
    Example:
    --------
        expression for floats: "^\d+?\.\d+?$"
        expression for less than "<"
    '''
    #store results in an array
    out = []
    #increment over the columns
    for i in np.arange(df.shape[1]):   
        #extract column values
        x = df.iloc[:,i].values
        # if it's not null and expression is matched
        y = np.array([ False if pd.isnull(element) else not re.match(expression,element) is None for element in x ])
        
        #if return bool, return an array of bool
        if return_bool:
            out += [y.reshape(len(y), 1)]
        else:
            out += [y.mean()]
    if return_bool:
        out = np.concatenate(out, axis = 1)
    else:
        out = np.array(out)
        
    return out

def checkNanPerRow(df):
    out = []
    #increment over each row, count the number not null
    for i in np.arange(df.shape[0]):
        out += [np.array([ pd.isnull(x) for x in df.iloc[i,:].values]).sum()]
    return np.array(out)

def checkNanPerCol(df):
    out = []
    #increment over each row, count the number not null
    for i in np.arange(df.shape[1]):
        out += [np.array([ pd.isnull(x) for x in df.iloc[:,i].values]).sum()]
    return np.array(out)
    
if __name__ == "__main__":
    
    #TODO: need to number rules, provide a short description

    #read in system config    
    from config import *

    #directory to raw tables
    table_dir = base_dir + '/tables'
    
    #get the tables
    tabs = os.listdir(table_dir)
    
    #TODO: want to group tables by there name
    
    #get the names the come before the (last) underscore
    table_groups = np.unique(np.array([ re.sub('_.*', '', f) for f in tabs]))
    
    #for each table_group get the number (assumption of relation between subsequent tables)
    tab_nums = {}
    for tg in table_groups:
        tab_nums[tg] = np.sort(np.array([ int(re.sub('^.*_|.csv', '', t)) for t in tabs if bool(re.search(tg, t))]))
    
    
    result = []
    
    #start by reading in a table
    for t in tab_nums.keys():
        #increment over the pages
        for p in tab_nums[t]:
            
            #TODO: may want to keep track of the rules that were implemented
            
            print('working on: %s_%d.csv'%(t,p))
            #read in data
            df = pd.read_csv(table_dir + '/' + t + '_' + str(p) + '.csv')

            ##########
            ### Description on original table - by column
            ##########
            
            #Goals:
            #1) have attributes per column (which exactly?)
            #2) have attributes of entire table (which exactly?)

            #get the original columns
            orgCol = df.columns
            
            #get the dtypes (data types) of the data.frame
            dt = df.dtypes
            
            #check the number of NaNs per column
            numNan = [ 'NA' if dt[i] == 'object' else np.isnan(df.iloc[:,i].values).mean()  for i in np.arange(len(dt))]
            
            #create an empty data.frame (not really used - drop?)
            descDf = pd.DataFrame(columns = ['DESC'] + list(orgCol))
            
            #how similar are the first n rows to the column names
            simRowtoCol = checkIfColLikeRow(df, n = 5)
            
            #put column descriptions into a single row table and combine
            nn = makeRowDf( numNan, desc_name = 'percent_nans', cols = list(descDf.columns))
            dtyp = makeRowDf( list(dt), desc_name = 'data_type', cols = list(descDf.columns))
            simRow = makeRowDf( list(simRowtoCol), desc_name = 'data_similar_to_colname', cols = list(descDf.columns))
            
            #check if values can be turned into floats (returns a percent)
            perToFloat = checkForExpression(df, expression = "^\d+?\.\d+?$", return_bool = False)
            perToFloat= makeRowDf( list(perToFloat), desc_name = 'turn_to_float', cols = list(descDf.columns))
            
            #has '<' 
            hasLessThan = checkForExpression(df, expression = "<", return_bool = False)
            hasLessThan = makeRowDf( list(hasLessThan), desc_name = 'has_less_than', cols = list(descDf.columns))
            
            
            #combine descriptions
            desc = pd.concat([nn, dtyp, simRow, hasLessThan, perToFloat])
            
            
            #check column names - are any Unnamed? - then those should be reported to deal with later
            
            #######
            ## fixing column names
            #######
            
            ## Known issues: 
            #1) there may not be any column names
            #2) columns may also be partly in first row
            #3) columns may be entirely in first and second row
            #    if column is most float and the top one or two rows are str then combine them (to make column name)
            #4) check if numbers are in column names and there are repeating elemnts
            #    i.e F30.1, F30.2, F30.3 - or unnamed:0, unnamed:1, etc
            #5) combining two columns: if one column is mostly NaNs and the other one to either side 
            #    has values mostly for where the other has NaNs, then merge the two
            #6) if row is mostly NaN (ie. only has one value - drop?)
            
            ## first row goes with column     
            newCol = checkIfColInFirstRow(df)  
            
            
            #check the number NaNs per row
            nanPerRow = checkNanPerRow(df)
            
            #TODO: define a threshold here  - how many is too many (all but one or two?)
            tooManyNans = (nanPerRow >= (df.shape[1] - 1))
            if tooManyNans.any():
                #TODO: added to findings to a rule implemented table
                df = df.iloc[~tooManyNans, :]
            
            #check Nans per column
            nanPerCol = checkNanPerCol(df)
            
            tooManyNansC =  (nanPerCol >= (df.shape[0] - 3))
            
            #TODO: instead of dropping column may want to merge them
            if tooManyNansC.any():
                #TODO: add findings to a rule implemented table
                df = df.iloc[:, ~tooManyNansC]
            
            
            ##########
            ### check contents of table
            ##########
            
            ## check how many elements can be converted to floats are integers in each column
            
            
            ##less than symbols
            
            #check columns, are there <1 values? (or similar)
            #-if so replace 
            print('trying to get numbers')
            
            lth = checkForExpression(df, expression = "<", return_bool = True)
            if lth.any():
                ltNum = df.values[lth]
                #remove the less than, turn to float and divide by 2
                df.values[lth] = np.array([ float(re.sub('<', '', x)) / 2 for x in ltNum])
            
            
                        
            #check if given table is similar to the previous
            #-want to have criteria, how many columns with the same name
            #-can missing names be implied?


            ##########
            ### Summary of what's been changed in the column
            ##########
            
            
        
            ########
            
            #store results in a 
            res = {'table_name': t + '_' + str(p), 
                   'column_desc': desc, 
                   'cleaned_table': df}
            
            result += [res]
            
            