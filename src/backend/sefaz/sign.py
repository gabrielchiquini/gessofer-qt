from typing import Any
from xml.etree.ElementTree import Element

# noinspection PyProtectedMember
from lxml.etree import _Element
from signxml import XMLSigner, namespaces, CanonicalizationMethod
from signxml.algorithms import SignatureMethod, DigestAlgorithm


# 1. Bypass the deprecated methods check to allow SHA-1
class XMLSignerWithSHA1(XMLSigner):
    def check_deprecated_methods(self):
        # Overriding this passes the security error for SHA-1
        pass


def sign_element(certificate: bytes, private_key: bytes, reference_id: str, xml_element: Element[Any]) -> _Element:
    # 3. Load your XML data

    # 4. Configure the signer with RSA-SHA1 and SHA-1 algorithms
    signer = XMLSignerWithSHA1(
        signature_algorithm=SignatureMethod.RSA_SHA1,
        digest_algorithm=DigestAlgorithm.SHA1,
    )

    signer.namespaces = {None: namespaces.ds}
    signer.c14n_alg = CanonicalizationMethod.CANONICAL_XML_1_0

    # 5. Sign the XML document
    signed_root = signer.sign(xml_element, key=private_key, cert=certificate.decode("utf-8"),
                              reference_uri=reference_id)

    # 6. Output the signed XML string

    return signed_root
