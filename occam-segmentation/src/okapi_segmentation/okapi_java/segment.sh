#!/bin/bash

# arguments: [file containing 1 line per paragraph] [output file] [2-letter language code] [SRX file]?
# if [SRX file] is not specified, default one is used (see config directory of Okapi)
# note: SRX file contains some attribute-field pairs for deleting white space at start / end of lines after segmentation

okapi_folder=$(dirname "$0")

srxswitch=
if [ $# -eq 4 ]
then
  srxswitch="-seg $4"
elif [ $# -ne 3 ]
then
  echo "specify 3 or 4 arguments"
  exit 1
fi

# create unique filename
infile=/tmp/okapi.in.$(date +"%s%N").txt
cp $1 $infile
outfile=$2
langcode=$3

$okapi_folder/tikal.sh -x $infile -sl $langcode
#$okapi_folder/tikal.sh -s -sl $langcode $srxswitch $infile.xlf
$okapi_folder/tikal.sh -s $srxswitch $infile.xlf
$okapi_folder/tikal.sh -xm $infile.out.xlf
mv $infile.out.xlf.$langcode $outfile

