"""CAC 40 company glossary — loads config/cac40_glossary.yaml into typed dataclasses."""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path

_GLOSSARY_PATH = Path("config") / "cac40_glossary.yaml"


@dataclass(frozen=True)
class CompanyInfo:
    ticker: str
    name: str
    abbrevs: list[str]
    broker_aliases: list[str]
    sector: str
    description: str

    def matches(self, query: str) -> bool:
        """Return True if *query* matches ticker, name, abbreviation, or broker alias (case-insensitive)."""
        q = query.strip().upper()
        return (
            q == self.ticker.upper()
            or q == self.name.upper()
            or q in (a.upper() for a in self.abbrevs)
            or q in (a.upper() for a in self.broker_aliases)
        )


@dataclass
class Glossary:
    companies: list[CompanyInfo] = field(default_factory=list)

    # --- lookup helpers ---

    def by_ticker(self, ticker: str) -> CompanyInfo | None:
        ticker = ticker.upper()
        return next((c for c in self.companies if c.ticker.upper() == ticker), None)

    def by_abbrev(self, abbrev: str) -> list[CompanyInfo]:
        abbrev = abbrev.upper()
        return [c for c in self.companies if abbrev in (a.upper() for a in c.abbrevs)]

    def by_broker_name(self, raw_name: str) -> CompanyInfo | None:
        """Resolve a raw broker-exported company name to a CompanyInfo.

        Normalises the query (strip spaces, uppercase) then checks broker_aliases
        first (exact), then falls back to name/abbrev matching via :meth:`matches`.
        Returns ``None`` if no match is found.
        """
        normalised = raw_name.strip().upper()
        # 1. exact broker alias match
        for c in self.companies:
            if normalised in (a.upper() for a in c.broker_aliases):
                return c
        # 2. fallback: name / ticker / abbrev
        for c in self.companies:
            if c.matches(raw_name):
                return c
        return None

    def by_sector(self, sector: str) -> list[CompanyInfo]:
        sector = sector.lower()
        return [c for c in self.companies if c.sector.lower() == sector]

    def search(self, query: str) -> list[CompanyInfo]:
        """Search across ticker, name, abbreviations, and broker aliases."""
        return [c for c in self.companies if c.matches(query)]

    # --- convenience views ---

    @property
    def sectors(self) -> list[str]:
        return sorted({c.sector for c in self.companies})

    def as_dict(self) -> dict[str, CompanyInfo]:
        return {c.ticker: c for c in self.companies}


def load_glossary(path: Path = _GLOSSARY_PATH) -> Glossary:
    """Parse *cac40_glossary.yaml* and return a :class:`Glossary` instance."""
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    companies = [
        CompanyInfo(
            ticker=entry["ticker"],
            name=entry["name"],
            abbrevs=entry.get("abbrevs", []),
            broker_aliases=entry.get("broker_aliases", []),
            sector=entry["sector"],
            description=entry["description"],
        )
        for entry in raw["companies"]
    ]
    return Glossary(companies=companies)


# Module-level singleton — import and use directly:
#   from src.market.glossary import GLOSSARY
#   info = GLOSSARY.by_ticker("MC.PA")
#   info = GLOSSARY.by_broker_name("LVMHMOET HENNESSY VUITTON")
GLOSSARY: Glossary = load_glossary()
