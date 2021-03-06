'''
Created on Jul 30, 2014

@author: carlosm
'''
from __future__ import division

import numpy as np
import wikidat.utils.ipresolver as ipr
import wikidat.utils.userresolver as usr

def countContributions(items, resolve):
    '''
    Returns the total number of contributions per country from the user list.
    
    users     A list of usernames
    
    Returns a dictionary of country codes where the value of each entry is 
    the number of contributions for that country. 
    '''
    contribs = {}
    for item in items:
        cc = resolve(item)
        if cc in contribs:
            contribs[cc] += 1
        else:
            contribs[cc] = 1
    return contribs

def filterNonBots(users, bots):
    '''
    Filter the given list of usernames to Bot users.
    
    Parameters:
    users       Original list of usernames
    bots        List of known Bots
    
    Return:
    nonBots     List of users which are not Bots.
    '''
    return [ user for user in users if not user in bots ]

def prepareData(ips, users, bots):
    '''
    Given a list of anonymous (IP) and registered user contributions
    build a list of contributions by country and the proportion 
    of contributions identified (via IP and via user info), for which 
    country is unknown and which can be ignored. Confidence on data 
    is the ratio of know / total data (after removing ignored data).
    
    Parameters:
    ips        List of IP contributions
    users      List of usernames
    bots       Set of known bots
    
    Returns:
    contribs   Dictionary of contributions by country code
    confidence Degree of confidence of known data.
    nIPs       Number of contributions known via IP
    nUsers     Number of contributions known via username
    nBots      Number of contributions ignored
    nUnknown   Number of contributions not known
    '''
    # Sanity check
    nrevs = (len(ips) + len(users))

    # Filter and count Bots
    nonBots = filterNonBots(users, bots)
    nBots = len(users) - len(nonBots)

    nUnknown = 0
    
    # Resolve IP's
    ipContribs = countContributions(ips, ipr.getCountryCode)
    if None in ipContribs:
        nUnknown += ipContribs[None]
        del ipContribs[None]
    nIPs = sum(ipContribs.values())

    # Resolve Usernames
    userContribs = countContributions(nonBots, usr.getUserCountry)
    if None in userContribs:
        nUnknown += userContribs[None]
        del userContribs[None]
    nUsers = sum(userContribs.values())

    # Sanity check
    assert nrevs == (nUnknown + nBots + nIPs + nUsers)

    contribs = {}
    for cc in np.unique(np.hstack([ ipContribs.keys(), userContribs.keys() ] )):
        contribs[cc] = 0
        contribs[cc] += ipContribs[cc] if cc in ipContribs else 0
        contribs[cc] += userContribs[cc] if cc in userContribs else 0

    # Sanity check
    assert (nIPs + nUsers) == sum(contribs.values())

    # How much confidence could we have on conclusions drawn from this data
    usedData = nIPs + nUsers + nUnknown
    confidence = (nIPs + nUsers) / usedData
    
    # Sanity check
    assert confidence>=0 and confidence<=1
    
    return contribs, confidence, nIPs, nUsers, nBots, nUnknown

def compareEdits(globalEdits, pageEdits):
    '''
    Compute how the number of edits performed by each country on an individual 
    page compares with the overall percentage of edits performed by each country
    to Wikipedia as a whole.
    
    For example, if US users perform 38% of the edits for the whole of Wikipedia, 
    it would be expected that for any given page, ~38% of the edits are from 
    US users. A higher number of edits could be considered as HIGHER_THAN_USUAL
    and likewise a lower number of edits as LOWER_THAN_USUAL.
      
    Parameters:
    globalEdits   Percentage of edits performed by each country in Wikipedia
    pageEdits     Number of edits performed by each country to the wikipedia
                  page under analysis.
    
    Return:
    A dictionary (containing all countries from globalEdits and pageEdits), 
    whose values are tuples of (global, page, relative) where global is the 
    percentage of edits from that country to the whole of Wikipedia; 
    page is the percentage of edits from that country to the Wikipedia 
    page under analysis and relative is the comparison between the two. 
    The comparison is performed by relativeInterest function.
    '''
    cmpEdits = {}
    normFact = sum(pageEdits.values())

    allCountries = set(globalEdits.keys()).union(pageEdits.keys())
    for country in allCountries:
        try:
            e = globalEdits[country]  # Expected percentage of edits
        except:
            e = 0
        try:
            a = pageEdits[country] / normFact   # Actual percentage of edits
        except:
            a = 0
        m = relativeInterest(e,a)
        cmpEdits[country] = (e,a,m)
    return cmpEdits

def relativeInterest(gEdit,pEdit):
    '''
    Given an expected (global) and actual (current page) percentages of 
    countributions from a specific country to Wikipedia, calculate the relative 
    intereste from that country on the topic of the page under analysis.
    
    This measure of relative interest is scaled in the interval [-1,1], 
    where negative numbers represent LOWER_THAN_USUAL and positive numbers 
    represent HIGHER_THAN_USUAL interest. This measure reaches 0 if the 
    contributions made to the current page match the global contributions 
    from the country. The measure grows linearly between [-1,0) and
    asymptotic between (0,1].

    Parameters:
    gEdit    Percentage of global edits from country in question.
    pEdit    Percentage of page edits from country in question.
    
    Return:
    The relative measure of interest expressed by a country on a given page.
    '''
    return (pEdit/gEdit-1) if pEdit<gEdit else (1-gEdit/pEdit)

def getDebugWiki(host='en.wikipedia.org'):
    '''
    If you want to trace the requests made by mwclient, use this method
    to create your site
    
    wiki = getDebugWiki(host='en.wikipedia.org')
    page = wiki.pages['Ice hockey']
    '''
    import mwclient
    import http
    
    class VerboseHTTPPool(http.HTTPPool):
        def post(self, host, path, headers=None, data=None):
            print 'Using MyPool'
            print ' > Host: ',host
            print ' > Path: ',path
            print ' > Head: ',headers
            print ' > Data: ',data
            return super(VerboseHTTPPool, self).post(host, path, headers, data)

    wiki = mwclient.Site(host=host, pool=VerboseHTTPPool())
    return wiki
