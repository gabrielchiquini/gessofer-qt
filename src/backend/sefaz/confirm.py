import logging
from datetime import datetime, timezone, timedelta

from lxml import etree

from backend.certificate import get_certificate_pair
from backend.sefaz.config import WSDL_CONFIRM
from backend.sefaz.sign import sign_element
from backend.sefaz.util import CNPJ, NS, create_session


def confirm_nfe(
        nfe_key: str,
        tp_amb: int = 1,  # 1 = PROD
) -> str:
    """
    Replica a função sefazManifesta do NFePHP para o evento 210200 (Confirmação da Operação).
    Utiliza requests para comunicação SOAP direta e cryptography para assinatura.
    """
    certificate_pem, private_key_pem = get_certificate_pair()

    # 1. Validações básicas
    if not nfe_key or len(nfe_key) != 44:
        raise ValueError("Chave de acesso inválida. Deve ter 44 dígitos.")

    tp_evento = 210200
    n_seq_evento_str = str(1).zfill(2)
    id_evento = f"ID{tp_evento}{nfe_key}{n_seq_evento_str}"

    # Data do evento
    # Usar horário de Brasília
    now = datetime.now(timezone(timedelta(hours=-3)))
    dh_evento_str = now.strftime('%Y-%m-%dT%H:%M:%S-03:00')

    # Tentar obter CNPJ do Subject ou do SAN
    if not CNPJ:
        # Fallback: tentar CPF (11 digitos)
        # Ou usar um CNPJ padrão se não encontrado (depende da implementação)
        raise ValueError("Não foi possível extrair CNPJ/CPF do certificado.")

    # Criar elementos
    # noinspection PyAbstractClass
    evento_elem = etree.Element('evento', NS)
    evento_elem.set('versao', '1.00')  # Versão padrão para eventos recentes

    inf_evento = etree.SubElement(evento_elem, 'infEvento')
    inf_evento.set('Id', id_evento)

    c_orgao = "91"

    etree.SubElement(inf_evento, 'cOrgao').text = c_orgao
    etree.SubElement(inf_evento, 'tpAmb').text = str(tp_amb)

    # CNPJ ou CPF
    if len(CNPJ) == 14:
        etree.SubElement(inf_evento, 'CNPJ').text = CNPJ
    else:
        etree.SubElement(inf_evento, 'CPF').text = CNPJ

    etree.SubElement(inf_evento, 'chNFe').text = nfe_key
    etree.SubElement(inf_evento, 'dhEvento').text = dh_evento_str
    etree.SubElement(inf_evento, 'tpEvento').text = str(tp_evento)
    etree.SubElement(inf_evento, 'nSeqEvento').text = str(1)
    etree.SubElement(inf_evento, 'verEvento').text = '1.00'

    det_evento = etree.SubElement(inf_evento, 'detEvento')
    det_evento.set('versao', '1.00')
    etree.SubElement(det_evento, 'descEvento').text = 'Confirmacao da Operacao'

    ds = sign_element(certificate=certificate_pem,
                      private_key=private_key_pem,
                      reference_id=id_evento,
                      xml_element=evento_elem,
                      )

    # Inserir a assinatura no final do infEvento
    evento_elem = ds

    # 6. Montar o envelope envEvento
    lote = datetime.now().strftime('%Y%m%d%H%M%S') + str(hash(datetime.now().microsecond) % 10)

    # noinspection PyAbstractClass
    env_evento = etree.Element('envEvento', NS)
    env_evento.set('versao', '1.00')

    etree.SubElement(env_evento, 'idLote').text = lote
    env_evento.append(evento_elem)  # Adiciona o evento já assinado

    # Converter o envelope para string
    envelope_xml_str = etree.tostring(env_evento, encoding='unicode', xml_declaration=False)

    # 7. Comunicação SOAP via requests direto

    # Construir o envelope SOAP 1.1 manualmente
    soap_envelope = (
        '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">'
        '  <soap:Body>'
        '    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4">'
        f'       {envelope_xml_str}'
        '    </nfeDadosMsg>'
        '  </soap:Body>'
        '</soap:Envelope>'
    )

    # Configurar sessão com SSL para comunicação HTTPS com certificado digital
    session = create_session()

    # URL do serviço SOAP (stripar o ?WSDL)
    service_url = WSDL_CONFIRM.replace('?WSDL', '')

    headers = {
        'Content-Type': 'application/soap+xml;charset=utf-8;action="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4/nfeRecepcaoEvento"'
    }
    print(soap_envelope)
    response = session.post(service_url, data=soap_envelope, headers=headers, timeout=60)
    logging.info(f"Confirmação realizada status={response.status_code} response={response.text}")
    response_xml = etree.fromstring(response.content)

    # Namespace SOAP
    soap_ns = {'soap': 'http://www.w3.org/2003/05/soap-envelope'}
    body_elem = response_xml.find('soap:Body', soap_ns)
    if body_elem is None:
        raise ValueError("Resposta SOAP não contém um Body válido.")
    reasons = response_xml.findall('.//{*}xMotivo')
    reasons = list(map(lambda item: item.text, reasons))

    logging.info(f"Motivos retornados: {" | ".join(reasons)}")
    # Retornar o XML do body como string
    return etree.tostring(body_elem, encoding='unicode', xml_declaration=False)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        style='{',
        format='{asctime} | {levelname:<8} | {name:<12} | {message}'
    )
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True
    confirm_nfe("35260567647412000199550020004829291638420304", tp_amb=2)
