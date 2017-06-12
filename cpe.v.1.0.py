# -*- coding: utf-8 -*

import argparse
import os, re, time, sys
from bs4 import BeautifulSoup
import json
import progressbar as pb
import ConfigParser
import pymongo

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
            'cpe': cpe
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
def ShowCPEdata(field):
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
def analyzeWord(word, rdata, first):
    from fuzzywuzzy import fuzz

    for auxword in rdata:
        find = False
        value = fuzz.ratio(word, auxword)
        result = []
        value_part = fuzz.ratio(word, auxword)
        if value == 100:
            # print "[{0}]->[{1}]:{2}".format(word,auxword,value)
            find = True
            result.append((auxword, value, 0))
            break
        elif value_part == 100:
            # print "[{0}]->[{1}]:{2}".format(word, auxword, value_part                                         )
            find = True
            result.append((auxword, 0, value_part))
            break
        elif value > 50 or value_part > 50:
            result.append((auxword, value, value_part))
    if not find and first:
        if len(word.split(" ")) > 1:
            result.extend(analyzeWord(word.replace(" ", ""), rdata, False))
        else:
            result.append((word, 0, 0))
    elif not find:
        result.append((word, 0, 0))
    return result


def analyzeValues(rdata, adata):
    for name in re.split("\n", adata):
        if name.isalpha():
            result = analyzeWord(name.lower(), rdata, True)
            Ffind = lambda (x, y, z): y > 1 or z > 1
            find=Ffind(result[0])
            print "{0}->{1}:[{2}]".format(name, result[0][0],find)


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
        ALLDATA = ShowCPEdata("cpe.vendor")
        print ALLDATA
    elif args.listPRODUCT:
        ALLDATA = ShowCPEdata("cpe.product")
        print ALLDATA
    elif args.checkVENDOR:
        if not os.path.exists(args.checkVENDOR):
            print ("[*] [*]  {0} file not found").format(args.checkVENDOR)
            exit(0)
        else:
            vendor = ShowCPEdata("cpe.vendor")
            df = open(args.checkVENDOR)
            svendor = df.read()
            df.close()
            analyzeValues(vendor, svendor)
    elif args.checkPRODUCT:
        if not os.path.exists(args.checkPRODUCT):
            print ("[*] [*]  {0} file not found").format(args.checkPRODUCT)
            exit(0)
        else:
            product = ShowCPEdata("cpe.product")
            df = open(args.checkPRODUCT)
            sproduct = df.read()
            df.close()
            analyzeValues(product, sproduct)
    print "eof\n"
