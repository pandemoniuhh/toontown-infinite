#!/bin/sh

SRC_DIR="$(dirname "$(dirname "$(readlink -fm "$0")")")"

# Get the user input:
read -p "Username: " ttiUsername

# Export the environment variables:
export ttiUsername=$ttiUsername
export ttiPassword="password"
export TTI_PLAYCOOKIE=$ttiUsername
export TTI_GAMESERVER="127.0.0.1"

echo ===============================
echo Starting Toontown Infinite...
echo Username: $ttiUsername
echo Gameserver: $TTI_GAMESERVER
echo ===============================

while [ true ]
do
    python2 -m toontown.toonbase.ClientStart
    read -r -p "Press any key to continue..." key
done
