#!/bin/bash

### Icinga Passive create host for a Hopzero Agent
HZCONFIG=/opt/hopzero/config/hopzero.ini

ICIGNA_CHECK_BIN=/opt/hopzero/icinga/bin
ICIGNA_PASSIVE_CHECK=${ICIGNA_CHECK_BIN}/icinga_passive_service.py
#VERBOSE=""
VERBOSE="-v"

## The Icigna Identifier is HZ_CustomerID_HZ_Serial_Number
HZ_ICINGA_IDENTIFIER=""

## Define outout log
LOG_FILE=/opt/hopzero/icinga_passive_checks.log

ICIGNA_IDENTIFIER_PREFIX="HZAU"

function create_host() {
    # OS utilization
    ${ICIGNA_PASSIVE_CHECK} ${VERBOSE} --host ${HZ_ICINGA_IDENTIFIER} -s 'TOTAL CPU PCT' -p total_cpu >> ${LOG_FILE}
}


function compose_icigna_identifier() {
    HZCUSTID=$(grep customer_id ${HZCONFIG} | awk '{print$2}')
    HZSERIAL=$(grep serial_number ${HZCONFIG} | awk '{print$2}')
    HZ_ICINGA_IDENTIFIER=${ICIGNA_IDENTIFIER_PREFIX}_${HZCUSTID}_${HZSERIAL}
}

########  Main

# Genreate this hosts HZ_ICIGNA Identifer
compose_icigna_identifier

## Execute the icigna passive checks
create_host