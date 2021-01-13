#!/bin/csh -f

if ( ${?MGICONFIG} == 0 ) then
        setenv MGICONFIG /usr/local/mgi/live/mgiconfig
endif

source ${MGICONFIG}/master.config.csh

cd `dirname $0`

setenv LOG $0.log
rm -rf $LOG
touch $LOG
 
#ssh bhmgiapp01
cd /data/loads/mgi/littriageload/input.last
tar -cvf /home/lec/lec.tar .
rm -rf input/lit*/*
cd /data/loads/mgi/littriageload/testRelevance
testRelevance.sh

#ssh bhmgiapp14ld
cd ${DATALOADSOUTPUT}/mgi/littriageload
mv /home/lec/lec.tar .
cd ${DATALOADSOUTPUT}/mgi/littriageload/input
tar -xvf ../lec.tar

${LITTRIAGELOAD}/bin/littriageload.sh
${LITTRIAGELOAD}/bin/testRelevance.sh
mv ${LITTRIAGELOAD}/bin/testRelevance.sh.log ${OUTPUTDIR}

dumpDB.csh mgi-testdb4 lec mgd /bhmgidevdb01/dump/lec.dump


#cd ${DATALOADSOUTPUT}/mgi/littriageload
#rm -rf lec.tar
#cd /mgi/all//Triage/PDF_files/_New_Newcurrent
#tar -cvf ${DATALOADSOUTPUT}/mgi/littriageload/lec.tar .
#cd ${DATALOADSOUTPUT}/mgi/littriageload/input
#tar -xvf ../lec.tar

