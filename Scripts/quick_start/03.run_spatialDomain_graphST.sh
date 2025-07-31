#!/bin/bash

tool_dir=../../sdas-1.0.0
binsize=100
h5ad_file=../../Test_data/single_slice/sample.h5ad
output_dir=../../output/spatialDomain_graphST/

#GPU: 
#firstly, use nvidia-smi to check the avalability of gpu, then decide the index of gpu to use
${tool_dir}/SDAS spatialDomain graphst -i $h5ad_file -o $output_dir --gpu_id 0 --n_clusters 10 --n_hvg 3000 --bin_size $binsize
