#!/bin/bash
langlist="it_IT zh_CN"
for lang in $langlist; do
    pylupdate6 GUI/*.ui tr/tr.py --no-obsolete --ts i18n/ts/"$lang".ts
done