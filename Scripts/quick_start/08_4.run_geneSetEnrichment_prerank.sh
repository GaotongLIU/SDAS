#!/bin/bash

tool_dir=../../sdas-1.0.0
csv_file=../../output/DEG_wilcoxon/de_wilcoxon.domain_graphst.3-vs-8.all.csv # need to use all genes
output_dir=../../output/geneSetEnrichment_prerank


${tool_dir}/SDAS geneSetEnrichment prerank -i $csv_file --species human -o $output_dir --min_size 3

