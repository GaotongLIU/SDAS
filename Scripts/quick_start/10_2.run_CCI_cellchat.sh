#!/bin/bash

tool_dir=../../sdas-1.0.0
binsize=100
h5ad_file=../../output/cellAnnotation_rctd/sample_anno_rctd.h5ad
output_dir=../../output/CCI_cellchat

${tool_dir}/SDAS CCI cellchat -i $h5ad_file -o $output_dir --bin_size $binsize --label_key anno_rctd --gene_symbol_key _index --species human --type truncatedMean --add_spatial
