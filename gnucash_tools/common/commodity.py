import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from ..util import ValueHistory, _get_child_by_tag_name


@dataclass(frozen=True)
class CommodityId:
    space: str
    id: str

    @staticmethod
    def from_xml_element(commodity_element: ET.Element) -> "CommodityId":
        return CommodityId(
            space=_get_child_by_tag_name(commodity_element, "space").text,
            id=_get_child_by_tag_name(commodity_element, "id").text,
        )


@dataclass
class Commodity:
    id: CommodityId
    name: str
    price_history: ValueHistory = field(default_factory=ValueHistory)
    book: "Book | None" = None

    @staticmethod
    def from_xml_element(commodity_element: ET.Element) -> "Commodity":
        name_element = _get_child_by_tag_name(commodity_element, "name")
        name = name_element.text if name_element is not None else None
        return Commodity(
            id=CommodityId.from_xml_element(commodity_element),
            name=name,
        )

    def __repr__(self) -> str:
        return f"Commodity {self.id}, {self.name}"
