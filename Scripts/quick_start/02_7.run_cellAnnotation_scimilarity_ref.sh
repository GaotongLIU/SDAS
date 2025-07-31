#!/bin/bash

tool_dir=../../sdas-1.0.0
ref_file=../../Test_data/single_slice/sample_ref.h5ad
output_dir=../../output/cellAnnotation_scimilarity_ref
# download scimilarity model from https://zenodo.org/records/10685499 and extract it to ../../databases/scimilarity/ before running the script 
model_dir=../../databases/scimilarity/model_v1.1

#GPU: 
#firstly, use nvidia-smi to check the avalability of gpu, then decide the index of gpu to use
${tool_dir}/SDAS cellAnnotation scimilarityMakeRef --reference $ref_file -o $output_dir --model_dir $model_dir --label_key annotation2 --filter_rare_cell 0 --remove_tmp --gpu_id 0
