import base64
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from xml.dom.minidom import parseString
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.bindings._rust.x509 import Certificate
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import load_pem_x509_certificate
from zeep import Client
from zeep.transports import Transport

from backend.sefaz.util import CNPJ, NS


def sefaz_manifesta_python(
        nfe_key: str,
        certificate_pem: str,
        private_key_pem: str,
        tp_amb: int = 1,  # 1 = Homologação, 2 = Produção
        x_just: str = '',
        n_seq_evento: int = 1,
        dh_evento: Optional[datetime] = None,
        lote: Optional[str] = None,
        url_portal: str = 'http://www.portalfiscal.inf.br/nfe'
) -> str:
    """
    Replica a função sefazManifesta do NFePHP para o evento 210200 (Confirmação da Operação).
    Utiliza zeep para comunicação SOAP e cryptography para assinatura.
    """

    # 1. Validações básicas
    if not nfe_key or len(nfe_key) != 44:
        raise ValueError("Chave de acesso inválida. Deve ter 44 dígitos.")

    # 2. Determinar UF e URL do WebService
    # A UF é extraída dos dois primeiros dígitos da chave
    uf_code = int(nfe_key[:2])

    # Mapeamento simples de UF para sigla (pode ser expandido conforme necessário)
    # Nota: Em um sistema real, use uma lista completa de UFs.
    # Aqui assumimos que a UF da chave define o destino.
    # Para 210200, o evento é enviado para a UF do Emitente (que é a UF da chave).
    # A biblioteca NFePHP usa 'AN' (Nacional) para manifestação, mas a validação da chave define a UF no evento.
    # No entanto, o webservice de RecepcaoEvento pode variar.
    # Para simplificar e seguir o padrão NFePHP, usamos a UF extraída da chave para o webservice,
    # a menos que seja um evento específico da AN.
    # A função sefazManifesta no PHP chama sefazEvento('AN', ...), mas sefazEvento ajusta a UF para o webservice.
    # Vamos usar a UF da chave para buscar a URL do webservice.

    sigla_uf = "52"  # GO

    # URL base do webservice (Exemplo para SP, ajustar conforme UF)
    # Em produção, isso deve vir de um arquivo de configuração ou webservice de distribuição
    url_ws = "https://www.nfe.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx"

    # 3. Preparar dados do Evento
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
    certificate = load_pem_x509_certificate(certificate_pem.encode('utf-8'), default_backend())
    private_key = load_pem_private_key(private_key_pem.encode('utf-8'), default_backend())
    # Tentar obter CNPJ do Subject ou do SAN
    if not CNPJ:
        # Fallback: tentar CPF (11 digitos)
        # Ou usar um CNPJ padrão se não encontrado (depende da implementação)
        raise ValueError("Não foi possível extrair CNPJ/CPF do certificado.")

    # Criar elementos
    evento_elem = ElementTree.Element('evento', nsmap=NS)
    evento_elem.set('versao', '3.10')  # Versão padrão para eventos recentes

    inf_evento = ElementTree.SubElement(evento_elem, 'infEvento')
    inf_evento.set('Id', id_evento)

    # cOrgao: Código do órgão processador. Para a maioria das UFs, é o código da UF.
    # Para alguns eventos específicos pode ser 92 (SVRS). Para 210200, usa-se o código da UF.
    c_orgao = str(uf_code)

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
    ElementTree.SubElement(inf_evento, 'verEvento').text = '3.10'

    det_evento = ElementTree.SubElement(inf_evento, 'detEvento')
    det_evento.set('versao', '3.10')
    ElementTree.SubElement(det_evento, 'descEvento').text = 'Confirmacao da Operacao'

    # tagAdic vazio para Confirmacao
    # ET.SubElement(det_evento, 'xCondUso').text = '...' # Opcional, mas recomendado pela NT

    ds = signature(certificate, private_key, id_evento, inf_evento)

    # Inserir a assinatura no final do infEvento
    inf_evento.append(ds)

    # 6. Montar o envelope envEvento
    if lote is None:
        lote = datetime.now().strftime('%Y%m%d%H%M%S') + str(hash(datetime.now().microsecond) % 10)

    env_evento = ElementTree.Element('envEvento', nsmap=NS)
    env_evento.set('versao', '3.10')

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
            'versaoDados': '3.10'
        }
    }

    # Usar WSSE Signature para passar o certificado no SOAP (opcional, mas comum)
    # Ou passar o certificado no cabeçalho se o webservice suportar.
    # Para simplificar, vamos usar o cliente zeep padrão e passar o XML bruto no body se necessário,
    # ou usar o método "soap_env" se o webservice exigir.

    # Nota: Muitos webservers de NFe exigem que o corpo da mensagem seja exatamente o XML gerado.
    # Zeep serializa objetos Python. Vamos usar o recurso de "raw" ou construir o body manualmente.

    transport = Transport()
    client = Client(wsdl=f"{url_ws}?wsdl", transport=transport)

    # Preparar o body da mensagem
    # O webservice espera um nó <nfeDadosMsg> que contém o XML do envEvento
    nfe_dados_msg = ElementTree.Element('nfeDadosMsg', nsmap={'nfe': url_portal})
    # Adicionar o XML do envEvento como texto dentro de nfeDadosMsg
    # Para evitar escape de caracteres HTML, usamos ET.SubElement com texto
    # Ou melhor, adicionamos os elementos filhos de envEvento diretamente
    for child in env_evento:
        nfe_dados_msg.append(child)

    nfe_dados_msg_str = ElementTree.tostring(nfe_dados_msg, encoding='unicode')

    # Chamar o serviço
    # O nome do método SOAP geralmente é 'NfeRecepcaoEvento' ou 'recepcaoEvento'
    # Vamos tentar pegar o nome do primeiro método disponível
    service_name = client.wsdl.services[client.wsdl.services.keys()[0]].ports[0].binding.name
    port_name = client.wsdl.services[client.wsdl.services.keys()[0]].ports[0].name

    # Tenta chamar o serviço
    try:
        # Passa o XML como string no corpo
        # Alguns wsds esperam um objeto, outros esperam string.
        # Vamos tentar passar a string diretamente no argumento nfeDadosMsg
        response = client.service.NfeRecepcaoEvento(
            nfeDadosMsg=nfe_dados_msg_str,
            nfeCabecMsg={'cUF': uf_code, 'versaoDados': '3.10'}
        )
    except Exception as e:
        # Se falhar, tenta outra abordagem
        raise e

    # A resposta é um XML string
    return response


def signature(cert: Certificate, private_key: RSAPrivateKey, id_evento: str, inf_evento: Element[str]) -> Any:
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
        hashes.SHA1()
    )

    signature_b64 = base64.b64encode(signature_value).decode('utf-8')

    # Adicionar a assinatura ao XML
    # Estrutura da assinatura XML
    ds = ElementTree.Element('ds:Signature', nsmap={'ds': 'http://www.w3.org/2000/09/xmldsig#'})
    signed_info = ElementTree.SubElement(ds, 'ds:SignedInfo')

    # CanonicalizationMethod
    canon_method = ElementTree.SubElement(signed_info, 'ds:CanonicalizationMethod')
    canon_method.set('Algorithm', 'http://www.w3.org/2001/10/xml-exc-c14n#')

    # SignatureMethod
    sig_method = ElementTree.SubElement(signed_info, 'ds:SignatureMethod')
    sig_method.set('Algorithm', 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256')

    # Reference
    ref = ElementTree.SubElement(signed_info, 'ds:Reference', URI=f"#{id_evento}")
    transforms = ElementTree.SubElement(ref, 'ds:Transforms')

    # Enveloped Signature Transform
    transform = ElementTree.SubElement(transforms, 'ds:Transform')
    transform.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#enveloped-signature')

    # Exc Canonicalization
    exc_canon = ElementTree.SubElement(transforms, 'ds:Transform')
    exc_canon.set('Algorithm', 'http://www.w3.org/2001/10/xml-exc-c14n#')

    # DigestMethod
    digest_method = ElementTree.SubElement(ref, 'ds:DigestMethod')
    digest_method.set('Algorithm', 'http://www.w3.org/2001/04/xmlenc#sha256')

    # DigestValue
    # Calcular o digest do infEvento CANONICALIZADO
    # Precisamos canonicalizar o inf_evento_str
    # Uma forma simples é usar minidom para canonicalizar
    dom = parseString(inf_evento_str)
    canonicalized_xml = dom.toxml()

    digest = hashlib.sha256(canonicalized_xml.encode('utf-8')).digest()
    digest_b64 = base64.b64encode(digest).decode('utf-8')

    ElementTree.SubElement(ref, 'ds:DigestValue').text = digest_b64

    # SignatureValue
    ElementTree.SubElement(ds, 'ds:SignatureValue').text = signature_b64

    # KeyInfo
    key_info = ElementTree.SubElement(ds, 'ds:KeyInfo')
    x509_data = ElementTree.SubElement(key_info, 'ds:X509Data')
    x509_cert = ElementTree.SubElement(x509_data, 'ds:X509Certificate')
    x509_cert.text = base64.b64encode(cert.public_bytes(serialization.Encoding.PEM)).decode('utf-8').replace(
        '-----BEGIN CERTIFICATE-----', '').replace('-----END CERTIFICATE-----', '').replace('\n', '')
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
