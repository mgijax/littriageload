#
# use this to test the pubmed agent and/or directlry to the eutils/api
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

for pubmedid in (30026924, 12136102):
    print(pubmedid)
    #pubMedRef = pma.getReferenceInfo(pubmedid)
    #if pubMedRef.getPubMedID() == None:
    #    time.sleep(5)
    #    pubMedRef = pma.getReferenceInfo(pubmedid)
    #    print("1", pubMedRef.getPubMedID(), pubMedRef.getTitle() ,pubMedRef.getJournal() ,pubMedRef.getDate() ,pubMedRef.getYear() ,pubMedRef.getPublicationType())
    #if pubMedRef.getPubMedID() == None:
    #    time.sleep(5)
    #    pubMedRef = pma.getReferenceInfo(pubmedid)
    #    print("2", pubMedRef.getPubMedID(), pubMedRef.getTitle() ,pubMedRef.getJournal() ,pubMedRef.getDate() ,pubMedRef.getYear() ,pubMedRef.getPublicationType())
    #if pubMedRef.getPubMedID() == None:
    #    time.sleep(5)
    #    pubMedRef = pma.getReferenceInfo(pubmedid)
    #    print("3", pubMedRef.getPubMedID(), pubMedRef.getTitle() ,pubMedRef.getJournal() ,pubMedRef.getDate() ,pubMedRef.getYear() ,pubMedRef.getPublicationType())
    #else:
    #    print(pubMedRef.getPubMedID(), pubMedRef.getTitle() ,pubMedRef.getJournal() ,pubMedRef.getDate() ,pubMedRef.getYear() ,pubMedRef.getPublicationType())
    #print()

    apicall = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=%s&retmode=text&rettype=medline&api_key=93420e6dcf419d7a62e18570657    2e08K" % (pubmedid)
    print(apicall)
    medLineRecord = gov.get(apicall)
    print('api call done')
    print(medLineRecord)

