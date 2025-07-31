#!/bin/bash

tool_dir=../../sdas-1.0.0
binsize=100
h5ad_file=../../output/spatialDomain_graphST/sample_domain_graphst.h5ad
output_dir=../../output/DEG_ttest


${tool_dir}/SDAS DEG -i $h5ad_file -o $output_dir --de_method t-test --group_key domain_graphst --ident1 3 --ident2 8
