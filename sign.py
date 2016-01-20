from __future__ import print_function

import sys
import io

from ecdsa import SigningKey, SECP256k1, util
from hashlib import sha256
from pycoin.tx import Tx
from multisigtx import sign_detached, get_key_from_wif, compileASM

REDEEM_SCRIPT = "OP_2 022d64dbbf23829276cbd6bc7f51315e5ad0a488be14cfea1dfe67d79f9bac7a74 0331d348033d3af5256aff968042559757c4aafd04b337ce920431eebde7e5d4c0 03eb960150d1ef3b0e47195cb63a8c6421067cf3c389a1408f1fa1b9d4e6364f01 OP_3 OP_CHECKMULTISIG"


settings = {}

class SignableTx:
  def __init__(self, hex):
    self.tx = Tx.from_hex(hex)
    self.signatures = []

def signables():
  out = []
  s = ""
  with io.open(settings['file'], 'r') as f:
    s = f.read()

  for tx in s.split('\n'):
    if len(tx) > 0:
      out.append(SignableTx(tx))

  return out

def run():
  key = SigningKey.from_string(get_key_from_wif(settings['wif']), SECP256k1, sha256)
  rs = compileASM(REDEEM_SCRIPT)
  txs = signables()
  for tx in txs:
    tx.signatures = sign_detached(tx.tx, key, rs)
    print(",".join(tx.signatures))
  

if __name__ == '__main__':
  if len(sys.argv) != 3:
    print("Usage: python sign.py PRIVKEY_WIF TXFILE.HEX\n   returns ordered signatures for 1 tx per line")
    exit(1)

  settings["wif"] = sys.argv[1]
  settings["file"] = sys.argv[2]
  run()
