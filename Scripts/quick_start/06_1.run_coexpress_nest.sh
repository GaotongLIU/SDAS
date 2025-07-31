#!/bin/bash

tool_dir=../../sdas-1.0.0
binsize=100
h5ad_file=../../Test_data/single_slice/sample.h5ad
output_dir=../../output/coexpress_nest


${tool_dir}/SDAS coexpress nest -i $h5ad_file -o $output_dir --bin_size $binsize --selected_genes top3000
