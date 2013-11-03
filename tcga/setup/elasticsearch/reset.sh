#!/bin/bash
#Assumes that elasticsearch is already running
curl -XDELETE 'localhost:9200/_river'
curl -XDELETE 'localhost:9200/tcga-cghub'
curl -XPUT 'localhost:9200/tcga-cghub'
curl -XPUT 'localhost:9200/tcga-cghub/analysis/_mapping' -d @tcga_mapping.json
curl -XPUT 'localhost:9200/_river/tcga-cghub/_meta' -d @tcga_river.json
