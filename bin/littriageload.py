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
#	see wiki page:  sw:Littriageload for more information
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
#	there are subdirectories for each user
#	for example:
#		input/cms
#		input/csmith
#		input/terryh
#
#  Outputs:
#
#	OUTPUTDIR=${FILEDIR}/output : bcp files
#	MASTERTRIAGEDIR : master pdf files
#	FAILEDTRIAGEDIR : failed pdf files by user
#
#  Implementation:
#
#      This script will perform following steps:
#
#      1) initialize()
#      2) openFiles()
#      3) level1SanityChecks(): Iterate thru PDF directories and run sanity check
#      6) processPDFs():  Iterate thru PDFs that passed sanity check
#      7) closeFiles()
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
bcpon = 1

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
bibstatusTable = 'BIB_Workflow_Status'
bibstatusFileName = ''

#
# userDict = {'user' : [pdf1, pdf2]}
# {'cms': ['28069793_ag.pdf', '28069794_ag.pdf', '28069795_ag.pdf']}
userDict = {}

#
# doiidByUser = {('user name', 'pdf file') : doiid}
# {('cms, '28069793_ag.pdf'): ['xxxxx']}
doiidByUser = {}
#
# doiidById = {'pdf file' : doiid}
doiidById = {}

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
    global bibrefsFileName, bibstatusFileName

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

    if not errorLog:
        print 'Environment variable not set: LOG_ERROR'
        rc = 1

    if not inputDir:
        print 'Environment variable not set: INPUTDIR'
        rc = 1

    if not outputDir:
        print 'Environment variable not set: OUTPUTDIR'
        rc = 1

    if not masterDir:
        print 'Environment variable not set: MASTEREDTRIAGEDIR'
        rc = 1

    if not failDir:
        print 'Environment variable not set: FAILEDTRIAGEDIR'
        rc = 1

    if not bcpScript:
        print 'Environment variable not set: PG_DBUTILS'
        rc = 1

    # bcp files
    try:
        bibrefsFileName = outputDir + '/' + bibrefsTable + '.bcp'
    except:
        print 'Cannot create file: ' + outputDir + '/' + bibrefsTable + '.bcp'
        rc = 1

    try:
        bibstatusFileName = outputDir + '/' + bibstatusTable + '.bcp'
    except:
        print 'Cannot create file: ' + outputDir + '/' + bibstatusTable + '.bcp'
        rc = 1

    # initialized PdfParser.py
    try:
        PdfParser.setLitParserDir(litparser)
    except:
        print 'PdfParser.setLitParserDir(litparser) failed'
        rc = 1

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
# Returns: 0
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

    # close bcp files
    if bibrefsFileName:
        bibrefsFileName.close()
    if bibstatusFileName:
        bibstatusFileName.close()

    if DEBUG or not bcpon:
        return

    bcpI = '%s %s %s' % (bcpScript, db.get_sqlServer(), db.get_sqlDatabase())
    bcpII = '"|" "\\n" mgd'

    bcp1 = '%s %s "/" %s %s' % (bcpI, bibrefsTable, bibrefsFileName, bcpII)
    bcp2 = '%s %s "/" %s %s' % (bcpI, bibstatusTable, bibstatusFileName, bcpII)

    db.commit()

    for bcpCmd in [bcp1, bcp2]:
        diagFile.write('%s\n' % bcpCmd)
        os.system(bcpCmd)

    return 0

#
# Purpose: Level 1 Sanity Checks
# Returns: 0
#
def level1SanityChecks():
    global userDict
    global doiidByUser, doiidById

    errorLogFile.write('Literature Triage Level 1 Errors\n')
    errorLogFile.write(mgi_utils.date())
    errorLogFile.write('\n\n')
    errorLogFile.write('All PDFs have been moved to the %s directory of the given user' % (failDir))
    errorLogFile.write('\n\n')

    error1 = '' 
    error2 = ''
    error3 = ''

    # iterate thru input directory by user
    for userPath in os.listdir(inputDir):

	pdfPath = inputDir + '/' + userPath + '/'
	print inputDir + '/' + userPath + '/'
	print pdfPath

	for pdfFile in os.listdir(pdfPath):

	    #
	    # remove spaces
	    # rename '.PDF' with '.pdf'
	    #

	    origFile = pdfFile

	    if pdfFile.find(' ') > 0 or pdfFile.find('.PDF') > 0:
                pdfFile = pdfFile.replace(' ', '')
                pdfFile = pdfFile.replace('.PDF', '.pdf')
		os.rename(pdfPath + origFile, pdfPath + pdfFile)

	    #
	    # file in input directory does not end with pdf
	    #
	    if not pdfFile.lower().endswith('.pdf'):
	        diagFile.write('file in input directory does not end with pdf: %s/%s\n') % (userPath, pdfFile)
	        continue

	    #
	    # userDict of all pdfFiles by user
	    #
	    if userPath not in userDict:
	        userDict[userPath] = []
	    userDict[userPath].append(pdfFile)

    #
    # iterate thru userDict
    #
    for userPath in userDict:

	pdfPath = inputDir + '/' + userPath + '/'
	failPath = failDir + '/' + userPath + '/'

	#
	# for each pdfFile
	# if doi id can be found, store in doiidByUser dictionary
	# else, report error, move pdf to failed directory
	#
	for pdfFile in userDict[userPath]:

	    pdf = PdfParser.PdfParser(pdfPath + pdfFile)
	    doiid = ''

	    try:
                doiid = pdf.getFirstDoiID()

		if (doiid):
		    if doiid not in doiidById:
		        doiidById[doiid] = []
		        doiidById[doiid].append(pdfFile)
			debug('pdf.getFirstDoiID() : successful : %s%s : %s\n' % (pdfPath, pdfFile, doiid))
		    else:
			error3 = error3 + '%s, %s%s\n' % (doiid, failPath, pdfFile)
			os.rename(pdfPath + pdfFile, failPath + pdfFile)
			continue
		else:
		    error2 = error2 + '%s%s\n' % (failPath, pdfFile)
		    os.rename(pdfPath + pdfFile, failPath + pdfFile)
            except:
		error1 = error1 + '%s%s\n' % (failPath, pdfFile)
		os.rename(pdfPath + pdfFile, failPath + pdfFile)
		continue

	    # store by User as well 
	    if (userPath, doiid) not in doiidByUser:
	        doiidByUser[(userPath, doiid)] = []
	        doiidByUser[(userPath, doiid)].append(pdfFile)

    errorLogFile.write('1: not in PDF format\n\n' + error1 + '\n\n')
    errorLogFile.write('2: cannot extract/find DOI ID\n\n' + error2 + '\n\n')
    errorLogFile.write('3: duplicate published refs (same DOI ID)\n\n' + error3 + '\n\n')

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
    #   track pdf -> MGI numeric ####
    #

    # load BCP files
    # bcpFiles()
    
    # move pdf files from inputDir to masterPath, using new MGI numeric ####
    # masterPath = masterDir + '/' : determine path based on MGI numeric ####

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
