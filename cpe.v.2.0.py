#!/usr/bin/python
# -*- coding: utf-8 -*

import argparse
import os, re, time, sys
from bs4 import BeautifulSoup
import json
import progressbar as pb
import ConfigParser
import pymongo
from fuzzywuzzy import fuzz

reload(sys)
sys.setdefaultencoding('utf8')

VERBOSE = False

parser = argparse.ArgumentParser(
    description='Process some file.',
    epilog='comments > /dev/null'
)
parser.add_argument('--cpe', "-c", type=str, help='a dictionary downloaded')
parser.add_argument('--checkVENDOR', "-C", type=str, help='a set of words')
parser.add_argument('--checkPRODUCT', "-P", type=str, help='a set of words')
parser.add_argument('--createJSON', "-j", action='store_true', help='Create a file only')
parser.add_argument('--loadJSON', "-l", action='store_true', help='Read a file')
parser.add_argument('--listVENDOR', "-n", action='store_true', help='Show distinct vendor field')
parser.add_argument('--listPRODUCT', "-p", action='store_true', help='Show distinct product field')
parser.add_argument('--listCPE', "-e", action='store_true', help='Show distinct CPE')
parser.add_argument('--operativesystem', "-o", action='store_true', help='Show distinct CPE')
parser.add_argument('--application', "-a", action='store_true', help='Show distinct CPE')
parser.add_argument('--hardware', "-w", action='store_true', help='Show distinct CPE')
parser.add_argument('--banner', "-b", type=str, help='String to analyze, cr0hn\'s Method')
parser.add_argument('--name', "-m", type=str, help='String to analyze')
parser.add_argument('--nameCHCK', "-k", action='store_true', help='String to analyze')
parser.add_argument('--checkWTF', "-wtf", type=str, help='String to analyze')

parser.add_argument('--verbose', "-v", action='store_true', help='Verbose')

args = parser.parse_args()

defaultConfig = "config/config.ini"
Config = ConfigParser.ConfigParser()
Config.read(defaultConfig)


# ---------------------------------------------------

def ReadCPE(fcpe):
    timestart = time.time()
    FILE = BeautifulSoup(open(fcpe, "r"), "xml")
    timeend = time.time()
    print ("[*] Elapsed time in load {0}:[{1} sg]").format(fcpe, timeend - timestart)
    widgets = ['[*] Loading data from [{0}]: '.format(fcpe), pb.Percentage(), ' ',
               pb.Bar(marker=pb.RotatingMarker()), ' ', pb.ETA()]
    timer = pb.ProgressBar(widgets=widgets, maxval=1000000).start()
    cont = 0
    ALLDATA = []
    for i in FILE.find_all("cpe-item"):
        cont = cont + 1
        timer.update(cont)
        type = re.split(":", re.split("/", str(i['name']))[1])[0]
        title = re.split('<', re.split('>', str(i.title))[1])[0]
        cpe = re.split(':', i['name'])
        vendor = cpe[2]
        product = cpe[3]
        cpe = {
            'vendor': vendor,
            'product': product
        }
        data = {
            '_id': cont,
            'title': title,
            'name': str(i['name']),
            'cpe': cpe,
            'type': type
        }
        if VERBOSE:
            print json.dumps(data)
        ALLDATA.append(data)
    timer.finish()
    return (ALLDATA)


# ---------------------------------------------------

def insertCPEDATA(src, fcpe):
    host = Config.get('MONGO', 'ip')
    port = int(Config.get('MONGO', 'port'))
    client = pymongo.MongoClient(host, port)
    cpeddbb = client.LucienInventary
    widgets = ['Loading database with data from [{0}]: '.format(src), pb.Percentage(), ' ',
               pb.Bar(marker=pb.RotatingMarker()), ' ', pb.ETA()]
    timer = pb.ProgressBar(widgets=widgets, maxval=1000000).start()
    cont = 0
    for i in fcpe:
        cont += 1
        timer.update(cont)
        cpeddbb.CPE.insert(i)
    timer.finish()


# ---------------------------------------------------

def insertLOADCPE(src, fcpe):
    host = Config.get('MONGO', 'ip')
    port = int(Config.get('MONGO', 'port'))
    print ("[*] Connection to {0}:{1}").format(host, port)
    client = pymongo.MongoClient(host, port)
    print ("[*] Connected !!")
    cpeddbb = client.LucienInventory
    timestart = time.time()
    cpeddbb.CPE.insert_many(ALLDATA).inserted_ids

    cpeddbb.CPE.create_index([('title', pymongo.TEXT)], name='title', default_language='english')
    timeend = time.time()
    print ("[*] Elapsed time in load:[{0} sg]").format(timeend - timestart)
    print ("[*] Insertion done !!!")


# ---------------------------------------------------

def createJSONCPE(fcpe, dst):
    print ("Writing {0} with CPE data").format(dst)
    fd = open(dst, 'w')
    fd.write(json.dumps(fcpe))
    fd.close()
    print ("File writed")


# ---------------------------------------------------

def ShowDISTINCTdata(field):
    host = Config.get('MONGO', 'ip')
    port = int(Config.get('MONGO', 'port'))
    print ("[*] Connection to {0}:{1}").format(host, port)
    client = pymongo.MongoClient(host, port)
    print ("[*] Connected !!")
    cpeddbb = client.LucienInventory
    timestart = time.time()
    data = cpeddbb.CPE.distinct(field)
    timeend = time.time()
    print ("[*] Elapsed time getting {0}:[{1} sg]").format(field, timeend - timestart)
    print ("[*] Extraction done !!!")
    return data
# ---------------------------------------------------

def GetDataWithName (field):
    host = Config.get('MONGO', 'ip')
    port = int(Config.get('MONGO', 'port'))
    print ("[*] Connection to {0}:{1}").format(host, port)
    client = pymongo.MongoClient(host, port)
    print ("[*] Connected !!")
    cpeddbb = client.LucienInventory
    timestart = time.time()
    data = cpeddbb.CPE.find({ "$text": { "$search": field } },{"title": 1, "name": 1, "_id": 0} )
    aux = {}
    for i in data:
        aux.update({i['name']: i['title']})
    timeend = time.time()
    print ("[*] Elapsed time getting {0}:[{1} sg]").format(field, timeend - timestart)
    print ("[*] Extraction done !!!")
    return aux


# ---------------------------------------------------

def ShowCPEdata(field):
    host = Config.get('MONGO', 'ip')
    port = int(Config.get('MONGO', 'port'))
    print ("[*] Connection to {0}:{1}").format(host, port)
    client = pymongo.MongoClient(host, port)
    print ("[*] Connected !!")
    cpeddbb = client.LucienInventory
    timestart = time.time()
    data = list(cpeddbb.CPE.find({"type": field}, {"name": 1, "_id": 0}))
    aux = []
    for i in data:
        aux.append((i.values())[0])
    timeend = time.time()
    print ("[*] Elapsed time getting {0}:[{1} sg]").format(field, timeend - timestart)
    print ("[*] Extraction done !!!")
    return aux


# ---------------------------------------------------

def getElements():
    host = Config.get('MONGO', 'ip')
    port = int(Config.get('MONGO', 'port'))
    print ("[*] Connection to {0}:{1}").format(host, port)
    client = pymongo.MongoClient(host, port)
    print ("[*] Connected !!")
    cpeddbb = client.LucienInventory
    timestart = time.time()
    data = list(cpeddbb.CPE.find({'type': 'a'}, {'name': 1, 'title': 1, '_id': 0}))
    aux = {}
    for i in data:
        aux.update({i['name']: i['title']})

    timeend = time.time()
    print ("[*] Elapsed time getting {0}:[{1} sg]").format('Elements', timeend - timestart)
    print ("[*] Extraction done !!!")
    return aux


# ---------------------------------------------------

def analyzeWord(word, rdata, first):
    from fuzzywuzzy import fuzz
    result = []
    find = False
    value = 0
    for auxword in rdata:
        value = fuzz.ratio(word, auxword)
        if value == 100:
            find = True
            result.append((auxword, value, 0))
            break
    if not find and first:
        if len(word.split(" ")) > 1:
            result.extend(analyzeWord(word.replace(" ", ""), rdata, False))
        else:
            result.append((word, 0, 0))
    elif not find:
        result.append((word, 0, 0))
    return result


# ---------------------------------------------------

def analyzeValues(rdata, adata):
    for name in re.split("\n", adata):
        if name.isalpha():
            result = analyzeWord(name.lower(), rdata, True)
            Ffind = lambda (x, y, z): y > 1 or z > 1
            find = Ffind(result[0])
            print "{0}\t{1}\t{2}".format(name, result[0][0], find)


# ---------------------------------------------------

def printall(ALLDATA):
    for i in (ALLDATA):
        print i.encode("ascii")

# ---------------------------------------------------

def anotherSearch ( field, data, results_number):
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process
    aux={}
    result = []
    mR=4
    mP=2
    mS=4
    for k in data:
        value_ratio = fuzz.ratio(field, data[k])
        value_part = fuzz.partial_ratio(field, data[k])
        value_sort = fuzz.token_sort_ratio(field, data[k])
        aux[k] = int((value_part*mP + value_ratio*mR + value_sort*mS) / (mR+mP+mS))
    sorted_results = sorted(aux.iteritems(), key=lambda (k, v): v, reverse=True)
    results_number = results_number if len(sorted_results) >= results_number else len(sorted_results)
    for x, y in sorted_results[:results_number]:  # By value
        result.append((y, x))

    return result

# ---------------------------------------------------

def search_cpe( field, chck ):
    timestart = time.time()
    data= GetDataWithName(field)
    if not chck:
        for k in data:
            print "{0}\t{1}".format(data[k],k)
    else:
        dataAUX = anotherSearch ( field, data, 3)
        print "   |----"
        print "   | String searched : {0}".format(field)
        print "   |----"
        for prob, cpe in dataAUX:
            #(prob,value)=re.split(':',prob)
            print "   |----"
            print "   | CPE: %s" % cpe
            print "   | Title: %s" % data[cpe]
            print "   | Probability: %s%%" % prob
            #print "   | Value: %s%%" % value
            print "   |____"
            print
    timeend = time.time()
    print ("[*] Elapsed time analyzing {0}:[{1} sg]").format('Elements', timeend - timestart)
    print ("[*] analysis done !!!")
# ----------------------------------------------------------------------

def analyzeValues (file):
    timestart = time.time()
    for name in re.split("\n", file):
        if name.isalnum():
            data = GetDataWithName( name )
            result = anotherSearch ( name, data, 3)
            print "   |----"
            print "   | String searched : {0}".format(name)
            print "   |----"
            for prob, cpe in result:
                print "   |----"
                print "   | CPE: %s" % cpe
                print "   | Title: %s" % data[cpe]
                print "   | Probability: %s%%" % prob
                print "   |____"
                print
    timeend = time.time()
    print ("[*] Elapsed time analyzing {0}:[{1} sg]").format('Elements', timeend - timestart)
    print ("[*] analysis done !!!")
# ----------------------------------------------------------------------
def fsplit(text):
    return set(_fsplit(text))


# ----------------------------------------------------------------------

def _fsplit(text):
    splitters = [" ", "/", "-", "..", ",", ";"]

    if not any([x in text for x in splitters]):
        return [text]
    else:
        results = []
        for spliter in splitters:
            if spliter in text:
                for sp in text.split(spliter):
                    results.extend(_fsplit(sp))
    return results

# ----------------------------------------------------------------------

def search_cpe_cr0hn(search_term, results_number=1):
    # https://github.com/cr0hn/info2cpe
    # Algo está mal :-(
    terms = fsplit(search_term)
    acronyms = []
    print search_term
    list_items = getElements()
    # {type: 'a'}, {name: 1, title: 1, _id: 0}
    for x in search_term.split(" "):
        if x.isupper():
            tmp_acronyms = []
            for x1 in x:
                tmp_acronyms.append("([%s][a-z0-9]+)[\s]*" % x1)
            acronyms.append(re.compile("".join(tmp_acronyms)))
            # Filters for false positives
    filters = [
        re.compile("(^[0-9\.]+$)")  # To detect expression like: 1.0.0
    ]
    partial_results1 = []
    partial_results1_append = partial_results1.append
    for k, x in list_items.iteritems():
        # Only unicode strings
        try:
            str(x)
        except UnicodeError:
            continue

        # Any coincidence?
        if any(w in x.lower() for w in terms):
            partial_results1_append((k, x, False))

        # Search in CPE
        # if any(w in k.lower() for w in terms):
        #    partial_results1_append((k, x, False))

        # There is an acronym?
        if any(acronym.search(x) is not None for acronym in acronyms):
            partial_results1_append((k, x, True))

    # Apply token_set_ratio
    partial_results2 = {}

    # k = CPE (str)
    # x = CPE description (str)
    # is_acronym = Bool
    for k, x, is_acronym in partial_results1:
        r = fuzz.partial_token_set_ratio(search_term, x, force_ascii=True)

        # Is false positive?
        if any(fil.search(x) is not None for fil in filters):
            continue

        # More weight if there is an acronym
        if is_acronym:
            r *= 1.25
            # Fix Valuer
            r = r if r <= 100 else 100

        partial_results2[k.encode("ascii")] = int(r)

        if results_number == 1 and r == 100:
            break

    result = []
    # Transform and get only the first N elements

    sorted_results = sorted(partial_results2.iteritems(), key=lambda (k, v): v, reverse=True)
    results_number = results_number if len(sorted_results) >= results_number else len(sorted_results)
    for x, y in sorted_results[:results_number]:  # By value
        result.append((y, x, list_items[x]))

    return result


# ---------------------------------------------------

if __name__ == '__main__':
    ALLDATA = ""
    if args.verbose:
        VERBOSE = True
    print
    if args.cpe:
        if not os.path.exists(args.cpe):
            print ("[*] [*]  {0} file not found").format(args.cpe)
            exit(0)
        else:
            ALLDATA = ReadCPE(args.cpe)

            if args.createJSON:
                SRC = Config.get('MONGO', 'jsonfile')
                createJSONCPE(ALLDATA, SRC)
            else:
                # insertCPEDATA( args.cpe, ALLDATA )
                insertLOADCPE(args.cpe, ALLDATA)
    elif args.loadJSON:
        SRC = Config.get('MONGO', 'jsonfile')
        if not os.path.exists(SRC):
            print ("[*] [*] {0} file not found")
            exit(0)
        else:
            fd = open(SRC, 'r')
            ALLDATA = json.loads(fd.read())
            fd.close()
            insertLOADCPE(SRC, ALLDATA)
    elif args.listVENDOR:
        ALLDATA = ShowDISTINCTdata("cpe.vendor")
        printall(ALLDATA)
    elif args.listPRODUCT:
        ALLDATA = ShowDISTINCTdata("cpe.product")
        printall(ALLDATA)
    elif args.listCPE:
        if not (args.hardware or args.application or args.operativesystem):
            ALLDATA = ShowDISTINCTdata("name")
        else:
            if args.hardware:
                aux = "h"
            elif args.operativesystem:
                aux = "o"
            else:
                aux = "a"
            ALLDATA = ShowCPEdata(aux)
        printall(ALLDATA)
    elif args.checkVENDOR:
        if not os.path.exists(args.checkVENDOR):
            print ("[*] [*]  {0} file not found").format(args.checkVENDOR)
            exit(0)
        else:
            vendor = ShowDISTINCTdata("cpe.vendor")
            df = open(args.checkVENDOR)
            svendor = df.read()
            df.close()
            analyzeValues(vendor, svendor)
    elif args.checkPRODUCT:
        if not os.path.exists(args.checkPRODUCT):
            print ("[*] [*]  {0} file not found").format(args.checkPRODUCT)
            exit(0)
        else:
            product = ShowDISTINCTdata("cpe.product")
            df = open(args.checkPRODUCT)
            sproduct = df.read()
            df.close()
            analyzeValues(product, sproduct)
    elif args.banner:
        start_time = time.time()
        results = search_cpe_cr0hn(args.name, 3)
        stop_time = time.time()

        # Display results
        print "[*] Analysis time: %s" % (stop_time - start_time)
        print "[*] Results:\n"

        for prob, cpe, name in results:
            print "   |----"
            print "   | CPE: %s" % cpe
            print "   | Name: %s" % name
            print "   | Probability: %s%%" % prob
            print "   |____"
            print
    elif args.name:
        results = search_cpe(args.name, args.nameCHCK)
    elif args.checkWTF:
        if not os.path.exists(args.checkWTF):
            print ("[*] [*]  {0} file not found").format(args.checkWTF)
            exit(0)
        else:
            df = open(args.checkWTF)
            sproduct = df.read()
            df.close()
            analyzeValues(sproduct)
    print "eof\n"