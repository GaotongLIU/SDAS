#!/bin/bash

tool_dir=../../sdas-1.0.0
binsize=100
h5ad_file=../../output/spatialDomain_graphST/sample_domain_graphst.h5ad
output_dir=../../output/geneSetEnrichment_gsva


# run for all gmt files
${tool_dir}/SDAS geneSetEnrichment gsva -i $h5ad_file -o $output_dir --species human --group_key domain_graphst --idents 1,2,4 --subset_key level3 --subset_values boundary_neighborhoods
