#!/bin/bash

tool_dir=../../sdas-1.0.0
csv_file=../../output/DEG_wilcoxon/de_wilcoxon.domain_graphst.3-vs-8.sig_filtered.csv # need to use the differential genes
output_dir=../../output/geneSetEnrichment_enrichr


${tool_dir}/SDAS geneSetEnrichment enrichr -i $csv_file -o $output_dir --species human


