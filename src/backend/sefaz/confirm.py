import base64
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from xml import etree
from xml.dom.minidom import parseString
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import load_pem_x509_certificate, Certificate
from zeep import Client

from backend.certificate import get_certificate_pair
from backend.sefaz.config import WSDL_CONFIRM
from backend.sefaz.util import CNPJ, NS, create_transport


def sefaz_manifesta_python(
        nfe_key: str,
        tp_amb: int = 1, # 1 = PROD
        x_just: str = '',
        n_seq_evento: int = 1,
        dh_evento: Optional[datetime] = None,
        lote: Optional[str] = None,
) -> str:
    """
    Replica a função sefazManifesta do NFePHP para o evento 210200 (Confirmação da Operação).
    Utiliza zeep para comunicação SOAP e cryptography para assinatura.
    """
    url_portal: str = 'http://www.portalfiscal.inf.br/nfe'
    certificate_pem, private_key_pem = get_certificate_pair()

    # 1. Validações básicas
    if not nfe_key or len(nfe_key) != 44:
        raise ValueError("Chave de acesso inválida. Deve ter 44 dígitos.")
    uf_code = "AN"

    tp_evento = 210200
    n_seq_evento_str = str(n_seq_evento).zfill(2)
    id_evento = f"ID{tp_evento}{nfe_key}{n_seq_evento_str}"

    # Data do evento
    if dh_evento is None:
        # Usar horário de Brasília
        now = datetime.now(timezone(timedelta(hours=-3)))
        dh_evento_str = now.strftime('%Y-%m-%dT%H:%M:%S-03:00')
    else:
        # Formatar datetime para ISO 8601 com offset
        dh_evento_str = dh_evento.strftime('%Y-%m-%dT%H:%M:%S') + (
            f"-03:00" if dh_evento.tzinfo is None else dh_evento.strftime('%z')[:3] + ':' + dh_evento.strftime('%z')[3:]
        )

    # Justificativa (apenas para EVT_NAO_REALIZADA, mas mantemos a estrutura)
    x_just_clean = x_just.strip()[:255] if x_just else ''

    # 4. Montar XML do Evento (infEvento)
    # Estrutura básica conforme NT 2024.002
    # Nota: O CNPJ/CPF será preenchido pelo certificado. Para assinatura, precisamos extrair o CNPJ.

    # Extrair CNPJ do certificado
    certificate = load_pem_x509_certificate(certificate_pem, default_backend())
    private_key: RSAPrivateKey = load_pem_private_key(private_key_pem, None)  # type: ignore[union-attr]
    # Tentar obter CNPJ do Subject ou do SAN
    if not CNPJ:
        # Fallback: tentar CPF (11 digitos)
        # Ou usar um CNPJ padrão se não encontrado (depende da implementação)
        raise ValueError("Não foi possível extrair CNPJ/CPF do certificado.")

    # Criar elementos
    evento_elem = ElementTree.Element('evento', NS)
    evento_elem.set('versao', '1.00')  # Versão padrão para eventos recentes

    inf_evento = ElementTree.SubElement(evento_elem, 'infEvento')
    inf_evento.set('Id', id_evento)

    c_orgao = "91" 

    ElementTree.SubElement(inf_evento, 'cOrgao').text = c_orgao
    ElementTree.SubElement(inf_evento, 'tpAmb').text = str(tp_amb)

    # CNPJ ou CPF
    if len(CNPJ) == 14:
        ElementTree.SubElement(inf_evento, 'CNPJ').text = CNPJ
    else:
        ElementTree.SubElement(inf_evento, 'CPF').text = CNPJ

    ElementTree.SubElement(inf_evento, 'chNFe').text = nfe_key
    ElementTree.SubElement(inf_evento, 'dhEvento').text = dh_evento_str
    ElementTree.SubElement(inf_evento, 'tpEvento').text = str(tp_evento)
    ElementTree.SubElement(inf_evento, 'nSeqEvento').text = str(n_seq_evento)
    ElementTree.SubElement(inf_evento, 'verEvento').text = '1.00'

    det_evento = ElementTree.SubElement(inf_evento, 'detEvento')
    det_evento.set('versao', '1.00')
    ElementTree.SubElement(det_evento, 'descEvento').text = 'Confirmacao da Operacao'

    # tagAdic vazio para Confirmacao
    # ET.SubElement(det_evento, 'xCondUso').text = '...' # Opcional, mas recomendado pela NT

    ds = signature(certificate=certificate,
                   private_key=private_key,
                   certificate_bytes=certificate_pem,
                   id_evento=id_evento,
                   inf_evento=inf_evento)

    # Inserir a assinatura no final do infEvento
    evento_elem.append(ds)

    # 6. Montar o envelope envEvento
    if lote is None:
        lote = datetime.now().strftime('%Y%m%d%H%M%S') + str(hash(datetime.now().microsecond) % 10)

    env_evento = ElementTree.Element('envEvento', NS)
    env_evento.set('versao', '1.00')

    ElementTree.SubElement(env_evento, 'idLote').text = lote
    env_evento.append(evento_elem)  # Adiciona o evento já assinado

    # Converter o envelope para string
    envelope_xml_str = ElementTree.tostring(env_evento, encoding='unicode', xml_declaration=True)

    # 7. Comunicação SOAP via Zeep

    # Criar cliente Zeep
    # O cabeçalho SOAP é necessário para NFe
    # Exemplo de cabeçalho para SP
    header = {
        'nfeCabecMsg': {
            'cUF': uf_code,
            'versaoDados': '1.00'
        }
    }

    # Usar WSSE Signature para passar o certificado no SOAP (opcional, mas comum)
    # Ou passar o certificado no cabeçalho se o webservice suportar.
    # Para simplificar, vamos usar o cliente zeep padrão e passar o XML bruto no body se necessário,
    # ou usar o método "soap_env" se o webservice exigir.

    # Nota: Muitos webservers de NFe exigem que o corpo da mensagem seja exatamente o XML gerado.
    # Zeep serializa objetos Python. Vamos usar o recurso de "raw" ou construir o body manualmente.

    transport = create_transport()
    client = Client(wsdl=WSDL_CONFIRM, transport=transport)

    # Preparar o body da mensagem
    # O webservice espera um nó <nfeDadosMsg> que contém o XML do envEvento
    # nfe_dados_msg = ElementTree.Element('nfeDadosMsg', nsmap=NS)
    # Adicionar o XML do envEvento como texto dentro de nfeDadosMsg
    # Para evitar escape de caracteres HTML, usamos ET.SubElement com texto
    # Ou melhor, adicionamos os elementos filhos de envEvento diretamente
    # for child in env_evento:
    #     nfe_dados_msg.append(child)

    # Tenta chamar o serviço
    try:
        # Passa o XML como string no corpo
        # Alguns wsds esperam um objeto, outros esperam string.
        # Vamos tentar passar a string diretamente no argumento nfeDadosMsg
        print(etree.ElementTree.tostring(env_evento))
        response = client.service.nfeRecepcaoEventoNF(
            nfeDadosMsg=env_evento,
            # nfeCabecMsg={'cUF': uf_code, 'versaoDados': '1.00'}
        )
    except Exception as e:
        # Se falhar, tenta outra abordagem
        raise e

    # A resposta é um XML string
    return response


def signature(certificate: Certificate, private_key: RSAPrivateKey, certificate_bytes: bytes, id_evento: str,
              inf_evento: Element[str]) -> Any:
    # 5. Assinar o XML
    # A assinatura deve cobrir apenas o infEvento
    # Usamos a biblioteca cryptography para gerar a assinatura XML-Detached

    # Converter o infEvento para string para assinar
    # Importante: A assinatura XML requer a string serializada sem indentação excessiva ou com indentação controlada
    # O NFePHP usa canonicalização C14N. Vamos usar a canonicalização padrão do ElementTree ou minidom.

    inf_evento_str = ElementTree.tostring(inf_evento, encoding='unicode')
    # Assinar
    signature_value = private_key.sign(
        inf_evento_str.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    signature_b64 = base64.b64encode(signature_value).decode('utf-8')

    # Adicionar a assinatura ao XML
    # Estrutura da assinatura XML
    ds = ElementTree.Element('Signature', {'xmlns': 'http://www.w3.org/2000/09/xmldsig#'})
    signed_info = ElementTree.SubElement(ds, 'SignedInfo')

    # CanonicalizationMethod
    canon_method = ElementTree.SubElement(signed_info, 'CanonicalizationMethod')
    canon_method.set('Algorithm', 'http://www.w3.org/2001/10/xml-exc-c14n#')

    # SignatureMethod
    sig_method = ElementTree.SubElement(signed_info, 'SignatureMethod')
    sig_method.set('Algorithm', 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256')

    # Reference
    ref = ElementTree.SubElement(signed_info, 'Reference', URI=f"#{id_evento}")
    transforms = ElementTree.SubElement(ref, 'Transforms')

    # Enveloped Signature Transform
    transform = ElementTree.SubElement(transforms, 'Transform')
    transform.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#enveloped-signature')

    # Exc Canonicalization
    exc_canon = ElementTree.SubElement(transforms, 'Transform')
    exc_canon.set('Algorithm', 'http://www.w3.org/2001/10/xml-exc-c14n#')

    # DigestMethod
    digest_method = ElementTree.SubElement(ref, 'DigestMethod')
    digest_method.set('Algorithm', 'http://www.w3.org/2001/04/xmlenc#sha256')

    # DigestValue
    # Calcular o digest do infEvento CANONICALIZADO
    # Precisamos canonicalizar o inf_evento_str
    # Uma forma simples é usar minidom para canonicalizar
    dom = parseString(inf_evento_str)
    canonicalized_xml = dom.toxml()

    digest = hashlib.sha256(canonicalized_xml.encode('utf-8')).digest()
    digest_b64 = base64.b64encode(digest).decode('utf-8')

    ElementTree.SubElement(ref, 'DigestValue').text = digest_b64

    # SignatureValue
    ElementTree.SubElement(ds, 'SignatureValue').text = signature_b64

    # KeyInfo
    key_info = ElementTree.SubElement(ds, 'KeyInfo')
    x509_data = ElementTree.SubElement(key_info, 'X509Data')
    x509_cert = ElementTree.SubElement(x509_data, 'X509Certificate')
    certificate_text = (certificate_bytes.decode('utf-8')
                        .replace('-----BEGIN CERTIFICATE-----', '')
                        .replace('-----END CERTIFICATE-----', '')
                        .replace('\n', '')
                        .replace('\r', ''))
    x509_cert.text = certificate_text
    return ds


# Funções auxiliares

def get_uf_by_code(code: int) -> str:
    ufs = {
        11: 'RO', 12: 'AC', 13: 'AM', 14: 'RR', 15: 'PA', 16: 'AP', 17: 'TO',
        21: 'MA', 22: 'PI', 23: 'CE', 24: 'RN', 25: 'PB', 26: 'PE', 27: 'AL',
        28: 'SE', 29: 'BA', 31: 'MG', 32: 'ES', 33: 'RJ', 35: 'SP', 41: 'PR',
        42: 'SC', 43: 'RS', 50: 'MS', 51: 'MT', 52: 'GO', 53: 'DF'
    }
    return ufs.get(code, 'SP')  # Default SP se não encontrado


if __name__ == '__main__':
    sefaz_manifesta_python("35260567647412000199550020004829291638420304", tp_amb=2)
