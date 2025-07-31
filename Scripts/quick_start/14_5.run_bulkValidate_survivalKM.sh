#!/bin/bash

tool_dir=../../sdas-1.0.0
output_dir=../../output/bulkValidate_survivalKM
input=../../output/bulkValidate_immuneScore/tme_combine.txt
survival=../../Test_data/bulkValidate/survival.txt


${tool_dir}/SDAS bulkValidate survivalKM --input $input --clinical $survival --signature Macrophages_M2_CIBERSORT --project_name survival --time OS.time --status OS.status --time_type day -o $output_dir