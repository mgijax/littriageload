#
#  littriageload.py
###########################################################################
#
#  Purpose:
#
#      This script will process Lit Triage PDF files
#      for loading into BIB_Refs, BIB_Workflow_Status, BIB_Workflow_Data
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
#	SANITYCHECKONLY
#	LITPARSER
#	INPUTDIR
#	OUTPUTDIR
#	LOG_*
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
#
#	2) level1SanityChecks() : using PDF file...
#		check for duplicate PDF file names
#		extract DOI ID/text from PDF, translate DOI ID -> PubMed ID
#
#	3) setPrimaryKeys() : setting global primary keys
#
#	4) processPDFs() : iterate thru PDF files/run level2 and level3 sanity checks
#
#	   split text into sections
#
#          if not (userSupplement, userPDF, userGO, userGXDHT, userNLM, userDiscard):
#		run mice check
#
#	   supplmental check
#
#	   if (userPDF, userSupplement):
#	   	processExtractedText() : process extracted text (bib_workflow_data)
#
#	   else everything else:
#
#		level2SanityChecks() : using PubMed ID, extract NLM/Medline data
#
#		level3SanityChecks() :
# 			return 0   : add as new reference
# 			return 1/2 : skip/move to 'needs review'
# 			return 3   : add new accession ids (includes userNLM)
# 			return 4   : userNLM : will call processNLMRefresh()
#
#		if (userNLM):
#		    may add new DOI accession ids
#		    processNLMRefresh()    : update bib_refs fields
#		    processExtractedText() : process extracted text (bib_workflow_data)
#
#	5) bcpFiles() : load BCP files into database, runs SQL script, etc.
#
#       6) closeFiles() : close files
#
# lec	12/08/2017
#       - TR12705/added NLM refresh pipeline
#
# lec	06/20/2017
#       - TR12250/Lit Triage
#
###########################################################################

import sys 
import os
import shutil
import re
import traceback
import time
import db
import mgi_utils
import loadlib
import PdfParser
import PubMedAgent
import Pdfpath
import extractedTextSplitter

#db.setTrace(True)

# run sanity checking only
runSanityCheckOnly = False

# for setting where the litparser lives (see PdfParser)
litparser = ''
# for setting the PubMedAgent
pma = ''
# for using extracted text section splitter
textSplitter = ''

# special processing for specific cases
userSupplement = 'littriage_create_supplement'
userPDF = 'littriage_update_pdf'
userGO = 'littriage_go'
userGXDHT = 'littriage_gxdht'
userNLM = 'littriage_NLM_refresh'
userDiscard = 'littriage_discard'

# littriageload user
userLTKey = '1569'      

count_processPDFs = 0
count_userSupplement = 0
count_userPDF = 0
count_userNLM = 0
count_needsreview = 0
count_duplicate = 0
count_doipubmedadded = 0
count_mismatchedtitles = 0
count_lowextractedtext = 0
count_userGO = 0
count_userGXDHT = 0

diag = ''
diagFile = ''
curator = ''
curatorFile = ''
error = ''
errorFile = ''
sqllog = ''
sqllogFile = ''
duplicatelog = ''
duplicatelogFile = ''
pubtypelog = ''
pubtypelogFile = ''
doipubmedaddedlog = ''
doipubmedaddedlogFile = ''
splitterlog = ''
splitterlogFile = ''
pdflog = ''
pdflogFile = ''

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
tagFile = ''
tagFileName = ''
relevanceFile = ''
relevanceFileName = ''

# see bcpFiles: 
# store bcp files in python lists
# write out to bcp files once
accList = []
refList = []
statusList = []
dataList = []
tagList = []
relevanceList = []

accTable = 'ACC_Accession'
refTable = 'BIB_Refs'
statusTable = 'BIB_Workflow_Status'
dataTable = 'BIB_Workflow_Data'
tagTable = 'BIB_Workflow_Tag'
relevanceTable = 'BIB_Workflow_Relevance'

accKey = 0
refKey = 0
dataKey = 0
statusKey = 0
tagKey = 0
relevanceKey = 0
mgiKey = 0
jnumKey = 0

# to track duplicates
refKeyList = []

objDOI = 'doi'
mgiTypeKey = 1
mgiPrefix = 'MGI:'
referenceTypeKey = 31576687 	# Peer Reviewed Article
newCodedKey = 71027551
statusChosenKey = 31576671      # Chosen (workflow_status/_vocab_key = 128)
statusFullCodedKey = 31576674	# Full-coded (workflow_status/_vocab_key = 128)
miceInRefOnlyKey = 49170000	# MGI:Mice in reference only

# default isDiscard = not specified
relevanceVersion = ''
relevanceDiscardKey = 70594666  # discard
relevanceNotSpecKey = 70594668  # not specified
isDiscard = relevanceNotSpecKey

isReviewArticle = 0
isCurrent = 1
hasPDF = 1
isPrivate = 0
isPreferred = 1

# text check for 'mice'
checkMice = 'mice'

# bib_workflow_data._extractedtext_key values
bodySectionKey = 48804490
refSectionKey = 48804491
suppSectionKey = 48804492
starMethodSectionKey = 48804493
figureSectionKey = 48986625

# bib_workflow_data._supplemental_key values
suppFoundKey = 31576675	        # Db found supplement
suppNotFoundKey = 31576676      # Db supplement not found
suppAttachedKey = 34026997	# Supplemental attached
suppNotApplKey = 48874093	# Not Applicable

# erratum include
erratumIncludeList = [];
# erratum exclude
erratumExcludeList = [];
# erratum position
erratumPosition = 300;

# list of workflow groups
workflowGroupList = []

# list of supplemental words
suppWordList = []

# moving input/pdfs to master dir/pdfs
mvPDFtoMasterDir = {}

# delete SQL commands
deleteSQLAll = ''
# update SQL commands; in a list
updateSQLAll = []

loaddate = loadlib.loaddate

#
# userDict = {'user' : [pdf1, pdf2]}
# {'cms': ['28069793_ag.pdf', '28069794_ag.pdf', '28069795_ag.pdf']}
userDict = {}

#
# objByUser will process 'doi' or 'pm' or 'pmc' objects
#
# objByUser = {('userPath', 'object type', 'object id') : ('pdffile', 'pdftext', 'splittext')}
# objByUser = {('userPath', 'doi', 'doiid') : ('pdffile', 'pdftext', 'splittext')}
# objByUser = {('userPath', 'pm', 'pmid') : ('pdffile', 'pdftext', 'splittext')}
# objByUser = {('userPath', 'pmc', 'pmcid') : ('pdffile', 'pdftext', 'splittext')}
# objByUser = {('userPath', userPDF, 'mgiid') : ('pdffile', 'pdftext', 'splittext')}
# objByUser = {('userPath', userSupplement, 'mgiid') : ('pdffile', 'pdftext', 'splittext')}
# objByUser = {('userPath', userGO, 'mgiid') : ('pdffile', 'pdftext', 'splittext')}
# objByUser = {('userPath', userNLM, 'mgiid') : ('pdffile', 'pdftext', 'splittext')}
# {('cms, 'doi', '10.112xxx'): ['10.112xxx.pdf, 'text'']}
# {('cms, 'pm', 'PMID_14440025'): ['PDF_14440025.pdf', 'text'']}
# {('cms, 'pmc', 'PMCxxxx'): ['PMCxxxx.pdf', 'text'']}
objByUser = {}

#
# for checking duplicate doiids
# doiidById = {'doiid' : 'pdf file'}
doiidById = {}

# to track list of existing reference keys
# so that duplicates do not get created
# see processExtractedText
#
existingRefKeyList = []

# linkOut : link URL
linkOut = '<A HREF="%s">%s</A>' 

# error logs for level1, level2, level3, etc.

allErrors = ''
allCounts = ''

level0errorStart = '**********<BR>\nLiterature Triage Level 0 Errors : duplicate PDF file name<BR><BR>\n'
level1errorStart = '**********<BR>\nLiterature Triage Level 1 Errors : parse DOI ID from PDF files<BR><BR>\n'
level2errorStart = '**********<BR>\nLiterature Triage Level 2 Errors : parse PubMed IDs from PubMed API<BR><BR>\n\n'
level3errorStart = '**********<BR>\nLiterature Triage Level 3 Errors : check MGI for errors<BR><BR>\n\n'
level4errorStart = '**********<BR>\nLiterature Triage Level 4 Errors : Supplemental/Update PDF<BR><BR>\n\n'
level5errorStart = '**********<BR>\nLiterature Triage Level 5 Errors : Update NLM information<BR><BR>\n\n'
level6errorStart = '**********<BR>\nLiterature Triage Level 6 Errors : Possible mismatch citation - citation title not found in extracted text<BR><BR>\n\n'
level7errorStart = '**********<BR>\nLiterature Triage Level 7 Errors : Extracted text null or less than 100 characters<BR><BR>\n\n'

countStart = '**********<BR>\nLiterature Triage Counts<BR>\n'

level0error1 = '' 
level1error1 = '' 
level1error2 = ''
level1error3 = ''
level1error4 = ''
level2error1 = '' 
level2error2 = ''
level2error3 = ''
level2error4 = ''
level2error5 = ''
level3error1 = '' 
level4error1 = ''
level4error2 = ''
level5error1 = ''
level5error2 = ''
level6error1 = ''
level7error1 = ''

#
# Purpose: Initialization
# Returns: 0
#
def initialize():
    global runSanityCheckOnly
    global litparser
    global createSupplement, createPDF, updateNLM
    global diag, diagFile
    global error, errorFile
    global curator, curatorFile
    global sqllog, sqllogFile
    global duplicatelog, duplicatelogFile
    global pubtypelog, pubtypelogFile
    global doipubmedaddedlog, doipubmedaddedlogFile
    global splitterlog, splitterlogFile
    global pdflog, pdflogFile
    global inputDir, outputDir
    global masterDir, needsReviewDir
    global bcpScript
    global accFileName, refFileName, statusFileName, dataFileName, tagFileName, relevanceFileName
    global accFile, refFile, statusFile, dataFile, tagFile, relevanceFile
    global pma
    global textSplitter
    global workflowGroupList
    global suppWordList
    global erratumIncludeList, erratumExcludeList
    global relevanceVersion
    
    db.set_sqlLogFunction(db.sqlLogAll)

    runSanityCheckOnly = os.getenv('SANITYCHECKONLY')
    litparser = os.getenv('LITPARSER')
    diag = os.getenv('LOG_DIAG')
    error = os.getenv('LOG_ERROR')
    curator = os.getenv('LOG_CUR')
    sqllog = os.getenv('LOG_SQL')
    duplicatelog = os.getenv('LOG_DUPLICATE')
    pubtypelog = os.getenv('LOG_PUBTYPE')
    doipubmedaddedlog = os.getenv('LOG_DOIPUBMEDADDED')
    splitterlog = os.getenv('LOG_SPLITTER')
    pdflog = os.getenv('LOG_PDF')
    inputDir = os.getenv('INPUTDIR')
    outputDir = os.getenv('OUTPUTDIR')
    masterDir = os.getenv('MASTERTRIAGEDIR')
    needsReviewDir = os.getenv('NEEDSREVIEWTRIAGEDIR')
    bcpScript = os.getenv('PG_DBUTILS') + '/bin/bcpin.csh'
    relevanceVersion = os.getenv('RELEVANCE_VERSION')

    #
    # Make sure the required environment variables are set.
    #

    if not runSanityCheckOnly:
        exit(1, 'Environment variable not set: SANITYCHECKONLY')

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

    if not duplicatelog:
        exit(1, 'Environment variable not set: LOG_DUPLICATE')

    if not pubtypelog:
        exit(1, 'Environment variable not set: LOG_PUBTYPE')

    if not doipubmedaddedlog:
        exit(1, 'Environment variable not set: LOG_DOIPUBMEDADDED')

    if not splitterlog:
        exit(1, 'Environment variable not set: LOG_SPLITTER')

    if not pdflog:
        exit(1, 'Environment variable not set: LOG_PDF')

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
        duplicatelogFile = open(duplicatelog, 'w')
    except:
        exist(1,  'Cannot open duplicate file: ' + duplicatelogFile)

    try:
        pubtypelogFile = open(pubtypelog, 'w')
    except:
        exist(1,  'Cannot open pubtypelog file: ' + pubtypelogFile)

    try:
        doipubmedaddedlogFile = open(doipubmedaddedlog, 'w')
    except:
        exist(1,  'Cannot open doipubmedaddedlog file: ' + doipubmedaddedlogFile)

    try:
        splitterlogFile = open(splitterlog, 'w')
    except:
        exist(1,  'Cannot open splitterlog file: ' + splitterlogFile)

    try:
        pdflogFile = open(pdflog, 'w')
    except:
        exist(1,  'Cannot open pdflog file: ' + pdflogFile)

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
        tagFileName = outputDir + '/' + tagTable + '.bcp'
    except:
        exit(1, 'Cannot create file: ' + outputDir + '/' + tagTable + '.bcp')

    try:
        relevanceFileName = outputDir + '/' + relevanceTable + '.bcp'
    except:
        exit(1, 'Cannot create file: ' + outputDir + '/' + relevanceTable + '.bcp')

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

    try:
        tagFile = open(tagFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % tagFileName)

    try:
        relevanceFile = open(relevanceFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % relevanceFileName)

    # initialized PdfParser.py
    try:
        PdfParser.setLitParserDir(litparser)
    except:
        exit(1, 'PdfParser.setLitParserDir(litparser) needs review')

    try:
        pma = PubMedAgent.PubMedAgentMedline()
    except:
        exit(1, 'PubMedAgent.PubMedAgentMedline() could not be found')

    try:
        textSplitter = extractedTextSplitter.ExtTextSplitter()
    except:
        exit(1, 'lib_py_littriage/extractedTextSplitter.ExtTextSplitter() could not be found')

    results = db.sql('select _Term_key from VOC_Term where _Vocab_key = 127', 'auto')
    for r in results:
        workflowGroupList.append(r['_Term_key'])

    results = db.sql('select lower(term) as term from VOC_Term where _Vocab_key = 143', 'auto')
    for r in results:
        suppWordList.append(r['term'])

    results = db.sql('select term from VOC_Term where _Vocab_key = 145', 'auto')
    for r in results:
        erratumIncludeList.append(r['term'])

    results = db.sql('select term from VOC_Term where _Vocab_key = 146', 'auto')
    for r in results:
        erratumExcludeList.append(r['term'])

    errorFile.write('\n<BR>Start Date/Time: %s\n<BR>' % (mgi_utils.date()))

    duplicatelogFile.write('Literature Triage Duplicates\n\n')
    duplicatelogFile.write('Note : duplicate pdfs are deleted and are not moved to needs_review folder\n\n')
    duplicatelogFile.write('1: PubMed ID/DOI ID exists in MGI\n\n')

    pubtypelogFile.write('Literature Triage Excluded Publication Types\n\n')
    pubtypelogFile.write('Note : excluded publication type pdfs are deleted and are not moved to needs_review folder\n\n')

    doipubmedaddedlogFile.write('Literature Triage DOI ID/Pubmed ID Added\n\n')

    splitterlogFile.write('Literature Triage Splitter Info\n\n')
    splitterlogFile.write('pubmed id, mgi id, body count, ref count, figure count, star method count, supplement count, reference section issue reason\n\n')

    return 0


#
# Purpose: Close files.
# Returns: 0
#
def closeFiles():

    if diagFile:
        diagFile.close()
    if sqllogFile:
        sqllogFile.close()
    if duplicatelogFile:
        duplicatelogFile.close()
    if pubtypelogFile:
        pubtypelogFile.close()
    if doipubmedaddedlogFile:
        doipubmedaddedlogFile.close()
    if splitterlogFile:
        splitterlogFile.close()
    if pdflogFile:
        pdflogFile.close()
    if refFile:
        refFile.close()
    if statusFile:
        statusFile.close()
    if dataFile:
        dataFile.close()
    if tagFile:
        tagFile.close()
    if relevanceFile:
        relevanceFile.close()
    if accFile:
        accFile.close()
    if errorFile:
        errorFile.close()
    if curatorFile:
        curatorFile.close()

    return 0

#
# Purpose:  sets global primary key variables
# Returns: 0
#
def setPrimaryKeys():
    global accKey, refKey, dataKey, mgiKey, jnumKey, tagKey, statusKey, relevanceKey

    results = db.sql(''' select nextval('bib_refs_seq') as maxKey ''', 'auto')
    refKey = results[0]['maxKey']

    results = db.sql(''' select nextval('bib_workflow_data_seq') as maxKey ''', 'auto')
    dataKey = results[0]['maxKey']

    results = db.sql(''' select nextval('bib_workflow_tag_seq') as maxKey ''', 'auto')
    tagKey = results[0]['maxKey']

    results = db.sql(''' select nextval('bib_workflow_status_seq') as maxKey ''', 'auto')
    statusKey = results[0]['maxKey']

    results = db.sql(''' select nextval('bib_workflow_relevance_seq') as maxKey ''', 'auto')
    relevanceKey = results[0]['maxKey']

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

    diagFile.write('\n%s:bcpFiles():running sanity checks only = %s\n' % (mgi_utils.date(), runSanityCheckOnly))

    bcpI = '%s %s %s' % (bcpScript, db.get_sqlServer(), db.get_sqlDatabase())
    bcpII = '"|" "\\n" mgd'

    #
    # write out to bcp files once
    #
    if len(accList) > 0:
        accFile.write('\n'.join(accList) + '\n')
    if len(refList) > 0:
        refFile.write('\n'.join(refList) + '\n')
    if len(statusList) > 0:
        statusFile.write('\n'.join(statusList) + '\n')
    if len(dataList) > 0:
        dataFile.write('\n'.join(dataList) + '\n')
    if len(tagList) > 0:
        tagFile.write('\n'.join(tagList) + '\n')
    if len(relevanceList) > 0:
        relevanceFile.write('\n'.join(relevanceList) + '\n')

    #
    # flush bcp files
    #
    refFile.flush()
    statusFile.flush()
    dataFile.flush()
    tagFile.flush()
    relevanceFile.flush()
    accFile.flush()

    #
    # only execute bcp if bcp file has data
    #
    bcpRun = []
    if refFile.tell() > 0:
        bcpRun.append('%s %s "/" %s %s' % (bcpI, refTable, refFileName, bcpII))
    if statusFile.tell() > 0:
        bcpRun.append('%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII))
    if dataFile.tell() > 0:
        bcpRun.append('%s %s "/" %s %s' % (bcpI, dataTable, dataFileName, bcpII))
    if tagFile.tell() > 0:
        bcpRun.append('%s %s "/" %s %s' % (bcpI, tagTable, tagFileName, bcpII))
    if relevanceFile.tell() > 0:
        bcpRun.append('%s %s "/" %s %s' % (bcpI, relevanceTable, relevanceFileName, bcpII))
    if accFile.tell() > 0:
        bcpRun.append('%s %s "/" %s %s' % (bcpI, accTable, accFileName, bcpII))

    #
    # close bcp files
    #
    refFile.close()
    statusFile.close()
    dataFile.close()
    tagFile.close()
    relevanceFile.close()
    accFile.close()

    # if only running sanity checks, return
    if runSanityCheckOnly == 'True':
        return 0

    #
    # delete of BIB_Workflow_Data records
    # these will be reloaded via bcp
    #
    diagFile.write('\n%s:running deleteSQLAll commands\n' % (mgi_utils.date()))
    sqllogFile.write(deleteSQLAll)

    if len(deleteSQLAll) > 0:
        diagFile.write('\ndeleteSQLAll - details in littriageload.sql.log\n')
        try:
            db.sql(deleteSQLAll, None)
            db.commit()
        except:
            diagFile.write('\ndeleteSQLAll: failed\n')
            return 0

    #
    # copy bcp files into database
    # if any bcp fails, return (0)
    # this means the input files will remain
    # and can be used in the next running of the load
    #
    diagFile.write('\n%s:copy bcp files into database\n' % (mgi_utils.date()))
    for r in bcpRun:
        diagFile.write('%s\n' % r)
        diagFile.flush()
        try:
            os.system(r)
        except:
            diagFile.write('copy bcp files into database: failed\n')
            return 0
    diagFile.write('\n%s:copy bcp files into database : successful\n' % (mgi_utils.date()))
    diagFile.flush()

    #
    # compare BIB_Ref with BIB_Workflow_Data
    # the counts should match
    # else, error
    #
    results = db.sql('''
        select r._Refs_key from BIB_Refs r
        where not exists (select 1 from BIB_Workflow_Data d where r._refs_key = d._refs_key)
        ''', 'auto')
    if len(results) > 0:
        diagFile.write('FATAL BCP ERROR:  reload database from backup/contact SE\n')
        return 0

    #
    # updateSQLAll
    # if this fails, ok to keep going
    # if this fails, check details and manually run SQL to find issue
    #
    diagFile.write('\n%s:running updateSQLAll commands\n' % (mgi_utils.date()))
    for i in updateSQLAll:
        sqllogFile.write(i)
        db.sql(i, None)
        db.commit()
    diagFile.write('\n%s:updateSQLAll: successful\n' % (mgi_utils.date()))
    
    #
    # move PDF from inputdir to master directory
    # using numeric part of MGI id
    #
    # /data/loads/mgi/littriageload/input/cms/28473584_g.pdf is moved to: 
    #	-> /data/littriage/5904000/5904760.pdf
    #
    diagFile.write('\n%s: move oldPDF to newPDF\n' % (mgi_utils.date()))
    for oldPDF in mvPDFtoMasterDir:
        for newFileDir, newPDF in mvPDFtoMasterDir[oldPDF]:
            diagFile.write(oldPDF + '\t' +  newFileDir + '\t' + newPDF + '\n')
            try:
                os.makedirs(newFileDir)
            except:
                pass
            try:
                shutil.move(oldPDF, newFileDir + '/' + newPDF)
            except:
                diagFile.write('bcpFiles(): needs review : shutil.move(' + oldPDF + ',' + newFileDir + '/' + newPDF + '\n')
                #return 0
    diagFile.write('\n%s: move oldPDF to newPDF\n' % (mgi_utils.date()))

    # update the max accession ID value
    db.sql('select * from ACC_setMax (%d)' % (count_processPDFs), None)
    db.commit()

    # update bib_refs serialization
    db.sql(''' select setval('bib_refs_seq', (select max(_Refs_key) from BIB_Refs)) ''', None)
    db.commit()

    # update bib_workflow_data serialization
    db.sql(''' select setval('bib_workflow_data_seq', (select max(_Assoc_key) from BIB_Workflow_Data)) ''', None)
    db.commit()

    # update bib_workflow_status serialization
    db.sql(''' select setval('bib_workflow_status_seq', (select max(_Assoc_key) from BIB_Workflow_Status)) ''', None)
    db.commit()

    # update bib_workflow_tag serialization
    db.sql(''' select setval('bib_workflow_tag_seq', (select max(_Assoc_key) from BIB_Workflow_Tag)) ''', None)
    db.commit()

    # update bib_workflow_relevance serialization
    db.sql(''' select setval('bib_workflow_relevance_seq', (select max(_Assoc_key) from BIB_Workflow_Relevance)) ''', None)
    db.commit()

    # update the max accession ID value for J:
    if count_userGO or count_userGXDHT:
        count_acc = count_userGO + count_userGXDHT
        db.sql('select * from ACC_setMax (%d, \'J:\')' % (count_acc), None)
        db.commit()

    diagFile.write('\n%s:bcpFiles():successful\n' % (mgi_utils.date()))
    diagFile.flush()

    return 0

#
# Purpose: replace pdf.getText() for bcp loading
# 	remove non-ascii characters
# 	carriage returns, etc.
# Returns:  new extractedText value
#
def replaceText(extractedText):

   if extractedText == None:
       extractedText = ''
       return extractedText

   extractedText = re.sub(r'[^\x00-\x7F]','', extractedText)
   extractedText = extractedText.replace('\\', '\\\\')
   extractedText = extractedText.replace('\n', '\\n')
   extractedText = extractedText.replace('\r', '\\r')
   extractedText = extractedText.replace('|', '\\n')
   extractedText = extractedText.replace("'", "''")
   return extractedText

#
# Purpose: replace pubmed reference for bcp loading
#
#	getAuthors() 
#	getPrimaryAuthor()
#	getTitle()
#	getAbstract()
#	getVolumn()
#	getIssue()
#	getPages()
#       getELocator()
#
# 	remove non-ascii characters
# 	carriage returns, etc.
#	| -> \\|
#	' (single quote) -> ''
#	None -> null
#
# Returns:  new abstract, title value
#
def replacePubMedRef(isSQL, authors, primaryAuthor, title, abstract, vol, issue, pgs, elocator):

    if authors == None or authors == '':
        authors = ''
        primaryAuthor = ''
    elif isSQL:
        authors = authors.replace("'", "''")
        primaryAuthor = primaryAuthor.replace("'", "''")

    authors = authors.replace("||", "")

    if title == None or title == '':
        title = ''
    elif isSQL:
        title = title.replace("'", "''")
    else:
        title = title.replace('|', '\\|')

    if abstract == None or abstract == '':
        abstract = ''
    elif isSQL:
        abstract = abstract.replace("'", "''")
        abstract = abstract.replace("\\", "")
    else:
        abstract = abstract.replace('|', '\\|')

    if vol == None or vol == '':
        vol = ''
    elif isSQL:
        vol = vol.replace("'", "''")
    else:
        vol = vol.replace('|', '\\|')

    if issue == None or issue == '':
        issue = ''
    elif isSQL:
        issue = issue.replace("'", "''")
    else:
        issue = issue.replace('|', '\\|')

    if pgs == None or pgs == '':
        if elocator != None and elocator != '':
                pgs = elocator
        else:
                pgs = ''
    elif isSQL:
        pgs = pgs.replace("'", "''")
    else:
        pgs = pgs.replace('|', '\\|')

    return authors, primaryAuthor, title, abstract, vol, issue, pgs

#
# Purpose: Set the supplemental key based on extractedText
#
# at present, this is only called for new references only
#
# Return: supplemental key
#
def setSupplemental(userPath, extractedText):

    if extractedText == None:
        return suppNotFoundKey

    for i in suppWordList:
        if extractedText.lower().find(i) >= 0:
            return suppFoundKey

    return suppNotFoundKey

#
# Purpose: Level 1 Sanity Checks : parse DOI ID from PDF files
# Returns: 0
#
# if successful, pdf stays in the 'input' directory
# if needs review, pdf is moved to the 'needs review' directory
#
# level 0
# 1: duplicate PDF file names
#
# level 1
# 1: not in PDF format
# 2: cannot extract/find DOI ID
# 3: duplicate published refs (same DOI ID)
#
def level1SanityChecks():
    global userDict
    global objByUser
    global doiidById
    global allErrors, level0error1, level1error1, level1error2, level1error3, level1error4, level7error1
    global count_needsreview, count_lowextractedtext

    nodupFileName = []
    dupFileName = []

    # step 1 : iterate thru input directory by user 
    # determine if pdf file name is a duplicate
    # add to dupFileName list
    for userPath in os.listdir(inputDir):

        pdfPath = inputDir + '/' + userPath + '/'
        diagFile.write('%s:level1SanityChecks:step 1:%s\n' % (mgi_utils.date(), pdfPath))

        try:
                for pdfFile in os.listdir(pdfPath):

                        #
                        # remove spaces
                        # rename '.PDF' with '.pdf'
                        #

                        origFile = pdfFile

                        if pdfFile.find(' ') >= 0 or pdfFile.find('.PDF') >= 0:
                                pdfFile = pdfFile.replace(' ', '')
                                pdfFile = pdfFile.replace('.PDF', '.pdf')
                                shutil.move(os.path.join(pdfPath, origFile), os.path.join(pdfPath, pdfFile))

                        #
                        # file in input directory does not end with pdf
                        #
                        if not pdfFile.lower().endswith('.pdf'):
                                diagFile.write('file in input directory does not end with pdf: ' + userPath + ' ' + pdfFile + '\n')
                                continue

                        #
                        # is fileName a duplicate?
                        #
                        if pdfFile not in nodupFileName:
                                nodupFileName.append(pdfFile)
                        else:
                                # if duplicate userPDF/userNLM, then remove the duplicate
                                if userPath in (userPDF, userNLM):
                                        os.remove(os.path.join(pdfPath, pdfFile))
                                else:
                                        dupFileName.append(pdfFile)
        except:
                diagFile.write('skipping folder path: ' + pdfPath + '\n')
                continue

    # step 2: iterate thru input directory by user
    for userPath in os.listdir(inputDir):

        pdfPath = inputDir + '/' + userPath + '/'
        diagFile.write('%s:level1SanityChecks:step 2:%s\n' % (mgi_utils.date(), pdfPath))

        try:
                needsReviewPath = os.path.join(needsReviewDir, userPath)

                for pdfFile in os.listdir(pdfPath):

                        #
                        # if fileName is a duplicate, move to needsReviewPath
                        # do not add userPath info to userDict
                        #
                        if pdfFile in dupFileName:
                                level0error1 += linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR>\n'
                                shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
                                count_needsreview += 1
                                continue

                        #
                        # Add userPath info to userDict dictionary
                        #
                        if userPath not in userDict:
                                userDict[userPath] = []
                        if pdfFile not in userDict[userPath]:
                                userDict[userPath].append(pdfFile)
        except:
                diagFile.write('skipping folder path: ' + pdfPath + '\n')
                continue

    #
    # iterate thru userDict
    #

    for userPath in userDict:

        pdfPath = os.path.join(inputDir, userPath)
        needsReviewPath = os.path.join(needsReviewDir, userPath)
        diagFile.write('%s:level1SanityChecks:userDict:%s\n' % (mgi_utils.date(), pdfPath))

        #
        # for each pdfFile
        # if pdfFile starts with "PMID", then store in objByUser dictionary as 'pm'
        # else if doi id can be found, then store in objByUser dictionary as 'doi'
        # else, report error, move pdf to needs review directory
        #
        for pdfFile in userDict[userPath]:

            pdf = PdfParser.PdfParser(os.path.join(pdfPath, pdfFile))
            doiid = ''
            diagFile.write('%s:level1SanityChecks:PdfParser:%s,%s\n' % (mgi_utils.date(), pdfPath, pdfFile))

            try:
                pdftext = pdf.getText();
                #print('start: PDFTEXT\n')
                #print(pdftext)
                #print('\nend: PDFTEXT\n')
            except:
                #
                # stderr examples:
                #       Permission Error: Copying of text from this document is not allowed.
                #
                level1error1 += linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR>\n'
                level1error1 += '<pre>\n%s\n</pre>\n' % pdf.getStderr()
                fileName = os.path.join(needsReviewPath, pdfFile)
                pdflogFile.write("%s: pdftotext failed. Stderr:\n" % fileName)
                pdflogFile.write(pdf.getStderr())
                pdflogFile.write('\n')
                pdflogFile.flush()
                shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
                count_needsreview += 1
                continue
                
            #
            # may get msg from pdftotext even if no error
            #
            if pdf.getStderr(): 
                fileName = os.path.join(userPath, pdfFile)
                pdflogFile.write("%s: pdftotext succeeded, but has Stderr:\n" % fileName)
                pdflogFile.write(pdf.getStderr())
                pdflogFile.write('\n')
                pdflogFile.flush()

            #
            # if pdftext is null/empty or < 100, needsReview
            #
            if pdftext == None or len(pdftext) < 100:
                level7error1 += 'pdftext file is empty ' + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR>\n'
                shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
                count_lowextractedtext += 1
                continue;

            #
            # if userPath is in the 'userSupplement, userPDF or userNLM' folder
            #	store in objByUser
            #	skip DOI/PMID sanity checks
            #
            # may be in format:
            #	xxxx.pdf, xxxx_Jyyyy.pdf
            #
            if userPath in (userSupplement, userPDF, userNLM):
                try:
                    # store by mgiid
                    tokens = pdfFile.replace('.pdf', '').split('_')
                    mgiid = tokens[0]
                    #diagFile.write(pdftext + "\n\n")
                    if (userPath, userPath, mgiid) not in objByUser:
                        objByUser[(userPath, userPath, mgiid)] = []
                        objByUser[(userPath, userPath, mgiid)].append((pdfFile, pdftext))
                except:
                    level1error1 += linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR>\n'
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
                    if (userPath, 'pm', pmid) not in objByUser:
                        objByUser[(userPath, 'pm', pmid)] = []
                        objByUser[(userPath, 'pm', pmid)].append((pdfFile, pdftext))
                except:
                    level1error4 += linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR>\n'
                    shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
                    count_needsreview += 1
                    continue

            #
            # anything else
            #
            else:
                try:
                    doiid = pdf.getFirstDoiID()

                    if doiid:
                        if doiid not in doiidById:
                            doiidById[doiid] = []
                            doiidById[doiid].append(pdfFile)
                            diagFile.write('%s:pdf.getFirstDoiID():%s/%s:%s\n' % (mgi_utils.date(), pdfPath, pdfFile, doiid))
                            diagFile.flush()
                        else:
                            level1error3 += str(doiid) + '<BR>\n' + \
                                linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + \
                                '<BR>\nduplicate of: ' + userPath + '/' + doiidById[doiid][0] + \
                                '<BR><BR>\n\n'
                            shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
                            count_needsreview += 1
                            continue
                    else:
                        level1error2 += linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR>\n'
                        shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
                        count_needsreview += 1
                        continue
                except Exception as e:
                    level1error2 += linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR>\n'
                    shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
                    count_needsreview += 1
                    # write traceback to pdflog file
                    fileName = os.path.join(needsReviewPath, pdfFile)
                    exOutput = "Exception getting DOI from %s\n" % fileName
                    (t, v, tb) = sys.exc_info()
                    exOutput += ''.join(traceback.format_tb(tb))
                    exOutput += str(e) + '\n'
                    pdflogFile.write(exOutput)
                    pdflogFile.flush()
                    continue

                # store by doiid

                if userPath in (userDiscard):
                   if (userPath, userPath, doiid) not in objByUser:
                      objByUser[(userPath, userPath, doiid)] = []
                      objByUser[(userPath, userPath, doiid)].append((pdfFile, pdftext))
                elif (userPath, objDOI, doiid) not in objByUser:
                    objByUser[(userPath, objDOI, doiid)] = []
                    objByUser[(userPath, objDOI, doiid)].append((pdfFile, pdftext))

    #
    # write out level1 errors to both error log and curator log
    #
    level0error1 = '<B>1: same filename in more than one folder</B><BR><BR>\n\n' + level0error1 + '<BR>\n\n'
    level1error1 = '<B>1: error in PDF text extraction</B><BR><BR>\n\n' + level1error1 + '<BR>\n\n'
    level1error2 = '<B>2: cannot extract/find DOI ID</B><BR><BR>\n\n' + level1error2 + '<BR>\n\n'
    level1error3 = '<B>3: duplicate published refs (same DOI ID)</B><BR><BR>\n\n' + level1error3 + '<BR>\n\n'
    level1error4 = '<B>4: cannot extract PMID</B><BR><BR>\n\n' + level1error4 + '<BR>\n\n'
    allErrors = allErrors + level0errorStart + level0error1 + level1errorStart + level1error1 + level1error2 + level1error3 + level1error4


    return 0

#
# Purpose: Level 2 Sanity Checks : parse PubMed IDs from PubMed API
# Returns: ref object if successful, else returns 1
#
#  1: DOI ID maps to multiple pubmed IDs
#  2: DOI ID not found in pubmed
#  3: error getting medline record
#  4: missing data from required field for DOI ID
#  5: NLM Refresh issues
#
def level2SanityChecks(userPath, objType, objId, pdfFile, pdfPath, needsReviewPath):
    global level2error1, level2error2, level2error3, level2error4
    global level5error1, level5error2
    global pubtypelogFile

    diagFile.write('%s:level2SanityChecks: %s, %s, %s\n' % (mgi_utils.date(), userPath, objId, pdfFile))

    #
    # userNLM : part 1
    # convert objId = mgi to objId = pubmed id
    if objType == userNLM:
        mgiID = 'MGI:' + objId
        sql = '''
            select c._Refs_key, c.mgiID, c.pubmedID, c.doiID, c.journal, r.title
            from BIB_Citation_Cache c, BIB_Refs r
            where c.mgiID = '%s'
            and c.pubmedID is not null
            and c._Refs_key = r._Refs_key
            ''' % (mgiID)
        results = db.sql(sql, 'auto')
        if len(results) > 0:
            objId = results[0]['pubmedID']
        else:
            level5error1 += str(mgiID) + '<BR>\n' + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
            return 1

    if objType in (objDOI, userDiscard):
        # mapping of objId to pubmedID, return list of references
        try:
            mapping = pma.getReferences([objId])
        except:
            diagFile.write('level2SanityChecks:pma.getReferences() needs review: %s, %s, %s\n' % (objId, userPath, pdfFile))
            diagFile.write('  - objId (%s), objDOI (%s), userDiscard (%s)\n' % (objId, objDOI, userDiscard))
            diagFile.write('  - exception info:\n')
            (eType, eValue, eTraceback) = sys.exc_info()
            for line in traceback.format_exception(eType, eValue, eTraceback):
                diagFile.write(' - %s' % line)
            return -1

        refMappingList = mapping[objId]

        #  1: DOI ID maps to multiple pubmed IDs
        if len(refMappingList) > 1:
            for ref in refMappingList:
                level2error1 += str(objId) + ', ' + str(ref.getPubMedID()) + '<BR>\n' + \
                    linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
            return 1

        #  2: DOI ID not found in pubmed
        for ref in refMappingList:
            if ref == None:
                level2error2 += str(objId) + '<BR>\n' + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
                return 1

        pubMedRef = refMappingList[0]
        pubmedID = pubMedRef.getPubMedID()
    else:
        pubmedID = objId
        pubMedRef = pma.getReferenceInfo(pubmedID)
        if pubMedRef.getPubMedID() == None:
            pubMedRef = pma.getReferenceInfo(pubmedID)
        if pubMedRef.getPubMedID() == None:
            pubMedRef = pma.getReferenceInfo(pubmedID)
        if pubMedRef.getPubMedID() == None:
            pubMedRef = pma.getReferenceInfo(pubmedID)

    #  3: error getting medline record
    if not pubMedRef.isValid():
        level2error3 += str(objId) + ', ' + str(pubmedID) + '<BR>\n' + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
        return 1

    # check for required NLM fields
    else:
        # PMID - PubMed unique identifier
        # TI - title of article
        # TA - journal
        # DP - date
        # YR - year
        # PT - Comment|Editorial|News|Published Erratum|Retracetion of Publication

        requiredDict = {}
        missingList = []

        requiredDict['pmId'] = pubMedRef.getPubMedID()
        requiredDict['title'] = pubMedRef.getTitle()
        requiredDict['journal'] = pubMedRef.getJournal()
        requiredDict['date'] = pubMedRef.getDate()
        requiredDict['year'] = pubMedRef.getYear()
        requiredDict['publicationType'] = pubMedRef.getPublicationType()

        #  4: missing data from required field for DOI ID
        for reqLabel in requiredDict:
            if requiredDict[reqLabel] == None:
                missingList.append(reqLabel)
        if len(missingList):
           diagFile.write(str(requiredDict))
           diagFile.write('\n')
           level2error4 += str(objId) + ', ' + str(pubmedID) + '<BR>\n' + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
           return 1

        # skip & delete these publication types
        diagFile.write(requiredDict['publicationType'] + '\n')
        if requiredDict['publicationType'] in ('Comment', 'Editorial', 'News'):
           pubtypelogFile.write(requiredDict['publicationType'] + ',' + objId + ',' + pubmedID + '\n')
           os.remove(os.path.join(pdfPath, pdfFile))
           return -1

    # userNLM : part 2
    # results() where retrieved earlier
    # sanity check the pubmed fields
    if objType == userNLM:

        # match journal/title/doi id in MGD
        mgiID = results[0]['mgiID']
        journal = results[0]['journal']
        title = results[0]['title']
        doiId = results[0]['doiID']

        if pubMedRef.getJournal().lower() != journal.lower() \
            or pubMedRef.getTitle().lower() != title.lower() \
            or (doiId != None and pubMedRef.getDoiID() != doiId):

            level5error2 += str(mgiID) + ',' + str(pubmedID) + '<BR>\n' + \
                    'Journal/NLM: ' + pubMedRef.getJournal() + '<BR>\n' + \
                    'Journal/MGD: ' + journal + '<BR>\n' + \
                    'Title/NLM: ' + pubMedRef.getTitle() + '<BR>\n' + \
                    'Title/MGD: ' + title + '<BR>\n' + \
                    'DOI/NLM: ' + str(pubMedRef.getDoiID()) + '<BR>\n' + \
                    'DOI/MGD: ' + str(doiId) + '<BR>\n' + \
                    linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'

            return 1

    # if successful, return 'pubMedRef' object, else return 1, continue

    return pubMedRef

#
# Purpose: Level 3 Sanity Checks : check MGI for errors
# Returns: returns 0 if successful, 1 if errors are found
#
#  1 : PubMed or DOI ID associated with different MGI references
#  2a: input PubMed ID exists in MGI but missing DOI ID -> add DOI ID in MGI
#  2b: input DOI ID exists in MGI but missing PubMed ID -> add PubMed ID in MGI
#
def level3SanityChecks(userPath, objType, objId, pdfFile, pdfPath, needsReviewPath, ref):
    global level3error1
    global count_needsreview
    global count_duplicate

    # return 0   : add as new reference
    # return 1/2 : skip/move to 'needs review'
    # return 3   : add new accession ids (includes userNLM)
    # return 4   : userNLM : will call processNLMRefresh()

    diagFile.write('%s:level3SanityChecks:%s, %s, %s\n' % (mgi_utils.date(), userPath, objId, pdfFile))

    pubmedID = ref.getPubMedID()

    if objType == objDOI:
        sql = '''
            select c._Refs_key, c.mgiID, c.pubmedID, c.doiID from BIB_Citation_Cache c where c.pubmedID = '%s' or c.doiID = '%s'
            ''' % (pubmedID, objId)
    else:
        sql = '''
            select c._Refs_key, c.mgiID, c.pubmedID, c.doiID
            from BIB_Citation_Cache c
            where c.pubmedID = '%s'
            ''' % (pubmedID)

    results = db.sql(sql, 'auto')

    if objType not in (userNLM) and len(results) > 1:

        # 1: input PubMed ID or DOI ID associated with different MGI references
        diagFile.write('2: input PubMed ID or DOI ID associated with different MGI references: ' + objId + ',' + pubmedID + '\n')
        level3error1 += str(objId) + ', ' + str(pubmedID) + '<BR>\n' + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
        shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
        count_needsreview += 1
        return 2, results

    elif len(results) == 1:

        if objType in (objDOI):

            # 1: input PubMed ID or DOI ID associated with different MGI references
            if results[0]['pubmedID'] != None and results[0]['doiID'] != None:
                if (pubmedID == results[0]['pubmedID'] and objId != results[0]['doiID']) or \
                   (pubmedID != results[0]['pubmedID'] and objId == results[0]['doiID']):
                    diagFile.write('1: input PubMed ID or DOI ID associated with different MGI references: ' + objId + ',' + pubmedID + '\n')
                    level3error1 += str(objId) + ', ' + str(pubmedID) + '<BR>\n' + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
                    shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
                    count_needsreview += 1
                    return 2, results

            # 2a: input exists in MGI but missing PubMed ID -> add PubMed ID in MGI
            if results[0]['pubmedID'] == None:
                diagFile.write('2: pubmedID is missing in MGI: ' + objId + ',' + pubmedID + '\n')
                return 3, results

        if objType in (objDOI) or (objType in (userNLM) and ref.getDoiID() != None):

            # 2b: input exists in MGI but missing DOI ID -> add DOI ID in MGI
            if results[0]['doiID'] == None:
                diagFile.write('2: doiid is missing in MGI:' + objId + ',' + pubmedID + '\n')
                return 3, results

        if objType in (userNLM):
            return 4, results
        else:
            # duplicates are logged in duplicatelogFile and deleted/not moved to needs_review
            diagFile.write('duplicate: input PubMed ID or DOI ID exists in MGI: ' + objId + ',' + pubmedID + '\n')
            duplicatelogFile.write(userPath + ',' + objId + ', ' + pubmedID + '\n')
            os.remove(os.path.join(pdfPath, pdfFile))
            count_duplicate += 1
            return 1, results
                
    else:
        return 0, results

#
# Purpose: Process/Iterate PDF adds
# Returns: 0
#
def processPDFs():
    global accKey, refKey, mgiKey, jnumKey, dataKey, tagKey, statusKey, relevanceKey
    global mvPDFtoMasterDir
    global updateSQLAll
    global isDiscard
    global isReviewArticle
    global refKeyList
    global count_processPDFs
    global count_needsreview
    global count_userGO
    global count_userGXDHT
    global count_userPDF
    global count_userNLM
    global count_duplicate
    global doipubmedaddedlogFile
    global splitterlogFile
    global count_doipubmedadded
    global level2error5
    global level4error2
    global accList, refList, statusList, dataList, tagList, relevanceList 

    #
    # assumes the level1SanityChecks have passed
    #
    # for all rows in objByUser
    #	get info from pubmed API
    #   generate BCP file
    #   track pdf -> MGI numeric ####
    #

    diagFile.write('\n%s:processPDFs\n' % (mgi_utils.date()))

    # objByUser = {('userPath', 'doi', 'doiid') : ('pdffile', 'pdftext')}
    # objByUser = {('userPath', 'pm', 'pmid') : ('pdffile', 'pdftext')}
    # objByUser = {('userPath', userPDF, 'mgiid') : ('pdffile', 'pdftext')}
    # objByUser = {('userPath', userSupplement, 'mgiid') : ('pdffile', 'pdftext')}
    # objByUser = {('userPath', userGO, 'mgiid') : ('pdffile', 'pdftext')}
    # objByUser = {('userPath', userDiscard, 'mgiid') : ('pdffile', 'pdftext')}

    for key in objByUser:

        diagFile.write('\n%s:objByUser:%s\n' % (mgi_utils.date(), str(key)))

        pdfFile = objByUser[key][0][0]
        extractedText = objByUser[key][0][1]
        userPath = key[0]
        objType = key[1]
        objId = key[2] 
        pdfPath = os.path.join(inputDir, userPath) 
        needsReviewPath = os.path.join(needsReviewDir, userPath)

        isDiscard = relevanceNotSpecKey
        isMice = 0

        #
        # run splitter
        #
        
        bodyText = ''
        refText = ''
        figureText = ''
        starMethodText = ''
        suppText = ''

        if extractedText != None:
            (bodyText, refText, figureText, starMethodText, suppText)  = textSplitter.splitSections(extractedText)

        bodyText = replaceText(bodyText)
        refText = replaceText(refText)
        figureText = replaceText(figureText)
        starMethodText = replaceText(starMethodText)
        suppText = replaceText(suppText)

        #if len(bodyText):
        #    print('FOUND BODY')
        #    print(bodyText)
        #if len(refText):
        #    print('FOUND REF')
        #if len(figureText):
        #    print('FOUND FIGURE')
        #if len(starMethodText):
        #   print('FOUND STAR')
        #if len(suppText):
        #    print('FOUND SUPP')

        #
        # only interested in running checkMice for curator folders, etc.
        # if non-refText section checkMice = false, then isDiscard = relevanceDiscardKey
        #
        if userPath not in (userSupplement, userPDF, userGO, userGXDHT, userNLM, userDiscard):
            if bodyText.lower().find(checkMice) < 0 \
                and figureText.lower().find(checkMice) < 0 \
                and suppText.lower().find(checkMice) < 0 \
                and starMethodText.lower().find(checkMice) < 0 :

                    isDiscard = relevanceDiscardKey
                    isMice = 1

        # TR 12871/ERRATUM/correction/retraction
        # ignore littriage_xxxx folders
        # ignore 'bonferroni correction'
        checkErratum = 1
        isErratum = 0
        if userPath not in (userSupplement, userPDF, userGO, userGXDHT, userNLM, userDiscard) and objType not in ('pm'):
            diagFile.write('ERRATUM:searching:%s, %s, %s\n' % (objId, userPath, pdfFile))
            for e in erratumExcludeList:
                if bodyText.lower().find(e) >= 0:
                        diagFile.write('ERRATUM:skipping/excluded:%s, %s, %s, %s\n' % (e, objId, userPath, pdfFile))
                        checkErratum = 0
            if checkErratum == 1:
                for e in erratumIncludeList:
                        erratumFind = bodyText.lower().find(e)
                        if erratumFind >= 0 and erratumFind <= erratumPosition:
                                isErratum = 1
            # continue to next pdf
            if isErratum == 1:
                diagFile.write('ERRATUM:found/included:%s, %s, %s, %s\n' % (e, objId, userPath, pdfFile))
                level2error5 += linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR>\n'
                shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
                count_needsreview += 1
                continue
        else:
            diagFile.write('ERRATUM:skipping:%s, %s, %s\n' % (objId, userPath, pdfFile))

        # process supplemental but suppText not found
        if userPath in (userSupplement) and len(suppText) == 0:
            level4error2 += str(objId) + '<BR>\n' + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
            count_needsreview += 1
            diagFile.write('userSupplement:needs review:%s, %s, %s\n' % (objId, userPath, pdfFile))
            shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
            continue

        # process pdf/supplement
        if userPath in (userPDF, userSupplement):
            processExtractedText(key, bodyText, refText, figureText, starMethodText, suppText)
            continue

        #
        # level2SanityChecks()
        # parse PubMed IDs from PubMed API
        #
        pubmedRef = level2SanityChecks(userPath, objType, objId, pdfFile, pdfPath, needsReviewPath)

        if pubmedRef == -1:
           continue

        if pubmedRef == 1:
           diagFile.write('level2SanityChecks():needs review:%s, %s, %s, %s\n' % (objId, userPath, pdfFile, str(pubmedRef)))
           shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
           count_needsreview += 1
           continue

        try:
           pubmedID = pubmedRef.getPubMedID()
        except:
           diagFile.write('process:pubmedRef.getPubMedID()() needs review:%s, %s, %s\n' % (objId, userPath, pdfFile))
           continue

        try:
           doiID = pubmedRef.getDoiID()
        except:
           doiID = ''

        diagFile.write('level2SanityChecks():successful:%s, %s, %s, %s\n' % (objId, userPath, pdfFile, pubmedID))
        diagFile.flush()

        #
        # level3SanityChecks()
        # check MGI for errors
        #
        # return 0   : add as new reference
        # return 1/2 : skip/move to 'needs review'
        # return 3   : add new accession ids (userNLM included)
        # return 4   : userNLM : will call processNLMRefresh()
        #
        rc, mgdRef = level3SanityChecks(userPath, objType, objId, pdfFile, pdfPath, needsReviewPath, pubmedRef)

        if rc == 1 or rc == 2:
            diagFile.write('level3SanityChecks():needs review:%s, %s, %s, %s\n' % (objId, userPath, pdfFile, pubmedID))
            continue

        #
        # add accession ids to existing MGI reference
        #
        elif rc == 3:

            diagFile.write('level3SanityChecks():successful:add PubMed ID or DOI ID:%s, %s, %s, %s, %s\n' \
                % (objId, userPath, pdfFile, pubmedID, str(mgdRef)))
            diagFile.flush()

            # add pubmedID or doiId
            userKey = loadlib.verifyUser(userPath, 0, diagFile)
            objectKey = mgdRef[0]['_Refs_key']

            if objType in (userNLM):
                objId = pubmedRef.getDoiID()
                if objId == None: # do nothing
                    continue

            if mgdRef[0]['pubmedID'] == None:
                accID = pubmedID
                prefixPart = ''
                numericPart = accID
                logicalDBKey = 29
            else: # objId = doiid
                accID = objId
                prefixPart = accID
                numericPart = ''
                logicalDBKey = 65

            accRow = '%s|%s|%s|%s|%s|%d|%d|0|1|%s|%s|%s|%s' \
                % (accKey, accID, prefixPart, numericPart, logicalDBKey, objectKey, mgiTypeKey, userKey, userKey, loaddate, loaddate)
            accList.append(accRow)

            accKey += 1
            doipubmedaddedlogFile.write('%s, %s, %s, %s\n' % (objId, pdfFile, pubmedID, str(mgdRef)))
            count_doipubmedadded += 1

        # add new MGI reference
        #
        elif rc == 0 and objType not in (userNLM): 

            diagFile.write('level3SanityChecks():successful:add new:%s, %s, %s, %s\n' % (objId, userPath, pdfFile, pubmedID))
            diagFile.flush()

            # add pubmedID or doiId
            userKey = loadlib.verifyUser(userPath, 0, diagFile)
            logicalDBKey = 1

            #
            # bib_refs
            #

            authors, primaryAuthor, title, abstract, vol, issue, pgs = replacePubMedRef(\
                0,
                pubmedRef.getAuthors(), \
                pubmedRef.getPrimaryAuthor(), \
                pubmedRef.getTitle(), \
                pubmedRef.getAbstract(), \
                pubmedRef.getVolume(), \
                pubmedRef.getIssue(), \
                pubmedRef.getPages(),
                pubmedRef.getElocator())

            if pubmedRef.getPublicationType() in ('Review', 'Systematic Review'):
                isReviewArticle = 1
            else:
                isReviewArticle = 0

            # TR12958/userDiscard folder
            if objType in (userDiscard):
                isDiscard = relevanceDiscardKey
            #else:
            #    isDiscard = relevanceNotSpecKey

            #
            # skip, no need to report this as an error
            #
            if refKey in refKeyList:
                continue

            refRow = '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s' \
                % (refKey, referenceTypeKey, 
                   authors, \
                   primaryAuthor, \
                   title, \
                   pubmedRef.getJournal(), \
                   vol, \
                   issue, \
                   pubmedRef.getDate(), \
                   pubmedRef.getYear(), \
                   pgs, \
                   abstract, \
                   isReviewArticle, \
                   userKey, userKey, loaddate, loaddate)
            refList.append(refRow)

            refKeyList.append(refKey)
            count_processPDFs += 1

            #
            # bib_workflow_relevance
            # 1 row; set isCurrent = 1; set confidence = null
            relevanceRow = '%s|%s|%s|1||%s|%s|%s|%s|%s' \
                        %(relevanceKey, refKey, isDiscard, relevanceVersion, userLTKey, userLTKey, loaddate, loaddate)
            relevanceList.append(relevanceRow)
            relevanceKey += 1

            #
            # bib_workflow_status
            # 1 row per Group
            #
            for groupKey in workflowGroupList:
                # if userGO and group = GO, then status = Full-coded
                if userPath in (userGO) and groupKey == 31576666:
                    statusRow = '%s|%s|%s|%s|%s|%s|%s|%s|%s' \
                        % (statusKey, refKey, groupKey, statusFullCodedKey, isCurrent, userKey, userKey, loaddate, loaddate)
                    statusList.append(statusRow)
                elif userPath in (userGXDHT) and groupKey == 114000000:
                    statusRow = '%s|%s|%s|%s|%s|%s|%s|%s|%s' \
                        % (statusKey, refKey, groupKey, statusChosenKey, isCurrent, userKey, userKey, loaddate, loaddate)
                    statusList.append(statusRow)
                else:
                    statusRow = '%s|%s|%s|%s|%s|%s|%s|%s|%s' \
                        % (statusKey, refKey, groupKey, newCodedKey, isCurrent, userKey, userKey, loaddate, loaddate)
                    statusList.append(statusRow)
                statusKey += 1

            #
            # bib_workflow_data/body
            # check full extracted text to set supplemental key
            hasPDF = 1
            suppKey = setSupplemental(userPath, extractedText)
            dataRow = '%s|%s|%s|%s||%s|%s|%s|%s|%s|%s' \
                % (dataKey, refKey, hasPDF, suppKey, bodySectionKey, bodyText, userKey, userKey, loaddate, loaddate)
            dataList.append(dataRow)
            dataKey += 1

            # for any other section...i.e. not 'body'
            hasPDF = 0
            suppKey = suppNotApplKey
            if len(refText) > 0:
                dataRow = '%s|%s|%s|%s||%s|%s|%s|%s|%s|%s' \
                    % (dataKey, refKey, hasPDF, suppKey, refSectionKey, refText, userKey, userKey, loaddate, loaddate)
                dataList.append(dataRow)
                dataKey += 1
            if len(figureText) > 0:
                dataRow = '%s|%s|%s|%s||%s|%s|%s|%s|%s|%s' \
                    % (dataKey, refKey, hasPDF, suppKey, figureSectionKey, figureText, userKey, userKey, loaddate, loaddate)
                dataList.append(dataRow)
                dataKey += 1
            if len(starMethodText) > 0:
                dataRow = '%s|%s|%s|%s||%s|%s|%s|%s|%s|%s' \
                    % (dataKey, refKey, hasPDF, suppKey, starMethodSectionKey, starMethodText, userKey, userKey, loaddate, loaddate)
                dataList.append(dataRow)
                dataKey += 1
            if len(suppText) > 0:
                dataRow = '%s|%s|%s|%s||%s|%s|%s|%s|%s|%s' \
                    % (dataKey, refKey, hasPDF, suppKey, suppSectionKey, suppText, userKey, userKey, loaddate, loaddate)
                dataList.append(dataRow)
                dataKey += 1

            #
            # bib_workflow_tag/mice is in reference only
            if isMice == 1:
                tagRow = '%s|%s|%s|%s|%s|%s|%s' \
                        %(tagKey, refKey, miceInRefOnlyKey, userKey, userKey, loaddate, loaddate)
                tagList.append(tagRow)
                tagKey += 1

            #####
            # add other extracted text sections here
            #####

            # MGI:xxxx
            #
            mgiID = mgiPrefix + str(mgiKey)
            accRow = '%s|%s|%s|%s|%s|%d|%d|%s|%s|%s|%s|%s|%s' \
                % (accKey, mgiID, mgiPrefix, mgiKey, logicalDBKey, refKey, mgiTypeKey, \
                   isPrivate, isPreferred, userKey, userKey, loaddate, loaddate)
            accList.append(accRow)
            accKey += 1
            
            #
            # pubmedID
            #
            accID = pubmedID
            prefixPart = ''
            numericPart = accID
            logicalDBKey = 29

            accRow = '%s|%s|%s|%s|%s|%d|%d|%s|%s|%s|%s|%s|%s' \
                % (accKey, accID, prefixPart, numericPart, logicalDBKey, refKey, mgiTypeKey, \
                   isPrivate, isPreferred, userKey, userKey, loaddate, loaddate)
            accList.append(accRow)
            accKey += 1

            #
            # doiID only
            #
            if doiID != '':
                accID = doiID
                prefixPart = accID
                numericPart = ''
                logicalDBKey = 65

                accRow = '%s|%s|%s|%s|%s|%d|%d|%s|%s|%s|%s|%s|%s' \
                        % (accKey, accID, prefixPart, numericPart, logicalDBKey, refKey, mgiTypeKey, \
                        isPrivate, isPreferred, userKey, userKey, loaddate, loaddate)
                accList.append(accRow)
                accKey += 1

            elif objType in (objDOI, userDiscard):
                accID = objId
                prefixPart = accID
                numericPart = ''
                logicalDBKey = 65

                accRow = '%s|%s|%s|%s|%s|%d|%d|%s|%s|%s|%s|%s|%s' \
                        % (accKey, accID, prefixPart, numericPart, logicalDBKey, refKey, mgiTypeKey, \
                        isPrivate, isPreferred, userKey, userKey, loaddate, loaddate)
                accList.append(accRow)
                accKey += 1

            #
            # J:xxxx
            #
            if userPath in (userGO, userGXDHT):
                accID = 'J:' + str(jnumKey)
                prefixPart = 'J:'
                numericPart = jnumKey
                logicalDBKey = 1
                accRow = '%s|%s|%s|%s|%s|%d|%d|%s|%s|%s|%s|%s|%s' \
                        % (accKey, accID, prefixPart, numericPart, logicalDBKey, refKey, mgiTypeKey, \
                        isPrivate, isPreferred, userKey, userKey, loaddate, loaddate)
                accList.append(accRow)
                accKey += 1
                jnumKey += 1
                if userPath in (userGO):
                    count_userGO += 1
                elif userPath in (userGXDHT):
                    count_userGXDHT += 1

            #
            # if splitter does not find reference section
            #
            if extractedText != None and len(refText) == 0:
                (bodyInfo, refInfo, figureInfo, starMethodInfo, suppInfo)  = textSplitter.findSections(extractedText)
                splitterlogFile.write('%s, %s, %s, %s, %s, %s, %s, %s\n' \
                        % (pubmedID, mgiID, str(len(bodyText)), str(len(refText)), str(len(figureText)), \
                           str(len(starMethodText)), str(len(suppText)), refInfo))

            # store dictionary : move pdf file from inputDir to masterPath
            newPath = Pdfpath.getPdfpath(masterDir, mgiID)
            mvPDFtoMasterDir[pdfPath + '/' + pdfFile] = []
            mvPDFtoMasterDir[pdfPath + '/' + pdfFile].append((newPath,str(mgiKey) + '.pdf'))

            refKey += 1
            mgiKey += 1

        #
        # not using 'elif' statement because this needs to be checked/run regardless
        # of what also may have happened earlier
        #
        # processing for nlm refresh
        #
        if rc == 4 or objType in (userNLM): 
            processNLMRefresh(key, pubmedRef, bodyText, refText, figureText, starMethodText, suppText)

    diagFile.flush()
    return 0

#
# Purpose: Process Extracted Text/Suppliement (userSupplement, userPDF) : see processPDFs()
# Returns: nothing
#
# bib_workflow_data: 
#	store extracted
#	hasPDF = 1
#	if userSupplement, _supplimental_key = 34026997/'Supplement attached'
#
def processExtractedText(objKey, bodyText, refText, figureText, starMethodText, suppText):
    global level4error1
    global mvPDFtoMasterDir
    global deleteSQLAll, updateSQLAll
    global count_userSupplement
    global count_needsreview
    global count_userPDF
    global count_userNLM
    global existingRefKeyList
    global dataKey
    global accList, refList, statusList, dataList, tagList, relevanceList 
    global statusKey

    diagFile.write('\n%s:processExtractedText()\n' % (mgi_utils.date()))

    # objByUser = {('userPath', userPDF, 'mgiid') : ('pdffile', 'pdftext')}
    # objByUser = {('userPath', userSupplement, 'mgiid') : ('pdffile', 'pdftext')}
    # objByUser = {('userPath', userNLM, 'mgiid') : ('pdffile', 'pdftext')}

    pdfFile = objByUser[objKey][0][0]
    extractedText = objByUser[objKey][0][1]
    userPath = objKey[0]
    objType = objKey[1]
    mgiKey = objKey[2]
    mgiID = 'MGI:' + mgiKey
    pdfPath = os.path.join(inputDir, userPath)
    needsReviewPath = os.path.join(needsReviewDir, userPath)

    sql = '''select r._Refs_key, d._Supplemental_key
        from BIB_Citation_Cache r, BIB_Workflow_Data d 
        where r.mgiID = '%s'
        and r._Refs_key = d._Refs_key
        and d._extractedtext_key = 48804490
        ''' % (mgiID)
    results = db.sql(sql, 'auto')

    if len(results) == 0:
        level4error1 += str(mgiID) + '<BR>\n' + linkOut % (needsReviewPath + '/' + pdfFile, needsReviewPath + '/' + pdfFile) + '<BR><BR>\n\n'
        count_needsreview += 1
        diagFile.write('userPDF/userSupplement/userNLM level1:needs review:%s, %s, %s\n' % (mgiID, userPath, pdfFile))
        shutil.move(os.path.join(pdfPath, pdfFile), os.path.join(needsReviewPath, pdfFile))
        return

    existingRefKey = results[0]['_Refs_key']
    suppKey = results[0]['_Supplemental_key']
    userKey = loadlib.verifyUser(userPath, 0, diagFile)

    # if this reference's extracted text has already been processed by another folder, skip it
    if existingRefKey not in existingRefKeyList:
        existingRefKeyList.append(existingRefKey)
    else:
        return

    if objType == userSupplement:
        dataSuppKey = suppAttachedKey
        count_userSupplement += 1

        #
        # flr2-56/if GXD Status = Not Routed or Rejected, then set GXD Status = New
        # wts2-1092/remove Rejected
        #
        gxdCheck = db.sql('''
                select _assoc_key from bib_workflow_status 
                where _refs_key = %s
                and isCurrent = 1 
                and _group_key = 31576665
                and _status_key = 31576669
                ''' % (existingRefKey), 'auto')
        if len(gxdCheck) == 1:
            updateSQLAll.append('update BIB_Refs set _ModifiedBy_key = %s, modification_date = now() where _Refs_key = %s;\n' \
                % (userKey, existingRefKey))
            updateSQLAll.append('update bib_workflow_status set isCurrent = 0 where _assoc_key = %s;\n' % (gxdCheck[0]['_assoc_key']))
            statusRow = '%s|%s|31576665|71027551|1|%s|%s|%s|%s' % (statusKey, existingRefKey, userKey, userKey, loaddate, loaddate)
            statusList.append(statusRow)
            statusKey += 1

    elif objType == userPDF:
        dataSuppKey = suppKey
        count_userPDF += 1
    else:
        dataSuppKey = suppKey
        count_userNLM += 1

    # re-add body
    hasPDF = 1
    dataRow = '%s|%s|%s|%s||%s|%s|%s|%s|%s|%s' \
        % (dataKey, existingRefKey, hasPDF, dataSuppKey, bodySectionKey, bodyText, userKey, userKey, loaddate, loaddate)
    dataList.append(dataRow)
    dataKey += 1 

    # for any other section...i.e. not 'body'
    hasPDF = 0
    dataSuppKey = suppNotApplKey
    if len(refText) > 0: 
        dataRow = '%s|%s|%s|%s||%s|%s|%s|%s|%s|%s' \
            % (dataKey, existingRefKey, hasPDF, dataSuppKey, refSectionKey, refText, userKey, userKey, loaddate, loaddate)
        dataList.append(dataRow)
        dataKey += 1 
    if len(figureText) > 0: 
        dataRow = '%s|%s|%s|%s||%s|%s|%s|%s|%s|%s' \
            % (dataKey, existingRefKey, hasPDF, dataSuppKey, figureSectionKey, figureText, userKey, userKey, loaddate, loaddate)
        dataList.append(dataRow)
        dataKey += 1 
    if len(starMethodText) > 0: 
        dataRow = '%s|%s|%s|%s||%s|%s|%s|%s|%s|%s' \
            % (dataKey, existingRefKey, hasPDF, dataSuppKey, starMethodSectionKey, starMethodText, userKey, userKey, loaddate, loaddate)
        dataList.append(dataRow)
        dataKey += 1 
    if len(suppText) > 0: 
        dataRow = '%s|%s|%s|%s||%s|%s|%s|%s|%s|%s' \
            % (dataKey, existingRefKey, hasPDF, dataSuppKey, suppSectionKey, suppText, userKey, userKey, loaddate, loaddate)
        dataList.append(dataRow)
        dataKey += 1 

    deleteSQLAll += 'delete from BIB_Workflow_Data where _Refs_key = %s;\n' % (existingRefKey)
    updateSQLAll.append('update BIB_Refs set _ModifiedBy_key = %s, modification_date = now() where _Refs_key = %s;\n' % (userKey, existingRefKey))

    # store dictionary : move pdf file from inputDir to masterPath
    newPath = Pdfpath.getPdfpath(masterDir, mgiID)
    mvPDFtoMasterDir[pdfPath + '/' + pdfFile] = []
    mvPDFtoMasterDir[pdfPath + '/' + pdfFile].append((newPath,str(mgiKey) + '.pdf'))

    diagFile.flush()
    return

#
# Purpose: Process NLM Refresh (userNLM)
# Returns: nothing
#
# updates BIB_Refs fields
# call processExtractedText (extracted text & supplemental)
#
def processNLMRefresh(objKey, ref, bodyText, refText, figureText, starMethodText, suppText):
    global updateSQLAll

    diagFile.write('\n%s:processNLMRefresh()\n' % (mgi_utils.date()))

    # objByUser = {('userPath', userNLM, 'mgiid') : ('pdffile', 'pdftext')}

    userPath = objKey[0]
    mgiID = 'MGI:' + objKey[2]

    sql = '''
           select c._Refs_key
           from BIB_Citation_Cache c
           where c.mgiID = '%s'
           ''' % (mgiID)
    results = db.sql(sql, 'auto')

    userKey = loadlib.verifyUser(userPath, 0, diagFile)
    objectKey = results[0]['_Refs_key']

    authors, primaryAuthor, title, abstract, vol, issue, pgs = replacePubMedRef(\
        1,
        ref.getAuthors(), \
        ref.getPrimaryAuthor(), \
        ref.getTitle(), \
        ref.getAbstract(),
        ref.getVolume(),
        ref.getIssue(),
        ref.getPages(),
        ref.getElocator())

    #
    # set '' to true null, not 'None'
    #
    if len(authors) > 0:
        authors = ''' '%s' ''' % (authors)
    else:
        authors = 'null'
    if len(primaryAuthor) > 0:
        primaryAuthor = ''' '%s' ''' % (primaryAuthor)
    else:
        primaryAuthor = ' null'
    if len(title) > 0:
        title = ''' E'%s' ''' % (title)
    else:
        title = ' null'
    if len(abstract) > 0:
        abstract = ''' E'%s' ''' % (abstract)
    else:
        abstract = ' null'
    if len(vol) > 0:
        vol = ''' E'%s' ''' % (vol)
    else:
        vol = ' null'
    if len(issue) > 0:
        issue = ''' E'%s' ''' % (issue)
    else:
        issue = ' null'
    if len(pgs) > 0:
        pgs = ''' E'%s' ''' % (pgs)
    else:
        pgs = ' null'
    if ref.getPublicationType() in ('Review', 'Systematic Review'):
        isReviewArticle = 1
    else:
        isReviewArticle = 0

    newUpdate = '''
                update BIB_Refs 
                set 
                authors = %s,
                _primary = %s,
                title = %s,
                journal = E'%s',
                vol = %s,
                issue = %s,
                date = '%s',
                year = %s,
                pgs = %s,
                isReviewArticle = %s,
                abstract = %s,
                _ModifiedBy_key = %s, 
                modification_date = now() 
                where _Refs_key = %s
                ;
                ''' % (authors, 
                       primaryAuthor, \
                       title, \
                       ref.getJournal(), \
                       vol, \
                       issue, \
                       ref.getDate(), \
                       ref.getYear(), \
                       pgs, \
                       isReviewArticle, \
                       abstract, \
                       userKey, objectKey)

    updateSQLAll.append(newUpdate)

    #
    # process extracted text
    #
    processExtractedText(objKey, bodyText, refText, figureText, starMethodText, suppText)

    diagFile.flush()
    return

#
# Purpose: write errors to error log
# Returns: nothing
#
def writeErrors():
    global allErrors, allCounts
    global level2error1, level2error2, level2error3, level2error4, level2error5
    global level3error1
    global level4error1
    global level4error2
    global level5error1, level5error2
    global level6error1
    global level7error1
    global count_processPDFs
    global count_needsreview
    global count_userGO
    global count_userGXDHT
    global count_userPDF
    global count_userNLM
    global count_duplicate
    global count_doipubmedadded
    global count_mismatchedtitles
    global count_lowextractedtext

    #
    # write out level2 errors to both error log and curator log
    #
    level2error1 = '<B>1: DOI ID maps to multiple pubmed IDs</B><BR><BR>\n\n' + level2error1 + '<BR>\n\n'
    level2error2 = '<B>2: DOI ID not found in pubmed</B><BR><BR>\n\n' + level2error2 + '<BR>\n\n'
    level2error3 = '<B>3: error getting medline record</B><BR><BR>\n\n' + level2error3 + '<BR>\n\n'
    level2error4 = '<B>4: missing data from required field for DOI ID</B><BR><BR>\n\n' + level2error4 + '<BR>\n\n'
    level2error5 = '<B>1a: Possible correction/retraction</B><BR><BR>\n\n' + level2error5 + '<BR>\n\n'
    allErrors = allErrors + level2errorStart + level2error5 + level2error1 + level2error2 + level2error3 + level2error4

    level3error1 = '<B>1: PubMed ID/DOI ID is associated with different MGI references</B><BR><BR>\n\n' + \
        level3error1 + '<BR>\n\n'
    allErrors = allErrors + level3errorStart + level3error1

    level4error1 = '<B>1: MGI ID in filename does not match reference in MGI</B><BR><BR>\n\n' + level4error1 + '<BR>\n\n'
    level4error2 = '<B>2: PDF does not contain the text "MGI Lit Triage Supplemental Data".  Cannot find the Supplemental data section.</B><BR><BR>\n\n' + level4error2 + '<BR>\n\n'
    allErrors = allErrors + level4errorStart + level4error1 + level4error2

    level5error1 = '<B>1: MGI ID not found or no pubmedID</B><BR><BR>\n\n' + level5error1 + '<BR>\n\n'
    level5error2 = '<B>2: journal/title/doi ID do not match</B><BR><BR>\n\n' + level5error2 + '<BR>\n\n'
    allErrors = allErrors + level5errorStart + level5error1 + level5error2

    allErrors = allErrors + level6errorStart + level6error1
    allErrors = allErrors + level7errorStart + level7error1

    # copy all errors to error log, remove html and copy to curator log
    allCounts = allCounts + countStart
    allCounts = allCounts + 'Successful PDF\'s processed (All New_Newcurrent curator & PDF download directories): ' + str(count_processPDFs) + '<BR>\n\n'
    allCounts = allCounts + 'Records with Supplemental data added: ' + str(count_userSupplement) + '<BR>\n\n'
    allCounts = allCounts + 'Records with Updated PDF\'s: ' + str(count_userPDF) + '<BR>\n\n'
    allCounts = allCounts + 'Records with Updated NLM information: ' + str(count_userNLM) + '<BR>\n\n'
    allCounts = allCounts + 'Records with GO information: ' + str(count_userGO) + '<BR>\n\n'
    allCounts = allCounts + 'Records with GXD-HT information: ' + str(count_userGXDHT) + '<BR>\n\n'
    allCounts = allCounts + 'Records with Duplicates: ' + str(count_duplicate) + '<BR>\n\n'
    allCounts = allCounts + 'Records with DOI or Pubmed Ids added: ' + str(count_doipubmedadded) + '<BR>\n\n'
    allCounts = allCounts + 'Records with Mismatched titles: ' + str(count_mismatchedtitles) + '<BR>\n\n'
    allCounts = allCounts + 'Records with Low Extracted Text: ' + str(count_lowextractedtext) + '<BR>\n\n'
    allCounts = allCounts + 'New Failed PDFs in Needs_Review folder: ' + str(count_needsreview) + '<BR>\n\n'

    errorFile.write(allCounts)
    errorFile.write(allErrors)
    curatorFile.write(re.sub('<.*?>', '', allCounts))
    curatorFile.write(re.sub('<.*?>', '', allErrors))

    if errorFile:
        errorFile.close()
    if curatorFile:
        curatorFile.close()

    return 0

#
# Purpose: Post-Sanity Check tasks
# Returns: title or extractedText
#
# title = title.replace('omega', 'x')
# cannot replace omega since 'omega' is this word is also used in non-greek letter wording
# for example, "cytomegalovirus"
#
def postSanityCheck_replaceTitle1(r):
    title = r['title']
    title = title.replace('.', '')
    title = title.replace('-', '')
    title = title.replace('(', '')
    title = title.replace(')', '')
    title = title.replace('\'', '')
    title = title.replace('alpha', '')
    title = title.replace('-beta-', '-b-')
    title = title.replace('beta', '')
    title = title.replace('gamma', '')
    title = title.replace('delta', '')
    title = title.replace('epsilon', '')
    title = title.replace('kappa', '')
    title = title.replace('lambda', '')
    title = title.replace('theta', '')
    title = title.replace('zeta', '')
    title = title.replace('....', '')
    title = title.replace('+', '')
    title = title.replace('editor\'s highlight:', '')
    title = title.replace('editors highlight:', '')
    title = title[:10]
    return title

def postSanityCheck_replaceTitle2(r):
    title = r['title']
    title = title.replace('.', '')
    title = title.replace('-', '')
    title = title.replace('(', '')
    title = title.replace(')', '')
    title = title.replace('\'', '')
    title = title.replace('alpha', 'a')
    title = title.replace('-beta-', '-b-')
    title = title.replace('beta', 'b')
    title = title.replace('gamma', 'g')
    title = title.replace('delta', 'd')
    title = title.replace('epsilon', 'e')
    title = title.replace('kappa', 'k')
    title = title.replace('lambda', 'L')
    title = title.replace('theta', 't')
    title = title.replace('zeta', 'z')
    title = title.replace('....', '')
    title = title.replace('+', '')
    title = title.replace('editor\'s highlight:', '')
    title = title.replace('editors highlight:', '')
    title = title[:10]
    return title

def postSanityCheck_replaceExtracted(r):
    extractedText = r['extractedText']
    extractedText = extractedText.replace('\n', ' ')
    extractedText = extractedText.replace('\r', ' ')
    extractedText = extractedText.replace('.', '')
    extractedText = extractedText.replace('-', '')
    extractedText = extractedText.replace('(', '')
    extractedText = extractedText.replace(')', '')
    extractedText = extractedText.replace('\'', '')
    extractedText = extractedText.replace('alpha', '')
    extractedText = extractedText.replace('beta', '')
    extractedText = extractedText.replace('delta', '')
    extractedText = extractedText.replace('gamma', '')
    extractedText = extractedText.replace('kappa', '')
    #extractedText = extractedText.replace('omega', 'x')
    extractedText = extractedText.replace('theta', '')
    extractedText = extractedText.replace('zeta', '')
    extractedText = extractedText.replace('....', '')
    extractedText = extractedText.replace('+', '')
    return extractedText

#
# Purpose: Query database to check for potential mismatches (TR12836)
# Returns: nothing
#
def postSanityCheck():

    global level6error1
    global level7error1
    global count_mismatchedtitles
    global count_lowextractedtext

    querydate = mgi_utils.date('%m/%d/%Y')

    cmd = '''
    select a.accID as mgiID,
    lower(substring(r.title,1,20)) as title,
    lower(d.extractedText) as extractedText
    from acc_accession a, bib_refs r, bib_workflow_data d
    where r._referencetype_key = 31576687
    and r.title is not null
    and r.journal not in ('J Virol', 'J Neurochem')
    and r._refs_key = a._object_key
    and a._logicaldb_key = 1
    and a._mgitype_key = 1
    and a.prefixpart = 'MGI:'
    and a._object_key = d._refs_key
    and d._extractedtext_key = 48804490
    and d.extractedText is not null
    and (r.creation_date between '%s' and ('%s'::date + '1 day'::interval))
    ''' % (querydate, querydate)

    results = db.sql(cmd, 'auto')
    for r in results:

        title = postSanityCheck_replaceTitle1(r)
        extractedText = postSanityCheck_replaceExtracted(r)

        if extractedText.find(title) < 0:
            title = postSanityCheck_replaceTitle2(r)
            if extractedText.find(title) < 0:
                level6error1 += r['mgiID'] + '<BR>\n'
                count_mismatchedtitles += 1

    #
    # 'Peer Reviewed' references
    # bodyText = null or len(bodyText) < 100
    # hasPDF = 1
    #
    cmd = '''
    select distinct c.mgiid, c.pubmedid, c.short_citation, d.extractedText, r.creation_date
    from bib_refs r, bib_citation_cache c, bib_workflow_data d
    where r._referencetype_key = 31576687
    and r._refs_key = c._refs_key
    and r._refs_key = d._refs_key
    and d._extractedtext_key = 48804490
    and d.hasPDF = 1
    and (d.extractedText is null or length(d.extractedText) < 100)
    and (r.creation_date between '%s' and ('%s'::date + '1 day'::interval))
    ''' % (querydate, querydate)
    results = db.sql(cmd, 'auto')
    for r in results:
        level7error1 += r['mgiID'] + '<BR>\n'
        count_lowextractedtext += 1

    return 0

#
#  MAIN
#

#print('initialize')
if initialize() != 0:
    sys.exit(1)

#print('level1SanityChecks')
if level1SanityChecks() != 0:
    closeFiles()
    sys.exit(1)

#print('setPrimaryKeys')
if setPrimaryKeys() != 0:
    sys.exit(1)

#print('processPDFs')
if processPDFs() != 0:
    closeFiles()
    sys.exit(1)

#print('bcpFiles')
if bcpFiles() != 0:
    sys.exit(1)

#print('postSanityCheck')
if postSanityCheck() != 0:
    sys.exit(1)

#print('writeErrors')
if writeErrors() != 0:
    sys.exit(1)
    
closeFiles()
sys.exit(0)
