#!/bin/sh

cd `dirname $0` 

COMMON_CONFIG=../littriageload.config

# 
# Make sure the common configuration file exists and source it. 
#
if [ -f ${COMMON_CONFIG} ]
then
    . ${COMMON_CONFIG}
else
    echo "Missing configuration file: ${COMMON_CONFIG}"
    exit 1
fi

case `uname -n` in

bhmgiapp01)
	echo "must be logged in as mgiadmin"
	echo "on bhmgiapp01: tarring up input.last file from /data/loads/mgi/littriageload/input.last..."
	cd /data/loads/mgi/littriageload/input.last
	rm -rf /data/loads/mgi/littriageload/test.tar
	tar cvf /data/loads/mgi/littriageload/test.tar .
	;;

bhmgidevapp01|bhmgiapp14ld)
	echo "must be logged in as mgiadmin"
	echo "on bhmgidevapp01 or bhmgiapp14ld: loading test.tar file to /data/loads/mgi/littriageload/input..."
	cd ${DATALOADSOUTPUT}/mgi/littriageload
	rm -rf test.tar
	scp bhmgiapp01:/data/loads/mgi/littriageload/test.tar .
	ls -l ${DATALOADSOUTPUT}/mgi/littriageload/test.tar
	cd ${DATALOADSOUTPUT}/mgi/littriageload/input
	rm -rf */*
	tar xvf ${DATALOADSOUTPUT}/mgi/littriageload/test.tar
	;;

esac

