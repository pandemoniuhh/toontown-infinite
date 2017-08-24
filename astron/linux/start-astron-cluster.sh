#!/bin/sh

# Changes to the current file directory
scriptDir=$(dirname -- "$(readlink -f -- "$BASH_SOURCE")")
cd "$scriptDir"

cd ..

./astrond --loglevel info config/cluster.yml
