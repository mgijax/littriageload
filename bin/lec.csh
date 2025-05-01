#!/bin/csh -f

#
# Template
#


if ( ${?MGICONFIG} == 0 ) then
        setenv MGICONFIG /usr/local/mgi/live/mgiconfig
endif

source ${MGICONFIG}/master.config.csh

cd `dirname $0`

setenv LOG $0.log
rm -rf $LOG
touch $LOG
 
date | tee -a $LOG
 
cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0 | tee -a $LOG

select c.mgiid, r.*
from bib_workflow_relevance r, bib_citation_cache c
where c.mgiid in ( 'MGI:7856068', 'MGI:7856066', 'MGI:7856062', 'MGI:7856061')
and c._refs_key = r._refs_key
and r.iscurrent = 1
;

update bib_workflow_relevance set iscurrent = 0 where _assoc_key in (1155499,1155500,1155504,1155506)
;

insert into bib_workflow_relevance values(nextval('bib_workflow_relevance_seq'),721500,70594667,1,null,'11/06/2020',1667,1667,now(),now());
insert into bib_workflow_relevance values(nextval('bib_workflow_relevance_seq'),721501,70594667,1,null,'11/06/2020',1667,1667,now(),now());
insert into bib_workflow_relevance values(nextval('bib_workflow_relevance_seq'),721505,70594667,1,null,'11/06/2020',1667,1667,now(),now());
insert into bib_workflow_relevance values(nextval('bib_workflow_relevance_seq'),721507,70594667,1,null,'11/06/2020',1667,1667,now(),now());

EOSQL

date |tee -a $LOG

