__FILENAME__ = bci
#!/usr/bin/python
import urllib2, json, re, random, sys

# Makes a request to a given URL (first argument) and optional params (second argument)
def make_request(*args):
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0'+str(random.randrange(1000000)))]
    try:
        return opener.open(*args).read().strip()
    except Exception,e:
        try: p = e.read().strip()
        except: p = e
        raise Exception(p)

# Gets the unspent outputs of one or more addresses
def unspent(*args):
    # Valid input formats: history([addr1, addr2,addr3])
    #                      history(addr1, addr2, addr3)
    if len(args) == 0: return []
    elif isinstance(args[0],list): addrs = args[0]
    else: addrs = args
    u = []
    for addr in addrs:
        try: data = make_request('https://blockchain.info/unspent?address='+addr)
        except Exception,e: 
            if str(e) == 'No free outputs to spend': continue
            else: raise Exception(e)
        try:
            jsonobj = json.loads(data)
            #print 'd',data
            for o in jsonobj["unspent_outputs"]:
                h = o['tx_hash'].decode('hex')[::-1].encode('hex')
                u.append({
                    "output": h+':'+str(o['tx_output_n']),
                    "value": o['value'] 
                })
        except:
            raise Exception("Failed to decode data: "+data)
    return u

def blockr_unspent(*args):
    # Valid input formats: history([addr1, addr2,addr3])
    #                      history(addr1, addr2, addr3)
    if len(args) == 0: return []
    elif isinstance(args[0],list): addrs = args[0]
    else: addrs = args
    res = make_request('https://btc.blockr.io/api/v1/address/unspent/'+','.join(addrs))
    data = json.loads(res)['data']
    o = []
    if 'unspent' in data: data = [data]
    for dat in data:
        for u in dat['unspent']:
            o.append({
                "output": u['tx']+':'+str(u['n']),
                "value": int(u['amount'].replace('.',''))
            })
    return o

# Gets the transaction output history of a given set of addresses,
# including whether or not they have been spent
def history(*args):
    # Valid input formats: history([addr1, addr2,addr3])
    #                      history(addr1, addr2, addr3)
    if len(args) == 0: return []
    elif isinstance(args[0],list): addrs = args[0]
    else: addrs = args

    txs = []
    for addr in addrs:
        offset = 0
        while 1:
            data = make_request('https://blockchain.info/address/%s?format=json&offset=%s' % (addr,offset))
            try:
                jsonobj = json.loads(data)
            except:
                raise Exception("Failed to decode data: "+data)
            txs.extend(jsonobj["txs"])
            if len(jsonobj["txs"]) < 50: break
            offset += 50
            sys.stderr.write("Fetching more transactions... "+str(offset)+'\n')
    outs = {}
    for tx in txs:
        for o in tx["out"]:
            if o['addr'] in addrs:
                key = str(tx["tx_index"])+':'+str(o["n"])
                outs[key] = { 
                    "address" : o["addr"],
                    "value" : o["value"],
                    "output" : tx["hash"]+':'+str(o["n"]),
                    "block_height" : tx.get("block_height",None)
                }
    for tx in txs:
        for i, inp in enumerate(tx["inputs"]):
            if inp["prev_out"]["addr"] in addrs:
                key = str(inp["prev_out"]["tx_index"])+':'+str(inp["prev_out"]["n"])
                if outs.get(key): outs[key]["spend"] = tx["hash"]+':'+str(i)
    return [outs[k] for k in outs]

# Pushes a transaction to the network using https://blockchain.info/pushtx
def pushtx(tx):
    if not re.match('^[0-9a-fA-F]*$',tx): tx = tx.encode('hex')
    return make_request('https://blockchain.info/pushtx','tx='+tx)

def eligius_pushtx(tx):
    if not re.match('^[0-9a-fA-F]*$',tx): tx = tx.encode('hex')
    s = make_request('http://eligius.st/~wizkid057/newstats/pushtxn.php','transaction='+tx+'&send=Push')
    strings = re.findall('string[^"]*"[^"]*"',s)
    for string in strings:
        quote = re.findall('"[^"]*"',string)[0]
        if len(quote) >= 5: return quote[1:-1]

def blockr_pushtx(tx):
    if not re.match('^[0-9a-fA-F]*$', tx): tx = tx.encode('hex')
    return make_request('http://btc.blockr.io/api/v1/tx/push', '{"hex":"%s"}' % tx)

def last_block_height():
    data = make_request('https://blockchain.info/latestblock')
    jsonobj = json.loads(data)
    return jsonobj["height"]

# Gets a specific transaction
def bci_fetchtx(txhash):
    if not re.match('^[0-9a-fA-F]*$',txhash): txhash = txhash.encode('hex')
    data = make_request('https://blockchain.info/rawtx/'+txhash+'?format=hex')
    return data

def blockr_fetchtx(txhash):
    if not re.match('^[0-9a-fA-F]*$',txhash): txhash = txhash.encode('hex')
    jsondata = json.loads(make_request('https://btc.blockr.io/api/v1/tx/raw/'+txhash))
    return jsondata['data']['tx']['hex']

def fetchtx(txhash):
    try: return bci_fetchtx(txhash)
    except: return blockr_fetchtx(txhash)

def firstbits(address):
    if len(address) >= 25:
        return make_request('https://blockchain.info/q/getfirstbits/'+address)
    else:
        return make_request('https://blockchain.info/q/resolvefirstbits/'+address)

########NEW FILE########
__FILENAME__ = composite
# Takes privkey, address, value (satoshis), fee (satoshis)
def send(frm,to,value,fee=1000):
    u = unspent(privtoaddr(frm))
    u2 = select(u,value+fee)
    tx = mksend(to+':'+str(value),privtoaddr(to),fee)
    tx2 = signall(tx,privtoaddr(to))
    pushtx(tx)

########NEW FILE########
__FILENAME__ = deterministic
from main import *
import hmac, hashlib

### Electrum wallets

def electrum_stretch(seed): return slowsha(seed)

# Accepts seed or stretched seed, returns master public key
def electrum_mpk(seed):
    if len(seed) == 32: seed = electrum_stretch(seed)
    return privkey_to_pubkey(seed)[2:]

# Accepts (seed or stretched seed), index and secondary index
# (conventionally 0 for ordinary addresses, 1 for change) , returns privkey
def electrum_privkey(seed,n,for_change=0):
    if len(seed) == 32: seed = electrum_stretch(seed)
    mpk = electrum_mpk(seed)
    offset = dbl_sha256(str(n)+':'+str(for_change)+':'+mpk.decode('hex'))
    return add_privkeys(seed, offset)

# Accepts (seed or stretched seed or master public key), index and secondary index
# (conventionally 0 for ordinary addresses, 1 for change) , returns pubkey
def electrum_pubkey(masterkey,n,for_change=0):
    if len(masterkey) == 32: mpk = electrum_mpk(electrum_stretch(masterkey))
    elif len(masterkey) == 64: mpk = electrum_mpk(masterkey)
    else: mpk = masterkey
    bin_mpk = encode_pubkey(mpk,'bin_electrum')
    offset = bin_dbl_sha256(str(n)+':'+str(for_change)+':'+bin_mpk)
    return add_pubkeys('04'+mpk,privtopub(offset))

# seed/stretched seed/pubkey -> address (convenience method)
def electrum_address(masterkey,n,for_change=0,version=0):
    return pubkey_to_address(electrum_pubkey(masterkey,n,for_change),version)

# Given a master public key, a private key from that wallet and its index,
# cracks the secret exponent which can be used to generate all other private
# keys in the wallet
def crack_electrum_wallet(mpk,pk,n,for_change=0):
    bin_mpk = encode_pubkey(mpk,'bin_electrum')
    offset = dbl_sha256(str(n)+':'+str(for_change)+':'+bin_mpk)
    return subtract_privkeys(pk, offset)

# Below code ASSUMES binary inputs and compressed pubkeys
PRIVATE = '\x04\x88\xAD\xE4'
PUBLIC = '\x04\x88\xB2\x1E'

# BIP32 child key derivation
def raw_bip32_ckd(rawtuple, i):
    vbytes, depth, fingerprint, oldi, chaincode, key = rawtuple
    i = int(i)

    if vbytes == PRIVATE:
        priv = key
        pub = privtopub(key)
    else:
        pub = key

    if i >= 2**31:
        if vbytes == PUBLIC:
            raise Exception("Can't do private derivation on public key!")
        I = hmac.new(chaincode,'\x00'+priv[:32]+encode(i,256,4),hashlib.sha512).digest()
    else:
        I = hmac.new(chaincode,pub+encode(i,256,4),hashlib.sha512).digest()

    if vbytes == PRIVATE:
        newkey = add_privkeys(I[:32]+'\x01',priv)
        fingerprint = bin_hash160(privtopub(key))[:4]
    if vbytes == PUBLIC:
        newkey = add_pubkeys(compress(privtopub(I[:32])),key)
        fingerprint = bin_hash160(key)[:4]

    return (vbytes, depth + 1, fingerprint, i, I[32:], newkey)

def bip32_serialize(rawtuple):
    vbytes, depth, fingerprint, i, chaincode, key = rawtuple
    depth = chr(depth % 256)
    i = encode(i,256,4)
    chaincode = encode(hash_to_int(chaincode),256,32)
    keydata = '\x00'+key[:-1] if vbytes == PRIVATE else key
    bindata = vbytes + depth + fingerprint + i + chaincode + keydata
    return changebase(bindata+bin_dbl_sha256(bindata)[:4],256,58)

def bip32_deserialize(data):
    dbin = changebase(data,58,256)
    if bin_dbl_sha256(dbin[:-4])[:4] != dbin[-4:]:
        raise Exception("Invalid checksum")
    vbytes = dbin[0:4]
    depth = ord(dbin[4])
    fingerprint = dbin[5:9]
    i = decode(dbin[9:13],256)
    chaincode = dbin[13:45]
    key = dbin[46:78]+'\x01' if vbytes == PRIVATE else dbin[45:78]
    return (vbytes, depth, fingerprint, i, chaincode, key)

def raw_bip32_privtopub(rawtuple):
    vbytes, depth, fingerprint, i, chaincode, key = rawtuple
    return (PUBLIC, depth, fingerprint, i, chaincode, privtopub(key))

def bip32_privtopub(data):
    return bip32_serialize(raw_bip32_privtopub(bip32_deserialize(data)))

def bip32_ckd(data,i):
    return bip32_serialize(raw_bip32_ckd(bip32_deserialize(data),i))

def bip32_master_key(seed):
    I = hmac.new("Bitcoin seed",seed,hashlib.sha512).digest()
    return bip32_serialize((PRIVATE, 0, '\x00'*4, 0, I[32:], I[:32]+'\x01'))

def bip32_bin_extract_key(data):
    return bip32_deserialize(data)[-1]

def bip32_extract_key(data):
    return bip32_deserialize(data)[-1].encode('hex')

# Exploits the same vulnerability as above in Electrum wallets
# Takes a BIP32 pubkey and one of the child privkeys of its corresponding privkey
# and returns the BIP32 privkey associated with that pubkey
def raw_crack_bip32_privkey(parent_pub,priv):
    vbytes, depth, fingerprint, i, chaincode, key = priv
    pvbytes, pdepth, pfingerprint, pi, pchaincode, pkey = parent_pub
    i = int(i)

    if i >= 2**31: raise Exception("Can't crack private derivation!")

    I = hmac.new(pchaincode,pkey+encode(i,256,4),hashlib.sha512).digest()

    pprivkey = subtract_privkeys(key,I[:32]+'\x01')

    return (PRIVATE, pdepth, pfingerprint, pi, pchaincode, pprivkey)

def crack_bip32_privkey(parent_pub,priv):
    dsppub = bip32_deserialize(parent_pub)
    dspriv = bip32_deserialize(priv)
    return bip32_serialize(raw_crack_bip32_privkey(dsppub,dspriv))

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/python
import hashlib, re, sys, os, base64, time, random, hmac
import ripemd

### Elliptic curve parameters (secp256k1)

P = 2**256-2**32-2**9-2**8-2**7-2**6-2**4-1
N = 115792089237316195423570985008687907852837564279074904382605163141518161494337
A = 0
B = 7
Gx = 55066263022277343669578718895168534326250603453777594175500187360389116729240
Gy = 32670510020758816978083085130507043184471273380659243275938904335757337482424
G = (Gx,Gy)


def change_curve(p, n, a, b, gx, gy):
    global P, N, A, B, Gx, Gy, G
    P, N, A, B, Gx, Gy = p, n, a, b, gx, gy
    G = (Gx, Gy)

def getG():
    return G

### Extended Euclidean Algorithm

def inv(a,n):
    lm, hm = 1,0
    low, high = a%n,n
    while low > 1:
        r = high/low
        nm, new = hm-lm*r, high-low*r
        lm, low, hm, high = nm, new, lm, low
    return lm % n

### Base switching

def get_code_string(base):
    if base == 2: return '01'
    elif base == 10: return '0123456789'
    elif base == 16: return '0123456789abcdef'
    elif base == 32: return 'abcdefghijklmnopqrstuvwxyz234567'
    elif base == 58: return '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    elif base == 256: return ''.join([chr(x) for x in range(256)])
    else: raise ValueError("Invalid base!")

def lpad(msg,symbol,length):
    if len(msg) >= length: return msg
    return symbol * (length - len(msg)) + msg

def encode(val,base,minlen=0):
    base, minlen = int(base), int(minlen)
    code_string = get_code_string(base)
    result = ""   
    while val > 0:
        result = code_string[val % base] + result
        val /= base
    return lpad(result,code_string[0],minlen)

def decode(string,base):
    base = int(base)
    code_string = get_code_string(base)
    result = 0
    if base == 16: string = string.lower()
    while len(string) > 0:
        result *= base
        result += code_string.find(string[0])
        string = string[1:]
    return result

def changebase(string,frm,to,minlen=0):
    if frm == to: return lpad(string,minlen)
    return encode(decode(string,frm),to,minlen)

### JSON access (for pybtctool convenience)

def access(obj,prop):
    if isinstance(obj,dict):
        if prop in obj: return obj[prop]
        elif '.' in prop: return obj[float(prop)]
        else: return obj[int(prop)]
    else:
        return obj[int(prop)]

def multiaccess(obj,prop):
    return [access(o,prop) for o in obj]

def slice(obj,start=0,end=2**200):
    return obj[int(start):int(end)]

def count(obj):
    return len(obj)

_sum = sum
def sum(obj):
    return _sum(obj)
    
### Elliptic Curve functions

def isinf(p): return p[0] == 0 and p[1] == 0

def base10_add(a,b):
  if isinf(a): return b[0],b[1]
  if isinf(b): return a[0],a[1]
  if a[0] == b[0]: 
    if a[1] == b[1]: return base10_double((a[0],a[1]))
    else: return (0,0)
  m = ((b[1]-a[1]) * inv(b[0]-a[0],P)) % P
  x = (m*m-a[0]-b[0]) % P
  y = (m*(a[0]-x)-a[1]) % P
  return (x,y)
  
def base10_double(a):
  if isinf(a): return (0,0)
  m = ((3*a[0]*a[0]+A)*inv(2*a[1],P)) % P
  x = (m*m-2*a[0]) % P
  y = (m*(a[0]-x)-a[1]) % P
  return (x,y)

def base10_multiply(a,n):
  if isinf(a) or n == 0: return (0,0)
  if n == 1: return a
  if n < 0 or n >= N: return base10_multiply(a,n%N)
  if (n%2) == 0: return base10_double(base10_multiply(a,n/2))
  if (n%2) == 1: return base10_add(base10_double(base10_multiply(a,n/2)),a)

# Functions for handling pubkey and privkey formats

def get_pubkey_format(pub):
    if isinstance(pub,(tuple,list)): return 'decimal'
    elif len(pub) == 65 and pub[0] == '\x04': return 'bin'
    elif len(pub) == 130 and pub[0:2] == '04': return 'hex'
    elif len(pub) == 33 and pub[0] in ['\x02','\x03']: return 'bin_compressed'
    elif len(pub) == 66 and pub[0:2] in ['02','03']: return 'hex_compressed'
    elif len(pub) == 64: return 'bin_electrum'
    elif len(pub) == 128: return 'hex_electrum'
    else: raise Exception("Pubkey not in recognized format")

def encode_pubkey(pub,formt):
    if not isinstance(pub,(tuple,list)):
        pub = decode_pubkey(pub)
    if formt == 'decimal': return pub
    elif formt == 'bin': return '\x04' + encode(pub[0],256,32) + encode(pub[1],256,32)
    elif formt == 'bin_compressed': return chr(2+(pub[1]%2)) + encode(pub[0],256,32)
    elif formt == 'hex': return '04' + encode(pub[0],16,64) + encode(pub[1],16,64)
    elif formt == 'hex_compressed': return '0'+str(2+(pub[1]%2)) + encode(pub[0],16,64)
    elif formt == 'bin_electrum': return encode(pub[0],256,32) + encode(pub[1],256,32)
    elif formt == 'hex_electrum': return encode(pub[0],16,64) + encode(pub[1],16,64)
    else: raise Exception("Invalid format!")

def decode_pubkey(pub,formt=None):
    if not formt: formt = get_pubkey_format(pub)
    if formt == 'decimal': return pub
    elif formt == 'bin': return (decode(pub[1:33],256),decode(pub[33:65],256))
    elif formt == 'bin_compressed':
        x = decode(pub[1:33],256)
        beta = pow(x*x*x+A*x+B,(P+1)/4,P)
        y = (P-beta) if ((beta + ord(pub[0])) % 2) else beta
        return (x,y)
    elif formt == 'hex': return (decode(pub[2:66],16),decode(pub[66:130],16))
    elif formt == 'hex_compressed':
        return decode_pubkey(pub.decode('hex'),'bin_compressed')
    elif formt == 'bin_electrum':
        return (decode(pub[:32],256),decode(pub[32:64],256))
    elif formt == 'hex_electrum':
        return (decode(pub[:64],16),decode(pub[64:128],16))
    else: raise Exception("Invalid format!")

def get_privkey_format(priv):
    if isinstance(priv,(int,long)): return 'decimal'
    elif len(priv) == 32: return 'bin'
    elif len(priv) == 33: return 'bin_compressed'
    elif len(priv) == 64: return 'hex'
    elif len(priv) == 66: return 'hex_compressed'
    else:
        bin_p = b58check_to_bin(priv)
        if len(bin_p) == 32: return 'wif'
        elif len(bin_p) == 33: return 'wif_compressed'
        else: raise Exception("WIF does not represent privkey")

def encode_privkey(priv,formt,vbyte=0):
    if not isinstance(priv,(int,long)):
        return encode_privkey(decode_privkey(priv),formt,vbyte)
    if formt == 'decimal': return priv
    elif formt == 'bin': return encode(priv,256,32)
    elif formt == 'bin_compressed': return encode(priv,256,32)+'\x01'
    elif formt == 'hex': return encode(priv,16,64)
    elif formt == 'hex_compressed': return encode(priv,16,64)+'01'
    elif formt == 'wif':
        return bin_to_b58check(encode(priv,256,32),128+int(vbyte))
    elif formt == 'wif_compressed':
        return bin_to_b58check(encode(priv,256,32)+'\x01',128+int(vbyte))
    else: raise Exception("Invalid format!")

def decode_privkey(priv,formt=None):
    if not formt: formt = get_privkey_format(priv)
    if formt == 'decimal': return priv
    elif formt == 'bin': return decode(priv,256)
    elif formt == 'bin_compressed': return decode(priv[:32],256)
    elif formt == 'hex': return decode(priv,16)
    elif formt == 'hex_compressed': return decode(priv[:64],16)
    else:
        bin_p = b58check_to_bin(priv)
        if len(bin_p) == 32: return decode(bin_p,256)
        elif len(bin_p) == 33: return decode(bin_p[:32],256)
        else: raise Exception("WIF does not represent privkey")

def add_pubkeys(p1,p2):
  f1,f2 = get_pubkey_format(p1), get_pubkey_format(p2)
  return encode_pubkey(base10_add(decode_pubkey(p1,f1),decode_pubkey(p2,f2)),f1)

def add_privkeys(p1,p2):
  f1,f2 = get_privkey_format(p1), get_privkey_format(p2)
  return encode_privkey((decode_privkey(p1,f1) + decode_privkey(p2,f2)) % N,f1)

def multiply(pubkey,privkey):
  f1,f2 = get_pubkey_format(pubkey), get_privkey_format(privkey)
  pubkey, privkey = decode_pubkey(pubkey,f1), decode_privkey(privkey,f2)
  # http://safecurves.cr.yp.to/twist.html
  if not isinf(pubkey) and (pubkey[0]**3+B-pubkey[1]*pubkey[1]) % P != 0: 
      raise Exception("Point not on curve")
  return encode_pubkey(base10_multiply(pubkey,privkey),f1)

def divide(pubkey,privkey):
    factor = inv(decode_privkey(privkey),N)
    return multiply(pubkey,factor)

def compress(pubkey):
    f = get_pubkey_format(pubkey)
    if 'compressed' in f: return pubkey
    elif f == 'bin': return encode_pubkey(decode_pubkey(pubkey,f),'bin_compressed')
    elif f == 'hex' or f == 'decimal':
        return encode_pubkey(decode_pubkey(pubkey,f),'hex_compressed')

def decompress(pubkey):
    f = get_pubkey_format(pubkey)
    if 'compressed' not in f: return pubkey
    elif f == 'bin_compressed': return encode_pubkey(decode_pubkey(pubkey,f),'bin')
    elif f == 'hex_compressed' or f == 'decimal':
        return encode_pubkey(decode_pubkey(pubkey,f),'hex')

def privkey_to_pubkey(privkey):
    f = get_privkey_format(privkey)
    privkey = decode_privkey(privkey,f)
    if privkey == 0 or privkey >= N:
        raise Exception("Invalid privkey")
    if f in ['bin','bin_compressed','hex','hex_compressed','decimal']:
        return encode_pubkey(base10_multiply(G,privkey),f)
    else:
        return encode_pubkey(base10_multiply(G,privkey),f.replace('wif','hex'))

privtopub = privkey_to_pubkey

def privkey_to_address(priv,magicbyte=0):
    return pubkey_to_address(privkey_to_pubkey(priv),magicbyte)
privtoaddr = privkey_to_address

def neg_pubkey(pubkey): 
    f = get_pubkey_format(pubkey)
    pubkey = decode_pubkey(pubkey,f)
    return encode_pubkey((pubkey[0],(P-pubkey[1]) % P),f)

def neg_privkey(privkey):
    f = get_privkey_format(privkey)
    privkey = decode_privkey(privkey,f)
    return encode_privkey((N - privkey) % N,f)

def subtract_pubkeys(p1, p2):
  f1,f2 = get_pubkey_format(p1), get_pubkey_format(p2)
  k2 = decode_pubkey(p2,f2)
  return encode_pubkey(base10_add(decode_pubkey(p1,f1),(k2[0],(P - k2[1]) % P)),f1)

def subtract_privkeys(p1, p2):
  f1,f2 = get_privkey_format(p1), get_privkey_format(p2)
  k2 = decode_privkey(p2,f2)
  return encode_privkey((decode_privkey(p1,f1) - k2) % N,f1)

### Hashes

def bin_hash160(string):
   intermed = hashlib.sha256(string).digest()
   digest = ''
   try:
       digest = hashlib.new('ripemd160',intermed).digest()
   except:
       digest = ripemd.RIPEMD160(intermed).digest()
   return digest
def hash160(string):
    return bin_hash160(string).encode('hex')

def bin_sha256(string):
    return hashlib.sha256(string).digest()
def sha256(string):
    return bin_sha256(string).encode('hex')

def bin_dbl_sha256(string):
   return hashlib.sha256(hashlib.sha256(string).digest()).digest()
def dbl_sha256(string):
   return bin_dbl_sha256(string).encode('hex')

def bin_slowsha(string):
    orig_input = string
    for i in range(100000):
        string = hashlib.sha256(string + orig_input).digest()
    return string
def slowsha(string):
    return bin_slowsha(string).encode('hex')

def hash_to_int(x):
    if len(x) in [40,64]: return decode(x,16)
    else: return decode(x,256)

def num_to_var_int(x):
    x = int(x)
    if x < 253: return chr(x)
    elif x < 65536: return chr(253) + encode(x,256,2)[::-1]
    elif x < 4294967296: return chr(254) + encode(x,256,4)[::-1]
    else: return chr(255) + encode(x,256,8)[::-1]

# WTF, Electrum?
def electrum_sig_hash(message):
    padded = "\x18Bitcoin Signed Message:\n" + num_to_var_int( len(message) ) + message
    return bin_dbl_sha256(padded)

def random_key():
    # Gotta be secure after that java.SecureRandom fiasco...
    entropy = os.urandom(32)+str(random.randrange(2**256))+str(int(time.time())**7)
    return sha256(entropy)

def random_electrum_seed():
    entropy = os.urandom(32)+str(random.randrange(2**256))+str(int(time.time())**7)
    return sha256(entropy)[:32]

### Encodings

def bin_to_b58check(inp,magicbyte=0):
    inp_fmtd = chr(int(magicbyte)) + inp
    leadingzbytes = len(re.match('^\x00*',inp_fmtd).group(0))
    checksum = bin_dbl_sha256(inp_fmtd)[:4]
    return '1' * leadingzbytes + changebase(inp_fmtd+checksum,256,58)

def b58check_to_bin(inp):
    leadingzbytes = len(re.match('^1*',inp).group(0))
    data = '\x00' * leadingzbytes + changebase(inp,58,256)
    assert bin_dbl_sha256(data[:-4])[:4] == data[-4:]
    return data[1:-4]

def get_version_byte(inp):
    leadingzbytes = len(re.match('^1*',inp).group(0))
    data = '\x00' * leadingzbytes + changebase(inp,58,256)
    assert bin_dbl_sha256(data[:-4])[:4] == data[-4:]
    return ord(data[0])

def hex_to_b58check(inp,magicbyte=0):
    return bin_to_b58check(inp.decode('hex'),magicbyte)

def b58check_to_hex(inp): return b58check_to_bin(inp).encode('hex')

def pubkey_to_address(pubkey,magicbyte=0):
   if isinstance(pubkey,(list,tuple)):
       pubkey = encode_pubkey(pubkey,'bin')
   if len(pubkey) in [66,130]:
       return bin_to_b58check(bin_hash160(pubkey.decode('hex')),magicbyte)
   return bin_to_b58check(bin_hash160(pubkey),magicbyte)

pubtoaddr = pubkey_to_address

### EDCSA

def encode_sig(v,r,s):
    vb, rb, sb = chr(v), encode(r,256), encode(s,256)
    return base64.b64encode(vb+'\x00'*(32-len(rb))+rb+'\x00'*(32-len(sb))+sb)

def decode_sig(sig):
    bytez = base64.b64decode(sig)
    return ord(bytez[0]), decode(bytez[1:33],256), decode(bytez[33:],256)

# https://tools.ietf.org/html/rfc6979#section-3.2
def deterministic_generate_k(msghash,priv):
    v = '\x01' * 32
    k = '\x00' * 32
    priv = encode_privkey(priv,'bin')
    msghash = encode(hash_to_int(msghash),256,32)
    k = hmac.new(k, v+'\x00'+priv+msghash, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    k = hmac.new(k, v+'\x01'+priv+msghash, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    return decode(hmac.new(k, v, hashlib.sha256).digest(),256)

def ecdsa_raw_sign(msghash,priv):

    z = hash_to_int(msghash)
    k = deterministic_generate_k(msghash,priv)

    r,y = base10_multiply(G,k)
    s = inv(k,N) * (z + r*decode_privkey(priv)) % N

    return 27+(y%2),r,s

def ecdsa_sign(msg,priv):
    return encode_sig(*ecdsa_raw_sign(electrum_sig_hash(msg),priv))

def ecdsa_raw_verify(msghash,vrs,pub):
    v,r,s = vrs

    w = inv(s,N)
    z = hash_to_int(msghash)
    
    u1, u2 = z*w % N, r*w % N
    x,y = base10_add(base10_multiply(G,u1), base10_multiply(decode_pubkey(pub),u2))

    return r == x

def ecdsa_verify(msg,sig,pub):
    return ecdsa_raw_verify(electrum_sig_hash(msg),decode_sig(sig),pub)

def ecdsa_raw_recover(msghash,vrs):
    v,r,s = vrs

    x = r
    beta = pow(x*x*x+A*x+B,(P+1)/4,P)
    y = beta if v%2 ^ beta%2 else (P - beta)
    z = hash_to_int(msghash)

    Qr = base10_add(neg_pubkey(base10_multiply(G,z)),base10_multiply((x,y),s))
    Q = base10_multiply(Qr,inv(r,N))

    if ecdsa_raw_verify(msghash,vrs,Q): return Q
    return False

def ecdsa_recover(msg,sig):
    return encode_pubkey(ecdsa_raw_recover(electrum_sig_hash(msg),decode_sig(sig)),'hex')

########NEW FILE########
__FILENAME__ = ripemd
## ripemd.py - pure Python implementation of the RIPEMD-160 algorithm.
## Bjorn Edstrom <be@bjrn.se> 16 december 2007.
##
## Copyrights
## ==========
##
## This code is a derived from an implementation by Markus Friedl which is
## subject to the following license. This Python implementation is not
## subject to any other license.
##
##/*
## * Copyright (c) 2001 Markus Friedl.  All rights reserved.
## *
## * Redistribution and use in source and binary forms, with or without
## * modification, are permitted provided that the following conditions
## * are met:
## * 1. Redistributions of source code must retain the above copyright
## *    notice, this list of conditions and the following disclaimer.
## * 2. Redistributions in binary form must reproduce the above copyright
## *    notice, this list of conditions and the following disclaimer in the
## *    documentation and/or other materials provided with the distribution.
## *
## * THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
## * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
## * OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
## * IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
## * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
## * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
## * THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
## */
##/*
## * Preneel, Bosselaers, Dobbertin, "The Cryptographic Hash Function RIPEMD-160",
## * RSA Laboratories, CryptoBytes, Volume 3, Number 2, Autumn 1997,
## * ftp://ftp.rsasecurity.com/pub/cryptobytes/crypto3n2.pdf
## */

try:
    import psyco
    psyco.full()
except ImportError:
    pass

#block_size = 1
digest_size = 20
digestsize = 20

class RIPEMD160:
    """Return a new RIPEMD160 object. An optional string argument
    may be provided; if present, this string will be automatically
    hashed."""
    
    def __init__(self, arg=None):
        self.ctx = RMDContext()
        if arg:
            self.update(arg)
        self.dig = None
        
    def update(self, arg):
        """update(arg)"""        
        RMD160Update(self.ctx, arg, len(arg))
        self.dig = None
        
    def digest(self):
        """digest()"""        
        if self.dig:
            return self.dig
        ctx = self.ctx.copy()
        self.dig = RMD160Final(self.ctx)
        self.ctx = ctx
        return self.dig
    
    def hexdigest(self):
        """hexdigest()"""
        dig = self.digest()
        hex_digest = ''
        for d in dig:
            hex_digest += '%02x' % ord(d)
        return hex_digest
    
    def copy(self):
        """copy()"""        
        import copy
        return copy.deepcopy(self)



def new(arg=None):
    """Return a new RIPEMD160 object. An optional string argument
    may be provided; if present, this string will be automatically
    hashed."""    
    return RIPEMD160(arg)



#
# Private.
#

class RMDContext:
    def __init__(self):
        self.state = [0x67452301, 0xEFCDAB89, 0x98BADCFE,
                      0x10325476, 0xC3D2E1F0] # uint32
        self.count = 0 # uint64
        self.buffer = [0]*64 # uchar
    def copy(self):
        ctx = RMDContext()
        ctx.state = self.state[:]
        ctx.count = self.count
        ctx.buffer = self.buffer[:]
        return ctx

K0 = 0x00000000
K1 = 0x5A827999
K2 = 0x6ED9EBA1
K3 = 0x8F1BBCDC
K4 = 0xA953FD4E

KK0 = 0x50A28BE6
KK1 = 0x5C4DD124
KK2 = 0x6D703EF3
KK3 = 0x7A6D76E9
KK4 = 0x00000000

def ROL(n, x):
    return ((x << n) & 0xffffffff) | (x >> (32 - n))

def F0(x, y, z):
    return x ^ y ^ z

def F1(x, y, z):
    return (x & y) | (((~x) % 0x100000000) & z)

def F2(x, y, z):
    return (x | ((~y) % 0x100000000)) ^ z

def F3(x, y, z):
    return (x & z) | (((~z) % 0x100000000) & y)

def F4(x, y, z):
    return x ^ (y | ((~z) % 0x100000000))

def R(a, b, c, d, e, Fj, Kj, sj, rj, X):
    a = ROL(sj, (a + Fj(b, c, d) + X[rj] + Kj) % 0x100000000) + e
    c = ROL(10, c)
    return a % 0x100000000, c

PADDING = [0x80] + [0]*63

import sys
import struct

def RMD160Transform(state, block): #uint32 state[5], uchar block[64]
    x = [0]*16
    if sys.byteorder == 'little':
        x = struct.unpack('<16L', ''.join([chr(x) for x in block[0:64]]))
    else:
        raise "Error!!"
    a = state[0]
    b = state[1]
    c = state[2]
    d = state[3]
    e = state[4]

    #/* Round 1 */
    a, c = R(a, b, c, d, e, F0, K0, 11,  0, x);
    e, b = R(e, a, b, c, d, F0, K0, 14,  1, x);
    d, a = R(d, e, a, b, c, F0, K0, 15,  2, x);
    c, e = R(c, d, e, a, b, F0, K0, 12,  3, x);
    b, d = R(b, c, d, e, a, F0, K0,  5,  4, x);
    a, c = R(a, b, c, d, e, F0, K0,  8,  5, x);
    e, b = R(e, a, b, c, d, F0, K0,  7,  6, x);
    d, a = R(d, e, a, b, c, F0, K0,  9,  7, x);
    c, e = R(c, d, e, a, b, F0, K0, 11,  8, x);
    b, d = R(b, c, d, e, a, F0, K0, 13,  9, x);
    a, c = R(a, b, c, d, e, F0, K0, 14, 10, x);
    e, b = R(e, a, b, c, d, F0, K0, 15, 11, x);
    d, a = R(d, e, a, b, c, F0, K0,  6, 12, x);
    c, e = R(c, d, e, a, b, F0, K0,  7, 13, x);
    b, d = R(b, c, d, e, a, F0, K0,  9, 14, x);
    a, c = R(a, b, c, d, e, F0, K0,  8, 15, x); #/* #15 */
    #/* Round 2 */
    e, b = R(e, a, b, c, d, F1, K1,  7,  7, x);
    d, a = R(d, e, a, b, c, F1, K1,  6,  4, x);
    c, e = R(c, d, e, a, b, F1, K1,  8, 13, x);
    b, d = R(b, c, d, e, a, F1, K1, 13,  1, x);
    a, c = R(a, b, c, d, e, F1, K1, 11, 10, x);
    e, b = R(e, a, b, c, d, F1, K1,  9,  6, x);
    d, a = R(d, e, a, b, c, F1, K1,  7, 15, x);
    c, e = R(c, d, e, a, b, F1, K1, 15,  3, x);
    b, d = R(b, c, d, e, a, F1, K1,  7, 12, x);
    a, c = R(a, b, c, d, e, F1, K1, 12,  0, x);
    e, b = R(e, a, b, c, d, F1, K1, 15,  9, x);
    d, a = R(d, e, a, b, c, F1, K1,  9,  5, x);
    c, e = R(c, d, e, a, b, F1, K1, 11,  2, x);
    b, d = R(b, c, d, e, a, F1, K1,  7, 14, x);
    a, c = R(a, b, c, d, e, F1, K1, 13, 11, x);
    e, b = R(e, a, b, c, d, F1, K1, 12,  8, x); #/* #31 */
    #/* Round 3 */
    d, a = R(d, e, a, b, c, F2, K2, 11,  3, x);
    c, e = R(c, d, e, a, b, F2, K2, 13, 10, x);
    b, d = R(b, c, d, e, a, F2, K2,  6, 14, x);
    a, c = R(a, b, c, d, e, F2, K2,  7,  4, x);
    e, b = R(e, a, b, c, d, F2, K2, 14,  9, x);
    d, a = R(d, e, a, b, c, F2, K2,  9, 15, x);
    c, e = R(c, d, e, a, b, F2, K2, 13,  8, x);
    b, d = R(b, c, d, e, a, F2, K2, 15,  1, x);
    a, c = R(a, b, c, d, e, F2, K2, 14,  2, x);
    e, b = R(e, a, b, c, d, F2, K2,  8,  7, x);
    d, a = R(d, e, a, b, c, F2, K2, 13,  0, x);
    c, e = R(c, d, e, a, b, F2, K2,  6,  6, x);
    b, d = R(b, c, d, e, a, F2, K2,  5, 13, x);
    a, c = R(a, b, c, d, e, F2, K2, 12, 11, x);
    e, b = R(e, a, b, c, d, F2, K2,  7,  5, x);
    d, a = R(d, e, a, b, c, F2, K2,  5, 12, x); #/* #47 */
    #/* Round 4 */
    c, e = R(c, d, e, a, b, F3, K3, 11,  1, x);
    b, d = R(b, c, d, e, a, F3, K3, 12,  9, x);
    a, c = R(a, b, c, d, e, F3, K3, 14, 11, x);
    e, b = R(e, a, b, c, d, F3, K3, 15, 10, x);
    d, a = R(d, e, a, b, c, F3, K3, 14,  0, x);
    c, e = R(c, d, e, a, b, F3, K3, 15,  8, x);
    b, d = R(b, c, d, e, a, F3, K3,  9, 12, x);
    a, c = R(a, b, c, d, e, F3, K3,  8,  4, x);
    e, b = R(e, a, b, c, d, F3, K3,  9, 13, x);
    d, a = R(d, e, a, b, c, F3, K3, 14,  3, x);
    c, e = R(c, d, e, a, b, F3, K3,  5,  7, x);
    b, d = R(b, c, d, e, a, F3, K3,  6, 15, x);
    a, c = R(a, b, c, d, e, F3, K3,  8, 14, x);
    e, b = R(e, a, b, c, d, F3, K3,  6,  5, x);
    d, a = R(d, e, a, b, c, F3, K3,  5,  6, x);
    c, e = R(c, d, e, a, b, F3, K3, 12,  2, x); #/* #63 */
    #/* Round 5 */
    b, d = R(b, c, d, e, a, F4, K4,  9,  4, x);
    a, c = R(a, b, c, d, e, F4, K4, 15,  0, x);
    e, b = R(e, a, b, c, d, F4, K4,  5,  5, x);
    d, a = R(d, e, a, b, c, F4, K4, 11,  9, x);
    c, e = R(c, d, e, a, b, F4, K4,  6,  7, x);
    b, d = R(b, c, d, e, a, F4, K4,  8, 12, x);
    a, c = R(a, b, c, d, e, F4, K4, 13,  2, x);
    e, b = R(e, a, b, c, d, F4, K4, 12, 10, x);
    d, a = R(d, e, a, b, c, F4, K4,  5, 14, x);
    c, e = R(c, d, e, a, b, F4, K4, 12,  1, x);
    b, d = R(b, c, d, e, a, F4, K4, 13,  3, x);
    a, c = R(a, b, c, d, e, F4, K4, 14,  8, x);
    e, b = R(e, a, b, c, d, F4, K4, 11, 11, x);
    d, a = R(d, e, a, b, c, F4, K4,  8,  6, x);
    c, e = R(c, d, e, a, b, F4, K4,  5, 15, x);
    b, d = R(b, c, d, e, a, F4, K4,  6, 13, x); #/* #79 */

    aa = a;
    bb = b;
    cc = c;
    dd = d;
    ee = e;

    a = state[0]
    b = state[1]
    c = state[2]
    d = state[3]
    e = state[4]    

    #/* Parallel round 1 */
    a, c = R(a, b, c, d, e, F4, KK0,  8,  5, x)
    e, b = R(e, a, b, c, d, F4, KK0,  9, 14, x)
    d, a = R(d, e, a, b, c, F4, KK0,  9,  7, x)
    c, e = R(c, d, e, a, b, F4, KK0, 11,  0, x)
    b, d = R(b, c, d, e, a, F4, KK0, 13,  9, x)
    a, c = R(a, b, c, d, e, F4, KK0, 15,  2, x)
    e, b = R(e, a, b, c, d, F4, KK0, 15, 11, x)
    d, a = R(d, e, a, b, c, F4, KK0,  5,  4, x)
    c, e = R(c, d, e, a, b, F4, KK0,  7, 13, x)
    b, d = R(b, c, d, e, a, F4, KK0,  7,  6, x)
    a, c = R(a, b, c, d, e, F4, KK0,  8, 15, x)
    e, b = R(e, a, b, c, d, F4, KK0, 11,  8, x)
    d, a = R(d, e, a, b, c, F4, KK0, 14,  1, x)
    c, e = R(c, d, e, a, b, F4, KK0, 14, 10, x)
    b, d = R(b, c, d, e, a, F4, KK0, 12,  3, x)
    a, c = R(a, b, c, d, e, F4, KK0,  6, 12, x) #/* #15 */
    #/* Parallel round 2 */
    e, b = R(e, a, b, c, d, F3, KK1,  9,  6, x)
    d, a = R(d, e, a, b, c, F3, KK1, 13, 11, x)
    c, e = R(c, d, e, a, b, F3, KK1, 15,  3, x)
    b, d = R(b, c, d, e, a, F3, KK1,  7,  7, x)
    a, c = R(a, b, c, d, e, F3, KK1, 12,  0, x)
    e, b = R(e, a, b, c, d, F3, KK1,  8, 13, x)
    d, a = R(d, e, a, b, c, F3, KK1,  9,  5, x)
    c, e = R(c, d, e, a, b, F3, KK1, 11, 10, x)
    b, d = R(b, c, d, e, a, F3, KK1,  7, 14, x)
    a, c = R(a, b, c, d, e, F3, KK1,  7, 15, x)
    e, b = R(e, a, b, c, d, F3, KK1, 12,  8, x)
    d, a = R(d, e, a, b, c, F3, KK1,  7, 12, x)
    c, e = R(c, d, e, a, b, F3, KK1,  6,  4, x)
    b, d = R(b, c, d, e, a, F3, KK1, 15,  9, x)
    a, c = R(a, b, c, d, e, F3, KK1, 13,  1, x)
    e, b = R(e, a, b, c, d, F3, KK1, 11,  2, x) #/* #31 */
    #/* Parallel round 3 */
    d, a = R(d, e, a, b, c, F2, KK2,  9, 15, x)
    c, e = R(c, d, e, a, b, F2, KK2,  7,  5, x)
    b, d = R(b, c, d, e, a, F2, KK2, 15,  1, x)
    a, c = R(a, b, c, d, e, F2, KK2, 11,  3, x)
    e, b = R(e, a, b, c, d, F2, KK2,  8,  7, x)
    d, a = R(d, e, a, b, c, F2, KK2,  6, 14, x)
    c, e = R(c, d, e, a, b, F2, KK2,  6,  6, x)
    b, d = R(b, c, d, e, a, F2, KK2, 14,  9, x)
    a, c = R(a, b, c, d, e, F2, KK2, 12, 11, x)
    e, b = R(e, a, b, c, d, F2, KK2, 13,  8, x)
    d, a = R(d, e, a, b, c, F2, KK2,  5, 12, x)
    c, e = R(c, d, e, a, b, F2, KK2, 14,  2, x)
    b, d = R(b, c, d, e, a, F2, KK2, 13, 10, x)
    a, c = R(a, b, c, d, e, F2, KK2, 13,  0, x)
    e, b = R(e, a, b, c, d, F2, KK2,  7,  4, x)
    d, a = R(d, e, a, b, c, F2, KK2,  5, 13, x) #/* #47 */
    #/* Parallel round 4 */
    c, e = R(c, d, e, a, b, F1, KK3, 15,  8, x)
    b, d = R(b, c, d, e, a, F1, KK3,  5,  6, x)
    a, c = R(a, b, c, d, e, F1, KK3,  8,  4, x)
    e, b = R(e, a, b, c, d, F1, KK3, 11,  1, x)
    d, a = R(d, e, a, b, c, F1, KK3, 14,  3, x)
    c, e = R(c, d, e, a, b, F1, KK3, 14, 11, x)
    b, d = R(b, c, d, e, a, F1, KK3,  6, 15, x)
    a, c = R(a, b, c, d, e, F1, KK3, 14,  0, x)
    e, b = R(e, a, b, c, d, F1, KK3,  6,  5, x)
    d, a = R(d, e, a, b, c, F1, KK3,  9, 12, x)
    c, e = R(c, d, e, a, b, F1, KK3, 12,  2, x)
    b, d = R(b, c, d, e, a, F1, KK3,  9, 13, x)
    a, c = R(a, b, c, d, e, F1, KK3, 12,  9, x)
    e, b = R(e, a, b, c, d, F1, KK3,  5,  7, x)
    d, a = R(d, e, a, b, c, F1, KK3, 15, 10, x)
    c, e = R(c, d, e, a, b, F1, KK3,  8, 14, x) #/* #63 */
    #/* Parallel round 5 */
    b, d = R(b, c, d, e, a, F0, KK4,  8, 12, x)
    a, c = R(a, b, c, d, e, F0, KK4,  5, 15, x)
    e, b = R(e, a, b, c, d, F0, KK4, 12, 10, x)
    d, a = R(d, e, a, b, c, F0, KK4,  9,  4, x)
    c, e = R(c, d, e, a, b, F0, KK4, 12,  1, x)
    b, d = R(b, c, d, e, a, F0, KK4,  5,  5, x)
    a, c = R(a, b, c, d, e, F0, KK4, 14,  8, x)
    e, b = R(e, a, b, c, d, F0, KK4,  6,  7, x)
    d, a = R(d, e, a, b, c, F0, KK4,  8,  6, x)
    c, e = R(c, d, e, a, b, F0, KK4, 13,  2, x)
    b, d = R(b, c, d, e, a, F0, KK4,  6, 13, x)
    a, c = R(a, b, c, d, e, F0, KK4,  5, 14, x)
    e, b = R(e, a, b, c, d, F0, KK4, 15,  0, x)
    d, a = R(d, e, a, b, c, F0, KK4, 13,  3, x)
    c, e = R(c, d, e, a, b, F0, KK4, 11,  9, x)
    b, d = R(b, c, d, e, a, F0, KK4, 11, 11, x) #/* #79 */

    t = (state[1] + cc + d) % 0x100000000;
    state[1] = (state[2] + dd + e) % 0x100000000;
    state[2] = (state[3] + ee + a) % 0x100000000;
    state[3] = (state[4] + aa + b) % 0x100000000;
    state[4] = (state[0] + bb + c) % 0x100000000;
    state[0] = t % 0x100000000;

    pass


def RMD160Update(ctx, inp, inplen):
    if type(inp) == str:
        inp = [ord(i)&0xff for i in inp]
    
    have = (ctx.count / 8) % 64
    need = 64 - have
    ctx.count += 8 * inplen
    off = 0
    if inplen >= need:
        if have:
            for i in xrange(need):
                ctx.buffer[have+i] = inp[i]
            RMD160Transform(ctx.state, ctx.buffer)
            off = need
            have = 0
        while off + 64 <= inplen:
            RMD160Transform(ctx.state, inp[off:]) #<---
            off += 64
    if off < inplen:
        # memcpy(ctx->buffer + have, input+off, len-off);
        for i in xrange(inplen - off):
            ctx.buffer[have+i] = inp[off+i]

def RMD160Final(ctx):
    size = struct.pack("<Q", ctx.count)
    padlen = 64 - ((ctx.count / 8) % 64)
    if padlen < 1+8:
        padlen += 64
    RMD160Update(ctx, PADDING, padlen-8)
    RMD160Update(ctx, size, 8)
    return struct.pack("<5L", *ctx.state)


assert '37f332f68db77bd9d7edd4969571ad671cf9dd3b' == \
       new('The quick brown fox jumps over the lazy dog').hexdigest()
assert '132072df690933835eb8b6ad0b77e7b6f14acad7' == \
       new('The quick brown fox jumps over the lazy cog').hexdigest()
assert '9c1185a5c5e9fc54612808977ee8f548b2258d31' == \
       new('').hexdigest()

########NEW FILE########
__FILENAME__ = transaction
#!/usr/bin/python
import re, json, copy
from main import *

### Hex to bin converter and vice versa for objects

def json_is_base(obj,base):
    alpha = get_code_string(base)
    if isinstance(obj,(str,unicode)):
        for i in range(len(obj)):
            if alpha.find(obj[i]) == -1: return False
        return True
    elif isinstance(obj,(int,float,long)) or obj is None: return True
    elif isinstance(obj,list):
        for i in range(len(obj)):
            if not json_is_base(obj[i],base): return False
        return True
    else:
        for x in obj:
            if not json_is_base(obj[x],base): return False
        return True

def json_changebase(obj,changer):
    if isinstance(obj,(str,unicode)): return changer(obj)
    elif isinstance(obj,(int,float,long)) or obj is None: return obj
    elif isinstance(obj,list): return [json_changebase(x,changer) for x in obj]
    return dict((x, json_changebase(obj[x], changer)) for x in obj)

### Transaction serialization and deserialization

def deserialize(tx):
    if re.match('^[0-9a-fA-F]*$',tx):
        return json_changebase(deserialize(tx.decode('hex')),lambda x:x.encode('hex'))
    # http://stackoverflow.com/questions/4851463/python-closure-write-to-variable-in-parent-scope
    # Python's scoping rules are demented, requiring me to make pos an object so that it is call-by-reference
    pos = [0]

    def read_as_int(bytez):
        pos[0] += bytez
        return decode(tx[pos[0]-bytez:pos[0]][::-1],256)

    def read_var_int():
        pos[0] += 1
        if ord(tx[pos[0]-1]) < 253: return ord(tx[pos[0]-1])
        return read_as_int(pow(2,ord(tx[pos[0]-1]) - 252))

    def read_bytes(bytez):
        pos[0] += bytez
        return tx[pos[0]-bytez:pos[0]]

    def read_var_string():
        size = read_var_int()
        return read_bytes(size)

    obj = { "ins" : [] , "outs" : [] }
    obj["version"] = read_as_int(4)
    ins = read_var_int()
    for i in range(ins):
        obj["ins"].append({
            "outpoint" : {
                "hash" : read_bytes(32)[::-1],
                "index": read_as_int(4)
            },
            "script" : read_var_string(),
            "sequence" : read_as_int(4)
        })
    outs = read_var_int()
    for i in range(outs):
        obj["outs"].append({
            "value" : read_as_int(8),
            "script": read_var_string()
        })
    obj["locktime"] = read_as_int(4)
    return obj

def serialize(txobj):
    o = []
    if json_is_base(txobj,16):
        return serialize(json_changebase(txobj,lambda x: x.decode('hex'))).encode('hex')
    o.append(encode(txobj["version"],256,4)[::-1])
    o.append(num_to_var_int(len(txobj["ins"])))
    for inp in txobj["ins"]:
        o.append(inp["outpoint"]["hash"][::-1])
        o.append(encode(inp["outpoint"]["index"],256,4)[::-1])
        o.append(num_to_var_int(len(inp["script"]))+inp["script"])
        o.append(encode(inp["sequence"],256,4)[::-1])
    o.append(num_to_var_int(len(txobj["outs"])))
    for out in txobj["outs"]:
        o.append(encode(out["value"],256,8)[::-1])
        o.append(num_to_var_int(len(out["script"]))+out["script"])
    o.append(encode(txobj["locktime"],256,4)[::-1])
    return ''.join(o)

### Hashing transactions for signing

SIGHASH_ALL = 1
SIGHASH_NONE = 2
SIGHASH_SINGLE = 3
SIGHASH_ANYONECANPAY = 80

def signature_form(tx, i, script, hashcode = SIGHASH_ALL):
    i, hashcode = int(i), int(hashcode)
    if isinstance(tx,str):
        return serialize(signature_form(deserialize(tx),i,script,hashcode))
    newtx = copy.deepcopy(tx)
    for inp in newtx["ins"]: inp["script"] = ""
    newtx["ins"][i]["script"] = script
    if hashcode == SIGHASH_NONE:
        newtx["outs"] = []
    elif hashcode == SIGHASH_SINGLE:
        newtx["outs"] = newtx["outs"][:len(newtx["ins"])]
        for out in range(len(newtx["ins"]) - 1):
            out.value = 2**64 - 1
            out.script = ""
    elif hashcode == SIGHASH_ANYONECANPAY:
        newtx["ins"] = [newtx["ins"][i]]
    else:
        pass
    return newtx

### Making the actual signatures

def der_encode_sig(v,r,s):
    b1, b2 = encode(r,256).encode('hex'), encode(s,256).encode('hex')
    if r >= 2**255: b1 = '00' + b1
    if s >= 2**255: b2 = '00' + b2
    left = '02'+encode(len(b1)/2,16,2)+b1
    right = '02'+encode(len(b2)/2,16,2)+b2
    return '30'+encode(len(left+right)/2,16,2)+left+right

def der_decode_sig(sig):
    leftlen = decode(sig[6:8],16)*2
    left = sig[8:8+leftlen]
    rightlen = decode(sig[10+leftlen:12+leftlen],16)*2
    right = sig[12+leftlen:12+leftlen+rightlen]
    return (None,decode(left,16),decode(right,16))

def txhash(tx,hashcode=None):
    if re.match('^[0-9a-fA-F]*$',tx):
        tx = changebase(tx,16,256)
    if hashcode: return dbl_sha256(tx + encode(int(hashcode),256,4)[::-1])
    else: return bin_dbl_sha256(tx)[::-1].encode('hex')

def bin_txhash(tx,hashcode=None):
    return txhash(tx,hashcode).decode('hex')

def ecdsa_tx_sign(tx,priv,hashcode=SIGHASH_ALL):
    rawsig = ecdsa_raw_sign(bin_txhash(tx,hashcode),priv)
    return der_encode_sig(*rawsig)+encode(hashcode,16,2)

def ecdsa_tx_verify(tx,sig,pub,hashcode=SIGHASH_ALL):
    return ecdsa_raw_verify(bin_txhash(tx,hashcode),der_decode_sig(sig),pub)

def ecdsa_tx_recover(tx,sig,hashcode=SIGHASH_ALL):
    z = bin_txhash(tx,hashcode)
    _,r,s = der_decode_sig(sig)
    left = ecdsa_raw_recover(z,(0,r,s))
    right = ecdsa_raw_recover(z,(1,r,s))
    return (encode_pubkey(left,'hex'), encode_pubkey(right,'hex'))

### Scripts

def mk_pubkey_script(addr): # Keep the auxiliary functions around for altcoins' sake
    return '76a914' + b58check_to_hex(addr) + '88ac'

def mk_scripthash_script(addr):
    return 'a914' + b58check_to_hex(addr) + '87'

# Address representation to output script
def address_to_script(addr):
    if addr[0] == '3': return mk_scripthash_script(addr)
    else: return mk_pubkey_script(addr)

# Output script to address representation
def script_to_address(script,vbyte=0):
    if re.match('^[0-9a-fA-F]*$',script):
        script = script.decode('hex')
    if script[:3] == '\x76\xa9\x14' and script[-2:] == '\x88\xac' and len(script) == 25:
        return bin_to_b58check(script[3:-2],vbyte) # pubkey hash addresses
    else:
        return bin_to_b58check(script[2:-1],5) # BIP0016 scripthash addresses


def p2sh_scriptaddr(script, magicbyte=5):
    if re.match('^[0-9a-fA-F]*$', script):
        script = script.decode('hex')
    return hex_to_b58check(hash160(script), magicbyte)
scriptaddr = p2sh_scriptaddr


def deserialize_script(script):
    if re.match('^[0-9a-fA-F]*$',script):
        return json_changebase(deserialize_script(script.decode('hex')),lambda x:x.encode('hex'))
    out, pos = [], 0
    while pos < len(script):
        code = ord(script[pos])
        if code == 0:
            out.append(None)
            pos += 1
        elif code <= 75:
            out.append(script[pos+1:pos+1+code])
            pos += 1 + code
        elif code <= 78:
            szsz = pow(2,code - 76)
            sz = decode(script[pos + szsz : pos : -1],256)
            out.append(script[pos + 1 + szsz:pos + 1 + szsz + sz])
            pos += 1 + szsz + sz
        elif code <= 96:
            out.append(code - 80)
            pos += 1
        else:
            out.append(code)
            pos += 1
    return out

def serialize_script_unit(unit):
    if isinstance(unit,int):
        if unit < 16: return chr(unit + 80)
        else: return chr(unit)
    elif unit is None:
        return '\x00'
    else:
        if len(unit) <= 75: return chr(len(unit))+unit
        elif len(unit) < 256: return chr(76)+chr(len(unit))+unit
        elif len(unit) < 65536: return chr(77)+encode(len(unit),256,2)[::-1]+unit
        else: return chr(78)+encode(len(unit),256,4)[::-1]+unit

def serialize_script(script):
    if json_is_base(script,16):
        return serialize_script(json_changebase(script,lambda x:x.decode('hex'))).encode('hex')
    return ''.join(map(serialize_script_unit,script))

def mk_multisig_script(*args): # [pubs],k,n or pub1,pub2...pub[n],k,n
    if len(args) == 3: pubs, k, n = args[0], int(args[1]), int(args[2])
    else: pubs, k, n = list(args[:-2]), int(args[-2]), int(args[-1])
    return serialize_script([k]+pubs+[n,174])

### Signing and verifying

def verify_tx_input(tx,i,script,sig,pub):
    if re.match('^[0-9a-fA-F]*$',tx): tx = tx.decode('hex')
    if re.match('^[0-9a-fA-F]*$',script): script = script.decode('hex')
    if not re.match('^[0-9a-fA-F]*$',sig): sig = sig.encode('hex')
    hashcode = decode(sig[-2:],16)
    modtx = signature_form(tx,int(i),script,hashcode)
    return ecdsa_tx_verify(modtx,sig,pub,hashcode)

def sign(tx,i,priv):
    i = int(i)
    if not re.match('^[0-9a-fA-F]*$',tx):
        return sign(tx.encode('hex'),i,priv).decode('hex')
    if len(priv) <= 33: priv = priv.encode('hex')
    pub = privkey_to_pubkey(priv)
    address = pubkey_to_address(pub)
    signing_tx = signature_form(tx,i,mk_pubkey_script(address))
    sig = ecdsa_tx_sign(signing_tx,priv)
    txobj = deserialize(tx)
    txobj["ins"][i]["script"] = serialize_script([sig,pub])
    return serialize(txobj)

def signall(tx,priv):
    for i in range(len(deserialize(tx)["ins"])):
        tx = sign(tx,i,priv)
    return tx

def multisign(tx,i,script,pk,hashcode = SIGHASH_ALL):
    if re.match('^[0-9a-fA-F]*$',tx): tx = tx.decode('hex')
    if re.match('^[0-9a-fA-F]*$',script): script = script.decode('hex')
    modtx = signature_form(tx,i,script,hashcode)
    return ecdsa_tx_sign(modtx,pk,hashcode)

def apply_multisignatures(*args): # tx,i,script,sigs OR tx,i,script,sig1,sig2...,sig[n]
    tx, i, script = args[0], int(args[1]), args[2]
    sigs = args[3] if isinstance(args[3],list) else list(args[3:])

    if re.match('^[0-9a-fA-F]*$',script): script = script.decode('hex')
    sigs = [x.decode('hex') if x[:2] == '30' else x for x in sigs]
    if re.match('^[0-9a-fA-F]*$',tx):
        return apply_multisignatures(tx.decode('hex'),i,script,sigs).encode('hex')

    txobj = deserialize(tx)
    txobj["ins"][i]["script"] = serialize_script([None]+sigs+[script])
    return serialize(txobj)

def is_inp(arg):
    return len(arg) > 64 or "output" in arg or "outpoint" in arg

def mktx(*args): # [in0, in1...],[out0, out1...] or in0, in1 ... out0 out1 ...
    ins, outs = [], []
    for arg in args:
        if isinstance(arg,list):
            for a in arg: (ins if is_inp(a) else outs).append(a)
        else:
            (ins if is_inp(arg) else outs).append(arg)

    txobj = { "locktime" : 0, "version" : 1,"ins" : [], "outs" : [] }
    for i in ins:
        if isinstance(i,dict) and "outpoint" in i:
            txobj["ins"].append(i)
        else:
            if isinstance(i,dict) and "output" in i: i = i["output"]
            txobj["ins"].append({
                "outpoint" : { "hash": i[:64], "index": int(i[65:]) },
                "script": "",
                "sequence": 4294967295
            })
    for o in outs:
        if isinstance(o,str): o = {
            "address": o[:o.find(':')],
            "value": int(o[o.find(':')+1:])
        }
        txobj["outs"].append({
            "script": address_to_script(o["address"]),
            "value": o["value"]
        })
    return serialize(txobj)

def select(unspent,value):
    value = int(value)
    high = [u for u in unspent if u["value"] >= value]
    high.sort(key=lambda u:u["value"])
    low = [u for u in unspent if u["value"] < value]
    low.sort(key=lambda u:-u["value"])
    if len(high): return [high[0]]
    i, tv = 0, 0
    while tv < value and i < len(low):
        tv += low[i]["value"]
        i += 1
    if tv < value: raise Exception("Not enough funds")
    return low[:i]

# Only takes inputs of the form { "output": blah, "value": foo }
def mksend(*args):
    argz, change, fee = args[:-2], args[-2], int(args[-1])
    ins, outs = [], []
    for arg in argz:
        if isinstance(arg,list):
            for a in arg: (ins if is_inp(a) else outs).append(a)
        else:
            (ins if is_inp(arg) else outs).append(arg)

    isum = sum([i["value"] for i in ins])
    osum, outputs2 = 0, []
    for o in outs:
        if isinstance(o,str): o2 = {
            "address": o[:o.find(':')],
            "value": int(o[o.find(':')+1:])
        }
        else: o2 = o
        outputs2.append(o2)
        osum += o2["value"]

    if isum < osum+fee:
        raise Exception("Not enough money")
    elif isum > osum+fee+5430:
        outputs2 += [{"address": change, "value": isum-osum-fee }]

    return mktx(ins,outputs2)

########NEW FILE########
__FILENAME__ = test
import random, os, json, sys
import bitcoin.ripemd as ripemd

from bitcoin import *

argv = sys.argv + ['y']*15

if argv[1] == 'y':
    print "Starting ECC arithmetic tests"
for i in range(8 if argv[1] == 'y' else 0):
    print "### Round %d" % (i+1)
    x,y = random.randrange(2**256), random.randrange(2**256)
    print multiply(multiply(G,x),y)[0] == multiply(multiply(G,y),x)[0]
    print add_pubkeys(multiply(G,x),multiply(G,y))[0] == multiply(G,add_privkeys(x,y))[0]
    hx, hy = encode(x%N,16,64), encode(y%N,16,64)
    print multiply(multiply(G,hx),hy)[0] == multiply(multiply(G,hy),hx)[0]
    print add_pubkeys(multiply(G,hx),multiply(G,hy))[0] == multiply(G,add_privkeys(hx,hy))[0]
    h1601 = b58check_to_hex(pubtoaddr(privtopub(x)))
    h1602 = b58check_to_hex(pubtoaddr(multiply(G,hx),23))
    print h1601 == h1602
    p = privtopub(sha256(str(x)))
    if i%2 == 1: p = changebase(p,16,256)
    print decompress(compress(p)) == p
    print multiply(divide(G,x),x)[0] == G[0]

if argv[2] == 'y':
    print "Starting Electrum wallet internal consistency tests"
    for i in range(3):
        seed = sha256(str(random.randrange(2**40)))[:32]
        mpk = electrum_mpk(seed)
        print 'seed: ',seed
        print 'mpk: ',mpk
        for i in range(5):
            pk = electrum_privkey(seed,i)
            pub = electrum_pubkey((mpk,seed)[i%2],i)
            pub2 = privtopub(pk)
            print 'priv: ',pk
            print 'pub: ',pub
            print pub == pub2
            if pub != pub2: print 'DOES NOT MATCH!!!!\npub2: '+pub2

if argv[3] == 'y':
    # Requires Electrum
    wallet = "/tmp/tempwallet_"+str(random.randrange(2**40))
    print "Starting wallet tests with: "+wallet
    os.popen('echo "\n\n\n\n\n\n" | electrum -w %s create' % wallet).read()
    seed = str(json.loads(os.popen("electrum -w %s getseed" % wallet).read())['seed'])
    addies = json.loads(os.popen("electrum -w %s listaddresses" % wallet).read())
    for i in range(5):
        if addies[i] != electrum_address(seed,i,0):
            print "Address does not match!!!, seed: %s, i: %d" % (seed,i)

    print "Electrum-style signing and verification tests, against actual Electrum"
    for i in range(8):
        alphabet = "1234567890qwertyuiopasdfghjklzxcvbnm"
        msg = ''.join([random.choice(alphabet) for i in range(random.randrange(20,200))])
        addy = random.choice(addies)
        wif = os.popen('electrum -w %s dumpprivkey %s' % (wallet, addy)).readlines()[-2].replace('"','').strip()
        priv = b58check_to_hex(wif)
        pub = privtopub(priv)
    
        sig = os.popen('electrum -w %s signmessage %s %s' % (wallet, addy, msg)).readlines()[-1].strip()
        verified = ecdsa_verify(msg,sig,pub)
        print "Verified" if verified else "Verification error"
        rec = ecdsa_recover(msg,sig)
        if pub == rec: print "Recovery successful"
        if pub != rec or not verified:
            print "msg: "+msg
            print "sig: "+sig
            print "priv: "+priv
            print "addy: "+addy
        if pub != rec:
            print "Recovery error"
            print "original  pub: "+pub, hex_to_point(pub)[1]
            print "recovered pub: "+rec
    
        mysig = ecdsa_sign(msg,priv)
        v = os.popen('electrum -w %s verifymessage %s %s %s' % (wallet,addy, sig, msg)).read()
        print v

if argv[4] == 'y':
    print "Transaction-style signing and verification tests"
    for i in range(10):
        alphabet = "1234567890qwertyuiopasdfghjklzxcvbnm"
        msg = ''.join([random.choice(alphabet) for i in range(random.randrange(20,200))])
        priv = sha256(str(random.randrange(2**256)))
        pub = privtopub(priv)
        sig = ecdsa_tx_sign(msg,priv)
        v = ecdsa_tx_verify(msg,sig,pub)
        print "Verified" if v else "Verification error"
        rec = ecdsa_tx_recover(msg,sig)
        print "Recovered" if pub in rec else "Recovery failed"

if argv[5] == 'y':
    tx = '0100000001239f932c780e517015842f3b02ff765fba97f9f63f9f1bc718b686a56ed9c73400000000fd5d010047304402200c40fa58d3f6d5537a343cf9c8d13bc7470baf1d13867e0de3e535cd6b4354c802200f2b48f67494835b060d0b2ff85657d2ba2d9ea4e697888c8cb580e8658183a801483045022056f488c59849a4259e7cef70fe5d6d53a4bd1c59a195b0577bd81cb76044beca022100a735b319fa66af7b178fc719b93f905961ef4d4446deca8757a90de2106dd98a014cc95241046c7d87fd72caeab48e937f2feca9e9a4bd77f0eff4ebb2dbbb9855c023e334e188d32aaec4632ea4cbc575c037d8101aec73d029236e7b1c2380f3e4ad7edced41046fd41cddf3bbda33a240b417a825cc46555949917c7ccf64c59f42fd8dfe95f34fae3b09ed279c8c5b3530510e8cca6230791102eef9961d895e8db54af0563c410488d618b988efd2511fc1f9c03f11c210808852b07fe46128c1a6b1155aa22cdf4b6802460ba593db2d11c7e6cbe19cedef76b7bcabd05d26fd97f4c5a59b225053aeffffffff0310270000000000001976a914a89733100315c37d228a529853af341a9d290a4588ac409c00000000000017a9142b56f9a4009d9ff99b8f97bea4455cd71135f5dd87409c00000000000017a9142b56f9a4009d9ff99b8f97bea4455cd71135f5dd8700000000'
    print "Serialize roundtrip success" if serialize(deserialize(tx)) == tx else "Serialize roundtrip failed"
if argv[6] == 'y':
    script = '47304402200c40fa58d3f6d5537a343cf9c8d13bc7470baf1d13867e0de3e535cd6b4354c802200f2b48f67494835b060d0b2ff85657d2ba2d9ea4e697888c8cb580e8658183a801483045022056f488c59849a4259e7cef70fe5d6d53a4bd1c59a195b0577bd81cb76044beca022100a735b319fa66af7b178fc719b93f905961ef4d4446deca8757a90de2106dd98a014cc95241046c7d87fd72caeab48e937f2feca9e9a4bd77f0eff4ebb2dbbb9855c023e334e188d32aaec4632ea4cbc575c037d8101aec73d029236e7b1c2380f3e4ad7edced41046fd41cddf3bbda33a240b417a825cc46555949917c7ccf64c59f42fd8dfe95f34fae3b09ed279c8c5b3530510e8cca6230791102eef9961d895e8db54af0563c410488d618b988efd2511fc1f9c03f11c210808852b07fe46128c1a6b1155aa22cdf4b6802460ba593db2d11c7e6cbe19cedef76b7bcabd05d26fd97f4c5a59b225053ae'
    print "Script serialize roundtrip success" if serialize_script(deserialize_script(script)) == script else "Script serialize roundtrip failed"

if argv[7] == 'y':
    print "Attempting transaction creation"
    privs = [sha256(str(random.randrange(2**256))) for x in range(4)]
    pubs = [privtopub(priv) for priv in privs]
    addresses = [pubtoaddr(pub) for pub in pubs]
    mscript = mk_multisig_script(pubs[1:],2,3)
    msigaddr = p2sh_scriptaddr(mscript)
    tx = mktx(['01'*32+':1','23'*32+':2'],[msigaddr+':20202',addresses[0]+':40404'])
    tx1 = sign(tx,1,privs[0])
    sig1 = multisign(tx,0,mscript,privs[1])
    print "Verifying sig1:",verify_tx_input(tx1,0,mscript,sig1,pubs[1])
    sig3 = multisign(tx,0,mscript,privs[3])
    print "Verifying sig3:",verify_tx_input(tx1,0,mscript,sig3,pubs[3])
    tx2 = apply_multisignatures(tx1,0,mscript,[sig1,sig3])
    print "Outputting transaction: ",tx2

if argv[8] == 'y':
    # Created with python-ecdsa 0.9
    # Code to make your own vectors:
    # class gen:
    #     def order(self): return 115792089237316195423570985008687907852837564279074904382605163141518161494337
    # dummy = gen()
    # for i in range(10): ecdsa.rfc6979.generate_k(dummy,i,hashlib.sha256,hashlib.sha256(str(i)).digest())
    test_vectors = [32783320859482229023646250050688645858316445811207841524283044428614360139869L, 109592113955144883013243055602231029997040992035200230706187150761552110229971L, 65765393578006003630736298397268097590176526363988568884298609868706232621488L, 85563144787585457107933685459469453513056530050186673491900346620874099325918L, 99829559501561741463404068005537785834525504175465914981205926165214632019533L, 7755945018790142325513649272940177083855222863968691658328003977498047013576L, 81516639518483202269820502976089105897400159721845694286620077204726637043798L, 52824159213002398817852821148973968315579759063230697131029801896913602807019L, 44033460667645047622273556650595158811264350043302911918907282441675680538675L, 32396602643737403620316035551493791485834117358805817054817536312402837398361L]
    print "Beginning RFC6979 deterministic signing tests"
    for i in range(10):
        ti = test_vectors[i] 
        mine = deterministic_generate_k(bin_sha256(str(i)),encode(i,256,32))
        if ti == mine:
            print "Test vector matches"
        else:
            print "Test vector does not match"
            print ti
            print mine

if argv[9] == 'y':
    # From https://en.bitcoin.it/wiki/BIP_0032
    def full_derive(key,chain):
        if len(chain) == 0: return key
        elif chain[0] == 'pub': return full_derive(bip32_privtopub(key),chain[1:])
        else: return full_derive(bip32_ckd(key,chain[0]),chain[1:])
    test_vectors = [
        [ [], 'xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi' ],
        [ ['pub'], 'xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8' ],
        [ [ 2**31 ], 'xprv9uHRZZhk6KAJC1avXpDAp4MDc3sQKNxDiPvvkX8Br5ngLNv1TxvUxt4cV1rGL5hj6KCesnDYUhd7oWgT11eZG7XnxHrnYeSvkzY7d2bhkJ7' ],
        [ [ 2**31, 1 ], 'xprv9wTYmMFdV23N2TdNG573QoEsfRrWKQgWeibmLntzniatZvR9BmLnvSxqu53Kw1UmYPxLgboyZQaXwTCg8MSY3H2EU4pWcQDnRnrVA1xe8fs' ],
        [ [ 2**31, 1, 2**31 + 2], 'xprv9z4pot5VBttmtdRTWfWQmoH1taj2axGVzFqSb8C9xaxKymcFzXBDptWmT7FwuEzG3ryjH4ktypQSAewRiNMjANTtpgP4mLTj34bhnZX7UiM' ],
        [ [ 2**31, 1, 2**31 + 2, 'pub', 2, 1000000000], 'xpub6H1LXWLaKsWFhvm6RVpEL9P4KfRZSW7abD2ttkWP3SSQvnyA8FSVqNTEcYFgJS2UaFcxupHiYkro49S8yGasTvXEYBVPamhGW6cFJodrTHy' ]
    ]
    print "Beginning BIP0032 tests"
    mk = bip32_master_key('000102030405060708090a0b0c0d0e0f'.decode('hex'))
    print 'Master key:', mk
    for tv in test_vectors:
        left, right = full_derive(mk,tv[0]), tv[1]
        if left == right: print "Test vector matches"
        else:
            print "Test vector does not match"
            print tv[0]
            print [x.encode('hex') if isinstance(x,str) else x for x in bip32_deserialize(left)]
            print [x.encode('hex') if isinstance(x,str) else x for x in bip32_deserialize(right)]

if argv[10] == 'y':
    print "Starting address and script generation consistency tests"
    for i in range(5):
        a = privtoaddr(random_key())
        print a == script_to_address(address_to_script(a))
        b = privtoaddr(random_key(),5)
        print b == script_to_address(address_to_script(b))

if argv[11] == 'y':
    print "Testing the pure python backup for ripemd160."

    strvec = [""]*4

    strvec[0] = ""
    strvec[1] = "The quick brown fox jumps over the lazy dog"
    strvec[2] = "The quick brown fox jumps over the lazy cog"
    strvec[3] = "Nobody inspects the spammish repetition"

    target = ['']*4

    target[0] = '9c1185a5c5e9fc54612808977ee8f548b2258d31'
    target[1] = '37f332f68db77bd9d7edd4969571ad671cf9dd3b'
    target[2] = '132072df690933835eb8b6ad0b77e7b6f14acad7'
    target[3] = 'cc4a5ce1b3df48aec5d22d1f16b894a0b894eccc'

    hash160target = ['']*4

    hash160target[0] = 'b472a266d0bd89c13706a4132ccfb16f7c3b9fcb'
    hash160target[1] = '0e3397b4abc7a382b3ea2365883c3c7ca5f07600'
    hash160target[2] = '53e0dacac5249e46114f65cb1f30d156b14e0bdc'
    hash160target[3] = '1c9b7b48049a8f98699bca22a5856c5ef571cd68'

    success = True
    try:
        for i in range(len(strvec)):
            digest = ripemd.RIPEMD160(strvec[i]).digest()
            hash160digest = ripemd.RIPEMD160(bin_sha256(strvec[i])).digest()
            assert digest.encode('hex') == target[i]
            assert hash160digest.encode('hex') == hash160target[i]
            assert bin_hash160(strvec[i]).encode('hex') == hash160target[i]
            assert hash160(strvec[i]) == hash160target[i]
    except AssertionError:
        print 'ripemd160 test failed.'
        success = False
    
    if success:
        print "ripemd160 test successful."

########NEW FILE########
