#!/bin/bash

tool_dir=../../sdas-1.0.0
h5ad_file=../../output/cellAnnotation_rctd/sample_anno_rctd.h5ad
binsize=100
output_dir=../../output/spatialRelate_squidpy


${tool_dir}/SDAS spatialRelate squidpy -i $h5ad_file -o $output_dir --label_key anno_rctd --bin_size $binsize --coord_type grid
