import base64
import gzip
import logging

from lxml import etree
from lxml.etree import ElementBase
from zeep import Client

from backend.sefaz.util import create_transport, CNPJ


def _download_nfe_request(
        nfe_key: str,
        cnpj: str,
        tp_amb: int = 1,
        uf_autor_code: str = "52",  # Exemplo padrão, ajuste conforme necessário
) -> ElementBase:
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

    result = client.service.nfeDistDFeInteresse(nfeDadosMsg=xml_element)

    return result


def _download_nfe(nfe_key: str) -> bytes:
    logging.basicConfig(
        level=logging.DEBUG,
        style='{',
        format='{asctime} | {levelname:<8} | {name:<12} | {message}'
    )
    logger = logging.getLogger('zeep.transports')
    logger.setLevel(logging.DEBUG)
    response = _download_nfe_request(
        nfe_key=nfe_key,
        cnpj=CNPJ,
    )

    doc_zip_elem = response.find(".//nfe:docZip", namespaces=NS)
    if doc_zip_elem is not None:
        compressed = doc_zip_elem.text
        decompressed = gzip.decompress(base64.b64decode(compressed))
        return decompressed
    else:
        error_element = response.find(".//nfe:xMotivo", namespaces=NS)
        error_element_text = error_element.text
        print(error_element_text)
        raise Exception(f"Error searching NFe: {error_element_text}")


def search_nfe(nfe_key: str):
    response = _download_nfe(nfe_key)
    if response.startswith(b"<nfeProc"):
        return response.decode("utf-8")
    else:

        confirm_nfe(nfe_key)

# <retDistDFeInt xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.portalfiscal.inf.br/nfe" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" versao="1.01"><tpAmb>1</tpAmb><verAplic>1.7.8</verAplic><cStat>138</cStat><xMotivo>Documento localizado</xMotivo><dhResp>2026-07-28T19:22:01-03:00</dhResp><loteDistDFeInt><docZip schema="resNFe_v1.01.xsd">H4sIAAAAAAAEAIVS226CQBD9FcO77MyyXDNuYry2UbRqL+kbAgqtggUqfn5XsW3sS19mZ8+ey2SyVMSlP4xbp/0uK71TGXW0pKoOHmN1Xeu1oefFlnEAZC/TyTJM4n2g/ZDT/8ntNCurIAtjrXWMizLIOxrqgFePG/0hL6pgt0nLMNjpabbR1wXLNrEmKUzUiNIwuQWmZVvCFqhSAF3XNAHOrXC4y120DEdwMEAQazTU8+f38lZD7ALSyc/3sez6vdmi2xotZo/z1mTV7xJrHuhuIG0UgMraRnSIKYCiZLBPJQdutcFso7tCx0PXA2iDoSqxhkDVwR9KJHY56aiK5QjUTQWdLxSl26dgJ/N1kEdi8v7QE6+jJPkcv0Xj5/6H6/jTjvJqSCp0EYfrKv+Ty8Hj4jf3yqFsXuSVxPO60DVsg4Nt2sQamMJlWp03owb5bok1n0B+AQupGY8NAgAA</docZip></loteDistDFeInt></retDistDFeInt>
# _download_nfe("35260567647412000199550020004829291638420304")
