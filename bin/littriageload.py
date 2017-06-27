#!/usr/local/bin/python
#
#  littriageload.py
###########################################################################
#
#  Purpose:
#
#      This script will process Lit Triage PDF files
#      for loading into BIB_Refs, BIB_Workflow_Status
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

error = ''
errorFile = ''

inputDir = ''
outputDir = ''

masterDir = ''
failDir = ''

bcpScript = ''

accFile = ''
accFileName = ''
refFile = ''
refFileName = ''
statusFile = ''
statusFileName = ''

accTable = 'ACC_Accession'
refTable = 'BIB_Refs'
statusTable = 'BIB_Workflow_Status'

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
# Purpose: prints error message and exits
# Return: sys.exit()
#
def exit(
    status,          # numeric exitstatus (integer)
    message = None   # exitmessage (string)
    ):

    if message is not None:
        sys.stderr.write('\n' + str(message) + '\n')

    try:
        diagFile.write('\n\nEnd Date/Time: %s\n' % (mgi_utils.date()))
        errorFile.write('\n\nEnd Date/Time: %s\n' % (mgi_utils.date()))
        diagFile.close()
        errorFile.close()
    except:
        pass

    db.useOneConnection(0)
    sys.exit(status)

#
# Purpose: Initialization
# Returns: 0
#
def initialize():
    global litparser
    global diag, diagFile
    global error, errorFile
    global inputDir, outputDir
    global masterDir, failDir
    global bcpScript
    global accFileName, refFileName, statusFileName
    global accFile, refFile, statusFile

    litparser = os.getenv('LITPARSER')
    diag = os.getenv('LOG_DIAG')
    error = os.getenv('LOG_ERROR')
    inputDir = os.getenv('INPUTDIR')
    outputDir = os.getenv('OUTPUTDIR')
    masterDir = os.getenv('MASTERTRIAGEDIR')
    failDir = os.getenv('FAILEDTRIAGEDIR')
    bcpScript = os.environ['PG_DBUTILS'] + '/bin/bcpin.csh'

    #
    # Make sure the required environment variables are set.
    #

    if not litparser:
        exit(1, 'Environment variable not set: LITPARSER')

    if not diag:
        exit(1, 'Environment variable not set: LOG_DIAG')

    if not error:
        exit(1, 'Environment variable not set: LOG_ERROR')

    if not inputDir:
        exit(1, 'Environment variable not set: INPUTDIR')

    if not outputDir:
        exit(1, 'Environment variable not set: OUTPUTDIR')

    if not masterDir:
        exit(1, 'Environment variable not set: MASTEREDTRIAGEDIR')

    if not failDir:
        exit(1, 'Environment variable not set: FAILEDTRIAGEDIR')

    if not bcpScript:
        exit(1, 'Environment variable not set: PG_DBUTILS')

    try:
        diagFile = open(diag, 'a')
    except:
        exist(1,  'Cannot open diagnostic log file: ' + diagFile)

    try:
        errorFile = open(error, 'w')
    except:
        exist(1,  'Cannot open error log file: ' + errorFile)

    try:
        accFileName = outputDir + '/' + accTable + '.bcp'
    except:
        exit(1, 'Cannot create file: ' + outputDir + '/' + accTable + '.bcp')

    try:
        refFileName = outputDir + '/' + refTable + '.bcp'
    except:
        exit(1, 'Cannot create file: ' + outputDir + '/' + refTable + '.bcp')

    try:
        statusFileName = outputDir + '/' + statusTable + '.bcp'
    except:
        exit(1, 'Cannot create file: ' + outputDir + '/' + statusTable + '.bcp')

    try:
        accFile = open(accFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % accFileName)

    try:
        refFile = open(refFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % refFileName)

    try:
        statusFile = open(statusFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % statusFileName)

    # initialized PdfParser.py
    try:
        PdfParser.setLitParserDir(litparser)
    except:
        exit(1, 'PdfParser.setLitParserDir(litparser) failed')

    return 0


#
# Purpose: Close files.
# Returns: 0
#
def closeFiles():

    diagFile.close()
    errorFile.close()
    accFile.close()
    refFile.close()
    statusFile.close()
    return 0

#
# Purpose:  sets global primary key variables
# Returns: 0
#
def setPrimaryKeys():

    global accKey, refKey, statusKey

    results = db.sql('select max(_Refs_key) + 1 as maxKey from BIB_Refs', 'auto')
    refKey = results[0]['maxKey']

    results = db.sql('select max(_Accession_key) + 1 as maxKey from ACC_Accession', 'auto')
    accKey = results[0]['maxKey']

    results = db.sql('select max(_Assoc_key) + 1 as maxKey from BIB_Workflow_Status', 'auto')
    statusKey = results[0]['maxKey']

    return 0

#
# Purpose: BCPs the data into the database
# Returns: 0
#
def bcpFiles():

    bcpdelim = "|" 

    # close bcp files
    if accFileName:
        accFileName.close()
    if refFileName:
        refFileName.close()
    if statusFileName:
        statusFileName.close()

    if DEBUG or not bcpon:
        return

    bcpI = '%s %s %s' % (bcpScript, db.get_sqlServer(), db.get_sqlDatabase())
    bcpII = '"|" "\\n" mgd'

    bcp1 = '%s %s "/" %s %s' % (bcpI, refTable, refFileName, bcpII)
    bcp2 = '%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII)

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

    errorFile.write('<H4>Literature Triage Level 1 Errors</H4>\n')
    errorFile.write('<H4>' + mgi_utils.date() + '</H4>\n')

    linkIt = '<A HREF="%s%s">%s%s</A><P>' 

    error1 = '' 
    error2 = ''
    error3 = ''

    # iterate thru input directory by user
    for userPath in os.listdir(inputDir):

	pdfPath = inputDir + '/' + userPath + '/'

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
	                if DEBUG:
			    diagFile.write('pdf.getFirstDoiID() : successful : %s%s : %s\n' % (pdfPath, pdfFile, doiid))
			    diagFile.flush()
		    else:
		        error3 = error3 + linkIt % (failPath, pdfFile, failPath, pdfFile)
			os.rename(pdfPath + pdfFile, failPath + pdfFile)
			continue
		else:
		    error2 = error2 + linkIt % (failPath, pdfFile, failPath, pdfFile)
		    os.rename(pdfPath + pdfFile, failPath + pdfFile)
            except:
		error1 = error1 + linkIt % (failPath, pdfFile, failPath, pdfFile)
		os.rename(pdfPath + pdfFile, failPath + pdfFile)
		continue

	    # store by User as well 
	    if (userPath, doiid) not in doiidByUser:
	        doiidByUser[(userPath, doiid)] = []
	        doiidByUser[(userPath, doiid)].append(pdfFile)

    errorFile.write('<H4>1: not in PDF format</H4>\n\n' + error1 + '\n\n')
    errorFile.write('<H4>2: cannot extract/find DOI ID</H4>\n\n' + error2 + '\n\n')
    errorFile.write('<H4>3: duplicate published refs (same DOI ID)</H4>\n\n' + error3 + '\n\n')

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

    for (userPath, doiid) in doiidByUser:
        print userPath, doiid

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

if level1SanityChecks() != 0:
    closeFiles()
    sys.exit(1)

#if setPrimaryKeys() != 0:
#    sys.exit(1)

#if processPDFs() != 0:
#    closeFiles()
#    sys.exit(1)

closeFiles()
sys.exit(0)

