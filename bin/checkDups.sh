#!/bin/sh

TMP_ALL_FILES=/tmp/`basename $0`_all.$$
TMP_DUP_FILES=/tmp/`basename $0`_dup.$$
trap "rm -f ${TMP_ALL_FILES} ${TMP_DUP_FILES}" 0 1 2 15

# Create a full list of all PDFs (directory/filename).
ls */*.pdf > ${TMP_ALL_FILES}

# Create a list of just the duplicate file names that are in the full list.
cat ${TMP_ALL_FILES} | sed 's/.*\///' | sort | uniq -d > ${TMP_DUP_FILES}

# Find the duplicate file names in the full list so it shows the directory
# where each duplicate was found.
for i in `cat ${TMP_DUP_FILES}`
do
    grep $i ${TMP_ALL_FILES}
done

if [ `cat ${TMP_DUP_FILES} | wc -l` -ne 0 ]
then
    echo "Duplicates found"
    exit 1
fi

exit 0
