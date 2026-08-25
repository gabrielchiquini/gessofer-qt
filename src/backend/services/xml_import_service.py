from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from xml.etree import ElementTree as ET

from backend.errors import XmlParseError
from models.order import Order
from models.output import Product

logger = logging.getLogger(__name__)

# NFe XML namespace
NFE_NS = "http://www.portalfiscal.inf.br/nfe"


@dataclass
class XmlImportResult:
    """Result of an XML import operation."""
    orders: List[Order]
    warnings: List[str]


class XmlImportService:
    """
    Parses NFe (Nota Fiscal Eletrônica) XML files and extracts order + product data.

    Extracts:
    - Order-level: nfeKey, supplier, date
    - Product-level: name, quantity, price (adjusted for IPI/ICMS-ST), total

    Per docs §3.2.5:
    - vIPI and vICMS-ST are added to the base price.
    - If quantity is non-integer, a warning is generated and quantity is set to 0.
    - Warnings are space-separated strings.
    """

    def parse_file(self, file_path: str) -> XmlImportResult:
        """
        Parse a single NFe XML file.

        Args:
            file_path: Path to the XML file.

        Returns:
            XmlImportResult with parsed orders and warnings.

        Raises:
            XmlParseError: If the XML cannot be parsed or is not a valid NFe.
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except ET.ParseError as exc:
            raise XmlParseError(f"Erro de parsing XML: {exc}") from exc
        except FileNotFoundError as exc:
            raise XmlParseError(f"Arquivo não encontrado: {file_path}") from exc

        return self._parse_nfe_root(root)

    def parse_string(self, xml_content: str) -> XmlImportResult:
        """
        Parse NFe XML content from a string.

        Args:
            xml_content: XML string content.

        Returns:
            XmlImportResult with parsed orders and warnings.

        Raises:
            XmlParseError: If the XML cannot be parsed or is not a valid NFe.
        """
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as exc:
            raise XmlParseError(f"Erro de parsing XML: {exc}") from exc

        return self._parse_nfe_root(root)

    def _parse_nfe_root(self, root: ET.Element) -> XmlImportResult:
        """Parse the root element of an NFe XML document."""
        warnings: list[str] = []

        # Find the NFe element (may be nested under infNFe, nFe, etc.)
        nfe = self._find_nfe_element(root)
        if nfe is None:
            raise XmlParseError("Documento não é uma NFe válida.")

        # Extract order-level data
        nfe_key = self._extract_text(nfe, "chNFe") or ""
        if not nfe_key:
            # Fallback: extract from infNFe Id attribute (format: "NFe{44 digits}")
            inf_nfe = nfe.find(f".//{{{NFE_NS}}}infNFe")
            if inf_nfe is not None:
                id_attr = inf_nfe.get("Id", "")
                if id_attr.startswith("NFe"):
                    nfe_key = id_attr[3:]  # Remove "NFe" prefix
        supplier = self._extract_emit_name(nfe) or ""
        date_raw = self._extract_text(nfe, "dhEmi") or ""
        date_iso = self._extract_date(date_raw)

        # Extract products
        products = self._extract_products(nfe, warnings)

        # Create a single order from the NFe
        order_id = str(uuid.uuid4())
        order = Order(
            id=order_id,
            date=date_iso,
            supplier=supplier,
            nfe_key=nfe_key,
            freight=0,
            unloading=0,
            products=products,
        )

        return XmlImportResult(orders=[order], warnings=warnings)

    def parse_multiple_files(self, file_paths: List[str]) -> XmlImportResult:
        """
        Parse multiple NFe XML files and combine results into a single list of orders.

        Args:
            file_paths: List of file paths to parse.

        Returns:
            XmlImportResult with all parsed orders and combined warnings.
        """
        all_orders: list[Order] = []
        all_warnings: list[str] = []

        for file_path in file_paths:
            result = self.parse_file(file_path)
            all_orders.extend(result.orders)
            all_warnings.extend(result.warnings)

        return XmlImportResult(orders=all_orders, warnings=all_warnings)

    def _find_nfe_element(self, root: ET.Element) -> Optional[ET.Element]:
        """Find the NFe root element, handling various XML structures."""
        # Try direct child
        for tag in ["NFe", "nfe", "infNFe"]:
            elem = root.find(f".//{{{NFE_NS}}}{tag}")
            if elem is not None:
                return elem

        # Try by local name (namespace-agnostic)
        for child in root:
            local_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if local_name in ("NFe", "nfe", "infNFe"):
                return child

        return None

    def _extract_text(self, parent: ET.Element, path: str) -> Optional[str]:
        """Extract text content from a child element by path."""
        elem = parent.find(f".//{{{NFE_NS}}}{path}")
        if elem is not None and elem.text:
            return elem.text.strip()
        return None

    def _extract_emit_name(self, nfe: ET.Element) -> Optional[str]:
        """Extract the supplier/company name from emit/xNome."""
        emit = nfe.find(f".//{{{NFE_NS}}}emit")
        if emit is not None:
            xnome = emit.find(f".//{{{NFE_NS}}}xNome")
            if xnome is not None and xnome.text:
                return xnome.text.strip()
        return None

    def _extract_date(self, date_raw: str) -> str:
        """Extract and convert date from ISO 8601 to YYYY-MM-DD."""
        if not date_raw:
            return ""
        # Take first 10 characters (YYYY-MM-DD)
        date_str = date_raw[:10]
        # Validate it's a valid date
        try:
            datetime.fromisoformat(date_str)
            return date_str
        except ValueError:
            return ""

    def _extract_products(self, nfe: ET.Element, warnings: list[str]) -> List[Product]:
        """Extract product data from det elements."""
        products: list[Product] = []

        # Find all det elements
        det_elements = nfe.findall(f".//{{{NFE_NS}}}det")

        for det in det_elements:
            # Extract product data from prod
            prod = det.find(f".//{{{NFE_NS}}}prod")
            if prod is None:
                continue

            current_warnings: list[str] = []

            x_prod = self._get_child_text(prod, "xProd") or ""
            v_prod_str = self._get_child_text(prod, "vProd") or "0"
            q_com_str = self._get_child_text(prod, "qCom") or "0"

            # Parse base price and quantity
            try:
                base_price = round(float(v_prod_str) * 100)  # to cents
            except ValueError:
                base_price = 0

            try:
                quantity = float(q_com_str)
            except ValueError:
                quantity = 0.0

            # Check if quantity is an integer
            if quantity != int(quantity):
                current_warnings.append("Quantidade não inteira.")
                quantity = 0

            quantity_int = int(quantity)

            # Extract IPI and ICMS-ST adjustments
            imposto = det.find(f".//{{{NFE_NS}}}imposto")
            ipi_value = 0
            icms_st_value = 0

            if imposto is not None:
                ipi_elem = imposto.find(f".//{{{NFE_NS}}}IPI")
                if ipi_elem is not None:
                    ipi_v_elem = ipi_elem.find(f".//{{{NFE_NS}}}vIPI")
                    if ipi_v_elem is not None and ipi_v_elem.text:
                        try:
                            ipi_value = round(float(ipi_v_elem.text) * 100)
                            if ipi_value > 0:
                                current_warnings.append("Produto com IPI.")
                        except ValueError:
                            pass

                icms_st_elem = imposto.find(f".//{{{NFE_NS}}}ICMSST")
                if icms_st_elem is not None:
                    v_elem = icms_st_elem.find(f".//{{{NFE_NS}}}vICMSST")
                    if v_elem is not None and v_elem.text:
                        try:
                            icms_st_value = round(float(v_elem.text) * 100)
                            if icms_st_value > 0:
                                current_warnings.append("Produto com ST.")
                        except ValueError:
                            pass

            # Calculate adjusted price
            adjusted_price = base_price + ipi_value + icms_st_value

            # Calculate unit price and total
            if quantity_int > 0:
                unit_price = adjusted_price // quantity_int
                total_price = adjusted_price
            else:
                unit_price = 0
                total_price = adjusted_price

            product_id = str(uuid.uuid4())

            product = Product(
                id=product_id,
                name=x_prod,
                quantity=quantity_int,
                price=unit_price,
                price_with_freight=unit_price,
                total=total_price,
                order_id="",  # Will be set when order is created
                item_ordinal=None,
                warnings=current_warnings,
            )
            warnings.extend(current_warnings)
            products.append(product)

        return products

    @staticmethod
    def _get_child_text(parent: ET.Element, child_tag: str) -> Optional[str]:
        """Get text content of a direct child element (namespace-agnostic)."""
        for child in parent:
            local_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if local_name == child_tag and child.text:
                return child.text.strip()
        return None
