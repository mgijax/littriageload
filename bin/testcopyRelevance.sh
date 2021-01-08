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

#ssh bhmgiapp14ld
cd ${DATALOADSOUTPUT}/mgi/littriageload
/home/lec/lec.tar .
cd ${DATALOADSOUTPUT}/mgi/littriageload/input
tar -xvf ../lec.tar

#cd ${DATALOADSOUTPUT}/mgi/littriageload
#rm -rf lec.tar
#cd /mgi/all//Triage/PDF_files/_New_Newcurrent
#tar -cvf ${DATALOADSOUTPUT}/mgi/littriageload/lec.tar .
#cd ${DATALOADSOUTPUT}/mgi/littriageload/input
#tar -xvf ../lec.tar

