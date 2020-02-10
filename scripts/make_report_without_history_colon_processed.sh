#!/bin/bash

BASE_DIR=.
DATE=`date +%F-%Mm-%Ss`
HTAN_TRANSFER_BUCKET=gs://htan-dcc-staging-htapp

# DIRECTORIES
LS_DIR=${BASE_DIR}/ls
HL_DIR=${BASE_DIR}/historic-logs
TC_DIR=${BASE_DIR}/transfer-commands
TD_DIR=${BASE_DIR}/transfer-documentation
LOG_DIR=${BASE_DIR}/logs
TEMP_DIR=${BASE_DIR}/temp
ID_DIR=${BASE_DIR}/ids

# Make directory structure if needed
mkdir -p ${LS_DIR}
mkdir -p ${HL_DIR}
mkdir -p ${TC_DIR}
mkdir -p ${TD_DIR}
mkdir -p ${TEMP_DIR}
mkdir -p ${LOG_DIR}

# Tumors
COLON=colon-tumors

# Files
## GSUTIL LS
COLON_LS=${LS_DIR}/colon-empty.txt

## Updated historic running log
COLON_HL=${HL_DIR}/${COLON}-processed-history.txt
COLON_HL_TEMP=${TEMP_DIR}/${COLON}-processed-history-${DATE}.txt

## Transfer commands
COLON_TC=${TC_DIR}/${COLON}-processed-gsutil-${DATE}.txt

## Transfer documentation
COLON_TD=${TD_DIR}/${COLON}-processed-documentation-${DATE}.txt

## Prepare transfer docs Logging
COLON_TD_LOG=${LOG_DIR}/${COLON}-processed-prepare-${DATE}.log
COLON_TD_LOG_ERROR=${LOG_DIR}/${COLON}-processed-prepare-${DATE}.err

# ID files
COLON_IDS=${ID_DIR}/htapp-colon-id.txt
RENAMEMAPPING=${ID_DIR}/renaming-mapping.txt

# Get GSUTIL LS
## Colon raw
gsutil ls -Lr gs://fc-e6398377-57a7-41cf-82f0-32b0940e9e5d > ${COLON_LS}

# Make Documentation
# Commands for transfer
# And updated historical logs
## Colon
HTAPP-transfer.py document --cmd_out ${COLON_TC} \
                           --bucket ${HTAN_TRANSFER_BUCKET} \
                           --hist_temp ${COLON_HL_TEMP} \
                           --ls ${COLON_LS} \
                           --tumor ${COLON} \
                           --rename ${RENAMEMAPPING} \
                           --qc_ids ${COLON_IDS} \
                           --document_out ${COLON_TD} > ${COLON_TD_LOG} 2> ${COLON_TD_LOG_ERROR}
