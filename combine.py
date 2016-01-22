from __future__ import print_function

import sys
import io

from multisigtx import build_tx, compileASM
from util import *
from pycoin.tx import Tx

settings = {}
files = []

REDEEM_SCRIPT = "OP_2 022d64dbbf23829276cbd6bc7f51315e5ad0a488be14cfea1dfe67d79f9bac7a74 0331d348033d3af5256aff968042559757c4aafd04b337ce920431eebde7e5d4c0 03eb960150d1ef3b0e47195cb63a8c6421067cf3c389a1408f1fa1b9d4e6364f01 OP_3 OP_CHECKMULTISIG"

def readSigs():
  sigs = []

  for i in range(0,2):
    with io.open(files[i], 'r') as f:
      csv = f.read()
      sigs.append(parsecsv(csv))

  return sigs

def run():
  txs = parsetxsfile(settings['txs'])
  sigs = readSigs()

  for i in range(0, len(txs)):
    tx = txs[i].tx
    for j in range(0, len(tx.txs_in)):
      tx.txs_in[j].sigs = [sigs[0][i][j], sigs[1][i][j]]

  rs = compileASM(REDEEM_SCRIPT)

  for tx in txs:
    print(build_tx(tx.tx, rs).as_hex())

  

if __name__ == '__main__':
  if len(sys.argv) != 4:
    print("Usage: python combine.py TXS.HEX SIGS1.CSV SIGS2.CSV\n   returns 1 signed tx per line")
    exit(1)

  settings["txs"] = sys.argv[1]
  files.append(sys.argv[2])
  files.append(sys.argv[3])
  run()