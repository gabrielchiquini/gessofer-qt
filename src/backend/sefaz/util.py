import ssl

import requests
from requests import Session
from requests.adapters import HTTPAdapter
from zeep import Transport

from backend.certificate.read_pem import get_certificate_files

CNPJ = "10245625000177"
NS = {"xmlns": "http://www.portalfiscal.inf.br/nfe"}


def create_ssl_context():
    # 1. Read the binary PFX data
    certificate, private_key = get_certificate_files()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_cert_chain(certfile=certificate, keyfile=private_key)
    return context


def create_transport():
    # 1. Configurar o contexto SSL com o certificado PFX
    try:
        # carrega o certificado pfx
        # password pode ser string ou bytes
        ssl_context = create_ssl_context()
        # 2. Criar a sessão e configurar o adapter com o contexto SSL
        session = Session()
        session.ssl_context = ssl_context
        adapter = HTTPAdapter()
        adapter.init_poolmanager(
            connections=10,
            maxsize=10,
            block=False,
            ssl_context=ssl_context
        )
        session.mount('https://', adapter)

        # 3. Criar o transporte e o cliente
        return Transport(session=session)
    except Exception as e:
        raise ValueError(f"Erro ao carregar certificado PFX: {e}")

def create_session():
    ssl_context = create_ssl_context()
    session = requests.Session()
    session.ssl_context = ssl_context
    certificate, key = get_certificate_files()
    session.cert = (str(certificate), str(key))
    return session
