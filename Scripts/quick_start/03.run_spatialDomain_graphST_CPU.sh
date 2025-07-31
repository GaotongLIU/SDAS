#!/bin/bash

tool_dir=../../sdas-1.0.0
binsize=100
h5ad_file=../../Test_data/single_slice/sample.h5ad
output_dir=../../output/spatialDomain_graphST/

mkdir -p $output_dir

${tool_dir}/SDAS spatialDomain graphst -i $h5ad_file -o $output_dir --n_clusters 10 --n_hvg 3000 --bin_size $binsize
