#!/usr/bin/env python
import argparse
import os, re, time, sys
from bs4 import BeautifulSoup
import json
import progressbar as pb
import ConfigParser
import pymongo
from fuzzywuzzy import fuzz
import urllib2
import socket


reload(sys)
sys.setdefaultencoding('utf8')

VERBOSE = False

parser = argparse.ArgumentParser(
    description='Process some file.',
    epilog='comments > /dev/null'
)
parser.add_argument('--cve', "-v", type=str, help='a dictionary downloaded')
parser.add_argument('--url', "-u", type=str, help='year to download')

args = parser.parse_args()

defaultConfig = "config/config.ini"
Config = ConfigParser.ConfigParser()
Config.read(defaultConfig)


browserAgent={'User-Agent': 'None',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Charset': 'utf-8;q=0.7,*;q=0.3',
                    'Accept-Encoding': 'gzip',
                    'Accept-Language': 'en-US,en;q=0.8',
                    'Connection': 'keep-alive'}


# ---------------------------------------------------

def getPage (url, page, browserAgent):
    timeout = float(Config.get('CONFIG', 'TimeOut'))
    timestart = time.time()
    socket.setdefaulttimeout(timeout)
    req = urllib2.Request(url, headers=browserAgent)
    html=""
    try:
        response = urllib2.urlopen('https://example.com')
        print 'response headers: "%s"' % response.info()
        http=response.read()
    except urllib2.HTTPError as e:
        print "[!] Fail:[{}] !!!".format(e)
        return None
    except IOError, e:
        if hasattr(e, 'code'):  # HTTPError
            print '[!] http error code: ', e.code
        elif hasattr(e, 'reason'):  # URLError
            print "[!] can't connect, reason: ", e.reason
        else:
            raise
        return None
    fd = open(page, 'w')
    fd.write(html)
    fd.close()
    timeend = time.time()
    print ("[*] {1} downloaded from {2} :[{0} sg]").format(timeend - timestart, page, url )

# ---------------------------------------------------

def ReadCVE(cvefile):
    timestart = time.time()
    fd = open(cvefile, 'r')
    ALLDATA = json.loads(fd.read())
    fd.close()
    timeend = time.time()
    print ("[*] Elapsed time reading:[{0} sg]").format(timeend - timestart)
    return (ALLDATA)
# ---------------------------------------------------

def insertLOADCVE(ALLDATA):
    host = Config.get('MONGO', 'ip')
    port = int(Config.get('MONGO', 'port'))
    print ("[*] Connection to {0}:{1}").format(host, port)
    client = pymongo.MongoClient(host, port)
    print ("[*] Connected !!")
    cpeddbb = client.LucienInventory
    timestart = time.time()
    cpeddbb.CVE.insert_many(ALLDATA)
    #cpeddbb.CVE.create_index([('title', pymongo.TEXT)], name='title', default_language='english')
    timeend = time.time()
    print ("[*] Elapsed time in load:[{0} sg]").format(timeend - timestart)
    print ("[*] Insertion done !!!")

if args.cve:
    if not os.path.exists(args.cve):
        print ("[*] [*]  {0} file not found").format(args.cve)
        exit(0)
    else:
        ALLDATA = ReadCVE(args.cve)
        insertLOADCVE(ALLDATA['CVE_Items'])
elif args.url:
    if (args.url >= '2002' and args.url <= time.strftime("%Y")):
        #timestart = time.time()
        file="{0}nvdcve-1.0-{1}.json.zip".format(Config.get('CVE', 'path'), args.url)
        getPage ( Config.get('CVE', args.url), file, browserAgent )
        #timeend = time.time()
        #print ("[*] Elapsed time getting data :[{0} sg]").format(timeend - timestart)