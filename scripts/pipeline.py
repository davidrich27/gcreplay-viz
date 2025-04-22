import os,sys
import argparse
import subprocess
import pandas as pd
from pathlib import Path
from Bio.PDB import PDBParser,PDBIO
from Bio.PDB.DSSP import DSSP
from utility import *


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


def write_sitemap_csv(output_path):
    pass


def write_metric_csv(output_path):
    pass


def configure_dms_viz(sitemap_path, metric_paths, output_path)


### main ###


def parse_args():
    arg_parser = argparse.ArgumentParser("gcreplay-viz pipeline")
    arg_parser.add_argument("--input", "-i", type=str)
    arg_parser.add_argument("--output", "-o", type=str)
    arg_parser.add_argument("--temp-dir", type=str, default="_temp")
    args = arg_parser.parse_args()
    return args.__dict__


def main():
    args = parse_args()

    chainids = pdb_get_chainids(pdb_path=args["input"])
    print(f"chainids: {chainids}")

    for chainid in chainids:
        pdb_df = pdb_get_df(pdb_path=args["input"], chainids=[chainid])
        print(pdb_df)


if __name__ == "__main__":
    main()
