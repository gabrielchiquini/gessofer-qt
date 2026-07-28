import logging
import ssl
import tempfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree
from lxml.etree import Element
from requests import Session
from requests.sessions import HTTPAdapter
from zeep import Client
from zeep.transports import Transport


def download_nfe(
        nfe_key: str,
        cnpj: str,
        tp_amb: int = 1,
        uf_autor_code: str = "52",  # Exemplo padrão, ajuste conforme necessário
) -> Element:
    """
    Realiza o download de uma NFe manifestada via webservice NfeDistribuicaoDFe.

    Args:
        nfe_key (str): Chave de acesso da NFe (44 dígitos).
        cnpj (str): CNPJ do interessado (14 dígitos, sem formatação).
        tp_amb (int): Tipo de Ambiente (1=Produção, 2=Homologação).
        uf_autor_code (str): Código da UF do emitente/autor
        url_wsdl (str, optional): URL do WSDL do serviço de distribuição.
                                  Se None, usa a URL padrão da SEFAZ Nacional (AN).

    Returns:
        str: Resposta XML do webservice.
    """

    # Validação básica da chave
    if not nfe_key or len(nfe_key) != 44:
        raise ValueError("A chave da NFe deve ter exatamente 44 dígitos.")

    if not cnpj or len(cnpj) != 14:
        raise ValueError("O CNPJ deve ter exatamente 14 dígitos.")

    url_wsdl = "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NfeDistribuicaoDFe.asmx?WSDL"

    transport = create_transport()

    client = Client(wsdl=url_wsdl, transport=transport)

    xml_request = f"""<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
        <tpAmb>{tp_amb}</tpAmb>
        <cUFAutor>{uf_autor_code}</cUFAutor>
        <CNPJ>{cnpj}</CNPJ>
        <consChNFe><chNFe>{nfe_key}</chNFe></consChNFe>
    </distDFeInt>"""
    xml_element = etree.fromstring(xml_request)

    # soap_body_content = f'<nfeDistDFeInteresse xmlns="https://www.portalfiscal.inf.br/nfe">{xml_request}</nfeDistDFeInteresse>'

    result = client.service.nfeDistDFeInteresse(nfeDadosMsg=xml_element)

    return result


def create_transport():
    # 1. Configurar o contexto SSL com o certificado PFX
    try:
        # carrega o certificado pfx
        # password pode ser string ou bytes
        ssl_context = create_ssl_context_from_pfx(r"C:\Users\gabri\workpace\gessofer-rs\gessofer-qt\cert.pfx",
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


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        style='{',
        format='{asctime} | {levelname:<8} | {name:<12} | {message}'
    )
    logger = logging.getLogger('zeep.transports')
    logger.setLevel(logging.DEBUG)
    response = download_nfe(
        nfe_key="35260567647412000199550020004829291638420304",
        cnpj="10245625000177",
    )

    print(response)

# <retDistDFeInt xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.portalfiscal.inf.br/nfe" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" versao="1.01"><tpAmb>1</tpAmb><verAplic>1.7.8</verAplic><cStat>138</cStat><xMotivo>Documento localizado</xMotivo><dhResp>2026-07-28T19:22:01-03:00</dhResp><loteDistDFeInt><docZip schema="resNFe_v1.01.xsd">H4sIAAAAAAAEAIVS226CQBD9FcO77MyyXDNuYry2UbRqL+kbAgqtggUqfn5XsW3sS19mZ8+ey2SyVMSlP4xbp/0uK71TGXW0pKoOHmN1Xeu1oefFlnEAZC/TyTJM4n2g/ZDT/8ntNCurIAtjrXWMizLIOxrqgFePG/0hL6pgt0nLMNjpabbR1wXLNrEmKUzUiNIwuQWmZVvCFqhSAF3XNAHOrXC4y120DEdwMEAQazTU8+f38lZD7ALSyc/3sez6vdmi2xotZo/z1mTV7xJrHuhuIG0UgMraRnSIKYCiZLBPJQdutcFso7tCx0PXA2iDoSqxhkDVwR9KJHY56aiK5QjUTQWdLxSl26dgJ/N1kEdi8v7QE6+jJPkcv0Xj5/6H6/jTjvJqSCp0EYfrKv+Ty8Hj4jf3yqFsXuSVxPO60DVsg4Nt2sQamMJlWp03owb5bok1n0B+AQupGY8NAgAA</docZip></loteDistDFeInt></retDistDFeInt>
