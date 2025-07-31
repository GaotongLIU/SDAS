import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

USAGE = "python3 SDAS_pipeline_subprocess.py -c pipeline_input.conf -o ./"


def _readconf(conf):
    conf_dict = {}
    with open(conf, "r") as cf:
        for line in cf:
            line = line.strip()
            if not line.startswith("#") and "=" in line:
                lines = line.split("=", 1)
                para = lines[0].strip()
                value = lines[1].strip()
                if value:
                    conf_dict[para] = value
    return conf_dict


# 并行执行一批命令，每个元素是 (cmd, log_file, err_file)
def run_batch_parallel(cmds_with_logs, max_workers=8):
    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for cmd, log_file, err_file in cmds_with_logs:
            print(f"[SDAS_pipeline_subprocess] Running: {cmd}")
            log_f = open(log_file, "w") if log_file else subprocess.DEVNULL
            err_f = open(err_file, "w") if err_file else subprocess.DEVNULL
            futures.append(executor.submit(subprocess.run, cmd, shell=True, stdout=log_f, stderr=err_f))
        for future in as_completed(futures):
            try:
                result = future.result()
                if result.returncode != 0:
                    print(f"Command failed: {result.args}")
            except Exception as e:
                print(f"Exception in command: {e}")
    # 关闭所有文件
    for _, log_file, err_file in cmds_with_logs:
        if log_file and log_file != subprocess.DEVNULL:
            try:
                log_f = open(log_file, "a")
                log_f.close()
            except:
                pass
        if err_file and err_file != subprocess.DEVNULL:
            try:
                err_f = open(err_file, "a")
                err_f.close()
            except:
                pass


def _h5ad(sdas_conf, outdir):
    os.makedirs(f"{outdir}/input_file/result", exist_ok=True)
    result_file = ""
    log_file = f"{outdir}/input_file/merge_h5ads.log"
    err_file = f"{outdir}/input_file/merge_h5ads.e"
    h5ad_files = sdas_conf["h5ad_files"].split(";")
    cmds_with_logs = []
    if len(h5ad_files) == 1:
        filename = os.path.basename(h5ad_files[0])
        cmd = f"ln -sf {h5ad_files[0]} {outdir}/input_file/result > {log_file} 2>{err_file}"
        result_file = f"{outdir}/input_file/result/{filename}"
        cmds_with_logs.append((cmd, log_file, err_file))
    else:
        h5ad_csv_path = f"{outdir}/input_file/result/samples.csv"
        with open(h5ad_csv_path, "w") as h5ad_csv:
            h5ad_csv.write("\n".join(h5ad_files))
        cmd = f"{sdas_conf['SDAS_software']} dataProcess mergeAdata -i {h5ad_csv_path} -o {outdir}/input_file/result > {log_file} 2>{err_file}"
        result_file = f"{outdir}/input_file/result/combine.h5ad"
        cmds_with_logs.append((cmd, log_file, err_file))
    return result_file, cmds_with_logs


def _module(inmod, module, h5adfile, sdas_conf, outdir):
    os.makedirs(f"{outdir}/{module}/result", exist_ok=True)
    method = sdas_conf[f"{module}_method"]
    log_file = f"{outdir}/{module}/{module}.{inmod}.log"
    err_file = f"{outdir}/{module}/{module}.{inmod}.e"
    if module == "TF":
        para_method = ""
        if "TF_method" in sdas_conf.keys():
            para_method = f"--method {sdas_conf['TF_method']}"
        sh_code = f"{sdas_conf['SDAS_software']} TF -i {h5adfile} {para_method} "
    else:
        sh_code = f"{sdas_conf['SDAS_software']} {module} {method} -i {h5adfile} "
    for p in sdas_conf.keys():
        if p.startswith(f"{module}_") or p.startswith(f"{method}_"):
            if p != f"{module}_method" and p != f"{module}_input_process":
                pras = p.split("_", 1)
                if p == "cellchat_add_spatial":
                    if sdas_conf[p].upper() != "FALSE":
                        sh_code += f"--{pras[1]} "
                else:
                    sh_code += f"--{pras[1]} {sdas_conf[p]} "
    sh_code += f"-o {outdir}/{module}/result >{log_file} 2>{err_file}"
    out_file_name = os.path.basename(h5adfile)
    out_file_name = re.sub(r".h5ad", "", out_file_name)
    if module == "cellAnnotation":
        out_file_name = f"{out_file_name}_anno_{method}.h5ad"
    elif module == "spatialDomain":
        out_file_name = f"{out_file_name}_domain_{method}.h5ad"
    elif module == "coexpress":
        out_file_name = f"{out_file_name}_{method}.h5ad"
    elif module == "cellularNeighborhood":
        out_file_name = f"{out_file_name}_CN.h5ad"
    elif module == "spatialRelate":
        if method == "crawdad":
            out_file_name = f"{out_file_name}_processed_for_crawdad.h5ad"
        elif method == "squidpy":
            out_file_name = f"{out_file_name}_squidpy_processed.h5ad"
    elif module == "TF":
        out_file_name = f"{out_file_name}.loom"
    elif module == "CCI":
        out_file_name = f"{out_file_name}_{method}.rds"
    result_file = f"{outdir}/{module}/result/{out_file_name}"
    return result_file, [(sh_code, log_file, err_file)]


def _rmodule(inmod, module, h5adfile, sdas_conf, outdir):
    os.makedirs(f"{outdir}/{module}/result", exist_ok=True)
    file_name = os.path.basename(h5adfile)
    file_name = re.sub(r".h5ad", "", file_name)
    method = sdas_conf[f"{module}_method"]
    log_file = f"{outdir}/{module}/{module}.{inmod}.log"
    err_file = f"{outdir}/{module}/{module}.{inmod}.e"
    sh_code = f"{sdas_conf['SDAS_software']} dataProcess h5ad2rds -i {h5adfile} -o {outdir}/{module}/result > {log_file} 2>{err_file} "
    if method == "infercnv":
        sh_code += (
            f"&& {sdas_conf['SDAS_software']} infercnv -i {outdir}/{module}/result/{file_name}.rds --h5ad {h5adfile} "
        )
    else:
        sh_code += f"&& {sdas_conf['SDAS_software']} {module} {method} -i {outdir}/{module}/result/{file_name}.rds "
    for p in sdas_conf.keys():
        if p.startswith(f"{module}_") or p.startswith(f"{method}_"):
            if p != f"{module}_method" and p != f"{module}_input_process":
                pras = p.split("_", 1)
                sh_code += f"--{pras[1]} {sdas_conf[p]} "
    sh_code += f"-o {outdir}/{module}/result >> {log_file} 2>>{err_file}"
    out_file_name = os.path.basename(h5adfile)
    out_file_name = re.sub(r".h5ad", "", out_file_name)
    if module == "infercnv":
        out_file_name = f"{out_file_name}_run.final.infercnv_obj.rds"
    elif module == "trajectory":
        out_file_name = f"{out_file_name}_{method}.rds"
    result_file = f"{outdir}/{module}/result/{out_file_name}"
    return result_file, [(sh_code, log_file, err_file)]


def _deg(inmod, h5adfile, sdas_conf, outdir):
    os.makedirs(f"{outdir}/deg/result", exist_ok=True)
    diff_plans = sdas_conf["deg_plan"].split(";")
    log_file = f"{outdir}/deg/deg.{inmod}.log"
    err_file = f"{outdir}/deg/deg.{inmod}.e"
    deg_all_sh = f"rm {log_file} {err_file}\n"
    for dfp in diff_plans:
        deg_code = f"{sdas_conf['SDAS_software']} DEG -i {h5adfile} "
        df_infs = dfp.split(",")
        deg_code += f"--group_key {df_infs[0]} "
        if df_infs[1] != "all":
            deg_code += f"--ident1 {df_infs[1]} "
        if df_infs[2] != "rest":
            deg_code += f"--ident2 {df_infs[2]} "
        deg_code += f"--de_method {df_infs[3]} "
        if len(df_infs) >= 5:
            deg_code += f"--subset_key {df_infs[4]} "
        if len(df_infs) > 5:
            deg_code += f"--subset_values {df_infs[5]} "
        if df_infs[3] == "DESeq2" or df_infs[3] == "edgeR":
            deg_code += f"--sample_key {sdas_conf['deg_sample_key']} "
        for p in sdas_conf.keys():
            if p.startswith("deg_"):
                if p != "deg_plan" and p != "deg_sample_key" and p != "deg_species" and p != "deg_gmt":
                    pras = p.split("_", 1)
                    deg_code += f"--{pras[1]} {sdas_conf[p]} "
        deg_code += f"-o {outdir}/deg/result >> {log_file} 2>>{err_file} "
        deg_all_sh += f"{deg_code}\n"
    return f"{outdir}/deg/result", [(deg_all_sh, log_file, err_file)]


def _Enrich(inputmodule, genelist_dir, sdas_conf, outdir):
    os.makedirs(f"{outdir}/geneEnrichment/result/enrich_{inputmodule}", exist_ok=True)
    paras = ""
    log_file = f"{outdir}/geneEnrichment/enrich_{inputmodule}.log"
    err_file = f"{outdir}/geneEnrichment/enrich_{inputmodule}.e"
    for p in sdas_conf.keys():
        if p.startswith("geneSetEnrichment_species") or p.startswith("geneSetEnrichment_gmt"):
            pras = p.split("_", 1)
            paras += f"--{pras[1]} {sdas_conf[p]} "
    cmds_with_logs = []
    temp_dirs_to_clean = []  # 存储需要清理的临时目录
    # DEG分支
    if inputmodule == "DEG":
        # enrichr for *.sig_filtered.csv
        for dif in os.listdir(genelist_dir):
            if dif.endswith(".sig_filtered.csv"):
                filename = os.path.basename(dif).replace(".sig_filtered.csv", "")
                cmd = f"{sdas_conf['SDAS_software']} geneSetEnrichment enrichr -i {os.path.join(genelist_dir, dif)} {paras} -o {outdir}/geneEnrichment/result/enrich_{inputmodule}/{filename} >> {log_file} 2>> {err_file}"
                cmds_with_logs.append((cmd, log_file, err_file))
        # prerank for *.all.csv
        for dif in os.listdir(genelist_dir):
            if dif.endswith(".all.csv"):
                filename = os.path.basename(dif).replace(".all.csv", "")
                cmd = f"{sdas_conf['SDAS_software']} geneSetEnrichment prerank -i {os.path.join(genelist_dir, dif)} {paras} -o {outdir}/geneEnrichment/result/enrich_{inputmodule}/{filename} >> {log_file} 2>> {err_file}"
                cmds_with_logs.append((cmd, log_file, err_file))
    # coexpress分支
    elif inputmodule == "coexpress":
        genelist_dir = os.path.dirname(genelist_dir)
        for dif in os.listdir(genelist_dir):
            if dif.endswith(".module.csv"):
                filename = os.path.basename(dif).replace(".csv", "")
                input_dir = f"{outdir}/geneEnrichment/result/enrich_{inputmodule}/{filename}/input"
                os.makedirs(input_dir, exist_ok=True)
                # split
                _splitcoexpress(os.path.join(genelist_dir, dif), input_dir)
                for inf in os.listdir(input_dir):
                    if inf.endswith(".csv"):
                        inf_path = os.path.join(input_dir, inf)
                        cmd1 = f"{sdas_conf['SDAS_software']} geneSetEnrichment enrichr -i {inf_path} {paras} -o {outdir}/geneEnrichment/result/enrich_{inputmodule}/{filename} >> {log_file} 2>> {err_file}"
                        cmds_with_logs.append((cmd1, log_file, err_file))
                        cmd2 = f"{sdas_conf['SDAS_software']} geneSetEnrichment prerank -i {inf_path} {paras} -o {outdir}/geneEnrichment/result/enrich_{inputmodule}/{filename} >> {log_file} 2>> {err_file}"
                        cmds_with_logs.append((cmd2, log_file, err_file))
                # 记录需要清理的目录
                temp_dirs_to_clean.append(input_dir)
    # 其它分支，直接对*.csv做enrichr
    else:
        for dif in os.listdir(genelist_dir):
            if dif.endswith(".csv"):
                filename = os.path.basename(dif).replace(".csv", "")
                cmd = f"{sdas_conf['SDAS_software']} geneSetEnrichment enrichr -i {os.path.join(genelist_dir, dif)} {paras} -o {outdir}/geneEnrichment/result/enrich_{inputmodule}/{filename} >> {log_file} 2>> {err_file}"
                cmds_with_logs.append((cmd, log_file, err_file))
    return f"{outdir}/geneEnrichment/result/deg_enrich", cmds_with_logs, temp_dirs_to_clean


def _gsea(inmod, h5adfile, sdas_conf, outdir):
    os.makedirs(f"{outdir}/geneEnrichment/result/gsea", exist_ok=True)
    gsea_plans = sdas_conf["gsea_plan"].split(";")
    log_file = f"{outdir}/geneEnrichment/gsea.{inmod}.log"
    err_file = f"{outdir}/geneEnrichment/gsea.{inmod}.e"
    gsea_all_sh = f"rm {log_file} {err_file}\n"
    for gp in gsea_plans:
        gp_infs = gp.split(",")
        sh_code = f"{sdas_conf['SDAS_software']} geneSetEnrichment gsea -i {h5adfile} --group_key {gp_infs[0]} --ident1 {gp_infs[1]} --ident2 {gp_infs[2]} "
        if len(gp_infs) > 3:
            sh_code += f"--subset_key {gp_infs[3]} --subset_values {gp_infs[4]} "
        for p in sdas_conf.keys():
            if p.startswith("geneSetEnrichment_") or p.startswith("gsea_"):
                if p != "gsea_plan" and p != "geneSetEnrichment_input_process":
                    pras = p.split("_", 1)
                    sh_code += f"--{pras[1]} {sdas_conf[p]} "
        sh_code += f"-o {outdir}/geneEnrichment/result/gsea >> {log_file} 2>>{err_file} "
        gsea_all_sh += f"{sh_code}\n"
    return f"{outdir}/geneEnrichment/result/gsea", [(gsea_all_sh, log_file, err_file)]


def _gsva(inmod, h5adfile, sdas_conf, outdir):
    os.makedirs(f"{outdir}/geneEnrichment/result/gsva", exist_ok=True)
    gsva_plans = sdas_conf["gsva_plan"].split(";")
    log_file = f"{outdir}/geneEnrichment/gsva.{inmod}.log"
    err_file = f"{outdir}/geneEnrichment/gsva.{inmod}.e"
    gsva_all_sh = f"rm {log_file} {err_file}\n"
    for gsp in gsva_plans:
        gsp_infs = gsp.split(",")
        gsp_infs[1] = re.sub(r":", ",", gsp_infs[1])
        sh_code = f"{sdas_conf['SDAS_software']} geneSetEnrichment gsva -i {h5adfile} --group_key {gsp_infs[0]} --idents {gsp_infs[1]} "
        if len(gsp_infs) > 2:
            gsp_infs[3] = re.sub(r":", ",", gsp_infs[3])
            sh_code += f"--subset_key {gsp_infs[2]} --subset_values {gsp_infs[3]} "
        for p in sdas_conf.keys():
            if p.startswith("geneSetEnrichment_") or p.startswith("gsva_"):
                if p != "gsva_plan" and p != "geneSetEnrichment_input_process":
                    pras = p.split("_", 1)
                    sh_code += f"--{pras[1]} {sdas_conf[p]} "
        sh_code += f"-o {outdir}/geneEnrichment/result/gsva >> {log_file} 2>>{err_file} "
        gsva_all_sh += f"{sh_code}\n"
    return f"{outdir}/geneEnrichment/result/gsva", [(gsva_all_sh, log_file, err_file)]


def _ppi(inputmodule, inputdir, sdas_conf, outdir):
    os.makedirs(f"{outdir}/PPI/result", exist_ok=True)
    paras = ""
    for p in sdas_conf.keys():
        if p.startswith("PPI_") and p != "PPI_method" and p != "PPI_input_process":
            pras = p.split("_", 1)
            paras += f"--{pras[1]} {sdas_conf[p]} "
    log_file = f"{outdir}/PPI/PPI.{inputmodule}.log"
    err_file = f"{outdir}/PPI/PPI.{inputmodule}.e"
    cmds_with_logs = []
    # DEG分支
    if inputmodule == "DEG":
        for gf in os.listdir(inputdir):
            if gf.endswith(".sig_filtered.csv"):
                filename = os.path.basename(gf).replace(".csv", "")
                gene_list = os.path.join(outdir, "PPI", "result", filename, f"{filename}.genelist")
                os.makedirs(os.path.join(outdir, "PPI", "result", filename), exist_ok=True)
                # 生成genelist
                with open(os.path.join(inputdir, gf)) as f_in, open(gene_list, "w") as f_out:
                    next(f_in)
                    for line in f_in:
                        f_out.write(line.split(",")[0] + "\n")
                cmd = f"{sdas_conf['SDAS_software']} PPI -i {gene_list} {paras} -o {outdir}/PPI/result/{filename} >> {log_file} 2>>{err_file}"
                cmds_with_logs.append((cmd, log_file, err_file))
    # coexpress分支
    elif inputmodule == "coexpress":
        inputdir = os.path.dirname(inputdir)
        for gf in os.listdir(inputdir):
            if gf.endswith(".module.csv"):
                filename = os.path.basename(gf).replace(".csv", "")
                input_dir = os.path.join(outdir, "PPI", "result", filename, "input")
                os.makedirs(input_dir, exist_ok=True)
                _splitcoexpress(os.path.join(inputdir, gf), input_dir)
                for mf in os.listdir(input_dir):
                    if mf.endswith(".csv"):
                        filenameB = os.path.basename(mf).replace(".csv", "")
                        gene_list = os.path.join(outdir, "PPI", "result", filename, filenameB, f"{filenameB}.genelist")
                        os.makedirs(os.path.join(outdir, "PPI", "result", filename, filenameB), exist_ok=True)
                        # 生成genelist
                        with open(os.path.join(input_dir, mf)) as f_in, open(gene_list, "w") as f_out:
                            next(f_in)
                            for line in f_in:
                                f_out.write(line.split(",")[0] + "\n")
                        cmd = f"{sdas_conf['SDAS_software']} PPI -i {gene_list} {paras} -o {outdir}/PPI/result/{filename}/{filenameB} >> {log_file} 2>>{err_file}"
                        cmds_with_logs.append((cmd, log_file, err_file))
                # 清理input_dir
                for f in os.listdir(input_dir):
                    os.remove(os.path.join(input_dir, f))
                os.rmdir(input_dir)
    # 其它分支，直接对*.csv做PPI
    else:
        for gf in os.listdir(inputdir):
            if gf.endswith(".csv"):
                filename = os.path.basename(gf).replace(".csv", "")
                os.makedirs(os.path.join(outdir, "PPI", "result", filename), exist_ok=True)
                cmd = f"{sdas_conf['SDAS_software']} PPI -i {os.path.join(inputdir, gf)} {paras} -o {outdir}/PPI/result/{filename} >> {log_file} 2>>{err_file}"
                cmds_with_logs.append((cmd, log_file, err_file))
    return f"{outdir}/PPI/result", cmds_with_logs


def _splitcoexpress(coexpressresult, out):
    df = pd.read_csv(coexpressresult)
    infile_name = os.path.basename(coexpressresult)
    infile_name = re.sub(r".csv", "", infile_name)
    for module_name, group in df.groupby("Module"):
        output_df = group[["real_gene_name"]].rename(columns={"real_gene_name": "geneName"})
        output_df["log2FC"] = 1
        output_df.to_csv(f"{out}/{infile_name}.{module_name}.csv", index=False)


def main():
    parser = argparse.ArgumentParser(usage=USAGE)
    parser.add_argument("--split", action="store", type=str, help=argparse.SUPPRESS)
    parser.add_argument("-c", "--conf", action="store", type=str, dest="conf", help="input conf file")
    parser.add_argument(
        "-o", "--outdir", action="store", type=str, default="./", dest="outdir", help="output directory"
    )
    args = parser.parse_args()
    outdir = os.path.abspath(args.outdir)

    # split子命令，直接调用_splitcoexpress
    if args.split:
        _splitcoexpress(args.split, outdir)
        sys.exit(0)

    # 参数校验
    if not args.conf:
        print("conf file not set, please use -c")
        sys.exit(1)
    sdas_conf = _readconf(args.conf)
    if "SDAS_software" not in sdas_conf.keys():
        print("SDAS_software not in conf file, please set")
        sys.exit(1)
    if "h5ad_files" not in sdas_conf.keys():
        print("h5ad_files not in conf file, please set")
        sys.exit(1)
    if "process" not in sdas_conf.keys():
        print("process not in conf file, please set")
        sys.exit(1)

    os.makedirs(outdir, exist_ok=True)
    process = sdas_conf["process"].split(",")
    in_files_num = len(sdas_conf["h5ad_files"].split(";"))
    module_infos = {}

    # 1. h5ad 预处理
    input_file, h5ad_cmds = _h5ad(sdas_conf, outdir)
    module_infos["basic"] = [[input_file], h5ad_cmds]
    print("Running preprocessing...")
    run_batch_parallel(h5ad_cmds)

    # 2. 依次处理各模块，按依赖顺序，每批次 run_batch_parallel
    # 只有单片时才分析共表达，多片的数据跑不了
    if "coexpress" in process and in_files_num == 1:
        module_infos["coexpress"] = [[], []]
        coexp_in_process = sdas_conf["coexpress_input_process"].split(",")
        coexp_cmds = []
        for inmod in coexp_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for coexp_infile in set(module_infos[inmod][0]):
                    coexp_file, coexp_shs = _module(inmod, "coexpress", coexp_infile, sdas_conf, outdir)
                    module_infos["coexpress"][0].append(coexp_file)
                    coexp_cmds += coexp_shs
        if coexp_cmds:
            print("Running coexpress...")
            run_batch_parallel(coexp_cmds)
    # cellAnnotation
    if "cellAnnotation" in process:
        module_infos["cellAnnotation"] = [[], []]
        cann_in_process = sdas_conf["cellAnnotation_input_process"].split(",")
        cann_cmds = []
        for inmod in cann_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for cann_infile in set(module_infos[inmod][0]):
                    cell_anno, anno_shs = _module(inmod, "cellAnnotation", cann_infile, sdas_conf, outdir)
                    module_infos["cellAnnotation"][0].append(cell_anno)
                    cann_cmds += anno_shs
        if cann_cmds:
            print("Running cellAnnotation...")
            run_batch_parallel(cann_cmds)
    # 只有单片时才分析，多片的数据跑不了
    if "spatialDomain" in process and in_files_num == 1:
        module_infos["spatialDomain"] = [[], []]
        spd_in_process = sdas_conf["spatialDomain_input_process"].split(",")
        spd_cmds = []
        for inmod in spd_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for spd_infile in set(module_infos[inmod][0]):
                    st_domain, domain_shs = _module(inmod, "spatialDomain", spd_infile, sdas_conf, outdir)
                    module_infos["spatialDomain"][0].append(st_domain)
                    spd_cmds += domain_shs
        if spd_cmds:
            print("Running spatialDomain...")
            run_batch_parallel(spd_cmds)
    # infercnv
    if "infercnv" in process:
        module_infos["infercnv"] = [[], []]
        cnv_in_process = sdas_conf["infercnv_input_process"].split(",")
        cnv_cmds = []
        for inmod in cnv_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for cnv_infile in set(module_infos[inmod][0]):
                    cnv_result, cnv_shs = _rmodule(inmod, "infercnv", cnv_infile, sdas_conf, outdir)
                    module_infos["infercnv"][0].append(cnv_result)
                    cnv_cmds += cnv_shs
        if cnv_cmds:
            print("Running infercnv...")
            run_batch_parallel(cnv_cmds)
    # trajectory
    if "trajectory" in process:
        module_infos["trajectory"] = [[], []]
        traj_in_process = sdas_conf["trajectory_input_process"].split(",")
        traj_cmds = []
        for inmod in traj_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for traj_infile in set(module_infos[inmod][0]):
                    traj_result, traj_shs = _rmodule(inmod, "trajectory", traj_infile, sdas_conf, outdir)
                    module_infos["trajectory"][0].append(traj_result)
                    traj_cmds += traj_shs
        if traj_cmds:
            print("Running trajectory...")
            run_batch_parallel(traj_cmds)
    # DEG
    if "DEG" in process and "deg_plan" in sdas_conf.keys():
        deg_in_process = sdas_conf["DEG_input_process"].split(",")
        module_infos["DEG"] = [[], []]
        deg_cmds = []
        for inmod in deg_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for deg_infile in set(module_infos[inmod][0]):
                    deg_result_dir, deg_shs = _deg(inmod, deg_infile, sdas_conf, outdir)
                    module_infos["DEG"][0].append(deg_result_dir)
                    deg_cmds += deg_shs
        if deg_cmds:
            print("Running DEG...")
            run_batch_parallel(deg_cmds)
    # geneSetEnrichment
    if "geneSetEnrichment" in process:
        gse_in_process = sdas_conf["geneSetEnrichment_input_process"].split(",")
        # gsea
        if "gsea_plan" in sdas_conf.keys():
            module_infos["gsea"] = [[], []]
            gsea_cmds = []
            for inmod in gse_in_process:
                if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                    for gsea_infile in set(module_infos[inmod][0]):
                        gsea_result, gsea_shs = _gsea(inmod, gsea_infile, sdas_conf, outdir)
                        module_infos["gsea"][0].append(gsea_result)
                        gsea_cmds += gsea_shs
            if gsea_cmds:
                print("Running gsea...")
                run_batch_parallel(gsea_cmds)
        # gsva
        if "gsva_plan" in sdas_conf.keys():
            module_infos["gsva"] = [[], []]
            gsva_cmds = []
            for inmod in gse_in_process:
                if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                    for gsva_infile in set(module_infos[inmod][0]):
                        gsva_result, gsva_shs = _gsva(inmod, gsva_infile, sdas_conf, outdir)
                        module_infos["gsva"][0].append(gsva_result)
                        gsva_cmds += gsva_shs
            if gsva_cmds:
                print("Running gsva...")
                run_batch_parallel(gsva_cmds)
        # genelist_enrich
        if "genelist_enrich_input_process" in sdas_conf.keys():
            enr_in_process = sdas_conf["genelist_enrich_input_process"].split(",")
            for inmod in enr_in_process:
                if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                    for genelist_dir in set(module_infos[inmod][0]):
                        enr_dir, enr_shs, temp_dirs = _Enrich(inmod, genelist_dir, sdas_conf, outdir)
                        if enr_shs:
                            print("Running enrich...")
                            run_batch_parallel(enr_shs)
                            # 清理临时目录
                            for temp_dir in temp_dirs:
                                if os.path.exists(temp_dir):
                                    for f in os.listdir(temp_dir):
                                        os.remove(os.path.join(temp_dir, f))
                                    os.rmdir(temp_dir)
    # cellularNeighborhood
    if "cellularNeighborhood" in process:
        module_infos["cellularNeighborhood"] = [[], []]
        cn_in_process = sdas_conf["cellularNeighborhood_input_process"].split(",")
        cn_cmds = []
        for inmod in cn_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for cn_infile in set(module_infos[inmod][0]):
                    cn_file, cn_shs = _module(inmod, "cellularNeighborhood", cn_infile, sdas_conf, outdir)
                    module_infos["cellularNeighborhood"][0].append(cn_file)
                    cn_cmds += cn_shs
        if cn_cmds:
            print("Running cellularNeighborhood...")
            run_batch_parallel(cn_cmds)
    # CCI
    if "CCI" in process:
        module_infos["CCI"] = [[], []]
        cci_in_process = sdas_conf["CCI_input_process"].split(",")
        cci_cmds = []
        for inmod in cci_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for cci_infile in set(module_infos[inmod][0]):
                    cci_result, cci_shs = _module(inmod, "CCI", cci_infile, sdas_conf, outdir)
                    module_infos["CCI"][0].append(cci_result)
                    cci_cmds += cci_shs
        if cci_cmds:
            print("Running CCI...")
            run_batch_parallel(cci_cmds)
    # spatialRelate
    if "spatialRelate" in process:
        module_infos["spatialRelate"] = [[], []]
        spr_in_process = sdas_conf["spatialRelate_input_process"].split(",")
        spr_cmds = []
        for inmod in spr_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for spr_infile in set(module_infos[inmod][0]):
                    spr_file, spr_shs = _module(inmod, "spatialRelate", spr_infile, sdas_conf, outdir)
                    module_infos["spatialRelate"][0].append(spr_file)
                    spr_cmds += spr_shs
        if spr_cmds:
            print("Running spatialRelate...")
            run_batch_parallel(spr_cmds)
    # TF
    if "TF" in process:
        module_infos["TF"] = [[], []]
        tf_in_process = sdas_conf["TF_input_process"].split(",")
        tf_cmds = []
        for inmod in tf_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for tf_infile in set(module_infos[inmod][0]):
                    tf_file, tf_shs = _module(inmod, "TF", tf_infile, sdas_conf, outdir)
                    module_infos["TF"][0].append(tf_file)
                    tf_cmds += tf_shs
        if tf_cmds:
            print("Running TF...")
            run_batch_parallel(tf_cmds)
    # PPI
    if "PPI" in process:
        module_infos["PPI"] = [[], []]
        ppi_in_process = sdas_conf["PPI_input_process"].split(",")
        ppi_cmds = []
        for inmod in ppi_in_process:
            if inmod in module_infos.keys() and len(module_infos[inmod][0]) > 0:
                for ppi_infile in set(module_infos[inmod][0]):
                    ppi_result, ppi_shs = _ppi(inmod, ppi_infile, sdas_conf, outdir)
                    module_infos["PPI"][0].append(ppi_result)
                    ppi_cmds += ppi_shs
        if ppi_cmds:
            print("Running PPI...")
            run_batch_parallel(ppi_cmds)


if __name__ == "__main__":
    main()
