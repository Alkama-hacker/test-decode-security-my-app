import struct, hashlib, zipfile, sys
sys.path.insert(0,'/home/user/venv/lib/python3.11/site-packages')
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography import x509

def lp(b,o):
    n=struct.unpack_from('<I',b,o)[0]; return b[o+4:o+4+n], o+4+n

def verify(p):
    d=open(p,'rb').read()
    eocd=d.rfind(b'PK\x05\x06')
    cd_off=struct.unpack_from('<I',d,eocd+16)[0]
    assert d[cd_off:cd_off+4]==b'PK\x01\x02', "cd sig"
    assert d[cd_off-16:cd_off]==b'APK Sig Block 42', "magic"
    size2=struct.unpack_from('<Q',d,cd_off-24)[0]
    start=cd_off-size2-8
    assert struct.unpack_from('<Q',d,start)[0]==size2
    sec_c=bytearray(d[eocd:]); struct.pack_into('<I',sec_c,16,start)
    chunks=[]
    for sec in (d[:start], d[cd_off:eocd], bytes(sec_c)):
        for k in range(0,len(sec),1048576):
            c=sec[k:k+1048576]
            chunks.append(hashlib.sha256(b'\xa5'+struct.pack('<I',len(c))+c).digest())
    expect=hashlib.sha256(b'\x5a'+struct.pack('<I',len(chunks))+b''.join(chunks)).digest()
    pairs={}; q=start+8
    while q<cd_off-24:
        ln=struct.unpack_from('<Q',d,q)[0]; pid=struct.unpack_from('<I',d,q+8)[0]
        pairs[pid]=d[q+12:q+8+ln]; q+=8+ln
    val,_=lp(pairs[0x7109871a],0); signer,_=lp(val,0); sd,o=lp(signer,0)
    rest=signer[o:]; sigs,o2=lp(rest,0); pk,_=lp(rest,o2)
    sig,_=lp(sigs,0); algo=struct.unpack_from('<I',sig,0)[0]; sb,_=lp(sig,4)
    dl,oo=lp(sd,0); e0,_=lp(dl,0); dg,_=lp(e0,4)
    certs,_=lp(sd,oo); c0,_=lp(certs,0)
    cert=x509.load_der_x509_certificate(c0)
    ok_digest = dg==expect
    cert.public_key().verify(sb, sd, padding.PKCS1v15(), hashes.SHA256())
    ok_pub = pk==cert.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    z=zipfile.ZipFile(p)
    b=z.read('assets/index.android.bundle')
    print(f"{p}")
    print(f"  pairs           : {[hex(k) for k in pairs]}")
    print(f"  v2 digest match : {ok_digest}")
    print(f"  signature valid : True")
    print(f"  pubkey match    : {ok_pub}")
    print(f"  cert            : {cert.subject.rfc4514_string()} sha256={hashlib.sha256(c0).hexdigest()[:16]}")
    print(f"  zip             : {len(z.namelist())} entries, testzip={z.testzip()}")
    print(f"  bundle patch    : footer_ok={hashlib.sha1(b[:-20]).digest()==b[-20:]} initial_state={struct.unpack_from('<H',b,0x2142c9+0x30)[0]} t3={b[0x25ef00:0x25ef04].hex(' ')}")
    return ok_digest and ok_pub

for p in sys.argv[1:]:
    print("RESULT:", "PASS" if verify(p) else "FAIL"); print()
