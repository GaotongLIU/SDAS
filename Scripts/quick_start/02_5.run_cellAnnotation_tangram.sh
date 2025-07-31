#!/bin/bash

tool_dir=../../sdas-1.0.0
binsize=100
h5ad_file=../../Test_data/single_slice/sample.h5ad
ref_file=../../Test_data/single_slice/sample_ref.h5ad
output_dir=../../output/cellAnnotation_tangram

#GPU: 
#firstly, use nvidia-smi to check the avalability of gpu, then decide the index of gpu to use
${tool_dir}/SDAS cellAnnotation tangram -i $h5ad_file -o $output_dir --reference $ref_file --label_key annotation2 --input_gene_symbol_key _index --filter_rare_cell 0 --bin_size $binsize --gpu_id 0
