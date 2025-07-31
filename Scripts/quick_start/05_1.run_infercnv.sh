#!/bin/bash


tool_dir=../../sdas-1.0.0
binsize=100
h5ad_file=../../output/cellAnnotation_rctd/sample_anno_rctd.h5ad
rds_file=../../output/cellAnnotation_rctd/sample_anno_rctd.rds
output_dir=../../output/infercnv


${tool_dir}/SDAS infercnv -i $rds_file --h5ad $h5ad_file -o $output_dir --bin_size $binsize --label_key anno_rctd --gene_symbol_key _index --species human --cutoff 0.02 --ref_group_names Mac_SPP1,Monocyte_S100A8,Plasma_IgG,CD8_Tem --cluster_heatmap True
# ,CD8_Tem,Endo,Fibro_GPM6B,Fibro_MYH11,Fibro_NOTCH3,Mac_M1,Mac_M2,Mac_SPP1
