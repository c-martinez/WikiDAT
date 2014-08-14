'''
Created on Jul 29, 2014

@author: carlosm
'''

import mwclient
import pickle
import os

__DATAFILE__ = 'usernames.pkl'

def __getAllUsers__(cat):
    '''
    Produce a list of user & subcategories found under the given Category object
    
    Parameters:
    cat      A mwclient.Category object
    
    Returns
    users    A list of users registered in the given category
    cats     A list of categories registered in the given category
    '''
    users = []
    cats = []
    for user in cat:
        if user.namespace==2:    # isUser
            users.append(user)
        elif user.namespace==14: # isCategory
            cats.append(user)
        # We just ignore other namespaces
    return users, cats

def __fetchUsersCategory__(cats, log, visited):
    '''
    Fetch all the users on the given seed categories (and their subcategories)
    
    Parameters:
    cats       seed categories
    log        logging element to keep record of subcategories of each category
    visited    SET of previouly visited categories
    
    Returns:
    allUsers
    '''
    allUsers = []
    while len(cats)>0:
        cat = cats.pop()
        if cat.name in visited:
            print '   SKIPPING ',cat.name,' - previously visited'
        else:
            print 'Fetching ',cat.name,'...'

            catUsers, subCats = __getAllUsers__(cat)
            cats = cats + subCats
            if len(subCats)>0:
                for subCat in subCats:
                    log.append((cat.name,subCat.name))

            log.append((cat.name,len(catUsers)))
            allUsers = allUsers + catUsers
            visited.add(cat.name)
    return allUsers

def __getcountrySeeds__():
    '''
    Return seed country categories (manually defined). These seeds correspond to the 
    subcategories listed on Wikipedians_by_location category, for highest contributing countries.
    
    Wikipedians_by_location category found here:
    http://en.wikipedia.org/wiki/Category:Wikipedians_by_location
    
    Highest contributing countries found here:
    http://stats.wikimedia.org/wikimedia/squids/SquidReportPageEditsPerLanguageBreakdown.htm
    '''
    __countrySeeds__ = {}
    __countrySeeds__["US"] = [ "Wikipedians in U.S.A.", "Wikipedians in United States", "Wikipedians in United States Of America", "Wikipedians in United States of America", "Wikipedians in US", "Wikipedians in USA", "Wikipedians in the United States", "Wikipedians in the United States of America" ]
    __countrySeeds__["UK"] = [ "Wikipedians in UK", "Wikipedians in United Kingdom", "Wikipedians in the United Kingdom", "Wikipedians in the UK" ]
    __countrySeeds__["IN"] = [ "Wikipedians in India", "Wikipedians in the India", "Wikipedians in the Republic of INDIA" ]
    __countrySeeds__["CA"] = [ "Wikipedians in Canada" ]
    __countrySeeds__["AU"] = [ "Wikipedians in the Australia", "Wikipedians in AUSTRALIA", "Wikipedians in Australia" ]
    __countrySeeds__["PH"] = [ "Wikipedians in the Philippines", "Wikipedians in Philippines" ]
    __countrySeeds__["DE"] = [ "Wikipedians in Germany" ]
    __countrySeeds__["BR"] = [ "Wikipedians in Brazil" ]
    __countrySeeds__["IT"] = [ "Wikipedians in Italy" ]
    __countrySeeds__["IE"] = [ "Wikipedians in Ireland", "Wikipedians in the Republic of Ireland" ]
    __countrySeeds__["PK"] = [ "Wikipedians in Pakistan", "Wikipedians in the Pakistan" ]
    __countrySeeds__["FR"] = [ "Wikipedians in France" ]
    __countrySeeds__["MY"] = [ "Wikipedians in Malaysia" ]
    __countrySeeds__["NL"] = [ "Wikipedians in Netherlands", "Wikipedians in the Netherlands" ]
    __countrySeeds__["ID"] = [ "Wikipedians in Indonesia" ]
    __countrySeeds__["CN"] = [ "Wikipedians in China", "Wikipedians in Mainland China", "Wikipedians in the People's Republic of China", "Wikipedians in the People's Republic of China/", "Wikipedians in the Republic of China" ]
    __countrySeeds__["NZ"] = [ "Wikipedians in New Zealand" ]
    __countrySeeds__["ES"] = [ "Wikipedians in Spain", "Wikipedians in in Spain" ]
    __countrySeeds__["IR"] = [ "Wikipedians in the Iran", "Wikipedians in Iran" ]
    __countrySeeds__["MX"] = [ "Wikipedians in Mexico" ]
    __countrySeeds__["SE"] = [ "Wikipedians in Sweden" ]
    __countrySeeds__["RU"] = [ "Wikipedians in Russia" ]
    __countrySeeds__["GR"] = [ "Wikipedians in Greece" ]
    __countrySeeds__["TR"] = [ "Wikipedians in Turkey" ]
    return __countrySeeds__

def __fetchData__():
    '''
    Use Wikimedia API to download a list of users from the given seed categories 
    for selected countries. User country resolution will be limited to the selected countries 
    and users in each country will be limited to users in one of the seed categories 
    (or its subcategories) given for each country.
    
    Downloaded data is preserved to __DATAFILE__ pickle file
    '''
    # TODO: we should provide a way of selecting which WIKI to use
    __wiki__ = mwclient.Site('en.wikipedia.org')

    __countrySeeds__ = __getCountrySeeds__()

    log = []      # Log records parent-child tuples
    users = {}
    visited = set()

    for country in __countrySeeds__:
        seeds = __countrySeeds__[country]
        cats = [ __wiki__.Categories[seed] for seed in seeds ]
        log = log + [ (country, seed) for seed in seeds ]
        users[country] = __fetchUsersCategory__(cats, log, visited)

    usernameSets = {}
    for country in users:
        usernameSets[country] = set()
        for user in users[country]:
            usernameSets[country].add(user.name)

    return usernameSets, log

def __loadData__():
    '''
    Load data from existing pickled __DATAFILE__
    '''
    path = os.path.dirname(__file__)
    dataFile = path + '/' + __DATAFILE__
    usernameSets, log = pickle.load(open(dataFile, 'r'))
    return usernameSets, log

def getUserCountry(user):
    '''
    Search for the given username and return its country code.
            whe
    user    Wikipedia username.
    '''
    uUser = 'User:' + user
    for country in __usernameSets__:
        if uUser in __usernameSets__[country]:
            return country
    return None

# When the module is first loaded, pickled user names are read.
# If no pickle file exists, a fresh one is generated.
try:
    __usernameSets__, __log__ = __loadData__()
except:
    print 'Unable to find ' + __DATAFILE__ + ' -- new one will be created'
    __usernameSets__, __log__ = __fetchData__()

    print 'Preserving data to ' + __DATAFILE__ + '...'
    path = os.path.dirname(__file__)
    dataFile = path + '/' + __DATAFILE__
    pickle.dump((__usernameSets__, __log__), open(dataFile, 'w'))

if __name__ == '__main__':
    assert getUserCountry('Alaney2k')=='CA' # Random canadian user
