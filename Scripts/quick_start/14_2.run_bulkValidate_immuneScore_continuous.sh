#!/bin/bash

tool_dir=../../sdas-1.0.0
output_dir=../../output/bulkValidate_immuneScore_continuous
fpkm=../../Test_data/bulkValidate/fpkm.txt
cli=../../Test_data/bulkValidate/clinical.txt


${tool_dir}/SDAS bulkValidate immuneScore --expression $fpkm --clinical $cli --group_col age_at_diagnosis.diagnoses --group_type continuous -o $output_dir
