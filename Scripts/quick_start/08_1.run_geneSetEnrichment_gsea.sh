#!/bin/bash

tool_dir=../../sdas-1.0.0
binsize=100
h5ad_file=../../output/spatialDomain_graphST/sample_domain_graphst.h5ad
output_dir=../../output/geneSetEnrichment_gsea


# run for all gmt files
${tool_dir}/SDAS geneSetEnrichment gsea -i $h5ad_file -o $output_dir --species human --group_key domain_graphst --ident1 3 --ident2 8
