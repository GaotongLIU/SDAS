# Stereo Data Analysis Solution (SDAS)


## Introduction
Stereo Data Analysis Solution (SDAS) is an advanced bioinformatics software suite for spatial transcriptomics data developed by STOmics. It provides a comprehensive solution for spatial transcriptomics data analysis, supporting the full process from raw data to biological interpretation.

- **Functional Modules:**
  - 14 modules, 31 algorithms/methods
  - Includes: data processing, cell type annotation, spatial domain identification, cellular neighborhood analysis, CNV analysis, spatial gene co-expression, differential gene identification, gene set enrichment analysis, protein interaction network analysis, cell communication analysis, trajectory analysis, transcription factor analysis, cell-type spatial relationship analysis, and public bulk database validation.
- **Input:** h5ad files (from SAW count, SAW convert gef2h5ad), h5mu files (from SAW aggr), rds files
- **Output:** h5ad, rds, csv, txt, png, pdf
![SDAS Introduction](https://www.gitbook.com/cdn-cgi/image/dpr=2,width=2400,onerror=redirect,format=auto/https%3A%2F%2Ffiles.gitbook.com%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252FCggbEDCoTSjskIWVTMeM%252Fuploads%252Fn6rrmVLDNOhW96rd40hg%252Fsdas_intro_eng.png%3Falt%3Dmedia%26token%3D3820acc1-6278-4ada-89a8-4630c4e60bf4)


## Documentation
- English Manual: [https://mysite.gitbook.io/sdas_manual_eng/](https://mysite.gitbook.io/sdas_manual_eng/)
- Chinese Manual: [https://mysite.gitbook.io/sdas_manual_cn/](https://mysite.gitbook.io/sdas_manual_cn/)
- Chinese Manual (html): [https://stomics.github.io/StereoTools_manual/SDAS-Manual/cn/1.0/](https://stomics.github.io/StereoTools_manual/SDAS-Manual/cn/1.0/)


## Installation Guide
### 1. System Requirements
- 8-core Intel/AMD CPU (>24 cores recommended)
- 128GB RAM (>256GB recommended)
- 200GB free disk space
- 64-bit CentOS/RedHat 7.8 or Ubuntu 20.04

### 2. Software Download
- Baidu Netdisk: https://bgipan.genomics.cn/#/link/LRlWY2OYRtd5QYP5ql1k code:wfFT
- Github (Note: The repository does not include .tar.gz file or test data): 
  ```bash
  git clone https://github.com/STOmics/SDAS.git
  ```


### 3. Installation

**Important:** After extraction, run the setup.sh script. Do not change the installation path or rename the directory after installation.

```bash
tar -xzf sdas-1.0.0.tar.gz
cd sdas-1.0.0
sh setup.sh
```

### 4. Test Run
```bash
./SDAS -h
```

```bash
SDAS functions:
    dataProcess                              Prerocess data, include mergeAdata, h5ad2rds, h5mu2h5ad, printAdataInfo and subsetAdata
    cellAnnotation                           Annotate celltype of spatial transcriptomics
    coexpress                                Identify spatially coexpressed gene modules in spatial transcriptomics
    cellularNeighborhood                     Identify cellular neighborhood in spatial transcriptomics
    trajectory                               Construct cell trajectories from spatial transcriptomics or scRNA-Seq data
    CCI                                      Infer cell-cell communication in spatial transcriptomics or scRNA-Seq data
    infercnv                                 Detect copy number variations in spatial transcriptomics or scRNA-Seq data
    spatialDomain                            Identify spatial domain in spatial transcriptomics
    spatialRelate                            Characterize cell-type spatial relationships for spatial transcriptomics
    DEG                                      Identify differentially expressed genes in spatial transcriptomics or scRNA-Seq data
    geneSetEnrichment                        Analyze functional enrichment of gene sets in spatial transcriptomics or scRNA-Seq data
    TF                                       Analyze TF gene sets in spatial transcriptomics or scRNA-Seq data
    PPI                                      Analyze protein-protein interaction of gene sets
    bulkValidate                             Analyze immuneScore|geneSetScore|survivalKM in bulk RNA-Seq data

For command line options of each command, type: SDAS COMMAND -h

SDAS VERSION:
     1.0.0
```

### 5. Other Notes
- The software package is about 30GB, after extraction about 70GB
- For GPU usage: install CUDA >= 11.8 (see https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)

## Quick Start
Below are typical SDAS commands for common analysis steps. For more, see the [English Manual](https://mysite.gitbook.io/sdas_manual_eng/) and  [Chinese Manual](https://mysite.gitbook.io/sdas_manual_cn/).

### 1. Cell Type Annotation (cell2location)
```bash
SDAS cellAnnotation cell2locationMakeRef --reference sample_ref.h5ad -o output/cellAnnotation_cell2location_ref --label_key annotation2 --filter_rare_cell 0 --cell_percentage_cutoff2 0.05 --nonz_mean_cutoff 1.45 --gpu_id 0
SDAS cellAnnotation cell2location -i sample.h5ad -o output/cell2location --reference_csv output/cellAnnotation_cell2location_ref/sample_ref_inf_aver.csv --input_gene_symbol_key _index --bin_size 100 --gpu_id 0
```

### 2. Spatial Domain Identification (graphST)
```bash
SDAS spatialDomain graphst -i sample.h5ad -o output/spatialDomain_graphST --gpu_id 0 --tool mclust --n_clusters 10 --n_hvg 3000 --bin_size 100
```

### 3. CNV Analysis (inferCNV)
```bash
SDAS dataProcess h5ad2rds -i sample_anno_rctd.h5ad -o output/cellAnnotation_rctd
SDAS infercnv -i sample_anno_rctd.rds --h5ad sample_anno_rctd.h5ad -o output/infercnv --bin_size 100 --label_key anno_rctd --gene_symbol_key _index --species human --cutoff 0.02 --ref_group_names Mac_SPP1,Monocyte_S100A8,Plasma_IgG,CD8_Tem
```

### 4. Differential Gene Analysis
```bash
SDAS DEG -i sample_domain_graphst.h5ad -o output/DEG_wilcoxon --de_method wilcoxon --group_key domain_graphst --ident1 3 --ident2 8
```

### 5. Gene Set Enrichment Analysis (GSEA)
```bash
SDAS geneSetEnrichment gsea -i sample_domain_graphst.h5ad -o output/geneSetEnrichment_gsea --species human --group_key domain_graphst --ident1 3 --ident2 8 --gmt sdas_deg_enrichment/lib/GSEADB/h.all.v2024.1.Hs.symbols.gmt
```

## Pipeline Example
For full pipeline automation and job scheduling, see the [Pipeline Example](https://mysite.gitbook.io/sdas_manual_eng/readme/05_pipline) and use the provided scripts for cluster or standalone mode.

---
© 2025 STOmics Tech Co., Ltd. All rights reserved.
