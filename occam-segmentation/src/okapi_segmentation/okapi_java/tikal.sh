#!/bin/bash
java -cp "`dirname $0`/lib/*" net.sf.okapi.applications.tikal.Main "$@"
