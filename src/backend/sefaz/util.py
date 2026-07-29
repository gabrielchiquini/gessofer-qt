import ssl
import tempfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from requests import Session
from requests.adapters import HTTPAdapter
from zeep import Transport


CNPJ = "10245625000177"
NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

def create_ssl_context_from_pfx(pfx_path: str, pfx_password: str):
    # 1. Read the binary PFX data
    with open(pfx_path, "rb") as f:
        pfx_data = f.read()

    # 2. Parse the PFX file safely using cryptography
    # Pass password as bytes (or None if no password)
    password_bytes = pfx_password.encode() if pfx_password else None
    private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
        pfx_data, password_bytes
    )

    # 3. Serialize key and certificate into PEM byte arrays
    pem_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    pem_cert = certificate.public_bytes(
        encoding=serialization.Encoding.PEM
    )

    # 4. Create standard SSL Context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    # 5. Write to temporary files so ssl_context can read them
    with tempfile.NamedTemporaryFile(delete=False) as key_file, \
            tempfile.NamedTemporaryFile(delete=False) as cert_file:
        key_file.write(pem_key)
        cert_file.write(pem_cert)

        # Flush the buffers to ensure data is written to disk
        key_file.flush()
        cert_file.flush()

        # Load the files into the context
        context.load_cert_chain(certfile=cert_file.name, keyfile=key_file.name)
        return context


def create_transport():
    # 1. Configurar o contexto SSL com o certificado PFX
    try:
        # carrega o certificado pfx
        # password pode ser string ou bytes
        ssl_context = create_ssl_context_from_pfx(r"/tests/util/cert.pfx",
                                                  "MwMU3vyBnc")
    except Exception as e:
        raise ValueError(f"Erro ao carregar certificado PFX: {e}")

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
