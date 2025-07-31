#!/bin/bash

tool_dir=../../sdas-1.0.0
h5ad_file=../../output/cellAnnotation_rctd/sample_anno_rctd.h5ad
output_dir=../../output/spatialRelate_crawdad


${tool_dir}/SDAS spatialRelate crawdad -i $h5ad_file -o $output_dir --label_key anno_rctd --crawdad_perms 2
