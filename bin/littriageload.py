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
#	LOG_SQL
#	MASTERTRIAGEDIR
#	NEEDSREVIEWTRIAGEDIR
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
#	NEEDSREVIEWTRIAGEDIR : needs review pdf files by user
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
import shutil
import re
import db
import mgi_utils
import loadlib
import PdfParser
import PubMedAgent
import Pdfpath

#db.setTrace(True)
DEBUG = 1
bcpon = 1

# for setting where the litparser lives (see PdfParser)
litparser = ''
# for setting the PubMedAgent
pma = ''

# special processing for specific cases
userSupplement = 'littriage_create_supplement'
userPDF = 'littriage_update_pdf'
userGOA = 'littriage_goa'
userNLM = 'littriage_update_nlm' # not yet implemented

count_processPDFs = 0
count_userSupplement = 0
count_userPDF = 0
count_userGOA = 0
count_userNLM = 0
count_needsreview = 0

diag = ''
diagFile = ''
curator = ''
curatorFile = ''
error = ''
errorFile = ''
sqllog = ''
sqllogFile = ''

inputDir = ''
outputDir = ''

masterDir = ''
needsReviewDir = ''
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
jnumKey = 0

objDOI = 'doi'
mgiTypeKey = 1
mgiPrefix = 'MGI:'
referenceTypeKey = 31576687 	# Peer Reviewed Article
notRoutedKey = 31576669		# Not Routed
fullCodedKey = 31576674		# Full-coded
isReviewArticle = 0
isDiscard = 0
isCurrent = 1
hasPDF = 1
isPrivate = 0
isPreferred = 1

# bib_workflow_data._supplemental_key values
supplementalKey = 31576677	# Not checked
suppfoundKey = 31576675	        # Db found supplement
suppnotfoundKey = 31576676      # Db supplement not found

# list of workflow groups
workflowGroupList = []

# moving input/pdfs to master dir/pdfs
mvPDFtoMasterDir = {}

# delete SQL commands
deleteSQLAll = ''
updateSQLAll = ''

loaddate = loadlib.loaddate

#
# userDict = {'user' : [pdf1, pdf2]}
# {'cms': ['28069793_ag.pdf', '28069794_ag.pdf', '28069795_ag.pdf']}
userDict = {}

#
# objByUser will process 'doi' or 'pm' objects
#
# objByUser = {('user name', 'object type', 'object id') : ('pdffile', 'pdftext')}
# objByUser = {('user name', 'doi', 'doiid') : ('pdffile', 'pdftext')}
# objByUser = {('user name', 'pm', 'pmid') : ('pdffile', 'pdftext')}
# objByUser = {('user name', userPDF, 'mgiid') : ('pdffile', 'pdftext')}
# objByUser = {('user name', userSupplement, 'mgiid') : ('pdffile', 'pdftext')}
# objByUser = {('user name', userGOA, 'mgiid') : ('pdffile', 'pdftext')}
# objByUser = {('user name', userNLM, 'mgiid') : ('pdffile', 'pdftext')}
# {('cms, 'doi', '10.112xxx'): ['10.112xxx.pdf, 'text'']}
# {('cms, 'pm', 'PMID_14440025'): ['PDF_14440025.pdf', 'text'']}
objByUser = {}

#
# for checking duplicate doiids
# doiidById = {'doiid' : 'pdf file'}
doiidById = {}

# linkOut : link URL
linkOut = '<A HREF="%s">%s</A>' 

# error logs for level1, level2, level3

allErrors = ''
allCounts = ''
level1errorStart = '**********<BR>\nLiterature Triage Level 1 Errors : parse DOI ID from PDF files<BR><BR>\n'
level2errorStart = '**********<BR>\nLiterature Triage Level 2 Errors : parse PubMed IDs from PubMed API<BR><BR>\n\n'
level3errorStart = '**********<BR>\nLiterature Triage Level 3 Errors : check MGI for errors<BR><BR>\n\n'
specialerrorStart = '**********<BR>\nLiterature Triage littriage_create_supplement/littriage_update_pdf Errors : check MGI for errors<BR><BR>\n\n'
countStart = '**********<BR>\nLiterature Triage Counts<BR>\n'

level1error1 = '' 
level1error2 = ''
level1error3 = ''
level1error4 = ''

level2error1 = '' 
level2error2 = ''
level2error3 = ''
level2error4 = ''

level3error1 = '' 
level3error2 = ''
level3error3 = ''

specialerror1 = ''

#
# Purpose: Initialization
# Returns: 0
#
def initialize():
    global litparser
    global createSupplement, createPDF, updateNLM
    global diag, diagFile
    global error, errorFile
    global curator, curatorFile
    global sqllog, sqllogFile
    global inputDir, outputDir
    global masterDir, needsReviewDir
    global bcpScript
    global accFileName, refFileName, statusFileName, dataFileName
    global accFile, refFile, statusFile, dataFile
    global pma
    global workflowGroupList

    litparser = os.getenv('LITPARSER')
    diag = os.getenv('LOG_DIAG')
    error = os.getenv('LOG_ERROR')
    curator = os.getenv('LOG_CUR')
    sqllog = os.getenv('LOG_SQL')
    inputDir = os.getenv('INPUTDIR')
    outputDir = os.getenv('OUTPUTDIR')
    masterDir = os.getenv('MASTERTRIAGEDIR')
    needsReviewDir = os.getenv('NEEDSREVIEWTRIAGEDIR')
    bcpScript = os.getenv('PG_DBUTILS') + '/bin/bcpin.csh'

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

    if not sqllog:
        exit(1, 'Environment variable not set: LOG_SQL')

    if not inputDir:
        exit(1, 'Environment variable not set: INPUTDIR')

    if not outputDir:
        exit(1, 'Environment variable not set: OUTPUTDIR')

    if not masterDir:
        exit(1, 'Environment variable not set: MASTEREDTRIAGEDIR')

    if not needsReviewDir:
        exit(1, 'Environment variable not set: NEEDSREVIEWTRIAGEDIR')

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
        sqllogFile = open(sqllog, 'w')
    except:
        exist(1,  'Cannot open sqllog file: ' + sqllogFile)

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
        exit(1, 'PdfParser.setLitParserDir(litparser) needs review')

    try:
        pma = PubMedAgent.PubMedAgentMedline()
    except:
        exit(1, 'PubMedAgent.PubMedAgentMedline() needs review')

    results = db.sql('select _Term_key from VOC_Term where _Vocab_key = 127', 'auto')
    for r in results:
        workflowGroupList.append(r['_Term_key'])

    errorFile.write('\n<BR>Start Date/Time: %s\n<BR>' % (mgi_utils.date()))

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
    if sqllogFile:
        sqllogFile.close()
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
    global accKey, refKey, statusKey, mgiKey, jnumKey

    results = db.sql('select max(_Refs_key) + 1 as maxKey from BIB_Refs', 'auto')
    refKey = results[0]['maxKey']

    results = db.sql('select max(_Assoc_key) + 1 as maxKey from BIB_Workflow_Status', 'auto')
    statusKey = results[0]['maxKey']

    results = db.sql('select max(_Accession_key) + 1 as maxKey from ACC_Accession', 'auto')
    accKey = results[0]['maxKey']

    results = db.sql('select max(maxNumericPart) + 1 as maxKey from ACC_AccessionMax where prefixPart = \'MGI:\'', 'auto')
    mgiKey = results[0]['maxKey']

    results = db.sql('select max(maxNumericPart) + 1 as maxKey from ACC_AccessionMax where prefixPart = \'J:\'', 'auto')
    jnumKey = results[0]['maxKey']

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

    #
    # delete of BIB_Workflow_Data records
    # these will be reloaded via bcp
    #
    diagFile.write('\nstart: delete/update sql commands\n')
    sqllogFile.write('\nstart: delete/update sql commands\n')
    sqllogFile.write(deleteSQLAll)
    sqllogFile.write(updateSQLAll)
    if len(deleteSQLAll) > 0:
        try:
            db.sql(deleteSQLAll, None)
	    db.commit()
        except:
            diagFile.write('bcpFiles(): failed: delete sql commands\n')
            sqllogFile.write('bcpFiles(): failed: delete sql commands\n')
	    return 0
    if len(updateSQLAll) > 0:
        try:
            db.sql(updateSQLAll, None)
	    db.commit()
        except:
            diagFile.write('bcpFiles(): failed: update sql commands\n')
            sqllogFile.write('bcpFiles(): failed: update sql commands\n')
	    return 0
    diagFile.write('\nend: delete/update sql commands\n')
    sqllogFile.write('\nend: delete/update sql commands\n')

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
	        diagFile.write('bcpFiles(): failed : os.system(%s)\n' (bcpCmd))
		return 0
    diagFile.write('\nend: copy bcp files into database\n')
    diagFile.flush()

    #
    # compare BIB_Ref with BIB_Workflow_Data
    # the counts should match
    # else, error
    #
    results = db.sql('''
    	select r._refs_key from BIB_Refs r
	where not exists (select 1 from BIB_Workflow_Data d where r._refs_key = d._refs_key)
    	''', 'auto')
    if len(results) > 0:
    	diagFile.write('FATAL BCP ERROR:  reload database from backup/contact SE\n')
	return 0

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
                    shutil.move(oldPDF, newFileDir + '/' + newPDF)
		except:
	            diagFile.write('bcpFiles(): needs review : os.rename(' + oldPDF + ',' + newFileDir + '/' + newPDF + '\n')
		    #return 0
    diagFile.write('\nend: move oldPDF to newPDF\n')

    # update the max Accession ID value
    db.sql('select * from ACC_setMax (%d)' % (count_processPDFs), None)
    db.commit()

    # update the max Accession ID value for J:
    if count_userGOA:
        db.sql('select * from ACC_setMax (%d, \'J:\')' % (count_userGOA), None)
        db.commit()

    diagFile.write('\nend: bcpFiles() : successful\n')
    #diagFile.flush()

    return 0

#
# Purpose: replace pdf.getText() for bcp loading
# 	remove non-ascii characters
# 	carriage returns, etc.
# Returns:  new extractedText value
#
def replaceText(extractedText):

   if extractedText == None:
       return extractedText

   extractedText = re.sub(r'[^\x00-\x7F]','', extractedText)
   extractedText = extractedText.replace('\\', '\\\\')
   extractedText = extractedText.replace('\n', '\\n')
   extractedText = extractedText.replace('\r', '\\r')
   extractedText = extractedText.replace('|', '\\n')
   extractedText = extractedText.replace("'", "''")
   return extractedText

#
# Purpose: Level 1 Sanity Checks : parse DOI ID from PDF files
# Returns: 0
#
# if successful, pdf stays in the 'input' directory
# if needs review, pdf is moved to the 'needs review' directory
#
# 1: not in PDF format
# 2: cannot extract/find DOI ID
# 3: duplicate published refs (same DOI ID)
#
def level1SanityChecks():
    global userDict
    global objByUser
    global doiidById
    global allErrors, level1error1, level1error2, level1error3, level1error4
    global count_needsreview

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
		shutil.move(os.path.join(pdfPath, origFile), os.path.join(pdfPath, pdfFile))

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
	needsReviewPath = os.path.join(needsReviewDir, userPath)

	#
	# for each pdfFile
	# if pdfFile starts with "PMID", then store in objByUser dictionary as 'pm'
	# else if doi id can be found, then store in objByUser dictionary as 'doi'
	# else, report error, move pdf to needs review directory
	#
	for pdfFile in userDict[userPath]:

	    pdf = PdfParser.PdfParser(os.path.join(pdfPath, pdfFile))
	    doiid = ''

	    #
	    # if userPath is in the 'userSupplement' folder
	    #	store in objByUser
	    #	skip DOI/PMID sanity checks
	    #
	    # may be in format:
	    #	xxxx.pdf, xxxx_Jyyyy.pdf
	    #
	    if userPath == userSupplement:
		try:
	            # store by mgiid
	            tokens = pdfFile.replace('.pdf', '').split('_')
	            mgiid = tokens[0]
	            pdftext = replaceText(pdf.getText())
	            if (userPath, userSupplement, mgiid) not in objByUser:
	                objByUser[(userPath, userSupplement, mgiid)] = []
	                objByUser[(userPath, userSupplement, mgiid)].append((pdfFile, pdftext))
                except:
		    level1error1 = level1error1 + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR>\n'
		    shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
		    count_needsreview += 1
		    continue

	    #
	    # if userPath is in the 'userPDF' folder
	    #	store in objByUser
	    #	skip DOI/PMID sanity checks
	    #
	    # may be in format:
	    #	xxxx.pdf, xxxx_Jyyyy.pdf
	    #
	    elif userPath == userPDF:
		try:
	            # store by mgiid
	            tokens = pdfFile.replace('.pdf', '').split('_')
	            mgiid = tokens[0]
	            pdftext = replaceText(pdf.getText())
	            if (userPath, userPDF, mgiid) not in objByUser:
	                objByUser[(userPath, userPDF, mgiid)] = []
	                objByUser[(userPath, userPDF, mgiid)].append((pdfFile, pdftext))
                except:
		    level1error1 = level1error1 + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR>\n'
		    shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
		    count_needsreview += 1
		    continue

	    #
	    # if pdf file is in "PMID_xxxx" format
	    #
	    elif pdfFile.lower().startswith('pmid'):
		try:
	            # store by pmid
	            pmid = pdfFile.lower().replace('pmid_', '')
	            pmid = pmid.replace('.pdf', '')
	            pdftext = replaceText(pdf.getText())
	            if (userPath, 'pm', pmid) not in objByUser:
	                objByUser[(userPath, 'pm', pmid)] = []
	                objByUser[(userPath, 'pm', pmid)].append((pdfFile, pdftext))
                except:
		    level1error4 = level1error4 + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR>\n'
		    shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
		    count_needsreview += 1
		    continue

	    #
	    # anything else
	    #
	    else:
	        try:
                    doiid = pdf.getFirstDoiID()
	            pdftext = replaceText(pdf.getText())

		    if doiid:
		        if doiid not in doiidById:
		            doiidById[doiid] = []
		            doiidById[doiid].append(pdfFile)
	                    if DEBUG:
			        diagFile.write('pdf.getFirstDoiID() : successful : %s/%s : %s\n' % (pdfPath, pdfFile, doiid))
			        diagFile.flush()
		        else:
				#linkOut % (os.path.join(pdfPath, doiidById[doiid][0]), os.path.join(pdfPath, doiidById[doiid][0])) + \
                            level1error3 = level1error3 + doiid + '<BR>\n' + \
			    	linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + \
			        '<BR>\nduplicate of: ' + userPath + '/' + doiidById[doiid][0] + \
				'<BR><BR>\n\n'
			    shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
			    count_needsreview += 1
			    continue
		    else:
		        level1error2 = level1error2 + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR>\n'
		        shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
			count_needsreview += 1
		        continue
                except:
		    level1error1 = level1error1 + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR>\n'
		    shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
		    count_needsreview += 1
		    continue

	        # store by doiid
		if (userPath, 'doi', doiid) not in objByUser:
	            objByUser[(userPath, 'doi', doiid)] = []
	            objByUser[(userPath, 'doi', doiid)].append((pdfFile, pdftext))


    #
    # write out level1 errors to both error log and curator log
    #
    level1error1 = '<B>1: not in PDF format</B><BR><BR>\n\n' + level1error1 + '<BR>\n\n'
    level1error2 = '<B>2: cannot extract/find DOI ID</B><BR><BR>\n\n' + level1error2 + '<BR>\n\n'
    level1error3 = '<B>3: duplicate published refs (same DOI ID)</B><BR><BR>\n\n' + level1error3 + '<BR>\n\n'
    level1error4 = '<B>4: cannot extract PMID</B><BR><BR>\n\n' + level1error4 + '<BR>\n\n'
    allErrors = allErrors + level1errorStart + level1error1 + level1error2 + level1error3 + level1error4

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
def level2SanityChecks(userPath, objType, objId, pdfFile, pdfPath, needsReviewPath):
    global level2error1, level2error2, level2error3, level2error4

    if DEBUG:
        diagFile.write('level2SanityChecks: %s, %s, %s\n' % (userPath, objId, pdfFile))

    if objType == objDOI:
        # mapping of objId to pubmedID, return list of references
        try:
            mapping = pma.getReferences([objId])
        except:
            diagFile.write('level2SanityChecks:pma.getReferences() needs review: %s, %s, %s\n' % (objId, userPath, pdfFile))
	    return -1

        refList = mapping[objId]

        #  1: DOI ID maps to multiple pubmed IDs
        if len(refList) > 1:
            for ref in refList:
	        level2error1 = level2error1 + objId + ', ' + str(ref.getPubMedID()) + '<BR>\n' + \
	    	    linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
	    return 1

        #  2: DOI ID not found in pubmed
        for ref in refList:
            if ref == None:
	        level2error2 = level2error2 + objId + '<BR>\n' + \
		            linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
	        return 1

        pubMedRef = refList[0]
        pubmedID = pubMedRef.getPubMedID()
    else:
	pubmedID = objId
        pubMedRef = pma.getReferenceInfo(pubmedID)

    #  3: error getting medline record
    if not pubMedRef.isValid():
	level2error3 = level2error3 + objId + ', ' + pubmedID + '<BR>\n' + \
		linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
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

	requiredDict['pmId'] = pubMedRef.getPubMedID()
	requiredDict['title'] = pubMedRef.getTitle()
	requiredDict['journal'] = pubMedRef.getJournal()
	requiredDict['date'] = pubMedRef.getDate()
	requiredDict['year'] = pubMedRef.getYear()

        #  4: missing data from required field for DOI ID
	for reqLabel in requiredDict:
	    if requiredDict[reqLabel] == None:
		missingList.append(reqLabel)
	if len(missingList):
	   level2error4 = level2error4 + str(objId) + ', ' + str(pubmedID) + '<BR>\n' + \
		linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
	   return 1

    # if successful, return 'pubMedRef' object, else return 1, continue

    return pubMedRef

#
# Purpose: Level 3 Sanity Checks : check MGI for errors
# Returns: returns 0 if successful, 1 if errors are found
#
#  1: input PubMed ID or DOI ID exists in MGI
#  2: PubMed or DOI ID associated with different MGI references
#  3a: input PubMed ID exists in MGI but missing DOI ID -> add DOI ID in MGI
#  3b: input DOI ID exists in MGI but missing PubMed ID -> add PubMed ID in MGI
#  4 : update PDF/extracted text
#
def level3SanityChecks(userPath, objType, objId, pdfFile, pdfPath, needsReviewPath, ref):
    global level3error1, level3error2, level3error3
    global count_needsreview

    # return 0 : will add as new reference
    # return 1/2 : will skip/move to 'needs review'
    # return 3 : will add new Accession ids

    if DEBUG:
        diagFile.write('level3SanityChecks: %s, %s, %s\n' % (userPath, objId, pdfFile))

    pubmedID = ref.getPubMedID()

    if objType == objDOI:
        results = db.sql('''
	    select _Refs_key, mgiID, pubmedID, doiID from BIB_Citation_Cache where pubmedID = '%s' or doiID = '%s'
    	    ''' % (pubmedID, objId), 'auto')
    else:
        results = db.sql('''
	    select _Refs_key, mgiID, pubmedID, doiID from BIB_Citation_Cache where pubmedID = '%s'
    	    ''' % (pubmedID), 'auto')

    # 2: input PubMed ID or DOI ID associated with different MGI references
    if len(results) > 1:
        diagFile.write('2: input PubMed ID or DOI ID associated with different MGI references: ' \
		+ objId + ',' + pubmedID + '\n')
	level3error2 = level3error2 + objId + ', ' + pubmedID + '<BR>\n' + \
	    	linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
	shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
	count_needsreview += 1
	return 2, results

    elif len(results) == 1:

        if objType == objDOI:

            # 2: input PubMed ID or DOI ID associated with different MGI references
	    if results[0]['pubmedID'] != None and results[0]['doiID'] != None:
	        if (pubmedID == results[0]['pubmedID'] and objId != results[0]['doiID']) or \
	           (pubmedID != results[0]['pubmedID'] and objId == results[0]['doiID']):
                    diagFile.write('2: input PubMed ID or DOI ID associated with different MGI references: ' \
		            + objId + ',' + pubmedID + '\n')
	            level3error2 = level3error2 + objId + ', ' + pubmedID + '<BR>\n' + \
	    	            linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
		    shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
		    count_needsreview += 1
	            return 2, results

            # 3a: input PubMed ID exists in MGI but missing DOI ID -> add DOI ID in MGI
	    if results[0]['pubmedID'] == None:
	        diagFile.write('3: pubmedID is missing in MGI: ' + objId + ',' + pubmedID + '\n')
	        level3error3 = level3error3 + objId + ', ' + pubmedID + ' : adding PubMed ID<BR>\n' + \
	    	    linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
	        shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
		count_needsreview += 1
	        return 3, results

            # 3b: input DOI ID exists in MGI but missing PubMed ID -> add PubMed ID in MGI
	    if results[0]['doiID'] == None:
	        diagFile.write('3: doiid is missing in MGI:' + objId + ',' + pubmedID + '\n')
	        level3error3 = level3error3 + objId + ', ' + pubmedID + ' : adding DOI ID<BR>\n' + \
	    	    linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
	        shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
		count_needsreview += 1
	        return 3, results

        # 1: input PubMed ID or DOI ID exists in MGI
	diagFile.write('1: input PubMed ID or DOI ID exists in MGI: ' + objId + ',' + pubmedID + '\n')
	level3error1 = level3error1 + objId + ', ' + str(ref.getPubMedID()) + '<BR>\n' + \
	    	linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
	shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
	count_needsreview += 1
        return 1, results

    else:
        return 0, results

#
# Purpose: Process/Iterate PDF adds
# Returns: 0
#
def processPDFs():
    global allErrors, allCounts
    global level2error1, level2error2, level2error3, level2error4
    global level3error1, level3error2, level3error3
    global specialerror1
    global accKey, refKey, statusKey, mgiKey, jnumKey
    global mvPDFtoMasterDir
    global count_processPDFs, count_needsreview, count_userGOA, count_userPDF

    #
    # assumes the level1SanityChecks have passed
    #
    # for all rows in objByUser
    #	get info from pubmed API
    #   generate BCP file
    #   track pdf -> MGI numeric ####
    #

    if DEBUG:
        diagFile.write('\nprocessPDFs()\n')

    # objByUser = {('user name', 'doi', 'doiid') : ('pdffile', 'pdftext')}
    # objByUser = {('user name', 'pm', 'pmid') : ('pdffile', 'pdftext')}
    # objByUser = {('user name', userPDF, 'mgiid') : ('pdffile', 'pdftext')}
    # objByUser = {('user name', userSupplement, 'mgiid') : ('pdffile', 'pdftext')}
    # objByUser = {('user name', userGOA, 'mgiid') : ('pdffile', 'pdftext')}

    for key in objByUser:

	if DEBUG:
            diagFile.write('\nobjByUser: %s\n' % (str(key)))

	pdfFile = objByUser[key][0][0]
	extractedText = objByUser[key][0][1]
	userPath = key[0]
	objType = key[1]
	objId = key[2]
        pdfPath = os.path.join(inputDir, userPath)
        needsReviewPath = os.path.join(needsReviewDir, userPath)

	# process pdf/supplement
	if objType in (userPDF, userSupplement):
	    processUserPDF(key)
	    continue

	#
	# level2SanityChecks()
	# parse PubMed IDs from PubMed API
	#
	pubmedRef = level2SanityChecks(userPath, objType, objId, pdfFile, pdfPath, needsReviewPath)

	if pubmedRef == -1:
           continue

	if pubmedRef == 1:
	   if DEBUG:
	       diagFile.write('level2SanityChecks() : needs review : %s, %s, %s, %s\n' % (objId, userPath, pdfFile, str(pubmedRef)))
	   shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
	   count_needsreview += 1
           continue

	try:
	   pubmedID = pubmedRef.getPubMedID()
	except:
           diagFile.write('process:pubmedRef.getPubMedID()() needs review: %s, %s, %s\n' % (objId, userPath, pdfFile))
           continue

	if DEBUG:
	    diagFile.write('level2SanityChecks() : successful : %s, %s, %s, %s\n' % (objId, userPath, pdfFile, pubmedID))

	#
	# level3SanityChecks()
	# check MGI for errors
	#
        # return 0 : will add as new reference
        # return 1/2 : will skip/move to 'needs review'
        # return 3 : will add new Accession ids
	#
	rc, mgdRef = level3SanityChecks(userPath, objType, objId, pdfFile, pdfPath, needsReviewPath, pubmedRef)

	if rc == 1 or rc == 2:
	    if DEBUG:
                diagFile.write('level3SanityChecks() : needs review : %s, %s, %s, %s\n' \
			% (objId, userPath, pdfFile, pubmedID))
	    continue

	#
	# add accession ids to existing MGI reference
	#
	elif rc == 3:

            diagFile.write('level3SanityChecks() : successful : add PubMed ID or DOI ID : %s, %s, %s, %s, %s\n' \
	    	% (objId, userPath, pdfFile, pubmedID, str(mgdRef)))

	    # add pubmedID or doiId
	    userKey = loadlib.verifyUser(userPath, 0, diagFile)
	    objectKey = mgdRef[0]['_Refs_key']

	    if mgdRef[0]['pubmedID'] == None:
	        accID = pubmedID
		prefixPart = ''
		numericPart = accID
		logicalDBKey = 29
	    else:
	        accID = objId
		prefixPart = accID
		numericPart = ''
		logicalDBKey = 65

	    accFile.write('%s|%s|%s|%s|%s|%d|%d|0|1|%s|%s|%s|%s\n' \
		% (accKey, accID, prefixPart, numericPart, logicalDBKey, objectKey, mgiTypeKey, \
		   userKey, userKey, loaddate, loaddate))

	    accKey += 1

	# add new MGI reference
	#
	elif rc == 0:
            diagFile.write('level3SanityChecks() : successful : add new : %s, %s, %s, %s\n' \
	    	% (objId, userPath, pdfFile, pubmedID))

	    # add pubmedID or doiId
	    userKey = loadlib.verifyUser(userPath, 0, diagFile)
	    logicalDBKey = 1

	    #
	    # bib_refs
	    #

	    abstract = pubmedRef.getAbstract()
	    abstract = abstract.replace('|', '')

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
		   abstract, \
		   isReviewArticle, \
		   isDiscard, \
		   userKey, userKey, loaddate, loaddate))

	    count_processPDFs += 1

	    #
	    # bib_workflow_status
	    # 1 row per Group
	    #
	    for groupKey in workflowGroupList:
	        # if userGOA and group = GO, then status = Full-coded
		if userPath == userGOA and groupKey == 31576666:
	            statusFile.write('%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
		        % (statusKey, refKey, groupKey, fullCodedKey, isCurrent, \
		              userKey, userKey, loaddate, loaddate))
		else:
	            statusFile.write('%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
		        % (statusKey, refKey, groupKey, notRoutedKey, isCurrent, \
		              userKey, userKey, loaddate, loaddate))
                statusKey += 1

	    #
	    # bib_workflow_data
	    if userPath == userGOA:
	        if extractedText.lower().find('supplemental') > 0 \
	           or extractedText.lower().find('supplementary') > 0 \
	           or extractedText.lower().find('supplement ') > 0 \
	           or extractedText.lower().find('additional file') > 0 \
	           or extractedText.lower().find('appendix') > 0:
	            dataFile.write('%s|%s|%s||%s|%s|%s|%s|%s\n' \
	    	        % (refKey, hasPDF, suppfoundKey, extractedText, userKey, userKey, loaddate, loaddate))
	        else:
	            dataFile.write('%s|%s|%s||%s|%s|%s|%s|%s\n' \
	    	        % (refKey, hasPDF, suppnotfoundKey, extractedText, userKey, userKey, loaddate, loaddate))
	    else:
	        dataFile.write('%s|%s|%s||%s|%s|%s|%s|%s\n' \
	    	    % (refKey, hasPDF, supplementalKey, extractedText, userKey, userKey, loaddate, loaddate))

	    # MGI:xxxx
	    #
	    mgiID = mgiPrefix + str(mgiKey)
	    accFile.write('%s|%s|%s|%s|%s|%d|%d|%s|%s|%s|%s|%s|%s\n' \
		% (accKey, mgiID, mgiPrefix, mgiKey, logicalDBKey, refKey, mgiTypeKey, \
		   isPrivate, isPreferred, userKey, userKey, loaddate, loaddate))
	    accKey += 1
	    
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
	    accKey += 1

	    #
	    # doiId only
	    #
	    if objType == objDOI:
	    	accID = objId
	    	prefixPart = accID
	    	numericPart = ''
	    	logicalDBKey = 65

	    	accFile.write('%s|%s|%s|%s|%s|%d|%d|%s|%s|%s|%s|%s|%s\n' \
			% (accKey, accID, prefixPart, numericPart, logicalDBKey, refKey, mgiTypeKey, \
		   	isPrivate, isPreferred, userKey, userKey, loaddate, loaddate))
	    	accKey += 1

	    #
	    # J:xxxx
	    #
            if userPath == userGOA:
	    	accID = 'J:' + str(jnumKey)
	    	prefixPart = 'J:'
	    	numericPart = jnumKey
	    	logicalDBKey = 1
	    	accFile.write('%s|%s|%s|%s|%s|%d|%d|%s|%s|%s|%s|%s|%s\n' \
			% (accKey, accID, prefixPart, numericPart, logicalDBKey, refKey, mgiTypeKey, \
		   	isPrivate, isPreferred, userKey, userKey, loaddate, loaddate))
	        accKey += 1
		jnumKey += 1
		count_userGOA += 1

	    # store dictionary : move pdf file from inputDir to masterPath
	    newPath = Pdfpath.getPdfpath(masterDir, mgiID)
	    mvPDFtoMasterDir[pdfPath + '/' + pdfFile] = []
	    mvPDFtoMasterDir[pdfPath + '/' + pdfFile].append((newPath,str(mgiKey) + '.pdf'))

	    refKey += 1
	    mgiKey += 1

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

    specialerror1 = '<B>1: MGI ID in filename does not match reference in MGI</B><BR><BR>\n\n' + \
    	specialerror1 + '<BR>\n\n'
    allErrors = allErrors + specialerrorStart + specialerror1

    # copy all errors to error log, remove html and copy to curator log
    allCounts = allCounts + countStart
    allCounts = allCounts + 'Successful PDF\'s processed (All New_Newcurrent curator & PDF download directories): ' + str(count_processPDFs) + '<BR>\n\n'
    allCounts = allCounts + 'Records with Supplemental data added: ' + str(count_userSupplement) + '<BR>\n\n'
    allCounts = allCounts + 'Records with Updated PDF\'s: ' + str(count_userPDF) + '<BR>\n\n'
    allCounts = allCounts + 'Records with Updated NLM information: ' + str(count_userNLM) + '<BR>\n\n'
    allCounts = allCounts + 'Records with GOA information: ' + str(count_userGOA) + '<BR>\n\n'
    allCounts = allCounts + 'New Failed PDF\'s in Needs_Review folder: ' + str(count_needsreview) + '<BR><BR>\n\n'

    errorFile.write(allCounts)
    errorFile.write(allErrors)
    curatorFile.write(re.sub('<.*?>', '', allCounts))
    curatorFile.write(re.sub('<.*?>', '', allErrors))

    diagFile.flush()

    return 0

#
# Purpose: Process userSupplement, userPDF Object : see processPDFs()
# Returns: nothing
#
# bib_workflow_data: 
#	store extracted
#	hasPDF = 1
#	if userSupplement, _supplimental_key = 34026997/'Supplement attached'
#
def processUserPDF(objKey):
    global specialerror1
    global mvPDFtoMasterDir
    global deleteSQLAll, updateSQLAll
    global count_userSupplement
    global count_needsreview
    global count_userPDF

    if DEBUG:
        diagFile.write('\nprocessUserPDF()\n')

    # objByUser = {('user name', userPDF, 'mgiid') : ('pdffile', 'pdftext')}
    # objByUser = {('user name', userSupplement, 'mgiid') : ('pdffile', 'pdftext')}

    pdfFile = objByUser[objKey][0][0]
    extractedText = objByUser[objKey][0][1]
    userPath = objKey[0]
    objType = objKey[1]
    mgiKey = objKey[2]
    mgiId = 'MGI:' + mgiKey
    pdfPath = os.path.join(inputDir, userPath)
    needsReviewPath = os.path.join(needsReviewDir, userPath)

    results = db.sql('''select r._Refs_key, d._Supplemental_key
    	from BIB_Citation_Cache r, BIB_Workflow_Data d 
	where r.mgiID = \'%s\' 
	and r._Refs_key = d._Refs_key''' % (mgiId), 'auto')

    if len(results) == 0:
	specialerror1 = specialerror1 + str(mgiId) + '<BR>\n' + \
		linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
	count_needsreview += 1

    	if DEBUG:
            diagFile.write('userPDF/userSupplement level1 : needs review : %s, %s, %s\n' % (mgiId, userPath, pdfFile))

	shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))

        return

    existingRefKey = results[0]['_Refs_key']
    suppKey = results[0]['_Supplemental_key']
    userKey = loadlib.verifyUser(userPath, 0, diagFile)

    if objType == userSupplement:
	dataSuppKey = 34026997
	count_userSupplement += 1
    else:
	dataSuppKey = suppKey
	count_userPDF += 1

    dataFile.write('%s|%s|%s||%s|%s|%s|%s|%s\n' \
	    	    % (existingRefKey, hasPDF, dataSuppKey, extractedText, userKey, userKey, loaddate, loaddate))

    deleteSQLAll = deleteSQLAll + 'delete from BIB_Workflow_Data where _Refs_key = %s;\n' % (existingRefKey)
    updateSQLAll = updateSQLAll + 'update BIB_Refs set _ModifiedBy_key = %s, modification_date = now() where _Refs_key = %s;\n' \
    		% (userKey, existingRefKey)

    # store dictionary : move pdf file from inputDir to masterPath
    newPath = Pdfpath.getPdfpath(masterDir, mgiId)
    mvPDFtoMasterDir[pdfPath + '/' + pdfFile] = []
    mvPDFtoMasterDir[pdfPath + '/' + pdfFile].append((newPath,str(mgiKey) + '.pdf'))

    return

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

