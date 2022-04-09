#!/bin/bash

### Icinga Passive checks for a Hopzero Agent
ICIGNA_CHECK_BIN=/opt/hopzero/icinga/plugins
ICIGNA_PASSIVE_CHECK=${ICIGNA_PASSIVE_CHECK}
#VERBOSE="-v"
VERBOSE=""

## The Icigna Identifier is HZ_CustomerID_HZ_Serial_Number
HZ_ICINGA_IDENTIFIER=""

## Define outout log
LOG_FILE=/opt/hopzero/icinga_passive_checks.log

function run_checks() {
    # OS utilization
    ${ICIGNA_PASSIVE_CHECK} ${VERBOSE} --host ${HZ_ICINGA_IDENTIFIER} -s 'TOTAL CPU PCT' -p total_cpu >> ${LOG_FILE}
    ${ICIGNA_PASSIVE_CHECK} ${VERBOSE} --host ${HZ_ICINGA_IDENTIFIER} -s 'TOTAL MEM'     -p total_mem >> ${LOG_FILE}
    ${ICIGNA_PASSIVE_CHECK} ${VERBOSE} --host ${HZ_ICINGA_IDENTIFIER} -s 'DISK SPACE USED OPT'  -p disk_space_opt >> ${LOG_FILE}
    ${ICIGNA_PASSIVE_CHECK} ${VERBOSE} --host ${HZ_ICINGA_IDENTIFIER} -s 'DISK SPACE USED ROOT' -p disk_space_root >> ${LOG_FILE}

    # Ensure hopzero agents are running
    ${ICIGNA_PASSIVE_CHECK} ${VERBOSE} --host ${HZ_ICINGA_IDENTIFIER} -s 'PROCS Python' -p num_procs_hzs3uploader --warn 0 --crit 0 >> ${LOG_FILE}
    ${ICIGNA_PASSIVE_CHECK} ${VERBOSE} --host ${HZ_ICINGA_IDENTIFIER} -s 'PROCS Python' -p num_procs_hzcollector  --warn 0 --crit 0 >> ${LOG_FILE}

    # Ensure  hopzero agents are running AND writing to the log file    
    ${ICIGNA_PASSIVE_CHECK} ${VERBOSE} --host ${HZ_ICINGA_IDENTIFIER} -s 'FILEAGE hzcollector'  -p fileage_hzcollector_log  --warn 60 --crit 240 >> ${LOG_FILE}
    ${ICIGNA_PASSIVE_CHECK} ${VERBOSE} --host ${HZ_ICINGA_IDENTIFIER} -s 'FILEAGE hzs3uplaoder' -p fileage_hzs3uploader_log --warn 60 --crit 240 >> ${LOG_FILE}
}


function compose_icigna_identifier() {
    HZCONFIG=/opt/hopzero/conf/hopzero.ini
    HZCUSTID=$(grep customer_id ${HZCONFIG} | awk '{print$2}')
    HZSERIAL=$(grep serial_number ${HZCONFIG} | awk '{print$2}')
    HZ_ICINGA_IDENTIFIER=${HZCUSTID}_${HZSERIAL}
}

########  Main

# Genreate this hosts HZ_ICIGNA Identifer
compose_icigna_identifier

## Execute the icigna passive checks
run_checks