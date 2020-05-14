#!/usr/bin/env bash

rm -rf ./calibrelib
calibredb --library-path=./calibrelib list  # this "creates" a library
calibre-server --trusted-ips=127.0.0.1 --port=8080 --max-request-body-size=2000 --max-job-time=60 ./calibrelib
