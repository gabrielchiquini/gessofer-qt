import ssl

import requests

from backend.certificate.read_pem import get_certificate_files

CNPJ = "10245625000177"
NS = {"xmlns": "http://www.portalfiscal.inf.br/nfe"}
NSMAP = {"nfe": "http://www.portalfiscal.inf.br/nfe"}


def create_ssl_context() -> ssl.SSLContext:
    # 1. Read the binary PFX data
    certificate, private_key = get_certificate_files()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_cert_chain(certfile=certificate, keyfile=private_key)
    return context


def create_session() -> requests.Session:
    ssl_context = create_ssl_context()
    session = requests.Session()
    session.ssl_context = ssl_context
    certificate, key = get_certificate_files()
    session.cert = (str(certificate), str(key))
    return session
