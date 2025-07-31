#!/bin/bash

tool_dir=../../sdas-1.0.0
h5ad_file=../../Test_data/single_slice/sample.h5ad
output_dir=../../output/dataProcess_printAdataInfo

${tool_dir}/SDAS dataProcess printAdataInfo -i $h5ad_file -o $output_dir
