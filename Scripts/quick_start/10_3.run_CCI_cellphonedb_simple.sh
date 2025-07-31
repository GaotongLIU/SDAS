#!/bin/bash

tool_dir=../../sdas-1.0.0
h5ad_file=../../output/cellAnnotation_rctd/sample_anno_rctd.h5ad
output_dir=../../output/CCI_cellphonedb_simple

${tool_dir}/SDAS CCI cellphonedb -i $h5ad_file -o $output_dir --label_key anno_rctd --method simple --counts_data gene_name --species human
