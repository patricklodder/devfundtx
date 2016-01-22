from __future__ import print_function

import sys
import io

from rpc import BitcoinRPC

settings = {}

def sendTx(rpc, txhex):
  sendreply = rpc.execute([rpc.build_request(0, 'sendrawtransaction', [txhex])])
  for resp_obj in sendreply:
    if rpc.response_is_error(resp_obj):
        print('JSON-RPC: error at sendrawtransaction' + resp_obj['error']['message'], file=sys.stderr)
        exit(1)

def run():
  rpc = BitcoinRPC('localhost', 22555, settings["user"], settings["pass"])

  with io.open(settings['combined']) as f:
    s = f.read()

  for tx in s.split('\n'):
    if len(tx) > 0:
      sendTx(rpc, tx)

if __name__ == '__main__':
  if len(sys.argv) != 4:
    print("Usage: python send.py USER PASS COMBINED.HEX\n   sends combined tx")
    exit(1)

  settings["user"] = sys.argv[1]
  settings["pass"] = sys.argv[2]
  settings["combined"] = sys.argv[3]
  run()