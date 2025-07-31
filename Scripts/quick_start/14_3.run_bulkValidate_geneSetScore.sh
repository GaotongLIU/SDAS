#!/bin/bash

tool_dir=../../sdas-1.0.0
output_dir=../../output/bulkValidate_geneSetScore
fpkm=../../Test_data/bulkValidate/fpkm.txt
cli=../../Test_data/bulkValidate/clinical.txt
geneset=../../Test_data/bulkValidate/geneset.txt


${tool_dir}/SDAS bulkValidate geneSetScore --expression $fpkm --gene_set $geneset --clinical $cli --group_col tissue_type.samples --group_type discrete -o $output_dir
