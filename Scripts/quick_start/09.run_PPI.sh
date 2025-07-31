#!/bin/bash

tool_dir=../../sdas-1.0.0
gene_list=../../Test_data/PPI/gene_300.txt
output_dir=../../output/PPI


${tool_dir}/SDAS PPI -i $gene_list -o $output_dir --species human --cluster mcl kmeans GN
