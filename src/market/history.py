"""Trade history loader — parses data/historic.csv into typed Transaction records."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from src.market.glossary import GLOSSARY

_HISTORY_PATH = Path("data") / "historic.csv"

Operation = Literal["Buy", "Sell"]


@dataclass(frozen=True)
class Transaction:
    date: date
    operation: Operation
    quantity: int
    broker_name: str       # raw name as it appears in the CSV
    ticker: str            # resolved Yahoo Finance ticker
    amount_eur: float


def _parse_amount(raw: str) -> float:
    """Parse European-style amounts that may contain spaces as thousand separators."""
    return float(raw.strip().replace("\u202f", "").replace(" ", "").replace(",", "."))


def load_history(path: Path = _HISTORY_PATH) -> list[Transaction]:
    """Parse *historic.csv* and return a list of :class:`Transaction` objects.

    Raises ``ValueError`` for rows whose company name cannot be resolved to a
    known CAC 40 ticker via the glossary.
    """
    transactions: list[Transaction] = []
    unresolved: list[str] = []

    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            raw_name = row["stock"].strip()
            info = GLOSSARY.by_broker_name(raw_name)
            if info is None:
                unresolved.append(raw_name)
                continue

            transactions.append(
                Transaction(
                    date=date(*reversed([int(p) for p in row["date"].strip().split("/")])),
                    operation=row["operation"].strip(),
                    quantity=int(row["quantity"].strip()),
                    broker_name=raw_name,
                    ticker=info.ticker,
                    amount_eur=_parse_amount(row["amount(EUR)"]),
                )
            )

    if unresolved:
        raise ValueError(
            f"Could not resolve {len(unresolved)} broker name(s) to a CAC 40 ticker:\n"
            + "\n".join(f"  - {n!r}" for n in unresolved)
        )

    return sorted(transactions, key=lambda t: t.date)
