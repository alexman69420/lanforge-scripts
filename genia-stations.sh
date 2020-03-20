#!/bin/bash

# Ideally we want to get close to 600 stations
# but we'll want to see how big a batch we can create

#wiphy0 stations sta0000-0199
#wiphy1 stations sta0200-0399
#wiphy2 stations sta0400-0462
#wiphy3 stations sta0463-0526

M=ct524-genia.jbr.candelatech.com
SSID=(jedway-wpa2-x2048-5-1 jedway-wpa2-x2048-5-1)
declare -A batches=(
    [wiphy0]=000,75
    [wiphy1]=075,75
    [wiphy2]=150,30
    [wiphy3]=180,30
)

function create_batch() {
    local radio=$1
    local start=$2
    local num=$3
    [[ x$radio = x ]] && echo "create_batch wants (radio, first, number_sta)" && exit 1
    [[ x$start = x ]] && echo "create_batch wants (radio, first, number_sta)" && exit 2
    [[ x$num = x ]] && echo "create_batch wants (radio, first, number_sta)" && exit 3

    #echo "radio[$radio] start[$start] num[$num]"
    set -x
    ./lf_associate_ap.pl --mgr $M --radio $radio --action add \
        --first_sta $start --num_sta $num \
        --first_ip DHCP --ssid ${SSID[0]} \
        --security wpa2 --passphrase ${SSID[1]} \
        --admin_down_on_add
    set +x
}

sorted=$(for radio in "${!batches[@]}"; do
    echo $radio
done | sort)

for radio in $sorted; do
    value="${batches[$radio]}"
    hunks=( ${value//,/ } )
    create_batch $radio ${hunks[0]} ${hunks[1]}
done

