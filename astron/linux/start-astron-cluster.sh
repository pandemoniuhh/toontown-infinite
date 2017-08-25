#!/bin/sh
ASTRON_DIR="$(dirname "$(dirname "$(readlink -fm "$0")")")"
cd $ASTRON_DIR
./astrond --loglevel info config/cluster.yml
