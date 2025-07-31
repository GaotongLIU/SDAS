import sys,re,os
import argparse
import pandas as pd

USAGE = 'python3 SDAS_pipeline.py -c pipeline_input.conf -o ./'


def _readconf(conf):
    conf_dict = {}
    with open(conf,'r') as cf:
        for line in cf:
            line = line.strip()
            if not line.startswith('#') and '=' in line:
                lines = line.split('=',1)
                para = lines[0].strip() 
                value = lines[1].strip()
                if value:
                    conf_dict[para] = value
    return conf_dict

def outshell(sh_file, sh_code, cpu, mem):
    outf =  open(sh_file,'w')
    outf.write(f'{sh_code}')
    # Capture exit code first, then output completion info
    outf.write('exit_code=$?\n')
    outf.write('echo "SDAS_EXIT_CODE: $exit_code"\n')
    outf.write('if [ $exit_code -eq 0 ]; then\n')
    outf.write('    echo "SDAS_STATUS: SUCCESS"\n')
    outf.write('else\n')
    outf.write('    echo "SDAS_STATUS: FAILED"\n')
    outf.write('    echo "SDAS_ERROR: Command failed with exit code $exit_code"\n')
    outf.write('fi\n')
    outf.write('echo "all commands done"\n')
    outf.close()
    sh_flag = f'{sh_file}:cpu:{cpu}:mem:{mem}G'
    return sh_flag

def _h5ad(sdas_conf, outdir):
    os.system(f'mkdir -p {outdir}/input_file/shell {outdir}/input_file/result')
    cpu = 1
    mem = 1
    result_file = ''
    h5ad_sh = f'{outdir}/input_file/shell/merge_h5ads.sh'
    sh_code = ''
    h5ad_files = sdas_conf['h5ad_files'].split(';')
    if len(h5ad_files) == 1:
        filename = os.path.basename(h5ad_files[0])
        #filename = re.sub(r'.h5ad$','',filename)
        sh_code = f'ln -sf {h5ad_files[0]} {outdir}/input_file/result > {h5ad_sh}.log 2>{h5ad_sh}.e\n'
        result_file = f'{outdir}/input_file/result/{filename}'
    else:
        h5ad_csv = open(f'{outdir}/input_file/result/samples.csv','w')
        h5ad_csv.write('\n'.join(h5ad_files))
        h5ad_csv.close()
        sh_code = f'{sdas_conf["SDAS_software"]} dataProcess mergeAdata -i {outdir}/input_file/result/samples.csv -o {outdir}/input_file/result > {h5ad_sh}.log 2>{h5ad_sh}.e\n'
        result_file = f'{outdir}/input_file/result/combine.h5ad'
        cpu = 3
        mem = 10
        
    sh_flag = outshell(h5ad_sh, sh_code, cpu, mem)
    shell_list = []
    shell_list.append(sh_flag)
    return result_file,shell_list

def _module(inmod, module, h5adfile, sdas_conf, outdir):
    os.system(f'mkdir -p {outdir}/{module}/shell {outdir}/{module}/result')
    cpu = 2
    mem = 20
    method = sdas_conf[f'{module}_method']
    sh_file = f'{outdir}/{module}/shell/{module}.{inmod}.sh'
    if module == 'TF':
        para_method = ''
        if 'TF_method' in sdas_conf.keys():
            para_method = f'--method {sdas_conf["TF_method"]}'
        sh_code = f'{sdas_conf["SDAS_software"]} TF -i {h5adfile} {para_method} '
    else:
        sh_code = f'{sdas_conf["SDAS_software"]} {module} {method} -i {h5adfile} '
    for p in sdas_conf.keys():
        if p.startswith(f'{module}_') or p.startswith(f'{method}_'):
            if p != f'{module}_method' and p != f'{module}_input_process':
                pras = p.split('_',1)
                if p == 'cellchat_add_spatial':
                    if sdas_conf[p].upper() != 'FALSE':
                        sh_code += f'--{pras[1]} '
                else:
                    sh_code += f'--{pras[1]} {sdas_conf[p]} '
            if p == f'{method}_n_cpus':
                cpu = sdas_conf[f'{method}_n_cpus']
            if p == f'{method}_n_threads':
                cpu = sdas_conf[f'{method}_n_threads']
            if p == f'{module}_n_cpus':
                cpu = sdas_conf[f'{module}_n_cpus']
    sh_code += f'-o {outdir}/{module}/result >{sh_file}.log 2>{sh_file}.e \n'
    sh_flag = outshell(sh_file, sh_code, cpu, mem)
    shell_list = []
    shell_list.append(sh_flag)
    result_file = ''
    out_file_name = os.path.basename(h5adfile)
    out_file_name = re.sub(r'.h5ad','',out_file_name)
    if module == 'cellAnnotation':
        out_file_name = f'{out_file_name}_anno_{method}.h5ad'
    elif module == 'spatialDomain':
        out_file_name = f'{out_file_name}_domain_{method}.h5ad'
    elif module == 'coexpress':
        out_file_name = f'{out_file_name}_{method}.h5ad'
    elif module == 'cellularNeighborhood':
        out_file_name = f'{out_file_name}_CN.h5ad'
    elif module == 'spatialRelate':
        if method == 'crawdad':
            out_file_name = f'{out_file_name}_processed_for_crawdad.h5ad'
        elif method == 'squidpy':
            out_file_name = f'{out_file_name}_squidpy_processed.h5ad'
    elif module == 'TF':
        out_file_name = f'{out_file_name}.loom'
    elif module == 'CCI':
        out_file_name = f'{out_file_name}_{method}.rds'

    result_file = f'{outdir}/{module}/result/{out_file_name}'
    return result_file,shell_list

def _rmodule(inmod, module, h5adfile, sdas_conf, outdir):
    os.system(f'mkdir -p {outdir}/{module}/shell {outdir}/{module}/result')
    cpu = 3
    mem = 20
    file_name = os.path.basename(h5adfile)
    file_name = re.sub(r'.h5ad','',file_name)
    method = sdas_conf[f'{module}_method']
    sh_file = f'{outdir}/{module}/shell/{module}.{inmod}.sh'
    sh_code = f'{sdas_conf["SDAS_software"]} dataProcess h5ad2rds -i {h5adfile} -o {outdir}/{module}/result > {sh_file}.log 2>{sh_file}.e \n'
    
    if method == 'infercnv':
        sh_code += f'{sdas_conf["SDAS_software"]} infercnv -i {outdir}/{module}/result/{file_name}.rds --h5ad {h5adfile} '
    else:
        sh_code += f'{sdas_conf["SDAS_software"]} {module} {method} -i {outdir}/{module}/result/{file_name}.rds '

    for p in sdas_conf.keys():
        if p.startswith(f'{module}_') or p.startswith(f'{method}_'):
            if p != f'{module}_method' and p != f'{module}_input_process':
                pras = p.split('_',1)
                sh_code += f'--{pras[1]} {sdas_conf[p]} '
            if p == f'{method}_n_cpus':
                cpu = sdas_conf[f'{method}_n_cpus']
            if p == f'{method}_n_threads':
                cpu = sdas_conf[f'{method}_n_threads']
            if p == f'{module}_n_cpus':
                cpu = sdas_conf[f'{module}_n_cpus']
    sh_code += f'-o {outdir}/{module}/result >> {sh_file}.log 2>>{sh_file}.e \n'
    sh_flag = outshell(sh_file, sh_code, cpu, mem)
    shell_list = []
    shell_list.append(sh_flag)
    result_file = ''
    out_file_name = os.path.basename(h5adfile)
    out_file_name = re.sub(r'.h5ad','',out_file_name)
    if module == 'infercnv':
        out_file_name = f'{out_file_name}_run.final.infercnv_obj.rds'
    elif module == 'trajectory':
        out_file_name = f'{out_file_name}_{method}.rds'
    result_file = f'{outdir}/{module}/result/{out_file_name}'
    return result_file,shell_list

def _deg(inmod, h5adfile, sdas_conf, outdir):
    os.system(f'mkdir -p {outdir}/deg/shell {outdir}/deg/result')
    cpu = 2
    mem = 20
    diff_plans = sdas_conf['deg_plan'].split(';')
    deg_sh = f'{outdir}/deg/shell/deg.{inmod}.sh'
    deg_all_sh = f'rm -f {deg_sh}.log {deg_sh}.e\n'
    for dfp in diff_plans:
        deg_code = f'{sdas_conf["SDAS_software"]} DEG -i {h5adfile} '
        df_infs = dfp.split(',')
        deg_code += f'--group_key {df_infs[0]} '
        
        if df_infs[1] != 'all':
            deg_code += f'--ident1 {df_infs[1]} '
        if df_infs[2] != 'rest':
            deg_code += f'--ident2 {df_infs[2]} '
            
        deg_code += f'--de_method {df_infs[3]} '
        
        if len(df_infs) >= 5:
            deg_code += f'--subset_key {df_infs[4]} '
        if len(df_infs) > 5:
            deg_code += f'--subset_values {df_infs[5]} '
            
        if df_infs[3] == 'DESeq2' or df_infs[3] == 'edgeR':
            deg_code += f"--sample_key {sdas_conf['deg_sample_key']} "
        for p in sdas_conf.keys():
            if p.startswith('deg_') :
                if p != 'deg_plan' and p != 'deg_sample_key' and p != 'deg_species' and p != 'deg_gmt':
                    pras = p.split('_',1)
                    deg_code += f'--{pras[1]} {sdas_conf[p]} '
        deg_code += f'-o {outdir}/deg/result >> {deg_sh}.log 2>>{deg_sh}.e \n'
        deg_all_sh += f'{deg_code}'
    sh_flag = outshell(deg_sh, deg_all_sh, cpu, mem)
    shell_list = []
    shell_list.append(sh_flag)
    diff_dir = f'{outdir}/deg/result'
    return diff_dir,shell_list

def _Enrich(inputmodule, genelist_dir, sdas_conf, outdir):
    cpu = 2
    mem = 20
    py = re.sub(r'SDAS$','data_process/anaconda/bin/python3',sdas_conf["SDAS_software"])
    os.system(f'mkdir -p {outdir}/geneEnrichment/shell {outdir}/geneEnrichment/result/enrich_{inputmodule}')
    paras = ''
    enrich_file = f'{outdir}/geneEnrichment/shell/enrich_{inputmodule}.sh'
    for p in sdas_conf.keys():
        if p.startswith('geneSetEnrichment_species') or p.startswith('geneSetEnrichment_gmt'):
            pras = p.split('_',1)
            paras += f'--{pras[1]} {sdas_conf[p]} '
            
    if inputmodule == 'DEG':
        enrich_shell = f'''rm -f {enrich_file}.log {enrich_file}.e
for dif in $(ls {genelist_dir}/*.sig_filtered.csv)
do
    filename=$(basename "$dif" .sig_filtered.csv)
    {sdas_conf["SDAS_software"]} geneSetEnrichment enrichr -i $dif {paras} -o {outdir}/geneEnrichment/result/enrich_{inputmodule}/$filename >> {enrich_file}.log 2>> {enrich_file}.e
done
'''
        enrich_shell += f'''
for dif in $(ls {genelist_dir}/*.all.csv)
do
    filename=$(basename "$dif" .all.csv)
    {sdas_conf["SDAS_software"]} geneSetEnrichment prerank -i $dif {paras} -o {outdir}/geneEnrichment/result/enrich_{inputmodule}/$filename >> {enrich_file}.log 2>> {enrich_file}.e
done
'''
    elif inputmodule == 'coexpress':
        genelist_dir = os.path.dirname(genelist_dir)
        enrich_shell = f'''rm -f {enrich_file}.log {enrich_file}.e
for dif in $(ls {genelist_dir}/*.module.csv)
do
    filename=$(basename "$dif" .csv)
    mkdir -p {outdir}/geneEnrichment/result/enrich_{inputmodule}/$filename/input
    {py} {os.path.abspath(__file__)} --split $dif -o {outdir}/geneEnrichment/result/enrich_{inputmodule}/$filename/input
    for inf in $(ls {outdir}/geneEnrichment/result/enrich_{inputmodule}/$filename/input/*.csv)
    do
        {sdas_conf["SDAS_software"]} geneSetEnrichment enrichr -i $inf {paras} -o {outdir}/geneEnrichment/result/enrich_{inputmodule}/$filename >> {enrich_file}.log 2>> {enrich_file}.e
    done
    rm -rf {outdir}/geneEnrichment/result/enrich_{inputmodule}/$filename/input
done
'''
    else:
        enrich_shell = f'''rm -f {enrich_file}.log {enrich_file}.e
for dif in $(ls {genelist_dir}/*.csv)
do
    filename=$(basename "$dif" .csv)
    {sdas_conf["SDAS_software"]} geneSetEnrichment enrichr -i $dif {paras} -o {outdir}/geneEnrichment/result/enrich_{inputmodule}/$filename >> {enrich_file}.log 2>> {enrich_file}.e
done
'''
        
    sh_flag = outshell(enrich_file, enrich_shell, cpu, mem)
    shell_list = []
    shell_list.append(sh_flag)
    result_dir = f'{outdir}/geneEnrichment/result'
    return result_dir,shell_list

def _gsea(inmod, h5adfile, sdas_conf, outdir):
    os.system(f'mkdir -p {outdir}/geneEnrichment/shell {outdir}/geneEnrichment/result/gsea')
    cpu = 2
    mem = 20
    gsea_plans = sdas_conf['gsea_plan'].split(';')
    gsea_sh = f'{outdir}/geneEnrichment/shell/gsea.{inmod}.sh'
    gsea_all_sh = f'rm -f {gsea_sh}.log {gsea_sh}.e\n'
    for gp in gsea_plans:
        gp_infs = gp.split(',')
        sh_code = f'{sdas_conf["SDAS_software"]} geneSetEnrichment gsea -i {h5adfile} --group_key {gp_infs[0]} --ident1 {gp_infs[1]} --ident2 {gp_infs[2]} '

        if len(gp_infs) > 3:
            sh_code += f'--subset_key {gp_infs[3]} --subset_values {gp_infs[4]} '
            
        for p in sdas_conf.keys():
            if p.startswith('geneSetEnrichment_') or p.startswith('gsea_'):
                if p != 'gsea_plan' and p != 'geneSetEnrichment_input_process':
                    pras = p.split('_',1)
                    sh_code += f'--{pras[1]} {sdas_conf[p]} '
            
        sh_code += f'-o {outdir}/geneEnrichment/result/gsea >> {gsea_sh}.log 2>>{gsea_sh}.e\n'
        gsea_all_sh += f'{sh_code}'
    sh_flag = outshell(gsea_sh, gsea_all_sh, cpu, mem)
    shell_list = []
    shell_list.append(sh_flag)
    gsea_result = f'{outdir}/geneEnrichment/result/gsea'
    return gsea_result,shell_list

def _gsva(inmod, h5adfile, sdas_conf, outdir):
    os.system(f'mkdir -p {outdir}/geneEnrichment/shell {outdir}/geneEnrichment/result/gsva')
    cpu = 2
    mem = 20
    gsva_plans = sdas_conf['gsva_plan'].split(';')
    gsva_sh = f'{outdir}/geneEnrichment/shell/gsva.{inmod}.sh'
    gsva_all_sh = f'rm -f {gsva_sh}.log {gsva_sh}.e\n'
    for gsp in gsva_plans:
        gsp_infs = gsp.split(',')
        gsp_infs[1] = re.sub(r':',',',gsp_infs[1])
        sh_code = f'{sdas_conf["SDAS_software"]} geneSetEnrichment gsva -i {h5adfile} --group_key {gsp_infs[0]} --idents {gsp_infs[1]} '
        if len(gsp_infs) > 2:
            gsp_infs[3] = re.sub(r':',',',gsp_infs[3])
            sh_code += f'--subset_key {gsp_infs[2]} --subset_values {gsp_infs[3]} '
        
        for p in sdas_conf.keys():
            if p.startswith('geneSetEnrichment_') or p.startswith('gsva_'):
                if p != 'gsva_plan' and p != 'geneSetEnrichment_input_process':
                    pras = p.split('_',1)
                    sh_code += f'--{pras[1]} {sdas_conf[p]} '
        sh_code += f'-o {outdir}/geneEnrichment/result/gsva >> {gsva_sh}.log 2>>{gsva_sh}.e\n'
        gsva_all_sh += f'{sh_code}'
    sh_flag = outshell(gsva_sh, gsva_all_sh, cpu, mem)
    shell_list = []
    shell_list.append(sh_flag)
    gsva_result = f'{outdir}/geneEnrichment/result/gsva'
    return gsva_result,shell_list

def _ppi(inputmodule, inputdir, sdas_conf, outdir):
    os.system(f'mkdir -p {outdir}/PPI/shell {outdir}/PPI/result')
    cpu = 2
    mem = 20
    paras = ''
    py = re.sub(r'SDAS$','data_process/anaconda/bin/python3',sdas_conf["SDAS_software"])
    for p in sdas_conf.keys():
        if p.startswith('PPI_') and p != 'PPI_method' and p != 'PPI_input_process':
            pras = p.split('_',1)
            paras += f'--{pras[1]} {sdas_conf[p]} '
            
    if inputmodule == 'DEG':
        ppi_file = f'{outdir}/PPI/shell/PPI.DEG.sh'
        ppi_shell = f'''rm -f {ppi_file}.log {ppi_file}.e
for gf in $(ls {inputdir}/*.sig_filtered.csv)
do
    filename=$(basename "$gf" .csv)
    mkdir -p {outdir}/PPI/result/$filename
    awk -F ',' 'NR>1 {{print $1}}' $gf > {outdir}/PPI/result/$filename/$filename.genelist
    {sdas_conf["SDAS_software"]} PPI -i {outdir}/PPI/result/$filename/$filename.genelist {paras} -o {outdir}/PPI/result/$filename >> {ppi_file}.log 2>>{ppi_file}.e
done
'''
    elif inputmodule == 'coexpress':
        inputdir = os.path.dirname(inputdir)
        ppi_file = f'{outdir}/PPI/shell/PPI.coexpress.sh'
        ppi_shell = f'''rm -f {ppi_file}.log {ppi_file}.e
for gf in $(ls {inputdir}/*.module.csv)
do
    filename=$(basename "$gf" .csv)
    mkdir -p {outdir}/PPI/result/$filename/input
    {py} {os.path.abspath(__file__)} --split $gf -o {outdir}/PPI/result/$filename/input
    for mf in $(ls {outdir}/PPI/result/$filename/input/*.csv)
    do
        filenameB=$(basename "$mf" .csv)
        mkdir -p {outdir}/PPI/result/$filename/$filenameB
        awk -F ',' 'NR>1 {{print $1}}' $mf > {outdir}/PPI/result/$filename/$filenameB/$filenameB.genelist
        {sdas_conf["SDAS_software"]} PPI -i {outdir}/PPI/result/$filename/$filenameB/$filenameB.genelist {paras} -o {outdir}/PPI/result/$filename/$filenameB >> {ppi_file}.log 2>>{ppi_file}.e
    done
    rm -rf {outdir}/PPI/result/$filename/input
done
'''
    else:
        ppi_file = f'{outdir}/PPI/shell/PPI.{inputmodule}.sh'
        ppi_shell = f'''rm -f {ppi_file}.log {ppi_file}.e
for gf in $(ls {inputdir}/*.csv)
do
    filename=$(basename "$gf" .csv)
    mkdir -p {outdir}/PPI/result/$filename
    {sdas_conf["SDAS_software"]} PPI -i $gf {paras} -o {outdir}/PPI/result/$filename >> {ppi_file}.log 2>>{ppi_file}.e
done
'''
        
    sh_flag = outshell(ppi_file, ppi_shell, cpu, mem)
    shell_list = []
    shell_list.append(sh_flag)
    result_file = f'{outdir}/PPI/result'
    return result_file,shell_list

def _splitcoexpress(coexpressresult, out):
    df = pd.read_csv(coexpressresult)
    infile_name = os.path.basename(coexpressresult)
    infile_name = re.sub(r'.csv','',infile_name)
    for module_name, group in df.groupby("Module"):
        output_df = group[["real_gene_name"]].rename(columns={"real_gene_name": "geneName"})
        output_df["log2FC"] = 1
        output_df.to_csv(f"{out}/{infile_name}.{module_name}.csv", index=False)

def main():
    parser = argparse.ArgumentParser(usage=USAGE)
    sub_parsers = parser.add_subparsers(help="Commands help.")
    parser.add_argument("--split", action="store", type=str, help=argparse.SUPPRESS)
    parser.add_argument("-c","--conf", action="store", type=str, dest="conf",help="input conf file")
    parser.add_argument("-o","--outdir", action="store", type=str, default="./", dest="outdir", help="output directory")
    args = parser.parse_args()

    outdir = os.path.abspath(args.outdir)
    
    if args.split:
        _splitcoexpress(args.split, outdir)
        sys.exit(0)
    
    sdas_conf = _readconf(args.conf)
    
    if 'SDAS_software' not in sdas_conf.keys():
        print('SDAS_software not in conf file, please set')
        sys.exit(1)
    if 'h5ad_files' not in sdas_conf.keys():
        print('h5ad_files not in conf file, please set')
        sys.exit(1)
    if 'process' not in sdas_conf.keys():
        print('process not in conf file, please set')
        sys.exit(1)

    os.system(f'mkdir -p {outdir}')
    outshell = open(f'{outdir}/all_shell.conf','w')
    process = sdas_conf['process'].split(',')
    in_files_num = len(sdas_conf['h5ad_files'].split(';'))
    module_infos = {}

    input_file,h5ad_shs = _h5ad(sdas_conf, outdir)
    module_infos['basic'] = [[input_file], h5ad_shs]

    # Only analyze co-expression when there is only one file, multi-file data cannot be run
    if 'coexpress' in process and in_files_num == 1:
        module_infos['coexpress'] = [[],[]]
        coexp_in_process = sdas_conf['coexpress_input_process'].split(',')
        for inmod in coexp_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for coexp_infile in set(module_infos[inmod][0]):
                    coexp_file,coexp_shs = _module(inmod, 'coexpress', coexp_infile, sdas_conf, outdir)
                    module_infos['coexpress'][0].append(coexp_file)
                    module_infos['coexpress'][1] += coexp_shs
                for esh in coexp_shs:
                    for upsh in set(module_infos[inmod][1]):
                        outshell.write(f'{upsh}\t{esh}\n')

    if 'cellAnnotation' in process:
        module_infos['cellAnnotation'] = [[],[]]
        cann_in_process = sdas_conf['cellAnnotation_input_process'].split(',')
        for inmod in cann_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for cann_infile in set(module_infos[inmod][0]):
                    cell_anno,anno_shs = _module(inmod, 'cellAnnotation', cann_infile, sdas_conf, outdir)
                    module_infos['cellAnnotation'][0].append(cell_anno)
                    module_infos['cellAnnotation'][1] += anno_shs
                for ansh in anno_shs:
                    for upsh in set(module_infos[inmod][1]):
                        outshell.write(f'{upsh}\t{ansh}\n')

    # Only analyze when there is only one file, multi-file data cannot be run
    if 'spatialDomain' in process and in_files_num == 1:
        module_infos['spatialDomain'] = [[],[]]
        spd_in_process = sdas_conf['spatialDomain_input_process'].split(',')
        for inmod in spd_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for spd_infile in set(module_infos[inmod][0]):
                    st_domain,domain_shs = _module(inmod, 'spatialDomain', spd_infile, sdas_conf, outdir)
                    module_infos['spatialDomain'][0].append(st_domain)
                    module_infos['spatialDomain'][1] += domain_shs
                for domsh in domain_shs:
                    for upsh in set(module_infos[inmod][1]):
                        outshell.write(f'{upsh}\t{domsh}\n')

    if 'infercnv' in process:
        module_infos['infercnv'] = [[],[]]
        cnv_in_process = sdas_conf['infercnv_input_process'].split(',')
        for inmod in cnv_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for cnv_infile in set(module_infos[inmod][0]):
                    cnv_result,cnv_shs = _rmodule(inmod, 'infercnv', cnv_infile, sdas_conf, outdir)
                    module_infos['infercnv'][0].append(cnv_result)
                    module_infos['infercnv'][1] += cnv_shs
                for csh in cnv_shs:
                    for upsh in set(module_infos[inmod][1]):
                        outshell.write(f'{upsh}\t{csh}\n')

    if 'trajectory' in process:
        module_infos['trajectory'] = [[],[]]
        traj_in_process = sdas_conf['trajectory_input_process'].split(',')
        for inmod in traj_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for traj_infile in set(module_infos[inmod][0]):
                    traj_result,traj_shs = _rmodule(inmod, 'trajectory', traj_infile, sdas_conf, outdir)
                    module_infos['trajectory'][0].append(traj_result)
                    module_infos['trajectory'][1] += traj_shs
                for tsh in traj_shs:
                    for upsh in set(module_infos[inmod][1]):
                        outshell.write(f'{upsh}\t{tsh}\n')

    if 'DEG' in process and 'deg_plan' in sdas_conf.keys():
        deg_in_process = sdas_conf['DEG_input_process'].split(',')
        module_infos['DEG'] = [[],[]]
        for inmod in deg_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for deg_infile in set(module_infos[inmod][0]):
                    deg_result_dir,deg_shs = _deg(inmod, deg_infile, sdas_conf, outdir)
                    module_infos['DEG'][0].append(deg_result_dir)
                    module_infos['DEG'][1] += deg_shs
                for sh in deg_shs:
                    for upsh in set(module_infos[inmod][1]):
                        outshell.write(f'{upsh}\t{sh}\n')

    if 'geneSetEnrichment' in process:
        gse_in_process = sdas_conf['geneSetEnrichment_input_process'].split(',')
        if 'gsea_plan' in sdas_conf.keys():
            module_infos['gsea'] = [[],[]]
            for inmod in gse_in_process:
                if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                    for gsea_infile in set(module_infos[inmod][0]):
                        gsea_result,gsea_shs = _gsea(inmod, gsea_infile, sdas_conf, outdir)
                        module_infos['gsea'][0].append(gsea_result)
                        module_infos['gsea'][1] += gsea_shs
                    for sh in gsea_shs:
                        for upsh in set(module_infos[inmod][1]):
                            outshell.write(f'{upsh}\t{sh}\n')
                            
        if 'gsva_plan' in sdas_conf.keys():
            module_infos['gsva'] = [[],[]]
            for inmod in gse_in_process:
                if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                    for gsva_infile in set(module_infos[inmod][0]):
                        gsva_result,gsva_shs = _gsva(inmod, gsva_infile, sdas_conf, outdir)
                        module_infos['gsva'][0].append(gsva_result)
                        module_infos['gsva'][1] += gsva_shs
                    for sh in gsva_shs:
                        for upsh in set(module_infos[inmod][1]):
                            outshell.write(f'{upsh}\t{sh}\n')

        if 'genelist_enrich_input_process' in sdas_conf.keys():
            enr_in_process = sdas_conf['genelist_enrich_input_process'].split(',')
            for inmod in enr_in_process:
                if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                    for genelist_dir in set(module_infos[inmod][0]):
                        enr_dir,enr_shs = _Enrich(inmod, genelist_dir, sdas_conf, outdir)
                    for sh in enr_shs:
                        for upsh in set(module_infos[inmod][1]):
                            outshell.write(f'{upsh}\t{sh}\n')

    if 'cellularNeighborhood' in process:
        module_infos['cellularNeighborhood'] = [[],[]]
        cn_in_process = sdas_conf['cellularNeighborhood_input_process'].split(',')
        for inmod in cn_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for cn_infile in set(module_infos[inmod][0]):
                    cn_file,cn_shs = _module(inmod, 'cellularNeighborhood', cn_infile, sdas_conf, outdir)
                    module_infos['cellularNeighborhood'][0].append(cn_file)
                    module_infos['cellularNeighborhood'][1] += cn_shs
                for cnsh in cn_shs:
                    for upsh in set(module_infos[inmod][1]):
                        outshell.write(f'{upsh}\t{cnsh}\n')

    if 'CCI' in process:
        module_infos['CCI'] = [[],[]]
        cci_in_process = sdas_conf['CCI_input_process'].split(',')
        for inmod in cci_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for cci_infile in set(module_infos[inmod][0]):
                    cci_result,cci_shs = _module(inmod, 'CCI', cci_infile, sdas_conf, outdir)
                    module_infos['CCI'][0].append(cci_result)
                    module_infos['CCI'][1] += cci_shs
                for ccsh in cci_shs:
                    for upsh in set(module_infos[inmod][1]):
                        outshell.write(f'{upsh}\t{ccsh}\n')

    if 'spatialRelate' in process:
        module_infos['spatialRelate'] = [[],[]]
        spr_in_process = sdas_conf['spatialRelate_input_process'].split(',')
        for inmod in spr_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for spr_infile in set(module_infos[inmod][0]):
                    spr_file,spr_shs = _module(inmod, 'spatialRelate', spr_infile, sdas_conf, outdir)
                    module_infos['spatialRelate'][0].append(spr_file)
                    module_infos['spatialRelate'][1] += spr_shs
                for sprsh in spr_shs:
                    for upsh in set(module_infos[inmod][1]):
                        outshell.write(f'{upsh}\t{sprsh}\n')

    if 'TF' in process:
        module_infos['TF'] = [[],[]]
        tf_in_process = sdas_conf['TF_input_process'].split(',')
        for inmod in tf_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for tf_infile in set(module_infos[inmod][0]):
                    tf_file,tf_shs = _module(inmod, 'TF', tf_infile, sdas_conf, outdir)
                    module_infos['TF'][0].append(tf_file)
                    module_infos['TF'][1] += tf_shs
                for tfsh in tf_shs:
                    for upsh in set(module_infos[inmod][1]):
                        outshell.write(f'{upsh}\t{tfsh}\n')

    if 'PPI' in process:
        module_infos['PPI'] = [[],[]]
        ppi_in_process = sdas_conf['PPI_input_process'].split(',')
        for inmod in ppi_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for ppi_infile in set(module_infos[inmod][0]):
                    ppi_result,ppi_shs = _ppi(inmod, ppi_infile, sdas_conf, outdir)
                    module_infos['PPI'][0].append(ppi_result)
                    module_infos['PPI'][1] += ppi_shs
                for ppi_sh in ppi_shs:
                    for upsh in set(module_infos[inmod][1]):
                        outshell.write(f'{upsh}\t{ppi_sh}\n')
    outshell.close()

if __name__ == '__main__':
    main()
