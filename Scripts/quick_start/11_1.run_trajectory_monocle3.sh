#!/bin/bash


tool_dir=../../sdas-1.0.0
rds_file=../../output/cellAnnotation_rctd/sample_anno_rctd.rds
output_dir=../../output/trajectory_monocle3

${tool_dir}/SDAS trajectory monocle3 -i $rds_file -o $output_dir --root_key anno_rctd --root CAF_CXCL14 --gene_symbol_key _index --deg
