#!/bin/csh -f

#
# Monday : Jan 11
# 1. load production backup into mgi-testdb4/lec
#
# 2. run migration part 1: sets 'keep', 'discard', 'Not Specified'
#       bibrelevance.csh.log is time stamped
#
# 3. run migration part 2:  littriageload/bin/processRelevance.sh
#       find all of the bib_workflow_relevance = 'Not Specified'
#       output/littriageload.relevance.predicted
#
# Sun
# 4. copy Mon-Sat production inputs (/data/loads/mgi/littriageload/input.last, etc) to lec
# 5. run littriageload
# 6. output folder : Tue-Sat
#
# On Production/QC report (Sun)
# 7. list of MGI ids, J:, pubmedid, isDiscard, creation_date, short citation where creation_date >= Monday date Jan 11
#       bhmgiapp01:/data/loads/mgi/littriageload/testrelevance
#
# Mon : check Production/QC report
# Mon : check lori/output folders (Mon, Sun)
#

if ( ${?MGICONFIG} == 0 ) then
        setenv MGICONFIG /usr/local/mgi/live/mgiconfig
endif

source ${MGICONFIG}/master.config.csh

cd `dirname $0`

setenv LOG $0.log
rm -rf $LOG
touch $LOG
 
#ssh bhmgiapp01
#cd /data/loads/mgi/littriageload/input.last
#tar -cvf /home/lec/lec.tar .
#cd ${DATALOADSOUTPUT}/mgi/littriageload
#/home/lec/lec.tar .
#cd ${DATALOADSOUTPUT}/mgi/littriageload/input
#tar -xvf ../lec.tar

#cd ${DATALOADSOUTPUT}/mgi/littriageload
#rm -rf lec.tar
#cd /mgi/all//Triage/PDF_files/_New_Newcurrent
#tar -cvf ${DATALOADSOUTPUT}/mgi/littriageload/lec.tar .
#cd ${DATALOADSOUTPUT}/mgi/littriageload/input
#tar -xvf ../lec.tar

cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0 | tee -a $LOG

select c.mgiID, c.jnumid, c.pubmedid, t.term, r.creation_date, c.short_citation
from bib_citation_cache c, bib_refs r, bib_workflow_relevance v, voc_term t
where r.creation_date::date >= '01/06/2021'
and r._refs_key = c._refs_key
and r._refs_key = v._refs_key
and v.isCurrent = 1
and v._relevance_key = t._term_key
order by c.short_citation
;

EOSQL

date |tee -a $LOG

