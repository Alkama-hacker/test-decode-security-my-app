#!/usr/bin/env python3
"""
Re-sign an APK with APK Signature Scheme v2 only (RSA-2048 / SHA-256).

Why this exists: the first build of RHK-COMMUNITY-nogate.apk used a hand-rolled
v2 signer whose content digest merged the Central Directory and the EOCD into a
single chunk stream.  Android computes the digest over THREE sections
(entries / central directory / EOCD) and therefore rejected the install with
"App not installed".  This script implements the spec correctly:

    digest = SHA256( 0x5a || uint32(num_chunks) || chunk_digest_1 || ... )
    chunk_digest_i = SHA256( 0xa5 || uint32(len(chunk)) || chunk )

with the chunks taken from the three sections separately, and the EOCD copy
patched so its central-directory-offset field points at the real CD (i.e. the
value the file would have without a signing block).

Usage:
    python3 resign_v2.py in.apk out.apk [--cn "CN name"]

Requires: `cryptography`.
"""
import datetime
import hashlib
import struct
import sys
import zipfile

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

CHUNK = 1024 * 1024
V2_BLOCK_ID = 0x7109871A
SIG_ALGO_RSA_PKCS1_SHA256 = 0x0103
DIGEST_ALGO_SHA256 = 0x0101
MAGIC = b"APK Sig Block 42"


# --------------------------------------------------------------------------- #
# signing block helpers
# --------------------------------------------------------------------------- #
def _lp(b):
    return struct.pack("<I", len(b)) + b


def _seq(items):
    return b"".join(_lp(i) for i in items)


def find_unsigned_parts(data):
    """Return (content, tail) where tail = central directory + EOCD, with no
    signing block in between, and the EOCD already pointing at `content`'s end."""
    eocd = data.rfind(b"PK\x05\x06")
    if eocd < 0:
        raise ValueError("EOCD not found")
    cd_off = struct.unpack_from("<I", data, eocd + 16)[0]
    if data[cd_off:cd_off + 4] != b"PK\x01\x02":
        raise ValueError("bad central directory offset")

    if data[cd_off - 16:cd_off] == MAGIC:
        size2 = struct.unpack_from("<Q", data, cd_off - 24)[0]
        sb_start = cd_off - size2 - 8
        if struct.unpack_from("<Q", data, sb_start)[0] != size2:
            raise ValueError("corrupt signing block")
        content = data[:sb_start]
    else:
        sb_start = cd_off
        content = data[:cd_off]

    tail = bytearray(data[cd_off:])
    struct.pack_into("<I", tail, (eocd - cd_off) + 16, sb_start)
    return content, bytes(tail), sb_start


def content_digest(content, tail, cd_position):
    """APK Signature Scheme v2 chunked content digest, three sections."""
    eocd_index = tail.rfind(b"PK\x05\x06")
    section_c = bytearray(tail[eocd_index:])
    # spec: the EOCD copy used for hashing carries the offset of the signing
    # block (i.e. where the central directory would start without a block)
    struct.pack_into("<I", section_c, 16, cd_position)

    sections = [
        content,                       # ZIP entries
        tail[:eocd_index],             # central directory only
        bytes(section_c),              # EOCD (+ comment)
    ]
    chunks = []
    for sec in sections:
        for k in range(0, len(sec), CHUNK):
            chunk = sec[k:k + CHUNK]
            chunks.append(hashlib.sha256(
                b"\xa5" + struct.pack("<I", len(chunk)) + chunk).digest())
    return hashlib.sha256(b"\x5a" + struct.pack("<I", len(chunks))
                          + b"".join(chunks)).digest()


def build_signing_block(key, cert_der, digest, signature):
    digests_field = _seq([struct.pack("<I", SIG_ALGO_RSA_PKCS1_SHA256)
                          + _lp(digest)])
    certs_field = _seq([cert_der])
    signed_data = _lp(digests_field) + _lp(certs_field) + _lp(b"")
    signatures_field = _seq([struct.pack("<I", SIG_ALGO_RSA_PKCS1_SHA256)
                             + _lp(signature)])
    pubkey_lp = _lp(key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo))
    signer = _lp(_lp(signed_data) + _lp(signatures_field) + pubkey_lp)
    v2_value = _lp(signer)
    pair = (struct.pack("<Q", len(v2_value) + 4)
            + struct.pack("<I", V2_BLOCK_ID) + v2_value)
    total = 8 + len(pair) + 8 + 16
    block = (struct.pack("<Q", total - 8) + pair
             + struct.pack("<Q", total - 8) + MAGIC)
    assert len(block) == total
    return block, signed_data


def make_key_and_cert(cn):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=365 * 25))
            .sign(key, hashes.SHA256()))
    return key, cert.public_bytes(serialization.Encoding.DER)


# --------------------------------------------------------------------------- #
def sign(apk_bytes, key, cert_der):
    content, tail, cd_position = find_unsigned_parts(apk_bytes)

    # The digest is computed over the APK *as if* it had no signing block, so the
    # EOCD's central-directory-offset field must carry `cd_position` (where the
    # block will start).  Only the final file's real EOCD points past the block.
    digest = content_digest(content, tail, cd_position)

    # signature width is fixed for RSA-2048, so a dummy of the same length lets
    # us learn signed_data before the real signature exists
    dummy = key.sign(b"x", padding.PKCS1v15(), hashes.SHA256())
    _, signed_data = build_signing_block(key, cert_der, digest, dummy)
    signature = key.sign(signed_data, padding.PKCS1v15(), hashes.SHA256())
    block, signed_data2 = build_signing_block(key, cert_der, digest, signature)
    assert signed_data == signed_data2

    final_tail = bytearray(tail)
    struct.pack_into("<I", final_tail, final_tail.rfind(b"PK\x05\x06") + 16,
                     cd_position + len(block))
    return content + block + bytes(final_tail)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    cn = "RHK COMMUNITY"
    if "--cn" in sys.argv:
        cn = sys.argv[sys.argv.index("--cn") + 1]

    data = open(src, "rb").read()
    key, cert_der = make_key_and_cert(cn)
    out = sign(data, key, cert_der)
    open(dst, "wb").write(out)

    # ---- self-check -------------------------------------------------------
    content, tail, cd_position = find_unsigned_parts(out)
    digest = content_digest(content, tail, cd_position)
    print("[+] digest(verify) = %s" % digest.hex())
    eocd = out.rfind(b"PK\x05\x06")
    cd_off = struct.unpack_from("<I", out, eocd + 16)[0]
    size2 = struct.unpack_from("<Q", out, cd_off - 24)[0]
    assert cd_off - size2 - 8 == cd_position, "signing block offset mismatch"
    print("[+] wrote %s (%d bytes)" % (dst, len(out)))
    print("[+] v2 content digest: %s" % digest.hex())
    print("[+] cert sha256: %s" % hashlib.sha256(cert_der).hexdigest())
    z = zipfile.ZipFile(dst)
    print("[+] zip entries: %d, testzip: %s" % (len(z.namelist()), z.testzip()))


if __name__ == "__main__":
    main()
