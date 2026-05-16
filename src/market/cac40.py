"""CAC 40 constituent tickers and display names."""

CAC40_TICKERS: dict[str, str] = {
    "AC.PA": "Accor",
    "AI.PA": "Air Liquide",
    "AIR.PA": "Airbus",
    "ALO.PA": "Alstom",
    "MT.AS": "ArcelorMittal",
    "CS.PA": "AXA",
    "BNP.PA": "BNP Paribas",
    "EN.PA": "Bouygues",
    "CAP.PA": "Capgemini",
    "CA.PA": "Carrefour",
    "ACA.PA": "Crédit Agricole",
    "BN.PA": "Danone",
    "DSY.PA": "Dassault Systèmes",
    "ENGI.PA": "Engie",
    "EL.PA": "EssilorLuxottica",
    "ERF.PA": "Eurofins Scientific",
    "RMS.PA": "Hermès",
    "KER.PA": "Kering",
    "LR.PA": "Legrand",
    "OR.PA": "L'Oréal",
    "MC.PA": "LVMH",
    "ML.PA": "Michelin",
    "ORA.PA": "Orange",
    "RI.PA": "Pernod Ricard",
    "PUB.PA": "Publicis Groupe",
    "RNO.PA": "Renault",
    "SAF.PA": "Safran",
    "SGO.PA": "Saint-Gobain",
    "SAN.PA": "Sanofi",
    "SU.PA": "Schneider Electric",
    "GLE.PA": "Société Générale",
    "STLAM.MI": "Stellantis",
    "STMPA.PA": "STMicroelectronics",
    "AKE.PA": "Arkema",
    "ENX.PA": "Euronext",
    "HO.PA": "Thales",
    "TTE.PA": "TotalEnergies",
    "URW.PA": "Unibail-Rodamco-Westfield",
    "VIE.PA": "Veolia",
    "DG.PA": "Vinci",
}

TICKERS = list(CAC40_TICKERS.keys())
NAMES = CAC40_TICKERS

# "LVMH (MC.PA)" display strings, used in dropdowns
DISPLAY_OPTIONS: list[str] = [
    f"{name} ({ticker})" for ticker, name in CAC40_TICKERS.items()
]
DISPLAY_TO_TICKER: dict[str, str] = {
    f"{name} ({ticker})": ticker for ticker, name in CAC40_TICKERS.items()
}
TICKER_TO_DISPLAY: dict[str, str] = {v: k for k, v in DISPLAY_TO_TICKER.items()}
