#!/bin/bash

tool_dir=../../sdas-1.0.0
binsize=100
h5ad_file=../../output/cellAnnotation_rctd/sample_anno_rctd.h5ad
output_dir=../../output/cellularNeighborhood_multiCelltypeScore


${tool_dir}/SDAS cellularNeighborhood multiCelltypeScore -i $h5ad_file -o $output_dir --bin_size $binsize --label_key anno_rctd --score_key anno_score_rctd
