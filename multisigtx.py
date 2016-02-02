import io
import json
import six
import base58
import math

from decimal import *
from ecdsa import SigningKey, SECP256k1, util
from hashlib import sha256
from binascii import hexlify, unhexlify
from collections import namedtuple

from pycoin.serialize import b2h, h2b, h2b_rev, b2h_rev
from pycoin.tx.script import tools
from pycoin.tx import Tx, Spendable, TxOut

# set decimal precision for Decimal to 8 positions
getcontext().prec = 8

# size estimation constants
TxComponents = namedtuple("TxComponents",
                           ("version", "in_count", "out_count", "locktime", "in_prevout",
                            "in_scriptlen", "in_ops", "in_m", "in_seq", "out_value", "out_scriptlen", "out_scriptsize"))
TX_COMPONENTS = TxComponents(4,3,3,4,36,4,3,73,4,8,1,35)

NETWORK_FEE = 1
COIN = Decimal(1e8)
FEE_MARGIN = Decimal(10) * COIN # pay 10 DOGE extra fee to compensate for float issues and tx size estimation errors

OUTSIZE = TX_COMPONENTS.out_scriptlen + TX_COMPONENTS.out_scriptsize + TX_COMPONENTS.out_scriptlen

def unwif(b58cstr):
    bytes = base58.b58decode_check(b58cstr)
    return (bytes[0], bytes[1:])

# extract hash160 from address
def get_pay_hash(pubkey):
    bytes = unwif(pubkey)[1]
    return hexlify(bytes).decode("utf-8")

def get_key_from_wif(key):
    private_key = unwif(key)[1]
    if (len(private_key) == 33):
        private_key = private_key[:-1]
    return private_key

def is_p2sh(address):
    return unwif(address)[0] in [22]

# unchecked p2sh script
def make_payto_script(address):
    asm = "OP_HASH160 %s OP_EQUAL" % get_pay_hash(address)
    return tools.compile(asm)

# unchecked p2pubkeyhash script
def make_payto_address(address):
    asm = "OP_DUP OP_HASH160 %s OP_EQUALVERIFY OP_CHECKSIG" % get_pay_hash(address)
    return tools.compile(asm)

def make_payto(address):
    if (is_p2sh(address)):
        outscript = make_payto_script(address)
    else:
        outscript = make_payto_address(address)
    return outscript

# extract required keys from RS
def required_keys(redeem_script):
    keyreq = read_int_from_bin(redeem_script[0])
    assert(keyreq & 0x50)
    return keyreq ^ 0x50

def read_int_from_bin(binstr):
    return int(b2h(binstr), base=16) if six.PY2 else int(binstr);

# calc input estimate based on RS
def estimate_input_size(redeem_script):
    size = 0
    num_m = required_keys(redeem_script)
    size += TX_COMPONENTS.in_prevout
    size += TX_COMPONENTS.in_scriptlen
    size += TX_COMPONENTS.in_ops
    size += TX_COMPONENTS.in_m * num_m
    size += TX_COMPONENTS.in_seq
    size += len(redeem_script)
    return size

def make_bare_tx(candidate, change_address, rs_asm, version=1):

    # <Tx> components
    spendables = []
    ins = []
    outs = []

    # estimate the final (signed) bytesize per input based on the redeemscript
    redeem_script = tools.compile(rs_asm)
    in_size = estimate_input_size(redeem_script)

    # initialize size and amount counters
    in_amount = Decimal(0)
    est_size = TX_COMPONENTS.version + TX_COMPONENTS.out_count + TX_COMPONENTS.in_count

    # add output size
    est_size += OUTSIZE * 2


    # iterate over unspents
    for utxo in candidate.utxos:

        value = Decimal(utxo.amount) * COIN
        in_amount += value

        script = h2b(utxo.script)
        # for now: test if the in_script we figured we would need, actually matches the in script :D

        # reverse that tx hash
        prevtx = h2b_rev(utxo.hash)

        # output index
        outnum = utxo.outpoint

        # create "spendable"
        spdbl = Spendable(value, script, prevtx, outnum)
        spendables.append(spdbl)

        # also create this as input
        as_input = spdbl.tx_in()
        as_input.sigs = []
        ins.append(as_input)

        # add the estimated size per input
        est_size += in_size

    # calc fee and out amount
    fee = (Decimal(math.ceil(est_size / 1000)) * COIN * NETWORK_FEE) + FEE_MARGIN
    change_amount = Decimal(math.floor(in_amount - (candidate.amount * COIN) - fee))

    # create outputs
    outs.append(TxOut(int(candidate.amount * COIN), make_payto(candidate.address)))
    outs.append(TxOut(int(change_amount), make_payto_script(change_address)))

    # create bare tx without sigs
    tx = Tx(version, ins, outs, 0, spendables)

    return tx

def sign_tx_with(tx, keys, redeem_script):
    for i in range(0, len(tx.txs_in)):
        data_to_sign = h2b(get_sighash_hex(tx, i, redeem_script))
        #sign with all keys
        for key in keys:

            # sign dat hash with the ecdsa lib
            s = key.sign_digest_deterministic(data_to_sign, sha256, util.sigencode_der_canonize)

            # add sigtype
            sig = b2h(s) + "01"

            tx.txs_in[i].sigs.append(sig)

    return tx

def sign_detached(tx, key, redeem_script):
    sigs = []
    for i in range(0, len(tx.txs_in)):
        data_to_sign = h2b(get_sighash_hex(tx, i, redeem_script))
        s = key.sign_digest_deterministic(data_to_sign, sha256, util.sigencode_der_canonize)
        sig = b2h(s) + "01"
        sigs.append(sig)
    return sigs

def build_tx(tx, redeem_script):
    for i in range(0, len(tx.txs_in)):
        asm = "OP_0 {sigs} {redeem_script}".format(sigs=" ".join(tx.txs_in[i].sigs), redeem_script=b2h(redeem_script))
        solution = tools.compile(asm)
        tx.txs_in[i].script = solution
    return tx

def compileASM(asm):
    return tools.compile(asm)

def get_sighash_hex(tx, i, redeem_script):
    # get sighash
    ddata = tx.signature_hash(redeem_script, i, 0x01)

    # make sure the sighash buffer is the right size
    return "{0:064x}".format(ddata)
