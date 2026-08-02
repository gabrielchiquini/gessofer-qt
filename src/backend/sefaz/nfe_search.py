import base64
import gzip
import logging
from time import sleep

from lxml import etree

from backend.sefaz.config import URL_SEARCH
from backend.sefaz.confirm import confirm_nfe
from backend.sefaz.util import CNPJ, NSMAP, create_session

logger = logging.getLogger(__name__)

SOAP_ACTION_SEARCH: str = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse"

def _download_nfe_request(
        nfe_key: str,
        cnpj: str,
        tp_amb: int = 1,
        uf_autor_code: str = "52",
) -> bytes:
    """
    Realiza o download de uma NFe manifestada via webservice NfeDistribuicaoDFe.

    Args:
        nfe_key (str): Chave de acesso da NFe (44 dígitos).
        cnpj (str): CNPJ do interessado (14 dígitos, sem formatação).
        tp_amb (int): Tipo de Ambiente (1=Produção, 2=Homologação).
        uf_autor_code (str): Código da UF do emitente/autor

    Returns:
        bytes: XML descompactado da NFe.
    """
    if not nfe_key or len(nfe_key) != 44:
        raise ValueError("A chave da NFe deve ter exatamente 44 dígitos.")

    if not cnpj or len(cnpj) != 14:
        raise ValueError("O CNPJ deve ter exatamente 14 dígitos.")

    xml_request = f"""<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
        <tpAmb>{tp_amb}</tpAmb>
        <cUFAutor>{uf_autor_code}</cUFAutor>
        <CNPJ>{cnpj}</CNPJ>
        <consChNFe><chNFe>{nfe_key}</chNFe></consChNFe>
    </distDFeInt>"""

    soap_envelope: str = (
        '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">'
        f'<soap:Body>'
        f'<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">'
        f'{xml_request}'
        f'</nfeDadosMsg>'
        f'</soap:Body>'
        f'</soap:Envelope>'
    )

    session = create_session()

    headers: dict[str, str] = {
        "Content-Type": f"application/soap+xml;charset=utf-8;action=\"{SOAP_ACTION_SEARCH}\"",
    }

    response = session.post(
        URL_SEARCH,
        data=soap_envelope,
        headers=headers,
        timeout=60,
    )
    response.raise_for_status()
    return response.content

def _download_nfe(nfe_key: str) -> bytes:
    response = _download_nfe_request(
        nfe_key=nfe_key,
        cnpj=CNPJ,
    )
    response_xml = etree.fromstring(response)

    doc_zip_elem = response_xml.find(".//nfe:docZip", namespaces=NSMAP)
    if doc_zip_elem is not None:
        compressed = doc_zip_elem.text
        decompressed = gzip.decompress(base64.b64decode(compressed))
        return decompressed
    else:
        error_element = response_xml.find(".//nfe:xMotivo", namespaces=NSMAP)
        if error_element is None:
            raise Exception(f"Error searching NFe: unknown")
        error_element_text = error_element.text
        logger.warning("Erro ao consultar NFe: %s", error_element_text)
        raise Exception(f"Error searching NFe: {error_element_text}")


def search_nfe(nfe_key: str):
    response = _download_nfe(nfe_key).decode("utf-8")
    logger.info(f"First search response: {response}")
    if _is_nfe(response):
        return response
    else:
        reasons = confirm_nfe(nfe_key)
        sleep(1)
        response = _download_nfe(nfe_key).decode("utf-8")
        if _is_nfe(response):
            return response
        logger.info(f"Second search response: {response}")
        raise Exception(f"Erro NFe: {reasons}")


def _is_nfe(response: str) -> bool:
    return response.startswith("<nfeProc")
