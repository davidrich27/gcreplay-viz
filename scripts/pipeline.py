#!/usr/bin/env python3

import os,sys
import argparse
import shutil
import glob
import numpy as np
import pandas as pd
import json
import pprint
from pathlib import Path
from Bio.PDB import PDBParser,PDBIO
from Bio.PDB.DSSP import DSSP
from utility import *

# palette for binding
DARK_PALETTE = ["#7570b3", "#808080"]  # original Dark2 pallete
VISIBLE_PALETTE = ["#675ed6", "#808080"]  # more visible pallete
COLOR_PALETTE = VISIBLE_PALETTE
# amino acid codes
AA_ALPHABET = sorted(list("RKHDEQNSTYWFAILMVGPC"))
AA_COUNT = len(AA_ALPHABET)


def pdb_get_chainids(pdb_path):
    chainids = []
    parser = PDBParser(PERMISSIVE=1)
    structure = parser.get_structure(pdb_path, pdb_path)
    pdb_sites = []
    for model in structure:
        for chain in model:
            chainids.append(chain.id)
    return chainids


def pdb_get_df(pdb_path, chainids=None):
    parser = PDBParser(PERMISSIVE=1)
    structure = parser.get_structure(pdb_path, pdb_path)
    pdb_sites = []
    for model in structure:
        for chain in model:
            if (chainids is None) or (chain.id in chainids):
                min_num = None
                for residue in chain:
                    # residue sequence number
                    res_num = int(residue.id[1])
                    if min_num is None:
                        min_num = res_num
                        min_num = int(min_num / 100) * 100
                    # residue insertion code
                    res_ins = (residue.id[2].strip() or "-")
                    # residue amino short code
                    aa_long = residue.resname
                    aa_short = Encoder.long2short(residue.resname)
                    pdb_sites.append((chain.id, res_num, res_ins, aa_long, aa_short))
    df = pd.DataFrame(pdb_sites, columns=['chainid', 'res_num', 'res_ins', 'aa_long', 'aa_short'])
    return df


def pdb_get_flat_df(pdb_path):
    with open('yourfile.pdb', 'r') as f:
        lines = f.readlines()

    atom_lines = [line for line in lines if line.startswith(('ATOM', 'HETATM'))]
    records = []
    for line in atom_lines:
        record = {
            'record_name': line[0:6].strip(),
            'atom_serial': int(line[6:11]),
            'atom_name': line[12:16].strip(),
            'alt_loc': line[16],
            'res_name': line[17:20].strip(),
            'chain_id': line[21],
            'res_seq': int(line[22:26]),
            'i_code': line[26],
            'x': float(line[30:38]),
            'y': float(line[38:46]),
            'z': float(line[46:54]),
            'occupancy': float(line[54:60]),
            'temp_factor': float(line[60:66]),
            'element': line[76:78].strip(),
            'charge': line[78:80].strip()
        }
        records.append(record)

    df = pd.DataFrame(records)
    return df


def metric_get_binding_df(pdb_df, metric_path, chainids=None, metric_names=None):
    raw_metric_df = pd.read_csv(metric_path)
    # raw_metric_df["position_IMGT"] = raw_metric_df["position_IMGT"].astype(int)
    raw_metric_df.loc[raw_metric_df["wildtype"] == raw_metric_df["mutant"], "mutant"] = "-"
    if chainids is not None:
        raw_metric_df = raw_metric_df[raw_metric_df["chain"].isin(chainids)]
    raw_metric_df["site"] = [x for x in range(1,len(set(raw_metric_df['position']))+1) for _ in range(AA_COUNT)]

    metric_df = pd.melt(
        raw_metric_df,
        id_vars=["site", "position", "position_IMGT", "chain", "wildtype", "mutant"],
        # value_vars=["bind_CGG", "expr"],
        value_vars=["single_nt",
                    "bind_CGG", "delta_bind_CGG", "n_bc_bind_CGG", "n_libs_bind_CGG",
                    "expr", "delta_expr", "n_bc_expr", "n_libs_expr"],
        var_name="condition",
        value_name="factor")
    if metric_names:
        metric_df = metric_df[metric_df["condition"].isin(metric_names)]
    return metric_df


def write_sitemap_csv(pdb_df, output_path, site_count=None):
    res_ins = [x if not x.startswith("-") else "" for x in pdb_df["res_ins"]]
    protein_sites = [f"{num}{ins}" for num, ins in zip(pdb_df["res_num"], res_ins)]
    sitemap_df = pd.DataFrame({
        'sequential_site': range(1, len(protein_sites) + 1),
        'reference_site': range(1, len(protein_sites) + 1),
        'protein_site': protein_sites,
    })
    if site_count:
        assert len(sitemap_df) >= site_count
        sitemap_df = sitemap_df[0:site_count].copy()

    if output_path:
        sitemap_df.to_csv(output_path, index=False)
    return sitemap_df


def write_metric_csv(pdb_df, metric_df, output_path, site_count=None):
    if site_count:
        assert len(metric_df) >= site_count
        metric_df = metric_df[metric_df["site"] > site_count]

    if output_path:
        metric_df.to_csv(output_path, index=False)
    return metric_df


def configure_dms_viz(
    name,
    plot_colors,
    metric,
    input_metric_path,
    input_sitemap_path,
    output_path,
    included_chains=[],
    excluded_chains=[],
    add_options="",
    local_pdb_path=None,
):
    program = "configure-dms-viz format"
    plot_colors_str = ",".join(plot_colors)
    base_options = f'--name "{name}" \
                     --title "{name}" \
                     --description "GCReplay: {name}" \
                     --colors "{plot_colors_str}" \
                     --metric "{metric}" '
    if local_pdb_path:
        base_options += f'--structure "{local_pdb_path}" '
    if len(included_chains) != 0:
        base_options += f'--included-chains "{" ".join(included_chains)}" '
    if len(excluded_chains) != 0:
        base_options += f'--excluded-chains "{" ".join(excluded_chains)}" '

    cmd = f'{program} {base_options} \
            --input "{input_metric_path}" \
            --sitemap "{input_sitemap_path}" \
            --output "{output_path}" \
            {add_options} '

    cmd = " ".join(cmd.split())
    output = run_command(cmd)

    if output is None:
        raise Exception("ERROR: configure-dms-viz format run failed.")
    pass


def compare_seqs(aa_seqs):
    for i, seq_i in enumerate(aa_seqs):
        for j, seq_j in enumerate(aa_seqs):
            if i >= j:
                continue
            is_equal = (seq_i == seq_j)
            print(f"seqs {i},{j}: {is_equal}")
            if not is_equal:
                print(seq_i)
                print(seq_j)
                for k in range(len(seq_i)):
                    if seq_i[k] == seq_j[k]:
                        print(seq_i[k], end="")
                    else:
                        print("-", end="")
                print()


### MAIN ###


def parse_args(args):
    arg_parser = argparse.ArgumentParser("gcreplay-viz pipeline")
    arg_parser.add_argument("--input-dir", type=Parser.parse_input_dir(), help="input directory for pdbs")
    arg_parser.add_argument("--output-dir", type=Parser.parse_output_dir(), help="output directory for dms-viz jsons")
    arg_parser.add_argument("--temp-dir", type=Parser.parse_output_dir(), help="temporary directory", default="_temp")
    arg_parser.add_argument("--chain-id", type=Parser.parse_list(str), help="heavy chain ids", default=["H"])
    arg_parser.add_argument("--light-chain-id", type=Parser.parse_list(str), help="light chain ids", default=["L"])
    parser = Parser(arg_parser=arg_parser)
    args = parser.parse_args()
    return args


def main(args=sys.argv):
    args = parse_args(args)
    input_dir = args['input_dir']
    output_dir = args['output_dir']
    temp_dir = args['temp_dir']
    chainids = args["chain_id"]
    light_chainids = args["light_chain_id"]

    summary_data = {
        "dmsviz_filepath": [],
        "pdb_filepath": [],
        "chainid": [],
        "metric_name": [],
        "metric_full_name": [],
    }

    aa_seqs = []
    all_chainids = []
    other_chainids = []

    # load pdb files
    input_pdb_paths = glob.glob(f"{input_dir}/*.pdb")
    print(input_pdb_paths)

    # get all chain ids
    for input_pdb_path in input_pdb_paths:
        all_chainids += pdb_get_chainids(pdb_path=input_pdb_path)
    # other chainids include chainids not in heavy or light chain
    all_chainids = list(set(all_chainids))
    for chainid in all_chainids:
        if chainid not in (chainids + light_chainids):
            other_chainids.append(chainid)
    print(f"all_chainids: {all_chainids}")

    # get all pdbs
    all_pdb_dfs = {}
    for input_pdb_path in input_pdb_paths:
        print(f"input_pdb_path: {input_pdb_path}")
        for chainid in all_chainids:
            pdb_df = pdb_get_df(
                pdb_path=input_pdb_path,
                chainids=chainids)
            all_pdb_dfs[tuple([input_pdb_path, chainid])] = pdb_df

            print(f"pdb_df({input_pdb_path},{chainid}): {len(pdb_df)}")
            aa_seq = ''.join(list(pdb_df['aa_short']))
            print(f"aa_seq: {len(aa_seq)} {aa_seq}")
            aa_seqs.append(aa_seq)

    # get first pdb_df from file
    first_key = next(iter(all_pdb_dfs))
    pdb_df = all_pdb_dfs[first_key]

    # parse metric files
    input_metric_paths = glob.glob(f"{input_dir}/*.csv")
    print(input_metric_paths)
    input_metric_path = input_metric_paths[0]

    # pdb_prefix = os.path.basename(input_pdb_path).split(".")[0]
    pdb_prefix = "CGG_naive_DMS"
    metric_names = {
        "value": ["bind_CGG", "expr"],
        "delta": ["delta_bind_CGG", "delta_expr"],
        "n_bc": ["n_bc_bind_CGG", "n_bc_expr"],
        "n_libs": ["n_libs_bind_CGG", "n_libs_expr"],
        "single_nt": ["single_nt"],
    }
    metric_full_names = {
        "value": "Binding and Expression",
        "delta": "Binding and Expression: Change Relative to Wildtype",
        "n_bc": "Binding and Expression: Number of Barcodes",
        "n_libs": "Binding and Expression: Number of Libraries",
        "single_nt": "Binding and Expression: Mutation by Single Nucleotide Change",
    }

    for metric_name, metric_cols in metric_names.items():
        metric_full_name = metric_full_names[metric_name]
        chain_str = f"{''.join(chainids)}"
        print(f"chain_str: {chain_str}")
        # file paths
        sitemap_path = f"{temp_dir}/{pdb_prefix}.{chain_str}.sitemap.csv"
        metric_path = f"{temp_dir}/{pdb_prefix}.{chain_str}.{metric_name}.csv"
        dmsviz_path = f"{temp_dir}/{pdb_prefix}.{chain_str}.{metric_name}.dmsviz.json"

        # add summary data entry
        summary_data["metric_full_name"].append(metric_full_name)
        summary_data["dmsviz_filepath"].append(os.path.basename(dmsviz_path))
        summary_data["pdb_filepath"].append(os.path.basename(input_pdb_path))
        summary_data["chainid"].append(chain_str)
        summary_data["metric_name"].append(metric_name)

        metric_df = metric_get_binding_df(
            pdb_df=pdb_df,
            metric_path=input_metric_path,
            chainids=chainids,
            metric_names=metric_cols)

        # get aa_seq
        # print(metric_df)
        tmp_metric_df = metric_df.drop_duplicates(subset=["position"])
        aa_seq = ''.join(list(tmp_metric_df['wildtype']))
        print(f"aa_seq: {len(aa_seq)} {aa_seq}")
        aa_seqs.append(aa_seq)

        # number of metrics
        metric_types = set(metric_df["condition"])
        num_metrics = len(metric_types)

        sitemap_df = write_sitemap_csv(
            pdb_df=pdb_df,
            output_path=sitemap_path)
        metric_df = write_metric_csv(
            pdb_df=pdb_df,
            metric_df=metric_df,
            output_path=metric_path)

        add_options = ""
        # add condition
        condition_options = '--condition "condition" '
        condition_options += '--condition-name "Factor" '
        add_options += condition_options

        configure_dms_viz(
            name=f"{pdb_prefix} :: {metric_full_name}",
            plot_colors=COLOR_PALETTE,
            metric="factor",
            input_metric_path=metric_path,
            input_sitemap_path=sitemap_path,
            output_path=dmsviz_path,
            included_chains=chainids,
            excluded_chains=other_chainids,
            add_options=add_options,
            local_pdb_path=input_pdb_path)

    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(f"{temp_dir}/summary.csv", index=False)
    summary_json = summary_df.to_json(orient='records')
    with open(f"{temp_dir}/summary.json", "w") as file:
        # json.dump(summary_json, file)
        file.write(f"{summary_json}\n")
    print(summary_df)

    if args['output_dir'] is not None:
        temp_jsons = glob.glob(f"{temp_dir}/*.dmsviz.json")
        for temp_json in temp_jsons:
            shutil.copy(temp_json, f"{output_dir}/dmsviz-jsons/")
        shutil.copy(f"{temp_dir}/summary.csv", f"{output_dir}/metadata/summary.csv")
        shutil.copy(f"{temp_dir}/summary.json", f"{output_dir}/metadata/summary.json")
    return


if __name__ == "__main__":
    print("[BEGIN] main")
    main()
    print("[END] main")
