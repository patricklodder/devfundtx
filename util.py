import io
from pycoin.tx import Tx

class SignableTx:
  def __init__(self, hex):
    self.tx = Tx.from_hex(hex)
    self.signatures = []

def parsecsv(s):
  lines = s.split('\n')
  out = []
  for l in lines:
    out.append(l.split(','))
  return out

def parsetxsfile(fn):
  out = []
  s = ""
  with io.open(fn, 'r') as f:
    s = f.read()

  for tx in s.split('\n'):
    if len(tx) > 0:
      out.append(SignableTx(tx))

  return out