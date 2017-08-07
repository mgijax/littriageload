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
#	LOG_DIAG
#	LOG_ERROR
#	LOG_CUR
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
#	1) initialize() : initiailze 
#	2) level1SanityChecks() : run Level 1 Sanity Checks
#	3) setPrimaryKeys() : setting global primary keys
#	4) processPDFs() : iterate thru PDF files/run level2 and level3 sanity checks
#	5) bcpFiles() : load BCP files into database
#       6) closeFiles() : close files
#
# lec	06/20/2017
#       - TR12250/Lit Triage
#
###########################################################################

import sys 
import os
import re
import db
import mgi_utils
import loadlib
import PdfParser
import PubMedAgent
import Pdfpath

DEBUG = 1
bcpon = 1

# for setting where the litparser lives (see PdfParser)
litparser = ''
# for setting the PubMedAgent
pma = ''

diag = ''
diagFile = ''
curator = ''
curatorFile = ''
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
dataFile = ''
dataFileName = ''

accTable = 'ACC_Accession'
refTable = 'BIB_Refs'
statusTable = 'BIB_Workflow_Status'
dataTable = 'BIB_Workflow_Data'

accKey = 0
refKey = 0
statusKey = 0
mgiKey = 0

mgiTypeKey = 1
mgiPrefix = 'MGI:'
referenceTypeKey = 31576687 	# Peer Reviewed Article
notRoutedKey = 31576669		# Not Routed
supplementalNotChecked = 31576677	# not checked
isReviewArticle = 0
isDiscard = 0
isCurrent = 1
hasPDF = 1
isPrivate = 0
isPreferred = 1

# list of workflow groups
workflowGroupList = []

# moving input/pdfs to master dir/pdfs
mvPDFtoMasterDir = {}

loaddate = loadlib.loaddate

#
# userDict = {'user' : [pdf1, pdf2]}
# {'cms': ['28069793_ag.pdf', '28069794_ag.pdf', '28069795_ag.pdf']}
userDict = {}

#
# doiidByUser = {('user name', 'pdf file') : doiid}
# {('cms, '28069793_ag.pdf'): ['xxxxx']}
doiidByUser = {}
#
# doiidById = {'doiid' : 'pdf file'}
doiidById = {}

# linkOut : link URL
linkOut = '<A HREF="%s">%s</A>' 

# error logs for level1, level2, level3

allErrors = 'Start Log: ' + mgi_utils.date() + '<BR><BR>\n\n'
level1errorStart = '**********<BR>\nLiterature Triage Level 1 Errors : parse DOI ID from PDF files<BR><BR>\n'
level2errorStart = '**********<BR>\nLiterature Triage Level 2 Errors : parse PubMed IDs from PubMed API<BR><BR>\n\n'
level3errorStart = '**********<BR>\nLiterature Triage Level 3 Errors : check MGI for errors<BR><BR>\n\n'

level1error1 = '' 
level1error2 = ''
level1error3 = ''

level2error1 = '' 
level2error2 = ''
level2error3 = ''
level2error4 = ''

level3error1 = '' 
level3error2 = ''
level3error3 = ''

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
        curatorFile.write('\n\nEnd Date/Time: %s\n' % (mgi_utils.date()))
        diagFile.close()
        errorFile.close()
        curatorFile.close()
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
    global curator, curatorFile
    global inputDir, outputDir
    global masterDir, failDir
    global bcpScript
    global accFileName, refFileName, statusFileName, dataFileName
    global accFile, refFile, statusFile, dataFile
    global pma
    global workflowGroupList

    litparser = os.getenv('LITPARSER')
    diag = os.getenv('LOG_DIAG')
    error = os.getenv('LOG_ERROR')
    curator = os.getenv('LOG_CUR')
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

    if not curator:
        exit(1, 'Environment variable not set: LOG_CUR')

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
        curatorFile = open(curator, 'a')
    except:
        exist(1,  'Cannot open curator log file: ' + curatorFile)

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
        dataFileName = outputDir + '/' + dataTable + '.bcp'
    except:
        exit(1, 'Cannot create file: ' + outputDir + '/' + dataTable + '.bcp')

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

    try:
        dataFile = open(dataFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % dataFileName)

    # initialized PdfParser.py
    try:
        PdfParser.setLitParserDir(litparser)
    except:
        exit(1, 'PdfParser.setLitParserDir(litparser) failed')

    try:
        pma = PubMedAgent.PubMedAgentMedline()
    except:
        exit(1, 'PubMedAgent.PubMedAgentMedline() failed')

    results = db.sql('select _Term_key from VOC_Term where _Vocab_key = 127', 'auto')
    for r in results:
        workflowGroupList.append(r['_Term_key'])

    return 0


#
# Purpose: Close files.
# Returns: 0
#
def closeFiles():

    if diagFile:
        diagFile.close()
    if errorFile:
        errorFile.close()
    if curatorFile:
        curatorFile.close()
    if refFile:
        refFile.close()
    if statusFile:
        statusFile.close()
    if dataFile:
        dataFile.close()
    if accFile:
        accFile.close()

    return 0

#
# Purpose:  sets global primary key variables
# Returns: 0
#
def setPrimaryKeys():
    global accKey, refKey, statusKey, mgiKey

    results = db.sql('select max(_Refs_key) + 1 as maxKey from BIB_Refs', 'auto')
    refKey = results[0]['maxKey']

    results = db.sql('select max(_Assoc_key) + 1 as maxKey from BIB_Workflow_Status', 'auto')
    statusKey = results[0]['maxKey']

    results = db.sql('select max(_Accession_key) + 1 as maxKey from ACC_Accession', 'auto')
    accKey = results[0]['maxKey']

    results = db.sql('select max(maxNumericPart) + 1 as maxKey from ACC_AccessionMax where prefixPart = \'MGI:\'', 'auto')
    mgiKey = results[0]['maxKey']

    return 0

#
# Purpose: BCPs the data into the database
# Returns: 0
#
def bcpFiles():

    diagFile.write('\nstart: bcpFiles()\n')

    # close bcp files
    if refFile:
        refFile.close()
    if statusFile:
        statusFile.close()
    if dataFile:
        dataFile.close()
    if accFile:
        accFile.close()

    bcpI = '%s %s %s' % (bcpScript, db.get_sqlServer(), db.get_sqlDatabase())
    bcpII = '"|" "\\n" mgd'

    bcp1 = '%s %s "/" %s %s' % (bcpI, refTable, refFileName, bcpII)
    bcp2 = '%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII)
    bcp3 = '%s %s "/" %s %s' % (bcpI, dataTable, dataFileName, bcpII)
    bcp4 = '%s %s "/" %s %s' % (bcpI, accTable, accFileName, bcpII)

    db.commit()

    #
    # copy bcp files into database
    # if any bcp fails, return (0)
    # this means the input files will remain
    # and can be used in the next running of the load
    #
    diagFile.write('\nstart: copy bcp files into database\n')
    for bcpCmd in [bcp1, bcp2, bcp3, bcp4]:
        diagFile.write('%s\n' % bcpCmd)
        diagFile.flush()
	if bcpon:
	    try:
                os.system(bcpCmd)
	    except:
	        diagFile.write('bcpFiles(): failed : os.system()\n')
		return 0
    diagFile.write('\nend: copy bcp files into database\n')
    diagFile.flush()

    #
    # move PDF from inputdir to master directory
    # using numeric part of MGI id
    #
    # /data/loads/mgi/littriageload/input/cms/28473584_g.pdf is moved to: 
    #	-> /data/littriage/5904000/5904760.pdf
    #
    diagFile.write('\nstart: move oldPDF to newPDF\n')
    for oldPDF in mvPDFtoMasterDir:
	for newFileDir, newPDF in mvPDFtoMasterDir[oldPDF]:
	    diagFile.write(oldPDF + '\t' +  newFileDir + '\t' + newPDF + '\n')
	    if bcpon:
	        try:
		    os.makedirs(newFileDir)
		except:
		    pass
		try:
                    os.rename(oldPDF, newFileDir + '/' + newPDF)
		except:
	            diagFile.write('bcpFiles(): failed : os.rename(' + oldPDF + ',' + newFileDir + '/' + newPDF + '\n')
		    return 0
    diagFile.write('\nend: move oldPDF to newPDF\n')

    diagFile.write('\nend: bcpFiles()\n')
    diagFile.flush()

    return 0

#
# Purpose: Level 1 Sanity Checks : parse DOI ID from PDF files
# Returns: 0
#
# if successful, pdf stays in the 'input' directory
# if failed, pdf is moved to the 'failed' directory
#
# 1: not in PDF format
# 2: cannot extract/find DOI ID
# 3: duplicate published refs (same DOI ID)
#
def level1SanityChecks():
    global userDict
    global doiidByUser, doiidById
    global allErrors, level1error1, level1error2, level1error3

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
		os.rename(os.path.join(pdfPath, origFile), os.path.join(pdfPath, pdfFile))

	    #
	    # file in input directory does not end with pdf
	    #
	    if not pdfFile.lower().endswith('.pdf'):
		if DEBUG:
	            diagFile.write('file in input directory does not end with pdf: %s %s\n') % (userPath, pdfFile)
	        continue

	    #
	    # userDict of all pdfFiles by user
	    #
	    if userPath not in userDict:
	        userDict[userPath] = []
	    if pdfFile not in userDict[userPath]:
	        userDict[userPath].append(pdfFile)

    #
    # iterate thru userDict
    #
    for userPath in userDict:

	pdfPath = os.path.join(inputDir, userPath)
	failPath = os.path.join(failDir, userPath)

	#
	# for each pdfFile
	# if doi id can be found, store in doiidByUser dictionary
	# else, report error, move pdf to failed directory
	#
	for pdfFile in userDict[userPath]:

	    pdf = PdfParser.PdfParser(os.path.join(pdfPath, pdfFile))
	    doiid = ''

	    try:
                doiid = pdf.getFirstDoiID()
		doitext = pdf.getText()

		if (doiid):
		    if doiid not in doiidById:
		        doiidById[doiid] = []
		        doiidById[doiid].append(pdfFile)
	                if DEBUG:
			    diagFile.write('pdf.getFirstDoiID() : successful : %s%s : %s\n' % (pdfPath, pdfFile, doiid))
			    diagFile.flush()
		    else:
		        level1error3 = level1error3 + doiid + '<BR>\n' + linkOut % (failPath + pdfFile, failPath + pdfFile) + \
				'<BR>\nduplicate of ' + \
				linkOut % (os.path.join(pdfPath, doiidById[doiid][0]), os.path.join(pdfPath, doiidById[doiid][0])) + '<BR><BR>\n\n'
			os.rename(os.path.join(pdfPath, pdfFile), os.path.join(failPath, pdfFile))
			continue
		else:
		    level1error2 = level1error2 + linkOut % (failPath + pdfFile, failPath + pdfFile) + '<BR>\n'
		    os.rename(os.path.join(pdfPath, pdfFile), os.path.join(failPath, pdfFile))
		    continue
            except:
		level1error1 = level1error1 + linkOut % (failPath + pdfFile, failPath + pdfFile) + '<BR>\n'
		os.rename(os.path.join(pdfPath, pdfFile), os.path.join(failPath, pdfFile))
		continue

	    # store by User as well 
	    if (userPath, doiid) not in doiidByUser:
	        doiidByUser[(userPath, doiid)] = []
	        doiidByUser[(userPath, doiid)].append((pdfFile, doitext))

    #
    # write out level1 errors to both error log and curator log
    #
    level1error1 = '<B>1: not in PDF format</B><BR><BR>\n\n' + level1error1 + '<BR>\n\n'
    level1error2 = '<B>2: cannot extract/find DOI ID</B><BR><BR>\n\n' + level1error2 + '<BR>\n\n'
    level1error3 = '<B>3: duplicate published refs (same DOI ID)</B><BR><BR>\n\n' + level1error3 + '<BR>\n\n'
    allErrors = allErrors + level1errorStart + level1error1 + level1error2 + level1error3

    return 0

#
# Purpose: Level 2 Sanity Checks : parse PubMed IDs from PubMed API
# Returns: ref object if successful, else returns 1
#
#  1: DOI ID maps to multiple pubmed IDs
#  2: DOI ID not found in pubmed
#  3: error getting medline record
#  4: missing data from required field for DOI ID
#
def level2SanityChecks(userPath, doiID, pdfFile, pdfPath, failPath):
    global level2error1, level2error2, level2error3, level2error4

    if DEBUG:
        diagFile.write('level2SanityChecks: %s, %s, %s\n' % (userPath, doiID, pdfFile))

    # mapping of doiID to pubmedID, return list of references
    mapping = pma.getReferences([doiID])
    refList = mapping[doiID]

    #  1: DOI ID maps to multiple pubmed IDs
    if len(refList) > 1:
        for ref in refList:
	    level2error1 = level2error1 + doiID + ', ' + str(ref.getPubMedID()) + '<BR>\n' + \
	    	linkOut % (failPath + pdfFile, failPath + pdfFile) + '<BR><BR>\n\n'
	return 1

    #  2: DOI ID not found in pubmed
    for ref in refList:
        if ref == None:
	    level2error2 = level2error2 + doiID + '<BR>\n' + \
		    linkOut % (failPath + pdfFile, failPath + pdfFile) + '<BR><BR>\n\n'
	    return 1

    # at this point there is only one reference
    for ref in refList:

	pubmedID = ref.getPubMedID()

        #  3: error getting medline record
	if not ref.isValid():
	    level2error3 = level2error3 + doiID + ', ' + pubmedID + '<BR>\n' + \
	    	linkOut % (failPath + pdfFile, failPath + pdfFile) + '<BR><BR>\n\n'
	    return 1

	# check for required NLM fields
	else:

	    # PMID - PubMed unique identifier
	    # TI - title of article
	    # TA - journal
	    # DP - date
	    # YR - year

	    requiredDict = {}
	    missingList = []

	    requiredDict['pmId'] = ref.getPubMedID()
	    requiredDict['title'] = ref.getTitle()
	    requiredDict['journal'] = ref.getJournal()
	    requiredDict['date'] = ref.getDate()
	    requiredDict['year'] = ref.getYear()

            #  4: missing data from required field for DOI ID
	    for reqLabel in requiredDict:
		if requiredDict[reqLabel] == None:
		    missingList.append(reqLabel)
	    if len(missingList):
	        level2error4 = level2error4 + doiID + ', ' + pubmedID + '<BR>\n' + \
			linkOut % (failPath + pdfFile, failPath + pdfFile) + '<BR><BR>\n\n'
		return 1

    # if successful, return 'ref' object, else return 1, continue

    return ref

#
# Purpose: Level 3 Sanity Checks : check MGI for errors
# Returns: returns 0 if successful, 1 if errors are found
#
#  1: input PubMed ID or DOI ID exists in MGI
#  2: PubMed or DOI ID associated with different MGI references
#  3a: input PubMed ID exists in MGI but missing DOI ID -> add DOI ID in MGI
#  3b: input DOI ID exists in MGI but missing PubMed ID -> add PubMed ID in MGI
#
def level3SanityChecks(userPath, doiID, pdfFile, pdfPath, failPath, ref):
    global level3error1, level3error2, level3error3

    # return 0 : will add as new reference
    # return 1/2 : will skip/move to 'failed'
    # return 3 : will add new Accession ids

    if DEBUG:
        diagFile.write('level3SanityChecks: %s, %s, %s\n' % (userPath, doiID, pdfFile))

    pubmedID = ref.getPubMedID()

    results = db.sql('''
	select _Refs_key, mgiID, pubmedID, doiID from BIB_Citation_Cache where pubmedID = '%s' or doiID = '%s'
    	''' % (pubmedID, doiID), 'auto')

    #  2: input PubMed ID or DOI ID associated with different MGI references
    if len(results) > 1:
        diagFile.write('2: input PubMed ID or DOI ID associated with different MGI references: ' \
		+ doiID + ',' + pubmedID + '\n')
	level3error2 = level3error2 + doiID + ', ' + pubmedID + '<BR>\n' + \
	    	linkOut % (failPath + pdfFile, failPath + pdfFile) + '<BR><BR>\n\n'
	os.rename(os.path.join(pdfPath, pdfFile), os.path.join(failPath, pdfFile))
	return 2, results

    elif len(results) == 1:

        #  2: input PubMed ID or DOI ID associated with different MGI references
	if results[0]['pubmedID'] != None and results[0]['doiID'] != None:
	    if (pubmedID == results[0]['pubmedID'] and doiID != results[0]['doiID']) or \
	       (pubmedID != results[0]['pubmedID'] and doiID == results[0]['doiID']):
                diagFile.write('2: input PubMed ID or DOI ID associated with different MGI references: ' \
		        + doiID + ',' + pubmedID + '\n')
	        level3error2 = level3error2 + doiID + ', ' + pubmedID + '<BR>\n' + \
	    	        linkOut % (failPath + pdfFile, failPath + pdfFile) + '<BR><BR>\n\n'
		os.rename(os.path.join(pdfPath, pdfFile), os.path.join(failPath, pdfFile))
	        return 2, results

        #  3: input PubMed ID exists in MGI but missing DOI ID -> add DOI ID in MGI
	if results[0]['pubmedID'] == None:
	    diagFile.write('3: pubmedID is missing in MGI: ' + doiID + ',' + pubmedID + '\n')
	    level3error3 = level3error3 + doiID + ', ' + pubmedID + ' : adding PubMed ID<BR>\n' + \
	    	linkOut % (failPath + pdfFile, failPath + pdfFile) + '<BR><BR>\n\n'
	    os.rename(os.path.join(pdfPath, pdfFile), os.path.join(failPath, pdfFile))
	    return 3, results

        #  3: input DOI ID exists in MGI but missing PubMed ID -> add PubMed ID in MGI
	if results[0]['doiID'] == None:
	    diagFile.write('3: doiid is missing in MGI:' + doiID + ',' + pubmedID + '\n')
	    level3error3 = level3error3 + doiID + ', ' + pubmedID + ' : adding DOI ID<BR>\n' + \
	    	linkOut % (failPath + pdfFile, failPath + pdfFile) + '<BR><BR>\n\n'
	    os.rename(os.path.join(pdfPath, pdfFile), os.path.join(failPath, pdfFile))
	    return 3, results

        #  1: input PubMed ID or DOI ID exists in MGI
	diagFile.write('1: input PubMed ID or DOI ID exists in MGI: ' + doiID + ',' + pubmedID + '\n')
	level3error1 = level3error1 + doiID + ', ' + str(ref.getPubMedID()) + '<BR>\n' + \
	    	linkOut % (failPath + pdfFile, failPath + pdfFile) + '<BR><BR>\n\n'
	os.rename(os.path.join(pdfPath, pdfFile), os.path.join(failPath, pdfFile))
        return 1, results

    else:
        return 0, results

#
# Purpose: Process/Iterate thru PDFs
# Returns: 0
#
def processPDFs():
    global allErrors
    global level2error1, level2error2, level2error3, level2error4
    global level3error1, level3error2, level3error3
    global accKey, refKey, statusKey, mgiKey
    global mvPDFtoMasterDir

    #
    # assumes the level1SanityChecks have passed
    #
    # for all rows in doiidByUser
    #	get info from pubmed API
    #   generate BCP file
    #   track pdf -> MGI numeric ####
    #

    if DEBUG:
        diagFile.write('\nprocessPDFs()\n')

    # doiidByUser = {('user name', 'doiid') : ('pdffile', 'doitext')}

    for key in doiidByUser:

	if DEBUG:
            diagFile.write('\ndoiidByUser: %s\n' % (str(key)))

	pdfFile = doiidByUser[key][0][0]
	extractedText = doiidByUser[key][0][1]
	userPath = key[0]
	doiID = key[1]
        pdfPath = os.path.join(inputDir, userPath)
        failPath = os.path.join(failDir, userPath)

	#
	# level2SanityChecks()
	# parse PubMed IDs from PubMed API
	#
	pubmedRef = level2SanityChecks(userPath, doiID, pdfFile, pdfPath, failPath)

	if pubmedRef == 1:
	   if DEBUG:
	       diagFile.write('level2SanityChecks() : failed : %s, %s, %s, %s\n' % (doiID, userPath, pdfFile, str(pubmedRef)))
	   os.rename(os.path.join(pdfPath, pdfFile), os.path.join(failPath, pdfFile))
           continue

	pubmedID = pubmedRef.getPubMedID()

	if DEBUG:
	    diagFile.write('level2SanityChecks() : successful : %s, %s, %s, %s\n' % (doiID, userPath, pdfFile, pubmedID))

	#
	# level3SanityChecks()
	# check MGI for errors
	#
        # return 0 : will add as new reference
        # return 1/2 : will skip/move to 'failed'
        # return 3 : will add new Accession ids
	#
	rc, mgdRef = level3SanityChecks(userPath, doiID, pdfFile, pdfPath, failPath, pubmedRef)

	if rc == 1 or rc == 2:
	    if DEBUG:
                diagFile.write('level3SanityChecks() : failed : %s, %s, %s, %s\n' \
			% (doiID, userPath, pdfFile, pubmedID))
	    continue

	#
	# add accession ids to existing MGI reference
	#
	elif rc == 3:

            diagFile.write('level3SanityChecks() : successful : add PubMed ID or DOI ID : %s, %s, %s, %s, %s\n' \
	    	% (doiID, userPath, pdfFile, pubmedID, str(mgdRef)))

	    # add pubmedID or doiId
	    userKey = loadlib.verifyUser(userPath, 0, diagFile)
	    objectKey = mgdRef[0]['_Refs_key']

	    if mgdRef[0]['pubmedID'] == None:
	        accID = pubmedID
		prefixPart = ''
		numericPart = accID
		logicalDBKey = 29
	    else:
	        accID = doiID
		prefixPart = accID
		numericPart = ''
		logicalDBKey = 65

	    accFile.write('%s|%s|%s|%s|%s|%d|%d|0|1|%s|%s|%s|%s\n' \
		% (accKey, accID, prefixPart, numericPart, logicalDBKey, objectKey, mgiTypeKey, \
		   userKey, userKey, loaddate, loaddate))

	    accKey = accKey + 1

	#
	# add new MGI reference
	#
	elif rc == 0:
            diagFile.write('level3SanityChecks() : successful : add new : %s, %s, %s, %s\n' \
	    	% (doiID, userPath, pdfFile, pubmedID))

	    # add pubmedID or doiId
	    userKey = loadlib.verifyUser(userPath, 0, diagFile)
	    logicalDBKey = 1

	    #
	    # bib_refs
	    #
	    refFile.write('%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
		% (refKey, referenceTypeKey, 
		   pubmedRef.getAuthors(), \
		   pubmedRef.getPrimaryAuthor(), \
		   pubmedRef.getTitle(), \
		   pubmedRef.getJournal(), \
		   pubmedRef.getVolume(), \
		   pubmedRef.getIssue(), \
		   pubmedRef.getDate(), \
		   pubmedRef.getYear(), \
		   pubmedRef.getPages(), \
		   pubmedRef.getAbstract(), \
		   isReviewArticle, \
		   isDiscard, \
		   userKey, userKey, loaddate, loaddate))

	    #
	    # bib_workflow_status
	    # 1 row per Group
	    #
	    for groupKey in workflowGroupList:
	        statusFile.write('%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
		   % (statusKey, refKey, groupKey, notRoutedKey, isCurrent, \
		      userKey, userKey, loaddate, loaddate))
                statusKey = statusKey + 1

	    #
	    # bib_workflow_data
	    # remove non-ascii characters
	    #
	    # remove non-ascii
	    # carriage returns, etc.
	    #
	    extractedText = re.sub(r'[^\x00-\x7F]','', extractedText)
	    extractedText = extractedText.replace('\\', '\\\\')
	    extractedText = extractedText.replace('\n', '\\n')
	    extractedText = extractedText.replace('\r', '\\r')
	    extractedText = extractedText.replace('|', '\\n')
	    dataFile.write('%s|%s|%s||%s|%s|%s|%s|%s\n' \
	    	% (refKey, hasPDF, supplementalNotChecked, extractedText, userKey, userKey, loaddate, loaddate))
            dataKey = statusKey + 1

	    # MGI:xxxx
	    #
	    mgiID = mgiPrefix + str(mgiKey)
	    accFile.write('%s|%s|%s|%s|%s|%d|%d|%s|%s|%s|%s|%s|%s\n' \
		% (accKey, mgiID, mgiPrefix, mgiKey, logicalDBKey, refKey, mgiTypeKey, \
		   isPrivate, isPreferred, userKey, userKey, loaddate, loaddate))
	    accKey = accKey + 1
	    
	    #
	    # pubmedID
	    #
	    accID = pubmedID
	    prefixPart = ''
	    numericPart = accID
	    logicalDBKey = 29

	    accFile.write('%s|%s|%s|%s|%s|%d|%d|%s|%s|%s|%s|%s|%s\n' \
		% (accKey, accID, prefixPart, numericPart, logicalDBKey, refKey, mgiTypeKey, \
		   isPrivate, isPreferred, userKey, userKey, loaddate, loaddate))
	    accKey = accKey + 1

	    #
	    # doiID
	    #
	    accID = doiID
	    prefixPart = accID
	    numericPart = ''
	    logicalDBKey = 65

	    accFile.write('%s|%s|%s|%s|%s|%d|%d|%s|%s|%s|%s|%s|%s\n' \
		% (accKey, accID, prefixPart, numericPart, logicalDBKey, refKey, mgiTypeKey, \
		   isPrivate, isPreferred, userKey, userKey, loaddate, loaddate))
	    accKey = accKey + 1

	    # store dictionary : move pdf file from inputDir to masterPath
	    newPath = Pdfpath.getPdfpath(masterDir, mgiID)
	    mvPDFtoMasterDir[pdfPath + pdfFile] = []
	    mvPDFtoMasterDir[pdfPath + pdfFile].append((newPath,str(mgiKey) + '.pdf'))

	    refKey = refKey + 1
	    mgiKey = mgiKey + 1

    #
    # write out level2 errors to both error log and curator log
    #
    level2error1 = '<B>1: DOI ID maps to multiple pubmed IDs</B><BR><BR>\n\n' + level2error1 + '<BR>\n\n'
    level2error2 = '<B>2: DOI ID not found in pubmed</B><BR><BR>\n\n' + level2error2 + '<BR>\n\n'
    level2error3 = '<B>3: error getting medline record</B><BR><BR>\n\n' + level2error3 + '<BR>\n\n'
    level2error4 = '<B>4: missing data from required field for DOI ID</B><BR><BR>\n\n' + level2error4 + '<BR>\n\n'
    allErrors = allErrors + level2errorStart + level2error1 + level2error2 + level2error3 + level2error4

    level3error1 = '<B>1: PubMed ID/DOI ID exists in MGI</B><BR><BR>\n\n' + \
    	level3error1 + '<BR>\n\n'
    level3error2 = '<B>2: PubMed ID/DOI ID is associated with different MGI references</B><BR><BR>\n\n' + \
    	level3error2 + '<BR>\n\n'
    level3error3 = '<B>3: missing PubMed ID or DOI ID in MGD -> will add PubMed ID or DOI ID to MGI</B><BR><BR>\n\n' + \
    	level3error3 + '<BR>\n\n'
    allErrors = allErrors + level3errorStart + level3error1 + level3error2 + level3error3

    # copy all errors to error log, remove html and copy to curator log
    errorFile.write(allErrors)
    curatorFile.write(re.sub('<.*?>', '', allErrors))

    diagFile.flush()

    return 0

#
#  MAIN
#

if initialize() != 0:
    sys.exit(1)

if level1SanityChecks() != 0:
    closeFiles()
    sys.exit(1)

if setPrimaryKeys() != 0:
    sys.exit(1)

if processPDFs() != 0:
    closeFiles()
    sys.exit(1)

if bcpFiles() != 0:
    sys.exit(1)

closeFiles()
sys.exit(0)

