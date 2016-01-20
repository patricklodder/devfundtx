# Copyright (c) 2013-2014 The Bitcoin Core developers
#
# Distributed under the MIT software license, see
# http://www.opensource.org/licenses/mit-license.php.
#

from __future__ import print_function
import json
import struct
import re
import base64
import httplib
import sys

class BitcoinRPC:
  def __init__(self, host, port, username, password):
    authpair = "%s:%s" % (username, password)
    self.authhdr = "Basic %s" % (base64.b64encode(authpair))
    self.conn = httplib.HTTPConnection(host, port, False, 30)

  def execute(self, obj):
    self.conn.request('POST', '/', json.dumps(obj),
      { 'Authorization' : self.authhdr,
        'Content-type' : 'application/json' })

    resp = self.conn.getresponse()
    if resp is None:
      print("JSON-RPC: no response", file=sys.stderr)
      return None

    body = resp.read()
    resp_obj = json.loads(body)
    return resp_obj

  @staticmethod
  def build_request(idx, method, params):
    obj = { 'version' : '1.1',
      'method' : method,
      'id' : idx }
    if params is None:
      obj['params'] = []
    else:
      obj['params'] = params
    return obj

  @staticmethod
  def response_is_error(resp_obj):
    return 'error' in resp_obj and resp_obj['error'] is not None
