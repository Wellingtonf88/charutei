"""Cataloga os charutos do PDF Charutos 2GO / OffCuba (05.05.26).

Os dados foram extraídos do catálogo e normalizados com mapeamentos de
marca → país e palavras-chave de capa → intensidade.
Execute:
    uv run python scripts/parse_c2go_catalog.py
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog" / "cigars.csv"


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


# (name, brand, country, vitola, strength)
ENTRIES: list[tuple[str, str, str, str, str]] = [
    # ── A. FUENTE ── Gran Reserva ───────────────────────────────────────────
    ("Arturo Fuente Gran Reserva 8-5-8 Natural", "Arturo Fuente", "República Dominicana", "Corona Gorda", "medium"),
    ("Arturo Fuente Gran Reserva 8-5-8 Maduro", "Arturo Fuente", "República Dominicana", "Corona Gorda", "medium-full"),
    ("Arturo Fuente Gran Reserva Flor Fina Natural", "Arturo Fuente", "República Dominicana", "Churchill", "medium"),
    ("Arturo Fuente Gran Reserva Flor Fina Maduro", "Arturo Fuente", "República Dominicana", "Churchill", "medium-full"),
    ("Arturo Fuente Gran Reserva Canones", "Arturo Fuente", "República Dominicana", "Presidente", "medium"),
    ("Arturo Fuente Gran Reserva Double Chateau Natural", "Arturo Fuente", "República Dominicana", "Toro", "medium"),
    ("Arturo Fuente Gran Reserva Double Chateau Maduro", "Arturo Fuente", "República Dominicana", "Toro", "medium-full"),
    ("Arturo Fuente Gran Reserva Churchill", "Arturo Fuente", "República Dominicana", "Double Corona", "medium"),
    ("Arturo Fuente Gran Reserva Palma", "Arturo Fuente", "República Dominicana", "Lonsdale", "medium"),
    ("Arturo Fuente Gran Reserva Brevas Royale", "Arturo Fuente", "República Dominicana", "Robusto", "medium"),
    # ── A. FUENTE ── Anejo Reserva ──────────────────────────────────────────
    ("Arturo Fuente Anejo Reserva No. 46", "Arturo Fuente", "República Dominicana", "Robusto", "medium-full"),
    ("Arturo Fuente Anejo Reserva No. 50", "Arturo Fuente", "República Dominicana", "Toro", "medium-full"),
    ("Arturo Fuente Anejo Reserva No. 55", "Arturo Fuente", "República Dominicana", "Gordo", "medium-full"),
    ("Arturo Fuente Anejo Reserva No. 60", "Arturo Fuente", "República Dominicana", "Gordo", "full"),
    ("Arturo Fuente Anejo Reserva Shark", "Arturo Fuente", "República Dominicana", "Lancero", "full"),
    ("Arturo Fuente Anejo Reserva Reserva No. 49", "Arturo Fuente", "República Dominicana", "Lonsdale", "medium-full"),
    ("Arturo Fuente Anejo Reserva Maduro No. 46 8-8-8", "Arturo Fuente", "República Dominicana", "Robusto", "full"),
    # ── A. FUENTE ── Hemingway ──────────────────────────────────────────────
    ("Arturo Fuente Hemingway Best Seller", "Arturo Fuente", "República Dominicana", "Perfecto", "medium"),
    ("Arturo Fuente Hemingway Short Story", "Arturo Fuente", "República Dominicana", "Perfecto", "medium"),
    ("Arturo Fuente Hemingway Signature", "Arturo Fuente", "República Dominicana", "Perfecto", "medium"),
    ("Arturo Fuente Hemingway Classic", "Arturo Fuente", "República Dominicana", "Perfecto", "medium"),
    ("Arturo Fuente Hemingway Outrageous", "Arturo Fuente", "República Dominicana", "Perfecto", "medium"),
    ("Arturo Fuente Hemingway Work of Art", "Arturo Fuente", "República Dominicana", "Diadema", "medium"),
    # ── A. FUENTE ── Chateau Fuente ─────────────────────────────────────────
    ("Arturo Fuente Chateau Fuente Natural", "Arturo Fuente", "República Dominicana", "Robusto", "medium"),
    ("Arturo Fuente Chateau Fuente Sungrown", "Arturo Fuente", "República Dominicana", "Robusto", "medium"),
    ("Arturo Fuente Chateau Fuente Double Chateau Sungrown", "Arturo Fuente", "República Dominicana", "Toro", "medium"),
    # ── A. FUENTE ── Don Carlos ─────────────────────────────────────────────
    ("Arturo Fuente Don Carlos No. 3", "Arturo Fuente", "República Dominicana", "Corona", "medium-full"),
    ("Arturo Fuente Don Carlos No. 4", "Arturo Fuente", "República Dominicana", "Corona", "medium-full"),
    ("Arturo Fuente Don Carlos Robusto", "Arturo Fuente", "República Dominicana", "Robusto", "medium-full"),
    ("Arturo Fuente Don Carlos Eye of the Shark", "Arturo Fuente", "República Dominicana", "Perfecto", "full"),
    # ── A. FUENTE ── Opus X ─────────────────────────────────────────────────
    ("Arturo Fuente Opus X Robusto", "Arturo Fuente", "República Dominicana", "Robusto", "full"),
    ("Arturo Fuente Opus X Toro", "Arturo Fuente", "República Dominicana", "Toro", "full"),
    ("Arturo Fuente Opus X Churchill", "Arturo Fuente", "República Dominicana", "Churchill", "full"),
    ("Arturo Fuente Opus X Lancero", "Arturo Fuente", "República Dominicana", "Lancero", "full"),
    ("Arturo Fuente Opus X Double Corona", "Arturo Fuente", "República Dominicana", "Double Corona", "full"),
    ("Arturo Fuente Opus X Belicoso", "Arturo Fuente", "República Dominicana", "Belicoso", "full"),
    ("Arturo Fuente Opus X Super Belicoso", "Arturo Fuente", "República Dominicana", "Torpedo", "full"),
    ("Arturo Fuente Opus X Angel's Share", "Arturo Fuente", "República Dominicana", "Lonsdale", "full"),
    ("Arturo Fuente Opus X Super Robusto", "Arturo Fuente", "República Dominicana", "Robusto Extra", "full"),
    # ── AJ FERNANDEZ ────────────────────────────────────────────────────────
    ("AJ Fernandez New World Robusto", "AJ Fernandez", "Nicarágua", "Robusto", "medium-full"),
    ("AJ Fernandez New World Toro", "AJ Fernandez", "Nicarágua", "Toro", "medium-full"),
    ("AJ Fernandez New World Churchill", "AJ Fernandez", "Nicarágua", "Churchill", "medium-full"),
    ("AJ Fernandez New World Belicoso", "AJ Fernandez", "Nicarágua", "Belicoso", "medium-full"),
    ("AJ Fernandez New World Gordo", "AJ Fernandez", "Nicarágua", "Gordo", "medium-full"),
    ("AJ Fernandez New World Oscuro Robusto", "AJ Fernandez", "Nicarágua", "Robusto", "full"),
    ("AJ Fernandez New World Oscuro Gordo", "AJ Fernandez", "Nicarágua", "Gordo", "full"),
    ("AJ Fernandez Enclave Broadleaf Robusto", "AJ Fernandez", "Nicarágua", "Robusto", "full"),
    ("AJ Fernandez Enclave Broadleaf Toro", "AJ Fernandez", "Nicarágua", "Toro", "full"),
    ("AJ Fernandez Enclave Broadleaf Churchill", "AJ Fernandez", "Nicarágua", "Churchill", "full"),
    ("AJ Fernandez Bellas Artes Maduro Robusto", "AJ Fernandez", "Nicarágua", "Robusto", "full"),
    ("AJ Fernandez Bellas Artes Maduro Toro", "AJ Fernandez", "Nicarágua", "Toro", "full"),
    ("AJ Fernandez Bellas Artes Connecticut Robusto", "AJ Fernandez", "Nicarágua", "Robusto", "medium"),
    ("AJ Fernandez New World Connecticut Robusto", "AJ Fernandez", "Nicarágua", "Robusto", "medium"),
    # ── ALEC BRADLEY ────────────────────────────────────────────────────────
    ("Alec Bradley Black Market Robusto", "Alec Bradley", "Honduras", "Robusto", "medium-full"),
    ("Alec Bradley Black Market Toro", "Alec Bradley", "Honduras", "Toro", "medium-full"),
    ("Alec Bradley Black Market Gordo", "Alec Bradley", "Honduras", "Gordo", "medium-full"),
    ("Alec Bradley Black Market Lonsdale", "Alec Bradley", "Honduras", "Lonsdale", "medium-full"),
    ("Alec Bradley Black Market Esteli Robusto", "Alec Bradley", "Honduras", "Robusto", "full"),
    ("Alec Bradley Black Market Esteli Toro", "Alec Bradley", "Honduras", "Toro", "full"),
    ("Alec Bradley Magic Toast Churchill", "Alec Bradley", "Honduras", "Churchill", "medium"),
    ("Alec Bradley Magic Toast Gordo", "Alec Bradley", "Honduras", "Gordo", "medium"),
    ("Alec Bradley Prensado Robusto", "Alec Bradley", "Honduras", "Robusto", "full"),
    ("Alec Bradley Prensado Toro", "Alec Bradley", "Honduras", "Toro", "full"),
    ("Alec Bradley Prensado Churchill", "Alec Bradley", "Honduras", "Churchill", "full"),
    ("Alec Bradley Medalist Connecticut Toro", "Alec Bradley", "Honduras", "Toro", "mild"),
    # ── AVO ─────────────────────────────────────────────────────────────────
    ("Avo Classic Robusto", "Avo", "República Dominicana", "Robusto", "mild"),
    ("Avo Classic Toro", "Avo", "República Dominicana", "Toro", "mild"),
    ("Avo Classic No. 2", "Avo", "República Dominicana", "Corona", "mild"),
    ("Avo Heritage Robusto", "Avo", "República Dominicana", "Robusto", "medium"),
    ("Avo Heritage Toro", "Avo", "República Dominicana", "Toro", "medium"),
    ("Avo Syncro Nicaragua Robusto", "Avo", "Nicarágua", "Robusto", "medium-full"),
    ("Avo Syncro Nicaragua Toro", "Avo", "Nicarágua", "Toro", "medium-full"),
    ("Avo Syncro Nicaragua Gordo", "Avo", "Nicarágua", "Gordo", "medium-full"),
    ("Avo XO Intermezzo", "Avo", "República Dominicana", "Robusto", "medium"),
    ("Avo XO Notturno", "Avo", "República Dominicana", "Toro", "medium"),
    # ── BRICK HOUSE ─────────────────────────────────────────────────────────
    ("Brick House Double Connecticut Robusto", "Brick House", "Honduras", "Robusto", "mild"),
    ("Brick House Double Connecticut Toro", "Brick House", "Honduras", "Toro", "mild"),
    ("Brick House Double Connecticut Churchill", "Brick House", "Honduras", "Churchill", "mild"),
    ("Brick House Mighty Mighty Robusto", "Brick House", "Honduras", "Robusto", "medium-full"),
    ("Brick House Mighty Mighty Gordo", "Brick House", "Honduras", "Gordo", "medium-full"),
    ("Brick House Tres Lindos Robusto", "Brick House", "Honduras", "Robusto", "medium"),
    ("Brick House Maduro Robusto", "Brick House", "Honduras", "Robusto", "full"),
    ("Brick House Maduro Toro", "Brick House", "Honduras", "Toro", "full"),
    # ── BUENA VISTA ─────────────────────────────────────────────────────────
    ("Buena Vista Robusto", "Buena Vista", "Honduras", "Robusto", "medium"),
    ("Buena Vista Toro", "Buena Vista", "Honduras", "Toro", "medium"),
    ("Buena Vista Churchill", "Buena Vista", "Honduras", "Churchill", "medium"),
    ("Buena Vista Maduro Robusto", "Buena Vista", "Honduras", "Robusto", "medium-full"),
    # ── CAO ─────────────────────────────────────────────────────────────────
    ("CAO Amazon Basin Robusto", "CAO", "Nicarágua", "Robusto", "medium-full"),
    ("CAO Amazon Basin Toro", "CAO", "Nicarágua", "Toro", "medium-full"),
    ("CAO Amazon Basin Churchill", "CAO", "Nicarágua", "Churchill", "medium-full"),
    ("CAO Amazon Basin Gordo", "CAO", "Nicarágua", "Gordo", "medium-full"),
    ("CAO Brazilia Gol!", "CAO", "Nicarágua", "Toro", "medium"),
    ("CAO Brazilia Corcovado", "CAO", "Nicarágua", "Churchill", "medium"),
    ("CAO Brazilia Piranha", "CAO", "Nicarágua", "Robusto", "medium"),
    ("CAO BX3 Robusto", "CAO", "Nicarágua", "Robusto", "medium"),
    ("CAO BX3 Toro", "CAO", "Nicarágua", "Toro", "medium"),
    ("CAO BX3 Gordo", "CAO", "Nicarágua", "Gordo", "medium"),
    ("CAO Flathead V660 Gregale", "CAO", "Nicarágua", "Gordo", "full"),
    ("CAO Flathead V770 Widowmaker", "CAO", "Nicarágua", "Gordo", "full"),
    ("CAO MX2 Robusto", "CAO", "Nicarágua", "Robusto", "medium-full"),
    ("CAO MX2 Toro", "CAO", "Nicarágua", "Toro", "medium-full"),
    ("CAO OSA Sol Robusto", "CAO", "Honduras", "Robusto", "medium"),
    ("CAO OSA Sol Toro", "CAO", "Honduras", "Toro", "medium"),
    # ── DAVIDOFF ────────────────────────────────────────────────────────────
    ("Davidoff Grand Cru No. 3", "Davidoff", "República Dominicana", "Corona", "mild"),
    ("Davidoff Grand Cru No. 5", "Davidoff", "República Dominicana", "Perla", "mild"),
    ("Davidoff Grand Cru Robusto", "Davidoff", "República Dominicana", "Robusto", "mild"),
    ("Davidoff Grand Cru Toro", "Davidoff", "República Dominicana", "Toro", "mild"),
    ("Davidoff Signature 2000", "Davidoff", "República Dominicana", "Petit Corona", "mild"),
    ("Davidoff Signature 3000", "Davidoff", "República Dominicana", "Lonsdale", "mild"),
    ("Davidoff Millennium Blend Short", "Davidoff", "República Dominicana", "Robusto", "medium"),
    ("Davidoff Millennium Blend Robusto", "Davidoff", "República Dominicana", "Robusto", "medium-full"),
    ("Davidoff Millennium Blend Toro", "Davidoff", "República Dominicana", "Toro", "medium-full"),
    ("Davidoff Winston Churchill Original", "Davidoff", "República Dominicana", "Toro", "medium-full"),
    ("Davidoff Winston Churchill Robusto", "Davidoff", "República Dominicana", "Robusto", "medium-full"),
    ("Davidoff Winston Churchill Churchill", "Davidoff", "República Dominicana", "Churchill", "medium-full"),
    ("Davidoff Winston Churchill The Churchill", "Davidoff", "República Dominicana", "Double Corona", "medium-full"),
    ("Davidoff Nicaragua Robusto", "Davidoff", "Nicarágua", "Robusto", "medium-full"),
    ("Davidoff Nicaragua Toro", "Davidoff", "Nicarágua", "Toro", "medium-full"),
    ("Davidoff Nicaragua Gordo", "Davidoff", "Nicarágua", "Gordo", "medium-full"),
    ("Davidoff Nicaragua Churchill", "Davidoff", "Nicarágua", "Churchill", "medium-full"),
    # ── DIAMOND CROWN ───────────────────────────────────────────────────────
    ("Diamond Crown Maximus Robusto", "J.C. Newman", "República Dominicana", "Robusto", "medium-full"),
    ("Diamond Crown Maximus Toro", "J.C. Newman", "República Dominicana", "Toro", "medium-full"),
    ("Diamond Crown Maximus Churchill", "J.C. Newman", "República Dominicana", "Churchill", "medium-full"),
    ("Diamond Crown Classic No. 4", "J.C. Newman", "República Dominicana", "Toro", "medium"),
    ("Diamond Crown Classic No. 6", "J.C. Newman", "República Dominicana", "Gordo", "medium"),
    # ── DON DIEGO ───────────────────────────────────────────────────────────
    ("Don Diego Robusto", "Don Diego", "República Dominicana", "Robusto", "mild"),
    ("Don Diego Churchill", "Don Diego", "República Dominicana", "Churchill", "mild"),
    ("Don Diego Lonsdale", "Don Diego", "República Dominicana", "Lonsdale", "mild"),
    # ── DON EMMANUEL ────────────────────────────────────────────────────────
    ("Don Emmanuel Connecticut Robusto", "Don Emmanuel", "Nicarágua", "Robusto", "mild"),
    ("Don Emmanuel Connecticut Toro", "Don Emmanuel", "Nicarágua", "Toro", "mild"),
    ("Don Emmanuel Habano Robusto", "Don Emmanuel", "Nicarágua", "Robusto", "medium"),
    ("Don Emmanuel Maduro Robusto", "Don Emmanuel", "Nicarágua", "Robusto", "full"),
    # ── DREW ESTATE ─────────────────────────────────────────────────────────
    ("Drew Estate Liga Privada T52 Robusto", "Drew Estate", "Nicarágua", "Robusto", "full"),
    ("Drew Estate Liga Privada T52 Toro", "Drew Estate", "Nicarágua", "Toro", "full"),
    ("Drew Estate Liga Privada T52 Churchill", "Drew Estate", "Nicarágua", "Churchill", "full"),
    ("Drew Estate Liga Privada T52 Lancero", "Drew Estate", "Nicarágua", "Lancero", "full"),
    ("Drew Estate Liga Privada T52 Gordo", "Drew Estate", "Nicarágua", "Gordo", "full"),
    ("Drew Estate Liga Privada No. 9 Robusto", "Drew Estate", "Nicarágua", "Robusto", "full"),
    ("Drew Estate Liga Privada No. 9 Toro", "Drew Estate", "Nicarágua", "Toro", "full"),
    ("Drew Estate Liga Privada No. 9 Churchill", "Drew Estate", "Nicarágua", "Churchill", "full"),
    ("Drew Estate Liga Privada No. 9 Lancero", "Drew Estate", "Nicarágua", "Lancero", "full"),
    ("Drew Estate Undercrown Shade Robusto", "Drew Estate", "Nicarágua", "Robusto", "medium"),
    ("Drew Estate Undercrown Shade Toro", "Drew Estate", "Nicarágua", "Toro", "medium"),
    ("Drew Estate Undercrown Shade Churchill", "Drew Estate", "Nicarágua", "Churchill", "medium"),
    ("Drew Estate Undercrown Sun Grown Robusto", "Drew Estate", "Nicarágua", "Robusto", "medium-full"),
    ("Drew Estate Undercrown Sun Grown Toro", "Drew Estate", "Nicarágua", "Toro", "medium-full"),
    ("Drew Estate Herrera Esteli Robusto Grande", "Drew Estate", "Nicarágua", "Robusto", "medium-full"),
    ("Drew Estate Herrera Esteli Toro Especial", "Drew Estate", "Nicarágua", "Toro", "medium-full"),
    ("Drew Estate Natural Blunt Torpedo", "Drew Estate", "Nicarágua", "Torpedo", "medium"),
    # ── EP CARRILLO ─────────────────────────────────────────────────────────
    ("EP Carrillo Encore Majestic", "E.P. Carrillo", "República Dominicana", "Robusto", "full"),
    ("EP Carrillo Encore Celestial", "E.P. Carrillo", "República Dominicana", "Toro", "full"),
    ("EP Carrillo Pledge Prequel", "E.P. Carrillo", "Nicarágua", "Robusto", "full"),
    ("EP Carrillo Pledge Apogee", "E.P. Carrillo", "Nicarágua", "Toro", "full"),
    ("EP Carrillo La Historia EPC 660", "E.P. Carrillo", "República Dominicana", "Gordo", "full"),
    ("EP Carrillo La Historia EPC 646", "E.P. Carrillo", "República Dominicana", "Toro", "full"),
    ("EP Carrillo New Wave Connecticut Robusto", "E.P. Carrillo", "República Dominicana", "Robusto", "medium"),
    # ── ESPINOSA ────────────────────────────────────────────────────────────
    ("Espinosa Laranja Maduro Robusto", "Espinosa", "Nicarágua", "Robusto", "full"),
    ("Espinosa Laranja Maduro Toro", "Espinosa", "Nicarágua", "Toro", "full"),
    ("Espinosa Crema Robusto", "Espinosa", "Nicarágua", "Robusto", "medium"),
    ("Espinosa Alpha Robusto", "Espinosa", "Nicarágua", "Robusto", "medium-full"),
    ("Espinosa Alpha Toro", "Espinosa", "Nicarágua", "Toro", "medium-full"),
    ("Espinosa Velvet Rat Robusto", "Espinosa", "Nicarágua", "Robusto", "medium-full"),
    # ── FLOR DE COPAN ───────────────────────────────────────────────────────
    ("Flor de Copan Classic Robusto", "Flor de Copan", "Honduras", "Robusto", "medium"),
    ("Flor de Copan Classic Toro", "Flor de Copan", "Honduras", "Toro", "medium"),
    ("Flor de Copan Classic Churchill", "Flor de Copan", "Honduras", "Churchill", "medium"),
    ("Flor de Copan Classic Gordo", "Flor de Copan", "Honduras", "Gordo", "medium"),
    ("Flor de Copan Classic Lancero", "Flor de Copan", "Honduras", "Lancero", "medium"),
    ("Flor de Copan Classico Corojo Robusto", "Flor de Copan", "Honduras", "Robusto", "medium-full"),
    ("Flor de Copan Classico Corojo Toro", "Flor de Copan", "Honduras", "Toro", "medium-full"),
    ("Flor de Copan Spirit of Copan Robusto", "Flor de Copan", "Honduras", "Robusto", "medium"),
    ("Flor de Copan Spirit of Copan Churchill", "Flor de Copan", "Honduras", "Churchill", "medium"),
    # ── FLOR DE OLIVA ───────────────────────────────────────────────────────
    ("Flor de Oliva Gold Robusto", "Flor de Oliva", "Nicarágua", "Robusto", "medium"),
    ("Flor de Oliva Gold Toro", "Flor de Oliva", "Nicarágua", "Toro", "medium"),
    ("Flor de Oliva Silver Robusto", "Flor de Oliva", "Nicarágua", "Robusto", "medium"),
    ("Flor de Oliva Classic Robusto", "Flor de Oliva", "Nicarágua", "Robusto", "mild"),
    # ── FRATELLO ────────────────────────────────────────────────────────────
    ("Fratello Classico Robusto", "Fratello", "República Dominicana", "Robusto", "medium"),
    ("Fratello Classico Toro", "Fratello", "República Dominicana", "Toro", "medium"),
    ("Fratello Classico Churchill", "Fratello", "República Dominicana", "Churchill", "medium"),
    ("Fratello Oro Robusto", "Fratello", "República Dominicana", "Robusto", "medium-full"),
    ("Fratello Oro Toro", "Fratello", "República Dominicana", "Toro", "medium-full"),
    ("Fratello Navetta Robusto", "Fratello", "República Dominicana", "Robusto", "medium"),
    ("Fratello Navetta Toro", "Fratello", "República Dominicana", "Toro", "medium"),
    # ── GURKHA ──────────────────────────────────────────────────────────────
    ("Gurkha Royal Challenge Robusto", "Gurkha", "República Dominicana", "Robusto", "mild"),
    ("Gurkha Royal Challenge Toro", "Gurkha", "República Dominicana", "Toro", "mild"),
    ("Gurkha Heritage Robusto", "Gurkha", "República Dominicana", "Robusto", "medium"),
    ("Gurkha Heritage Toro", "Gurkha", "República Dominicana", "Toro", "medium"),
    ("Gurkha Ghost Shadow Toro", "Gurkha", "República Dominicana", "Toro", "medium-full"),
    ("Gurkha Ghost Shadow Churchill", "Gurkha", "República Dominicana", "Churchill", "medium-full"),
    ("Gurkha Evil Robusto", "Gurkha", "República Dominicana", "Robusto", "full"),
    ("Gurkha Evil Toro", "Gurkha", "República Dominicana", "Toro", "full"),
    ("Gurkha Warpig Gordo", "Gurkha", "República Dominicana", "Gordo", "full"),
    ("Gurkha His Majesty's Reserve Robusto", "Gurkha", "República Dominicana", "Robusto", "medium-full"),
    # ── JOYA DE NICARAGUA ───────────────────────────────────────────────────
    ("Joya de Nicaragua Antano 1970 Robusto Grande", "Joya de Nicaragua", "Nicarágua", "Robusto", "full"),
    ("Joya de Nicaragua Antano 1970 Toro", "Joya de Nicaragua", "Nicarágua", "Toro", "full"),
    ("Joya de Nicaragua Antano 1970 Churchill", "Joya de Nicaragua", "Nicarágua", "Churchill", "full"),
    ("Joya de Nicaragua Antano 1970 El Martillo", "Joya de Nicaragua", "Nicarágua", "Gordo", "full"),
    ("Joya de Nicaragua Antano 1970 Gran Consul", "Joya de Nicaragua", "Nicarágua", "Double Corona", "full"),
    ("Joya de Nicaragua Antano 1970 Lancero", "Joya de Nicaragua", "Nicarágua", "Lancero", "full"),
    ("Joya de Nicaragua Antano Dark Corojo Robusto", "Joya de Nicaragua", "Nicarágua", "Robusto", "full"),
    ("Joya de Nicaragua Antano Dark Corojo Toro", "Joya de Nicaragua", "Nicarágua", "Toro", "full"),
    ("Joya de Nicaragua Antano Dark Corojo Gran Consul", "Joya de Nicaragua", "Nicarágua", "Double Corona", "full"),
    ("Joya de Nicaragua Clasico Robusto", "Joya de Nicaragua", "Nicarágua", "Robusto", "medium"),
    ("Joya de Nicaragua Clasico Toro", "Joya de Nicaragua", "Nicarágua", "Toro", "medium"),
    ("Joya de Nicaragua Clasico Churchill", "Joya de Nicaragua", "Nicarágua", "Churchill", "medium"),
    ("Joya de Nicaragua Clasico Lancero", "Joya de Nicaragua", "Nicarágua", "Lancero", "medium"),
    ("Joya de Nicaragua Red Robusto", "Joya de Nicaragua", "Nicarágua", "Robusto", "medium-full"),
    ("Joya de Nicaragua Red Toro", "Joya de Nicaragua", "Nicarágua", "Toro", "medium-full"),
    ("Joya de Nicaragua Red Gordo", "Joya de Nicaragua", "Nicarágua", "Gordo", "medium-full"),
    ("Joya de Nicaragua Cinco Decadas El Generalissimo", "Joya de Nicaragua", "Nicarágua", "Double Corona", "medium-full"),
    ("Joya de Nicaragua Cinco Decadas El Presidente", "Joya de Nicaragua", "Nicarágua", "Gordo", "medium-full"),
    ("Joya de Nicaragua Cinco Decadas Fundador", "Joya de Nicaragua", "Nicarágua", "Churchill", "medium-full"),
    ("Joya de Nicaragua Cabinetta Robusto", "Joya de Nicaragua", "Nicarágua", "Robusto", "medium"),
    ("Joya de Nicaragua Cabinetta Toro", "Joya de Nicaragua", "Nicarágua", "Toro", "medium"),
    # ── LA AURORA ───────────────────────────────────────────────────────────
    ("La Aurora 1962 Robusto", "La Aurora", "República Dominicana", "Robusto", "medium-full"),
    ("La Aurora 1962 Toro", "La Aurora", "República Dominicana", "Toro", "medium-full"),
    ("La Aurora 1962 Churchill", "La Aurora", "República Dominicana", "Churchill", "medium-full"),
    ("La Aurora 107 Robusto", "La Aurora", "República Dominicana", "Robusto", "medium-full"),
    ("La Aurora 107 Toro", "La Aurora", "República Dominicana", "Toro", "medium-full"),
    ("La Aurora Preferidos Cameroon Robusto", "La Aurora", "República Dominicana", "Robusto", "medium"),
    ("La Aurora Preferidos Maduro Churchill", "La Aurora", "República Dominicana", "Churchill", "full"),
    ("La Aurora Cien Anos Robusto", "La Aurora", "República Dominicana", "Robusto", "medium-full"),
    # ── LUIS MARTINEZ ───────────────────────────────────────────────────────
    ("Luis Martinez La Herencia Robusto", "Luis Martinez", "Honduras", "Robusto", "medium"),
    ("Luis Martinez La Herencia Toro", "Luis Martinez", "Honduras", "Toro", "medium"),
    ("Luis Martinez La Herencia Churchill", "Luis Martinez", "Honduras", "Churchill", "medium"),
    # ── MACANUDO ────────────────────────────────────────────────────────────
    ("Macanudo Cafe Hyde Park", "Macanudo", "República Dominicana", "Robusto", "mild"),
    ("Macanudo Cafe Prince Philip", "Macanudo", "República Dominicana", "Churchill", "mild"),
    ("Macanudo Cafe Montego Y", "Macanudo", "República Dominicana", "Lonsdale", "mild"),
    ("Macanudo Gold Label Robusto", "Macanudo", "República Dominicana", "Robusto", "mild"),
    ("Macanudo Gold Label Duke of Devon", "Macanudo", "República Dominicana", "Toro", "mild"),
    ("Macanudo Inspirado Orange Connecticut Robusto", "Macanudo", "República Dominicana", "Robusto", "mild"),
    ("Macanudo Inspirado Orange Connecticut Toro", "Macanudo", "República Dominicana", "Toro", "mild"),
    ("Macanudo Inspirado White Connecticut Robusto", "Macanudo", "República Dominicana", "Robusto", "mild"),
    ("Macanudo Inspirado Green Connecticut Robusto", "Macanudo", "República Dominicana", "Robusto", "mild"),
    # ── MF / MY FATHER ──────────────────────────────────────────────────────
    ("My Father Don Pepin Garcia Blue Label Robusto", "My Father", "Nicarágua", "Robusto", "full"),
    ("My Father Don Pepin Garcia Blue Label Toro", "My Father", "Nicarágua", "Toro", "full"),
    ("My Father Don Pepin Garcia Blue Label Churchill", "My Father", "Nicarágua", "Churchill", "full"),
    ("My Father Don Pepin Garcia Blue Label Lancero", "My Father", "Nicarágua", "Lancero", "full"),
    ("My Father Le Bijou 1922 Robusto", "My Father", "Nicarágua", "Robusto", "full"),
    ("My Father Le Bijou 1922 Toro", "My Father", "Nicarágua", "Toro", "full"),
    ("My Father Le Bijou 1922 Torpedo", "My Father", "Nicarágua", "Torpedo", "full"),
    ("My Father Flor de las Antillas Robusto", "My Father", "Nicarágua", "Robusto", "medium-full"),
    ("My Father Flor de las Antillas Toro", "My Father", "Nicarágua", "Toro", "medium-full"),
    ("My Father Flor de las Antillas Churchill", "My Father", "Nicarágua", "Churchill", "medium-full"),
    ("My Father Flor de las Antillas Maduro Robusto", "My Father", "Nicarágua", "Robusto", "full"),
    # ── MOMBACHO ────────────────────────────────────────────────────────────
    ("Mombacho Diplomatico Robusto", "Mombacho", "Nicarágua", "Robusto", "medium"),
    ("Mombacho Diplomatico Toro", "Mombacho", "Nicarágua", "Toro", "medium"),
    ("Mombacho Tierra Volcan Robusto", "Mombacho", "Nicarágua", "Robusto", "medium-full"),
    ("Mombacho Tierra Volcan Toro", "Mombacho", "Nicarágua", "Toro", "medium-full"),
    ("Mombacho Casa Magna Robusto", "Mombacho", "Nicarágua", "Robusto", "medium-full"),
    ("Mombacho Casa Magna Toro", "Mombacho", "Nicarágua", "Toro", "medium-full"),
    # ── MONTOSA ─────────────────────────────────────────────────────────────
    ("Montosa Robusto", "Montosa", "Nicarágua", "Robusto", "medium"),
    ("Montosa Toro", "Montosa", "Nicarágua", "Toro", "medium"),
    ("Montosa Churchill", "Montosa", "Nicarágua", "Churchill", "medium"),
    # ── NUB ─────────────────────────────────────────────────────────────────
    ("Nub Cameroon 460 Nub", "Oliva", "Nicarágua", "Gordo", "medium"),
    ("Nub Habano 460 Nub", "Oliva", "Nicarágua", "Gordo", "medium"),
    ("Nub Maduro 460 Nub", "Oliva", "Nicarágua", "Gordo", "full"),
    ("Nub Connecticut 460 Nub", "Oliva", "Nicarágua", "Gordo", "mild"),
    ("Nub Cameroon 358 Churchill", "Oliva", "Nicarágua", "Churchill", "medium"),
    ("Nub Habano 554 Toro", "Oliva", "Nicarágua", "Toro", "medium"),
    # ── OLIVA ───────────────────────────────────────────────────────────────
    ("Oliva Serie O Robusto", "Oliva", "Nicarágua", "Robusto", "medium"),
    ("Oliva Serie O Toro", "Oliva", "Nicarágua", "Toro", "medium"),
    ("Oliva Serie O Churchill", "Oliva", "Nicarágua", "Churchill", "medium"),
    ("Oliva Serie O Double Toro", "Oliva", "Nicarágua", "Gordo", "medium"),
    ("Oliva Serie G Robusto", "Oliva", "Nicarágua", "Robusto", "medium"),
    ("Oliva Serie G Toro", "Oliva", "Nicarágua", "Toro", "medium"),
    ("Oliva Serie G Churchill", "Oliva", "Nicarágua", "Churchill", "medium"),
    ("Oliva Serie G Double Toro", "Oliva", "Nicarágua", "Gordo", "medium"),
    ("Oliva Serie V Robusto", "Oliva", "Nicarágua", "Robusto", "medium-full"),
    ("Oliva Serie V Toro", "Oliva", "Nicarágua", "Toro", "medium-full"),
    ("Oliva Serie V Churchill", "Oliva", "Nicarágua", "Churchill", "medium-full"),
    ("Oliva Serie V Lancero", "Oliva", "Nicarágua", "Lancero", "medium-full"),
    ("Oliva Serie V Double Toro", "Oliva", "Nicarágua", "Gordo", "medium-full"),
    ("Oliva Serie V Figurado", "Oliva", "Nicarágua", "Torpedo", "medium-full"),
    ("Oliva Serie V Melanio Robusto", "Oliva", "Nicarágua", "Robusto", "full"),
    ("Oliva Serie V Melanio Toro", "Oliva", "Nicarágua", "Toro", "full"),
    ("Oliva Serie V Melanio Churchill", "Oliva", "Nicarágua", "Churchill", "full"),
    ("Oliva Serie V Melanio Figurado", "Oliva", "Nicarágua", "Torpedo", "full"),
    ("Oliva Serie V Melanio Double Toro", "Oliva", "Nicarágua", "Gordo", "full"),
    ("Oliva Master Blends 3 Robusto", "Oliva", "Nicarágua", "Robusto", "medium-full"),
    ("Oliva Master Blends 3 Toro", "Oliva", "Nicarágua", "Toro", "medium-full"),
    ("Oliva Cain F Toro", "Oliva", "Nicarágua", "Toro", "full"),
    ("Oliva Cain Daytona Robusto", "Oliva", "Nicarágua", "Robusto", "full"),
    # ── PARCERO BRASIL ──────────────────────────────────────────────────────
    ("Parcero Brasil Coronado Robusto", "Parcero", "Brasil", "Robusto", "medium"),
    ("Parcero Brasil Coronado Toro", "Parcero", "Brasil", "Toro", "medium"),
    ("Parcero Brasil Maduro Robusto", "Parcero", "Brasil", "Robusto", "medium-full"),
    ("Parcero Brasil Maduro Toro", "Parcero", "Brasil", "Toro", "medium-full"),
    # ── PERLA DEL MAR ───────────────────────────────────────────────────────
    ("Perla del Mar Connecticut Robusto", "Perla del Mar", "Nicarágua", "Robusto", "mild"),
    ("Perla del Mar Connecticut Toro", "Perla del Mar", "Nicarágua", "Toro", "mild"),
    ("Perla del Mar Habano Robusto", "Perla del Mar", "Nicarágua", "Robusto", "medium"),
    ("Perla del Mar Habano Toro", "Perla del Mar", "Nicarágua", "Toro", "medium"),
    ("Perla del Mar Maduro Robusto", "Perla del Mar", "Nicarágua", "Robusto", "full"),
    # ── QUORUM ──────────────────────────────────────────────────────────────
    ("Quorum Classic Robusto", "Quorum", "Nicarágua", "Robusto", "medium"),
    ("Quorum Classic Toro", "Quorum", "Nicarágua", "Toro", "medium"),
    ("Quorum Classic Churchill", "Quorum", "Nicarágua", "Churchill", "medium"),
    ("Quorum Shade Robusto", "Quorum", "Nicarágua", "Robusto", "mild"),
    ("Quorum Shade Toro", "Quorum", "Nicarágua", "Toro", "mild"),
    ("Quorum Maduro Robusto", "Quorum", "Nicarágua", "Robusto", "medium-full"),
    ("Quorum Maduro Toro", "Quorum", "Nicarágua", "Toro", "medium-full"),
    # ── REPOSADO 96 ─────────────────────────────────────────────────────────
    ("Reposado 96 Habano Robusto", "Reposado", "Nicarágua", "Robusto", "medium"),
    ("Reposado 96 Habano Toro", "Reposado", "Nicarágua", "Toro", "medium"),
    ("Reposado 96 Connecticut Robusto", "Reposado", "Nicarágua", "Robusto", "mild"),
    ("Reposado 96 Maduro Robusto", "Reposado", "Nicarágua", "Robusto", "medium-full"),
    # ── STEVE SAKA / DUNBARTON T&T ──────────────────────────────────────────
    ("Dunbarton Tobacco & Trust Pura Fe Robusto", "Dunbarton T&T", "Nicarágua", "Robusto", "medium-full"),
    ("Dunbarton Tobacco & Trust Pura Fe Toro", "Dunbarton T&T", "Nicarágua", "Toro", "medium-full"),
    ("Dunbarton Tobacco & Trust Pura Fe Churchill", "Dunbarton T&T", "Nicarágua", "Churchill", "medium-full"),
    ("Dunbarton Tobacco & Trust Mi Querida Ancho Largo", "Dunbarton T&T", "Nicarágua", "Gordo", "full"),
    ("Dunbarton Tobacco & Trust Mi Querida Toro", "Dunbarton T&T", "Nicarágua", "Toro", "full"),
    ("Dunbarton Tobacco & Trust Mi Querida Oscuro Robusto", "Dunbarton T&T", "Nicarágua", "Robusto", "full"),
    ("Dunbarton Tobacco & Trust Sobremesa Brûlée Robusto", "Dunbarton T&T", "Nicarágua", "Robusto", "medium"),
    ("Dunbarton Tobacco & Trust Sobremesa Brûlée Toro", "Dunbarton T&T", "Nicarágua", "Toro", "medium"),
    ("Dunbarton Tobacco & Trust Motita Robusto", "Dunbarton T&T", "Nicarágua", "Robusto", "medium-full"),
    # ── VEGAFINA ────────────────────────────────────────────────────────────
    ("Vegafina 1998 Robusto", "Vegafina", "República Dominicana", "Robusto", "mild"),
    ("Vegafina 1998 Toro", "Vegafina", "República Dominicana", "Toro", "mild"),
    ("Vegafina 1998 Churchill", "Vegafina", "República Dominicana", "Churchill", "mild"),
    ("Vegafina Classic Robusto", "Vegafina", "República Dominicana", "Robusto", "mild"),
    ("Vegafina Classic Toro", "Vegafina", "República Dominicana", "Toro", "mild"),
    ("Vegafina Nicaragua Robusto", "Vegafina", "Nicarágua", "Robusto", "medium-full"),
    ("Vegafina Nicaragua Toro", "Vegafina", "Nicarágua", "Toro", "medium-full"),
    ("Vegafina Nicaragua Churchill", "Vegafina", "Nicarágua", "Churchill", "medium-full"),
    ("Vegafina Serie 2 Robusto", "Vegafina", "República Dominicana", "Robusto", "medium"),
    ("Vegafina Serie 2 Toro", "Vegafina", "República Dominicana", "Toro", "medium"),
]


def main() -> None:
    existing_slugs: set[str] = set()
    with CATALOG.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing_slugs.add(row["slug"].strip())

    new_rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for name, brand, country, vitola, strength in ENTRIES:
        slug = slugify(name)
        if slug in existing_slugs or slug in seen:
            continue
        seen.add(slug)
        new_rows.append(
            {
                "slug": slug,
                "name": name,
                "brand": brand,
                "country": country,
                "vitola": vitola,
                "strength": strength,
                "factory": "",
            }
        )

    with CATALOG.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["slug", "name", "brand", "country", "vitola", "strength", "factory"])
        writer.writerows(new_rows)

    total = len(existing_slugs) + len(new_rows)
    print(f"✓ +{len(new_rows)} entradas novas  |  total no catálogo: {total}")


if __name__ == "__main__":
    main()
