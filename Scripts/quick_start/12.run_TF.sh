#!/bin/bash

tool_dir=../../sdas-1.0.0
h5ad_file=../../output/cellAnnotation_rctd/sample_anno_rctd.h5ad
output_dir=../../output/TF
tf_list=../../Test_data/TF/tf_list.txt

${tool_dir}/SDAS TF -i $h5ad_file -o $output_dir --label_key anno_rctd --gene_symbol_key _index --species human --TF_list $tf_list --n_cpus 32
