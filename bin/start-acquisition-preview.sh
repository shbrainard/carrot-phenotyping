#!/bin/bash

parent=$(pwd)

client=$parent/acquisition-preview-client
server=$parent/acquisition-preview-server

cd $server
node app.js src=$1 &

cd $client
yarn start
