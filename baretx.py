from __future__ import print_function

import sys
import io

from decimal import *
from rpc import BitcoinRPC
from multisigtx import make_bare_tx

# set decimal precision for Decimal to 8 positions
getcontext().prec = 8

COIN = Decimal(1e8)
MAXBLOCK = 9900000 # max block height to select utxo from
TARGET_CHANGE = 10000
LARGE_AMOUNT = 500000

ADDR = "9x9zSN9vx3Kf9B4ofwzEfWgiqxwBieCNEb" # address to withdraw from and send change to
REDEEM_SCRIPT = "OP_2 022d64dbbf23829276cbd6bc7f51315e5ad0a488be14cfea1dfe67d79f9bac7a74 0331d348033d3af5256aff968042559757c4aafd04b337ce920431eebde7e5d4c0 03eb960150d1ef3b0e47195cb63a8c6421067cf3c389a1408f1fa1b9d4e6364f01 OP_3 OP_CHECKMULTISIG"

settings = {}

mapAmounts = lambda u : u.amount
sortutxo = lambda u : (int(u.amount * COIN) << 16) + int(u.hash[:4], 16)
total = lambda a,b : a + b

class Utxo:
  def __init__(self, hash, outpoint, script, amount):
    self.hash = hash
    self.outpoint = outpoint
    self.script = script
    self.amount = Decimal(amount)
  def toString(self):
    return "%s:%d:%d" % (self.hash, self.outpoint, self.amount * COIN)

class TransactionCandidate:
  def __init__(self, address, amount):
    self.address = address
    self.amount = Decimal(amount)
    self.utxos = []
  def add(self, utxo):
    self.utxos.append(utxo)
  def inAmount(self):
    if len(self.utxos) < 1:
      return Decimal(0)
    return reduce(total, map(mapAmounts, self.utxos))
  def isComplete(self):
    return self.inAmount() > (self.amount + TARGET_CHANGE)
  def percentageFull(self):
    return self.inAmount() / self.amount
  def createBareTx(self):
    self.bare = make_bare_tx(self, ADDR, REDEEM_SCRIPT)

def parsecsv(s):
  lines = s.split('\n')
  out = []
  for l in lines:
    out.append(l.split(','))
  return out

def payees():
  csv = ''
  with io.open(settings['file'], 'r') as f:
    csv = f.read()

  payees = []
  for line in parsecsv(csv):
    payees.append(TransactionCandidate(line[0], line[1]))
  
  return payees

def getUtxo(rpc, minconf, maxconf):
  outpoints = []
  unspentreply = rpc.execute([rpc.build_request(1, 'listunspent', [minconf, maxconf, [ADDR]])])

  for resp_obj in unspentreply:
    if rpc.response_is_error(resp_obj):
        print('JSON-RPC: error at getblockhash for block ' + start, file=sys.stderr)
        exit(1)
    for utxo in resp_obj['result']:
      outpoints.append(Utxo(utxo['txid'], utxo['vout'], utxo['scriptPubKey'], utxo['amount']))

  return outpoints

def getCurrentHeight(rpc):
  inforeply = rpc.execute([rpc.build_request(0, 'getblockchaininfo', [])])
  currentHeight = 0
  for resp_obj in inforeply:
    if rpc.response_is_error(resp_obj):
        print('JSON-RPC: error at getblockhash for block ' + start, file=sys.stderr)
        exit(1)
    currentHeight = resp_obj['result']['blocks']
  return currentHeight

def distributeDust(utxos, txset, dustlimit):
  while utxos[0].amount < dustlimit:
    for tx in txset:
      tx.add(utxos.pop(0))

def distributeUtxo(utxos, txset, target, popidx):
  while len(txset) > 0:
    txset = filter(target, txset)
    for tx in txset:
      utxo = utxos.pop(popidx)
      tx.add(utxo)

def createCandidates(utxos):

  spreadDust = lambda x: len(x.utxos) < 300
  target60 = lambda x: x.percentageFull() < 0.60
  target80 = lambda x: x.percentageFull() < 0.95
  target100 = lambda x: not x.isComplete()

  #split candidates by payout value
  candidates = payees()
  txCandidatesH = filter(lambda x: x.amount >= LARGE_AMOUNT, candidates)
  txCandidatesL = filter(lambda x: x.amount < LARGE_AMOUNT, candidates)

  distributeUtxo(utxos, candidates, spreadDust, 0) # first include 300 small utxo per tx

  distributeUtxo(utxos, txCandidatesH, target60, -1) # fill high payout amounts until 60%, highest input value first
  distributeUtxo(utxos, txCandidatesL, target60, -1) # fill low payout amounts until 60%, highest input value first
  
  distributeUtxo(utxos, txCandidatesH, target80, -1) # until 80%, highest first
  distributeUtxo(utxos, txCandidatesL, target80, -1) # until 80%, highest first

  distributeUtxo(utxos, candidates, target100, -1) # finalize until target amount + change, lowest first

  return candidates

def run():
  rpc = BitcoinRPC('localhost', 22555, settings["user"], settings["pass"])
  
  maxconf = getCurrentHeight(rpc)
  minconf = maxconf-MAXBLOCK

  utxoset = getUtxo(rpc, minconf, maxconf)
  sortedset = sorted(utxoset, key=sortutxo)
  candidates = createCandidates(sortedset)

  for c in candidates:
    c.createBareTx()

  print("\n".join(map(lambda x: x.bare.as_hex(), candidates)))

if __name__ == '__main__':
  if len(sys.argv) != 4:
    print("Usage: python baretx.py RPC_USER RPC_PASS PAYEEFILE.CSV\n   returns 1 unsigned tx per line")
    exit(1)

  settings["user"] = sys.argv[1]
  settings["pass"] = sys.argv[2]
  settings["file"] = sys.argv[3]
  run()
