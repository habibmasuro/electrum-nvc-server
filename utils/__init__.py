#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import base64
from functools import partial
from itertools import imap
import random
import string
import threading
import time
import hashlib
import re
import sys
import scrypt

__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)


def rev_hex(s):
    return s.decode('hex')[::-1].encode('hex')


def int_to_hex(i, length=1):
    s = hex(i)[2:].rstrip('L')
    s = "0"*(2*length - len(s)) + s
    return rev_hex(s)


def var_int(i):
    if i < 0xfd:
        return int_to_hex(i)
    elif i <= 0xffff:
        return "fd" + int_to_hex(i, 2)
    elif i <= 0xffffffff:
        return "fe" + int_to_hex(i, 4)
    else:
        return "ff" + int_to_hex(i, 8)


Hash = lambda x: hashlib.sha256(hashlib.sha256(x).digest()).digest()

HashScrypt = lambda x: scrypt.hash(x, x, 1024, 1, 1, 32)

hash_encode = lambda x: x[::-1].encode('hex')


hash_decode = lambda x: x.decode('hex')[::-1]


def header_to_string(res):
    pbh = res.get('prev_block_hash')
    if pbh is None:
        pbh = '0'*64

    return int_to_hex(res.get('version'), 4) \
        + rev_hex(pbh) \
        + rev_hex(res.get('merkle_root')) \
        + int_to_hex(int(res.get('timestamp')), 4) \
        + int_to_hex(int(res.get('bits')), 4) \
        + int_to_hex(int(res.get('nonce')), 4)


def hex_to_int(s):
    return int('0x' + s[::-1].encode('hex'), 16)


def header_from_string(s):
    return {
        'version': hex_to_int(s[0:4]),
        'prev_block_hash': hash_encode(s[4:36]),
        'merkle_root': hash_encode(s[36:68]),
        'timestamp': hex_to_int(s[68:72]),
        'bits': hex_to_int(s[72:76]),
        'nonce': hex_to_int(s[76:80]),
    }


############ functions from pywallet #####################



def hash_160(public_key):
    try:
        md = hashlib.new('ripemd160')
        md.update(hashlib.sha256(public_key).digest())
        return md.digest()
    except:
        import ripemd
        md = ripemd.new(hashlib.sha256(public_key).digest())
        return md.digest()


def public_key_to_bc_address(public_key):
    return hash_160_to_bc_address(hash_160(public_key))


def hash_160_to_bc_address(h160, addrtype = 8):
    if h160 == 'None':
        return 'None'
    vh160 = chr(addrtype) + h160
    h = Hash(vh160)
    addr = vh160 + h[0:4]
    return b58encode(addr)


def bc_address_to_hash_160(addr):
    if addr == 'None':
        return 'None'
    bytes = b58decode(addr, 25)
    return bytes[1:21]


def b58encode(v):
    """encode v, which is a string of bytes, to base58."""

    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += (256**i) * ord(c)

    result = ''
    while long_value >= __b58base:
        div, mod = divmod(long_value, __b58base)
        result = __b58chars[mod] + result
        long_value = div
    result = __b58chars[long_value] + result

    # Bitcoin does a little leading-zero-compression:
    # leading 0-bytes in the input become leading-1s
    nPad = 0
    for c in v:
        if c == '\0':
            nPad += 1
        else:
            break

    return (__b58chars[0]*nPad) + result


def b58decode(v, length):
    """ decode v into a string of len bytes."""
    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += __b58chars.find(c) * (__b58base**i)

    result = ''
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = chr(mod) + result
        long_value = div
    result = chr(long_value) + result

    nPad = 0
    for c in v:
        if c == __b58chars[0]:
            nPad += 1
        else:
            break

    result = chr(0)*nPad + result
    if length is not None and len(result) != length:
        return None

    return result


def EncodeBase58Check(vchIn):
    hash = Hash(vchIn)
    return b58encode(vchIn + hash[0:4])


def DecodeBase58Check(psz):
    vchRet = b58decode(psz, None)
    key = vchRet[0:-4]
    csum = vchRet[-4:]
    hash = Hash(key)
    cs32 = hash[0:4]
    if cs32 != csum:
        return None
    else:
        return key




########### end pywallet functions #######################

def random_string(length):
    with open("/dev/urandom", 'rb') as f:
        return b58encode( f.read(length) )

def timestr():
    return time.strftime("[%d/%m/%Y-%H:%M:%S]")


print_lock = threading.Lock()


def print_log(*args):
    with print_lock:
        sys.stderr.write(timestr() + " " + " ".join(imap(str, args)) + "\n")
        sys.stderr.flush()
