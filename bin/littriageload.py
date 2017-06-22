#!/usr/local/bin/python
#
#  littriageload.py
###########################################################################
#
#  Purpose:
#
#      This script will process Lit Triage PDF files
#      for loading into BIB_Refs, etc. tables
#
#  Usage:
#
#      littriageload.py
#
#  Env Vars:
#
#      The following environment variables are set by the configuration
#      file that is sourced by the wrapper script:
#
#	LITPARSER
#	INPUTDIR
#	OUTPUTDIR
#	LOG_ERROR
#	MASTERTRIAGEDIR
#	FAILEDTRIAGEDIR
#	PG_DBUTILS
#
#  Inputs:
#
#	INPUTDIR=${FILEDIR}/input
#	there are subdirectories for each curator.
#	for example:
#		input/cms
#		input/csmith
#		input/terryh
#
#  Outputs:
#
#	OUTPUTDIR=${FILEDIR}/output : bcp files
#	MASTERTRIAGEDIR : master pdf files
#	FAILEDTRIAGEDIR : failed pdf files
#
#  Implementation:
#
#      This script will perform following steps:
#
#      1) Initialize variables.
#      2) Open files.
#      3) Read each PDF (input file)/sanity checks
#      4) If sanity check fails, send PDF to FAILEDTRIAGEDIR
#      5) If sanity check successful, create BCP files
#      6) Close files.
#
# lec	06/20/2017
#       - TR12250/Lit Triage
#
###########################################################################

import sys 
import os
import db
import mgi_utils
import PdfParser

DEBUG = 1

litparser = ''

errorLog = ''
errorLogFile = ''

inputDir = ''
outputDir = ''

masterDir = ''
failDir = ''

bcpScript = ''
bibrefsTable = 'BIB_Refs'
bibrefsFileName = ''


#
# userDict = {'user' : [pdf1, pdf2]}
# {'cms': ['28069793_ag.pdf', '28069794_ag.pdf', '28069795_ag.pdf']}
userDict = {}

#
# doiidByUser = {'pdf file' : doiid}
# {('cms, '28069793_ag.pdf'): ['xxxxx']}
doiidByUser = {}

#
# Purpose: Print Debugging statements
# Returns: 0
#
def debug(s):

    if DEBUG:
	print mgi_utils.date('%c')
    	print s

    return 0

#
# Purpose: Initialization
# Returns: 1 if file does not exist or is not readable, else 0
#
def initialize():
    global litparser
    global errorLog
    global inputDir, outputDir
    global masterDir, failDir
    global bcpScript
    global bibrefsFileName

    litparser = os.getenv('LITPARSER')
    errorLog = os.getenv('LOG_ERROR')
    inputDir = os.getenv('INPUTDIR')
    outputDir = os.getenv('OUTPUTDIR')
    masterDir = os.getenv('MASTERTRIAGEDIR')
    failDir = os.getenv('FAILEDTRIAGEDIR')
    bcpScript = os.environ['PG_DBUTILS'] + '/bin/bcpin.csh'

    rc = 0

    #
    # Make sure the required environment variables are set.
    #
    if not litparser:
        print 'Environment variable not set: LITPARSER'
        rc = 1

    #
    # Make sure the required environment variables are set.
    #
    if not errorLog:
        print 'Environment variable not set: LOG_ERROR'
        rc = 1

    #
    # Make sure the required environment variables are set.
    #
    if not inputDir:
        print 'Environment variable not set: INPUTDIR'
        rc = 1

    #
    # Make sure the required environment variables are set.
    #
    if not outputDir:
        print 'Environment variable not set: OUTPUTDIR'
        rc = 1

    #
    # Make sure the required environment variables are set.
    #
    if not masterDir:
        print 'Environment variable not set: MASTEREDTRIAGEDIR'
        rc = 1

    #
    # Make sure the required environment variables are set.
    #
    if not failDir:
        print 'Environment variable not set: FAILEDTRIAGEDIR'
        rc = 1

    #
    # Make sure the required environment variables are set.
    #
    if not bcpScript:
        print 'Environment variable not set: PG_DBUTILS'
        rc = 1

    if rc:
        return rc

    # must be initialized PdfParser.py
    PdfParser.setLitParserDir(litparser)

    # bcp files
    bibrefsFileName = outputDir + '/' + bibrefsTable + '.bcp'

    return rc


#
# Purpose: Open files.
# Returns: 1 if file does not exist or is not readable, else 0
#
def openFiles():
    global errorLogFile

    #
    # Open the error log file.
    #
    try:
        errorLogFile = open(errorLog, 'w')
    except:
        print 'Cannot open error log file: ' + errorLogFile
        return 1

    return 0


#
# Purpose: Close files.
# Returns: 1 if file does not exist or is not readable, else 0
#
def closeFiles():

    if errorLogFile:
        errorLogFile.close()

    return 0

#
# Purpose: BCPs the data into the database
# Returns: 0
#
def bcpFiles():

    bcpdelim = "|" 

    if DEBUG or not bcpon:
        return

    closeFiles()

    bcpI = '%s %s %s' % (bcpScript, db.get_sqlServer(), db.get_sqlDatabase())
    bcpII = '"|" "\\n" mgd'

    bcp1 = '%s %s "/" %s %s' % (bcpI, bibrefsTable, bibrefsFileName, bcpII)

    db.commit()

    for bcpCmd in [bcp1]:
        diagFile.write('%s\n' % bcpCmd)
        os.system(bcpCmd)

    return 0

#
# Purpose: Level 1 Sanity Checks
# Returns: 0
#
# 1) file does not end with pdf
# 2) not in PDF format
# 3) cannot extract/find DOI ID
# 4) duplicate published refs (same DOI ID)
#
def level1SanityChecks():
    global userDict
    global doiidByUser

    errorLogFile.write('Literature Triage Level 1 Errors\n')
    errorLogFile.write(mgi_utils.date())
    errorLogFile.write('\n\n')

    errorLogFile.write('Errors are reported here: %s\n\n' % (FAILEDTRIAGEDIR)
    
    errorLogFile.write('1:file does not end with pdf\n')
    errorLogFile.write('2:not in PDF format\n')
    errorLogFile.write('3:cannot extract/find DOI ID\n')
    errorLogFile.write('4:duplicate published refs (same DOI ID)\n')
    errorLogFile.write('\n##########\n\n')

    for userPath in os.listdir(inputDir):

        #if userPath != "lec":
	#    continue

	pdfPath = inputDir + '/' + userPath + '/'

	for pdfFile in os.listdir(pdfPath):

	    #
	    # remove spaces
	    # replace '.PDF' with '.pdf'
	    #

	    origFile = pdfFile

	    if pdfFile.find(' ') > 0 or pdfFile.endswith('.PDF'):
                pdfFile = pdfFile.replace(' ', '')
                pdfFile = pdfFile.replace('.PDF ', '.pdf')
		os.rename(pdfPath + origFile, pdfPath + pdfFile)

	    if not pdfFile.lower().endswith('.pdf'):
	        errorLogFile.write('1:file does not end with pdf : %s/%s\n' % (userPath, pdfFile))
	        continue

	    if userPath not in userDict:
	        userDict[userPath] = []
	    userDict[userPath].append(pdfFile)

    for userPath in userDict:

	#if userPath != "lec":
		#continue

	pdfPath = inputDir + '/' + userPath + '/'
	failPath = failDir + '/' + userPath + '/'

	for pdfFile in userDict[userPath]:

	    pdf = PdfParser.PdfParser(pdfPath + pdfFile)
	    doiid = ''

	    try:
                doiid = pdf.getFirstDoiID()

		if (doiid):
		    if (userPath, doiid) not in doiidByUser:
		        doiidByUser[(userPath, doiid)] = []
		        doiidByUser[(userPath, doiid)].append(pdfFile)
			debug('pdf.getFirstDoiID() : successful : %s%s\n' % (pdfPath, pdfFile))
		    else:
			errorLogFile.write('4:duplicate published refs (same DOI ID): %s, %s%s\n\n' \
				% (doiid, pdfPath, pdfFile))
			os.rename(pdfPath + pdfFile, failPath + pdfFile)
			continue
		else:
		    errorLogFile.write('3:cannot extract/find DOI ID: %s%s\n\n' % (pdfPath, pdfFile))
		    os.rename(pdfPath + pdfFile, failPath + pdfFile)
            except:
		errorLogFile.write('2:not in PDF format: %s%s\n\n' % (pdfPath, pdfFile))
		os.rename(pdfPath + pdfFile, failPath + pdfFile)
		continue

    return 0

#
# Purpose: Process/Iterate thru PDFs
# Returns: 0
#
def processPDFs():

    #
    # for all rows in doiidByUser
    #	get info from pubmed API
    #   generate BCP file
    #

    # load BCP files
    # bcpFiles()
    
    # move pdf files from inputDir to masterPath
    # masterPath = masterDir + '/' + userPath + '/'

    return 0

#
#  MAIN
#

if initialize() != 0:
    sys.exit(1)

if openFiles() != 0:
    sys.exit(1)

if level1SanityChecks() != 0:
    closeFiles()
    sys.exit(1)

#if processPDFs() != 0:
#    closeFiles()
#    sys.exit(1)

closeFiles()
sys.exit(0)
