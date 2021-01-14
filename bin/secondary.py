#
#  Purpose:
#
#  secondary triage :
#
#       http://mgiprodwiki/mediawiki/index.php/sw:Secondary_Triage_Loader_Requirements#Tumor_Criteria
#
# AP Criteria
# References: relevance status = "keep", APstatus = "New"
# text to search: extracted text except reference section
# text to look for: (case insensitive)
# 
# GXD Criteria
# References: relevance status = "keep", GXDstatus = "New"
# References: relevance status = "discard", confidence > -1.0
# text to search: extracted text except reference section
# text criteria: '%embryo%' ; exclude list (vocab_key 135). (case insensitive)
# 
# QTL Criteria
# References: relevance status = "keep", QTLstatus = "New"
# text to search: extracted text except reference section
# text to look for: 'qtl' (case insensitive)
#
# Tumor Criteria
# References: relevance status = "keep", Tumor status = "New"
# text to search: extracted text except reference section
# text criteria: exclude list (vocab_key 164). (case insensitive)
#
# logFile = 
#       mgiid, pubmedid, confidence, term, matchesTerm, subText
#
# outputFile = 
#       mgiid, pubmedid, onfidence, term, matchesTerm, matchesExcludedTerm, allSubText
#

import sys
import os
import re
import db
import mgi_utils
import loadlib

db.setTrace()

statusFile = ''
statusFileName = ''
statusTable = 'BIB_Workflow_Status'
statusKey = 0
userKey = 1618

bcpScript = os.getenv('PG_DBUTILS') + '/bin/bcpin.csh'
outputDir = os.getenv('OUTPUTDIR')
logDir = os.getenv('LOGDIR')

results = db.sql(''' select nextval('bib_workflow_status_seq') as maxKey ''', 'auto')
statusKey = results[0]['maxKey']

allIsCurrentSql = ''
setIsCurrentSql = '''update bib_workflow_status set isCurrent = 0 where isCurrent = 1 and _group_key = %s and _refs_key = %s;\n'''

bcpI = '%s %s %s' % (bcpScript, db.get_sqlServer(), db.get_sqlDatabase())
bcpII = '"|" "\\n" mgd'
bcpCmd = []

loaddate = loadlib.loaddate

isCurrent = "1"
routedKey = "31576670"
notroutedKey = "31576669"

searchTerms = []
excludedTerms = []
sql = ''
extractedSql = ''

def initialize():
        global excludedTerms
        global sql, extractedSql

        # distinct references
        # where relevance = 'keep'
        #       status = "New"
        #       non-reference extracted text exists
        sql = '''
                (
                select c._refs_key, c.mgiid, c.pubmedid, s._group_key, v.confidence
                from bib_citation_cache c, bib_refs r, bib_workflow_relevance v, bib_workflow_status s
                where r._refs_key = c._refs_key
                and r._refs_key = v._refs_key
                and v.isCurrent = 1
                and v._relevance_key = 70594667
                and r._refs_key = s._refs_key
                and s._status_key = 71027551
                and s._group_key = %s
                and exists (select 1 from bib_workflow_data d
                        where r._refs_key = d._refs_key
                        and d._extractedtext_key not in (48804491)
                        and d.extractedText is not null
                        )
                )
                order by mgiid desc
        '''

        # extracted_text by _refs_key where extracted text type != 'reference'
        extractedSql = '''
                select lower(d.extractedText) as extractedText
                from bib_workflow_data d
                where d._refs_key = %s
                and d._extractedtext_key not in (48804491)
                and d.extractedText is not null
        '''

        return 0

def process(sql):
        global statusFile
        global logFile
        global outputFile
        global allIsCurrentSql
        global statusKey

        # general processing

        results = db.sql(sql, 'auto')

        # iterate thru each distinct reference
        for r in results:

                refKey = r['_refs_key']
                mgiid = r['mgiid']
                pubmedid = r['pubmedid']
                groupKey = r['_group_key']
                confidence = r['confidence']
                termKey = notroutedKey
                term = 'Not Routed'

                logFile.write('\n')
                allSubText = []
                matchesTerm = 0

                eresults = db.sql(extractedSql % (refKey), 'auto')
                for e in eresults:
                        matchesExcludedTerm = 0
                        extractedText = e['extractedText']
                        extractedText = extractedText.replace('\n', ' ')
                        extractedText = extractedText.replace('\r', ' ')

                        for s in searchTerms:
                                for match in re.finditer(s, extractedText):
                                        subText = extractedText[match.start()-50:match.end()+50]
                                        if len(subText) == 0:
                                                 subText = extractedText[match.start()-50:match.end()+50]

                                        matchesExcludedTerm = 0
                                        for e in excludedTerms:
                                                for match2 in re.finditer(e, subText):
                                                        matchesExcludedTerm += 1

                                        # if subText matches excluded term, don't change to "Routed"
                                        if matchesExcludedTerm == 0:
                                                termKey = routedKey;
                                                term = 'Routed'
                                                matchesTerm += 1

                                        logFile.write(s + ' [ ' + subText + '] excluded term = ' + str(matchesExcludedTerm) + '\n')
                                        allSubText.append(subText)

                logFile.write(mgiid + ' ' + pubmedid + ' ' + str(confidence) + ' ' + term + ' ' + str(matchesTerm) + '\n')

                statusFile.write('%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
                        % (statusKey, refKey, groupKey, termKey, isCurrent, \
                           userKey, userKey, loaddate, loaddate))

                outputFile.write(mgiid + '|' + \
                        pubmedid + '|' + \
                        str(confidence) + '|' + \
                        term + '|' + \
                        str(matchesTerm) + '|' + \
                        str(matchesExcludedTerm) + '|' + \
                        '|'.join(allSubText) + '\n')

                statusKey += 1

                # set the existing isCurrent = 0
                allIsCurrentSql += setIsCurrentSql % (groupKey, refKey)

def closeFiles():
        logFile.flush()
        logFile.close()
        outputFile.flush()
        outputFile.close()

        return 0

def bcpFiles():

        # flush the status 
        statusFile.flush()
        statusFile.close()

        # update existing relevance isCurrent = 0
        # must be done *before* the new rows are added
        #print(allIsCurrentSql)
        db.sql(allIsCurrentSql, None)
        db.commit()

        # enter new relevance data
        for b in bcpCmd:
                #print(b)
                os.system(b)
        db.commit()

        # update bib_workflow_status serialization
        db.sql(''' select setval('bib_workflow_status_seq', (select max(_Assoc_key) from BIB_Workflow_Status)) ''', None)
        db.commit()

        return 0

def processAP():
        global statusFileName, statusFile
        global logFileName, logFile
        global outputFileName, outputFile
        global searchTerms
        global excludedTerms
        global bcpCmd

        statusFileName = outputDir + '/' + statusTable + '.AP.bcp'
        statusFile = open(statusFileName, 'w')
        logFileName = logDir + '/secondary.AP.log'
        logFile = open(logFileName, 'w')
        outputFileName = outputDir + '/AP.txt'
        outputFile = open(outputFileName, 'w')
        bcpCmd.append('%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII))

        searchTerms = [
        ' es cell',
        '-/-', 
        'crispr', 
        'cyagen', 
        'eucomm', 
        'gene trap', 
        'gene trapped', 
        'gene-trap', 
        'gene-trapped', 
        'generation of mice', 
        'generation of mutant mice', 
        'generation of transgenic mice', 
        'heterozygote', 
        'homozygote', 
        'induced mutation', 
        'jax', 
        'knock-in mice', 
        'knock-in mouse', 
        'knock-out mice', 
        'knock-out mouse', 
        'knockin mice', 
        'knockin mouse', 
        'knockout mice', 
        'knockout mouse', 
        'komp', 
        'mice were created', 
        'mice were generated', 
        'mmrrc', 'mutant mice', 
        'mutant mouse', 
        'novel mutant', 
        'novel mutation', 
        'ozgene', 
        'rrid_imsr', 
        'rrid_jax', 
        'rrid_mgi', 
        'rrid_mmrrc', 
        'rrid:imsr', 
        'rrid:jax', 
        'rrid:mgi', 
        'rrid:mmrrc', 
        'spontaneous mutant', 
        'spontaneous mutant', 
        'spontaneous mutation', 
        'talen', 
        'targeted mutation', 
        'targeting construct', 
        'targeting vector', 
        'transgene', 
        'transgenic mice', 
        'transgenic mouse'
        ]

        process(sql % (31576664))

        return 0


def processGXD():
        global statusFileName, statusFile
        global logFileName, logFile
        global outputFileName, outputFile
        global searchTerms
        global excludedTerms
        global bcpCmd

        statusFileName = outputDir + '/' + statusTable + '.GXD.bcp'
        statusFile = open(statusFileName, 'w')
        logFileName = logDir + '/secondary.GXD.log'
        logFile = open(logFileName, 'w')
        outputFileName = outputDir + '/GXD.txt'
        outputFile = open(outputFileName, 'w')
        bcpCmd.append('%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII))

        searchTerms = [
        'embryo',
        ]

        results = db.sql('select term from voc_term where _vocab_key = 135 order by term', 'auto')
        for r in results:
                excludedTerms.append(r['term'])
        print(excludedTerms)

        sql = '''
        (
        select c._refs_key, c.mgiid, c.pubmedid, s._group_key, v.confidence
        from bib_citation_cache c, bib_refs r, bib_workflow_relevance v, bib_workflow_status s
        where r._refs_key = c._refs_key
        and r._refs_key = v._refs_key
        and v.isCurrent = 1
        and v._relevance_key = 70594667
        and r._refs_key = s._refs_key
        and s._status_key = 71027551
        and s._group_key = 31576665
        and exists (select 1 from bib_workflow_data d
                where r._refs_key = d._refs_key
                and d._extractedtext_key not in (48804491)
                and d.extractedText is not null
                )
        union all
        select c._refs_key, c.mgiid, c.pubmedid, s._group_key, v.confidence
        from bib_citation_cache c, bib_refs r, bib_workflow_relevance v, bib_workflow_status s
        where r._refs_key = c._refs_key
        and r._refs_key = v._refs_key
        and v.isCurrent = 1
        and v._relevance_key = 70594666
        and v.confidence > -1.0
        and r._refs_key = s._refs_key
        and s._status_key = 71027551
        and s._group_key = 31576665
        and exists (select 1 from bib_workflow_data d
                where r._refs_key = d._refs_key
                and d._extractedtext_key not in (48804491)
                and d.extractedText is not null
                )
        )
        order by mgiid desc
        '''

        process(sql)

        return 0

def processQTL():
        global statusFileName, statusFile
        global logFileName, logFile
        global outputFileName, outputFile
        global searchTerms
        global excludedTerms
        global bcpCmd

        statusFileName = outputDir + '/' + statusTable + '.QTL.bcp'
        statusFile = open(statusFileName, 'w')
        logFileName = logDir + '/secondary.QTL.log'
        logFile = open(logFileName, 'w')
        outputFileName = outputDir + '/QTL.txt'
        outputFile = open(outputFileName, 'w')
        bcpCmd.append('%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII))

        searchTerms = [
        'qtl'
        ]

        process(sql % (31576668))

        return 0

def processTumor():
        global statusFileName, statusFile
        global logFileName, logFile
        global outputFileName, outputFile
        global searchTerms
        global excludedTerms
        global bcpCmd

        statusFileName = outputDir + '/' + statusTable + '.Tumor.bcp'
        statusFile = open(statusFileName, 'w')
        logFileName = logDir + '/secondary.Tumor.log'
        logFile = open(logFileName, 'w')
        outputFileName = outputDir + '/Tumor.txt'
        outputFile = open(outputFileName, 'w')
        bcpCmd.append('%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII))

        searchTerms = [
        'tumo',
        'inoma',
        'adenoma',
        'sarcoma',
        'lymphoma',
        'neoplas',
        'gioma',
        'papilloma',
        'leukemia',
        'leukaemia',
        'ocytoma',
        'thelioma',
        'blastoma',
        'hepatoma',
        'melanoma',
        'lipoma',
        'myoma',
        'acanthoma',
        'fibroma',
        'teratoma',
        'glioma',
        'thymoma'
        ]

        results = db.sql('select term from voc_term where _vocab_key = 164 order by term', 'auto')
        for r in results:
                excludedTerms.append(r['term'])
        print(excludedTerms)

        process(sql % (31576667))

        return 0

#
#  MAIN
#

#print('initialize')
if initialize() != 0:
    sys.exit(1)

#print('processAP')
if processAP() != 0:
    closeFiles()
    sys.exit(1)

#print('processGXD')
if processGXD() != 0:
    closeFiles()
    sys.exit(1)

#print('processQTL')
if processQTL() != 0:
    closeFiles()
    sys.exit(1)

#print('processTumor')
if processTumor() != 0:
    closeFiles()
    sys.exit(1)

#print('bcpFiles')
if bcpFiles() != 0:
    sys.exit(1)

closeFiles()
sys.exit(0)

