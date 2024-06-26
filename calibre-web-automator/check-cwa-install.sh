#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Print promt title
echo "==== Calibre-Web Automator -- Status of Monitoring Services ===="
echo ""

if s6-rc -a list | grep -q 'calibre-scan'; then
    echo -e "- Calibre-scan ${GREEN}is running${NC}"
    cs=true
else
    echo -e "- Calibre-scan ${RED}is not running${NC}"
    cs=false
fi


if s6-rc -a list | grep -q 'books-to-process-scan'; then
    echo -e "- Books-to-process-scan ${GREEN}is running${NC}"
    bs=true
else
    echo -e "- Books-to-process-scan ${RED}is not running${NC}"
    bs=false
fi

echo ""

if $cs && $bs; then
    echo -e "Calibre-Web-Automater was ${GREEN}sucsessfully installed ${NC}and ${GREEN}is running properly!${NC}"
else
    echo -e "Calibre-Web-Automater was ${RED}not installed sucsessfully${NC}, please check the logs for more information."
fi