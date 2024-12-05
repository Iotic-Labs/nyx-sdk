"""Structures for defining custom metadata (properties) for :class:`nyx_client.data.Data`.

Fields in said structures follow Nyx OpenAPI spec naming.
"""

from dataclasses import asdict, dataclass, fields
from typing import Any, ClassVar


@dataclass(frozen=True, kw_only=True)
class LangLiteral:
    """A metadata property type describing a string with a given language.

    Implicit datatype: `rdf:langString`
    """

    lang: str
    """2-character language code"""

    value: str
    """String representation of the value"""


@dataclass(frozen=True, kw_only=True)
class StringLiteral:
    """A metadata property type describing a string without a language.

    Implicit datatype: `rdf:string`
    """

    value: str
    """String representation of the value"""


@dataclass(frozen=True, kw_only=True)
class Literal:
    """A metadata property type describing a literal with the given datatype.

    Implicit datatype: `rdfs:Literal`
    """

    dataType: str
    """XSD data type without its namespace prefix.

    The following types (from `XSD namespace <http://www.w3.org/2001/XMLSchema#>`_) are currently supported:

    ``dateTime, time, date, boolean, integer, decimal, float, double, nonPositiveInteger, negativeInteger,
    nonNegativeInteger, positiveInteger, long, unsignedLong, int, unsignedInt, short, unsignedShort, byte,
    unsignedByte, base64Binary, anyURI``
    """

    value: str
    """String representation of the value"""


@dataclass(frozen=True, kw_only=True)
class Uri:
    """A metadata property type describing a Uri."""

    uri: str
    """String representation of the URI"""


PropertyValue = LangLiteral | StringLiteral | Literal | Uri
"""The value (object) of a property."""


@dataclass(frozen=True, kw_only=True)
class Property:
    """A metadata property with a single value.

    Multiple instances are used to represent a key (predicate) with multiple values.
    """

    key: str
    """The key (predicate) of the property. Must be an IRI."""

    value: PropertyValue
    """The value (object) of the property.

    One of :class:`LangLiteral`, :class:`StringLiteral`, :class:`Literal` or :class:`Uri`
    """

    def as_dict(self) -> dict[str, Any]:
        """Returns the object as a dictionary.

        Returns:
            A dictionary of the Property that matches layout expected by the API.

        """
        return asdict(self)

    # Mapping of expected dictionary keys for each type of property value to the class they belong to
    _PROPERTY_VALUE_DICT_KEYS: ClassVar[dict[frozenset[str], PropertyValue]] = {
        frozenset(field.name for field in fields(cls)): cls for cls in (LangLiteral, StringLiteral, Literal, Uri)
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Property":
        """Returns a new property instance constructed from the given dictionary.

        This is expected to be in the same format as generated by :meth:`as_dict()` (or returned nu the API).
        """
        value = data["value"]
        return cls(key=data["key"], value=cls._PROPERTY_VALUE_DICT_KEYS[frozenset(value.keys())](**value))

    @classmethod
    def lang_string(cls, key: str, value: str, lang: str) -> "Property":
        """Shorthand for creating a language-specific string property.

        See :class:`LangLiteral` for more details.
        """
        return cls(key=key, value=LangLiteral(lang=lang, value=value))

    @classmethod
    def string(cls, key: str, value: str) -> "Property":
        """Shorthand for creating a string property (without language).

        See :class:`StringLiteral` for more details.
        """
        return cls(key=key, value=StringLiteral(value=value))

    @classmethod
    def literal(cls, key: str, value: str, data_type: str) -> "Property":
        """Shorthand for creating a property with a specific data type.

        See :class:`Literal` for more details.
        """
        return cls(key=key, value=Literal(dataType=data_type, value=value))

    @classmethod
    def uri(cls, key: str, uri: str) -> "Property":
        """Shorthand for creating a URI property.

        See :class:`Uri` for more details.
        """
        return cls(key=key, value=Uri(uri=uri))
