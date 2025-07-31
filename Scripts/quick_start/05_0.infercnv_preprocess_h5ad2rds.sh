#!/bin/bash


tool_dir=../../sdas-1.0.0
h5ad_file=../../output/cellAnnotation_rctd/sample_anno_rctd.h5ad
output_dir=../../output/cellAnnotation_rctd

${tool_dir}/SDAS dataProcess h5ad2rds -i $h5ad_file -o $output_dir


