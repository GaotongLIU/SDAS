#!/bin/bash

tool_dir=../../sdas-1.0.0
binsize=100
h5ad_file=../../Test_data/single_slice/sample.h5ad
output_dir=../../output/cellAnnotation_scimilarity_with_ref
reference_database=../../output/cellAnnotation_scimilarity_ref
# download scimilarity model from https://zenodo.org/records/10685499 and extract it to ../../databases/scimilarity/ before running the script 
model_dir=../../databases/scimilarity/model_v1.1

#GPU: 
#firstly, use nvidia-smi to check the avalability of gpu, then decide the index of gpu to use
${tool_dir}/SDAS cellAnnotation scimilarity -i $h5ad_file --reference_database $reference_database -o $output_dir --model_dir $model_dir --input_gene_symbol_key _index --bin_size $binsize --gpu_id 0
