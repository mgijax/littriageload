#
# use this to test the:
#   pubmed agent 
#   directly to the eutils/api
#
# usage:  
# edit pubmedids as needed
# $PYTHON testeutilsapi.py
#

import sys 
import os
import db
import PdfParser
import PubMedAgent
import Pdfpath
import HttpRequestGovernor
import time
gov = HttpRequestGovernor.HttpRequestGovernor(.5, 120, 7200, 172800)

db.setTrace()

pma = PubMedAgent.PubMedAgentMedline()

#pubmedids = ['38880789', '7734751', '7735680', '7735690', '7736054', '7736420', '7736432', '7736510', '7736652', '30026924']
pubmedids = [
'37842081',
'37946043',
'37961316',
'38124345',
'38143961',
'38169386',
'38187646',
'38346723',
'38419621',
'38622407',
'38661305',
'38813868',
'38849535',
'38915624',
'38957358'
]


for pid in pubmedids:
    print(pid)
    pubMedRef = pma.getReferenceInfo(pid)
    if pubMedRef.getPubMedID() == None:
        time.sleep(5)
        pubMedRef = pma.getReferenceInfo(pid)
        print("1", pubMedRef.getPubMedID(), pubMedRef.getTitle() ,pubMedRef.getJournal() ,pubMedRef.getDate() ,pubMedRef.getYear() ,pubMedRef.getPublicationType())
    #if pubMedRef.getPubMedID() == None:
    #    time.sleep(5)
    #    pubMedRef = pma.getReferenceInfo(pid)
    #    print("2", pubMedRef.getPubMedID(), pubMedRef.getTitle() ,pubMedRef.getJournal() ,pubMedRef.getDate() ,pubMedRef.getYear() ,pubMedRef.getPublicationType())
    #if pubMedRef.getPubMedID() == None:
    #    time.sleep(5)
    #    pubMedRef = pma.getReferenceInfo(pid)
    #    print("3", pubMedRef.getPubMedID(), pubMedRef.getTitle() ,pubMedRef.getJournal() ,pubMedRef.getDate() ,pubMedRef.getYear() ,pubMedRef.getPublicationType())
    else:
        print(pubMedRef.getPubMedID(), pubMedRef.getTitle() ,pubMedRef.getJournal() ,pubMedRef.getDate() ,pubMedRef.getYear() ,pubMedRef.getPublicationType())
    print()

    #apicall = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=%s&retmode=text&rettype=medline&api_key=93420e6dcf419d7a62e18570657    2e08K" % (pid)
    #print(apicall)
    #medLineRecord = gov.get(apicall)
    #print('api call done')
    #print(medLineRecord)

