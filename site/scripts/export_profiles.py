#!/usr/bin/env python3
"""Export country-profile datasets (D5–D8) for the Observable Framework site.

Spec: docs/SITE_SPECS.md §4.2, §5.2 (contracts) and §10 (performance budget).
Source logic mirrors country_trade_profile.ipynb §1–§3, with two deliberate
refinements (documented in the per-country meta.json):

* mirror totals always sum the individual partner reports (verified live:
  the API returns no 'World' reporter row for reporter=all, and reporter=0
  returns empty) — the World row is never mixed into an aggregate, so the
  double counting a naive sum would risk cannot occur;
* partner/product names are emitted in Portuguese (curated dictionary with
  English fallback), matching the site's language.

Runs locally from the repo venv; reuses the comtradetools cache (cache/) and the
API key (config.ini). Fully resumable: re-running skips API chunks already in
cache, so after an interrupt just run the same command again.

Usage (from the repo root):
    venv/bin/python site/scripts/export_profiles.py                 # all 9 PLPs
    venv/bin/python site/scripts/export_profiles.py --countries angola brasil
    venv/bin/python site/scripts/export_profiles.py --end 2024

Query plan (per docs/SITE_SPECS.md §5.2, D5–D8):
    Q1/Q2  reporter=<9 PLPs>, partner=all, flow X/M, TOTAL   -> D5-direct + D6-direct
    Q3/Q4  reporter=all, partner=<9 PLPs>, flow M/X, TOTAL   -> D5-mirror + D6-mirror
    D7d    reporter=C, partner=World, flow X/M, AG6          -> direct top products
    D7m    strong direct reporters: derived from the D8 mirror frame;
           weak direct reporters: full reporter=all AG6 fetch (small there)
    D8     reporter=C partner=all / reporter=all partner=C, restricted to the
           all-time top HS6 codes via cmdCode CSV lists      -> product x partner

Mirror-side convention (verified live 2026-07-19): reporter=all responses
carry NO 'World' reporter row and reporterCode='0' returns empty, so mirror
totals and share bases always sum the individual reporters; the World row is
never mixed in (the notebook's blanket sum would double count if it were).
Direct-side product totals use the partnerCode=0 (World) rows of the
country's own AG6 report.

Large AG6 responses: fetch_guarded sanity-checks every result against the
per-call API record cap and refetches year by year only when suspicious —
period splitting and caching stay inside comtradetools.getFinalData.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "site" / "src" / "data"

# Profiled countries: slug -> (M49 code, Portuguese name). The slug is used in
# filenames and in /perfis/<slug> routes.
COUNTRIES = {
    "angola": (24, "Angola"),
    "brasil": (76, "Brasil"),
    "cabo-verde": (132, "Cabo Verde"),
    "guine-bissau": (624, "Guiné-Bissau"),
    "guine-equatorial": (226, "Guiné Equatorial"),
    "mocambique": (508, "Moçambique"),
    "portugal": (620, "Portugal"),
    "sao-tome-e-principe": (678, "São Tomé e Príncipe"),
    "timor-leste": (626, "Timor-Leste"),
}

SOURCE_NOTEBOOK = "country_trade_profile.ipynb"
TOP_N = 10            # rows kept per (year, basis) in D6/D7 (spec §10)
D8_COVERAGE = 25      # all-time top products whose product×partner detail is fetched
D8_PARTNERS = 8       # partners kept per (year, hs6, basis) in D8
STRONG_YEARS = 15     # direct AG6 covering >= this many years = "strong reporter"
ROW_CAP = 99_000  # a single API call near the record cap is probably truncated
D11_PARTNERS = 5       # all-time top direct partners in the competition analysis
D11_PRODUCTS = 8       # all-time top direct HS6 products per direction
D11_COMPETITORS = 5    # competitors kept per (year, partner, hs6), besides the country

# Portuguese names for frequent trade partners, keyed by Comtrade English
# reporter/partner names. Resolved to M49 codes via comtradetools at runtime;
# unknown partners fall back to their Comtrade English name.
# NOTE: keep the project's naming for China's special regions.
PARTNERS_EN2PT = {
    "China": "China",
    "China, Macao SAR": "Macau (RAEM)",
    "China, Hong Kong SAR": "Hong Kong (RAEHK)",
    "Other Asia, nes": "Taiwan (Prov. China)",
    "USA": "EUA",
    "Germany": "Alemanha",
    "Spain": "Espanha",
    "France": "França",
    "Italy": "Itália",
    "Netherlands": "Países Baixos",
    "United Kingdom": "Reino Unido",
    "Belgium": "Bélgica",
    "Switzerland": "Suíça",
    "Sweden": "Suécia",
    "Norway": "Noruega",
    "Denmark": "Dinamarca",
    "Finland": "Finlândia",
    "Poland": "Polónia",
    "Austria": "Áustria",
    "Ireland": "Irlanda",
    "Greece": "Grécia",
    "Portugal": "Portugal",
    "Türkiye": "Turquia",
    "Russian Federation": "Rússia",
    "Ukraine": "Ucrânia",
    "India": "Índia",
    "Japan": "Japão",
    "Rep. of Korea": "Coreia do Sul",
    "Dem. People's Rep. of Korea": "Coreia do Norte",
    "Singapore": "Singapura",
    "Thailand": "Tailândia",
    "Viet Nam": "Vietname",
    "Indonesia": "Indonésia",
    "Malaysia": "Malásia",
    "Philippines": "Filipinas",
    "Australia": "Austrália",
    "New Zealand": "Nova Zelândia",
    "Canada": "Canadá",
    "Mexico": "México",
    "Argentina": "Argentina",
    "Chile": "Chile",
    "Colombia": "Colômbia",
    "Peru": "Peru",
    "Uruguay": "Uruguai",
    "Paraguay": "Paraguai",
    "Brazil": "Brasil",
    "South Africa": "África do Sul",
    "Nigeria": "Nigéria",
    "Egypt": "Egito",
    "Morocco": "Marrocos",
    "Algeria": "Argélia",
    "Saudi Arabia": "Arábia Saudita",
    "United Arab Emirates": "Emirados Árabes Unidos",
    "Qatar": "Catar",
    "Kuwait": "Kuwait",
    "Iraq": "Iraque",
    "Iran": "Irão",
    "Israel": "Israel",
    "Bangladesh": "Bangladesh",
    "Pakistan": "Paquistão",
    "Sri Lanka": "Sri Lanka",
    "Cameroon": "Camarões",
    "Bulgaria": "Bulgária",
    "Estonia": "Estónia",
    "Latvia": "Letónia",
    "Lithuania": "Lituânia",
    "Romania": "Roménia",
    "Hungary": "Hungria",
    "Slovakia": "Eslováquia",
    "Slovenia": "Eslovénia",
    "Croatia": "Croácia",
    "Serbia": "Sérvia",
    "Czechia": "Chéquia",
    "Luxembourg": "Luxemburgo",
    "Iceland": "Islândia",
    "Malta": "Malta",
    "Cyprus": "Chipre",
    "Belarus": "Bielorrússia",
    "Kazakhstan": "Cazaquistão",
    "Ghana": "Gana",
    "Côte d'Ivoire": "Costa do Marfim",
    "Kenya": "Quénia",
    "United Rep. of Tanzania": "Tanzânia",
    "Dem. Rep. of the Congo": "RD Congo",
    "Congo": "Congo",
    "Senegal": "Senegal",
    "Benin": "Benim",
    "Togo": "Togo",
    "Gabon": "Gabão",
    "Namibia": "Namíbia",
    "Botswana": "Botsuana",
    "Zambia": "Zâmbia",
    "Zimbabwe": "Zimbabué",
    "Ethiopia": "Etiópia",
    "Uganda": "Uganda",
    "Mauritania": "Mauritânia",
    "Mauritius": "Maurícias",
    "Comoros": "Comores",
    "Madagascar": "Madagáscar",
    "Dominican Rep.": "República Dominicana",
    "Cuba": "Cuba",
    "Venezuela": "Venezuela",
    "Bolivia (Plurinational State of)": "Bolívia",
    "Ecuador": "Equador",
    "Guatemala": "Guatemala",
    "Honduras": "Honduras",
    "Costa Rica": "Costa Rica",
    "Panama": "Panamá",
    "Oman": "Omã",
    "Bahrain": "Barém",
    "Jordan": "Jordânia",
    "Lebanon": "Líbano",
    "Angola": "Angola",
    "Cabo Verde": "Cabo Verde",
    "Guinea-Bissau": "Guiné-Bissau",
    "Equatorial Guinea": "Guiné Equatorial",
    "Mozambique": "Moçambique",
    "Sao Tome and Principe": "São Tomé e Príncipe",
    "Timor-Leste": "Timor-Leste",
}

# Portuguese labels for HS6 products frequent in PLP trade; other codes fall
# back to the English HS description from comtradetools.HS_CODES.
HS_PT = {
    "0302": "Peixe fresco ou refrigerado",
    "0303": "Peixe congelado",
    "0304": "Filetes de peixe",
    "0306": "Crustáceos",
    "0307": "Moluscos",
    "0801": "Cocos, castanhas de caju e nozes",
    "0901": "Café",
    "0902": "Chá",
    "1006": "Arroz",
    "1201": "Soja",
    "1507": "Óleo de soja",
    "1511": "Óleo de palma",
    "1701": "Açúcar de cana ou de beterraba",
    "1801": "Cacau",
    "2203": "Cerveja",
    "2204": "Vinho",
    "2401": "Tabaco não manufaturado",
    "2402": "Cigarros",
    "2501": "Sal",
    "2601": "Minério de ferro",
    "2603": "Minério de cobre",
    "2709": "Petróleo bruto",
    "2710": "Combustíveis refinados",
    "2711": "Gás natural e outros gases de petróleo",
    "2713": "Coque de petróleo e betume",
    "3004": "Medicamentos",
    "3901": "Polímeros de etileno",
    "4403": "Madeira em bruto",
    "4407": "Madeira serrada",
    "5201": "Algodão em fibra",
    "7102": "Diamantes",
    "7108": "Ouro",
    "7403": "Cobre refinado",
    "7601": "Alumínio em bruto",
    "8703": "Automóveis de passageiros",
    "8704": "Veículos de mercadorias",
    "8901": "Navios",
    # 4-digit headings that occur anywhere in the exported site data — short
    # PT labels in the same informal style (added 2026-07-22 after the mixed
    # PT/EN labels on the profile pages were flagged).
    "0202": "Carne de bovino, congelada",
    "0207": "Carne de aves",
    "0305": "Peixe seco ou salgado",
    "0401": "Leite e natas, não concentrados",
    "0402": "Leite e natas, concentrados ou em pó",
    "0602": "Plantas vivas",
    "0603": "Flores cortadas",
    "0709": "Legumes frescos ou refrigerados",
    "0713": "Leguminosas secas",
    "0714": "Raízes e tubérculos (mandioca, etc.)",
    "0802": "Frutos de casca rija",
    "0803": "Bananas",
    "0809": "Frutos frescos (pêssegos, etc.)",
    "0813": "Frutos secos",
    "0904": "Pimenta e pimentão",
    "0905": "Baunilha",
    "1001": "Trigo",
    "1005": "Milho",
    "1101": "Farinha de trigo",
    "1203": "Copra",
    "1205": "Sementes de colza",
    "1207": "Outras sementes oleaginosas",
    "1210": "Lúpulo",
    "1211": "Plantas para farmácia e perfumaria",
    "1212": "Algas e produtos vegetais para alimentação",
    "1302": "Seivas e extratos vegetais",
    "1404": "Produtos vegetais diversos",
    "1504": "Óleos de peixe",
    "1508": "Óleo de amendoim",
    "1509": "Azeite",
    "1513": "Óleo de coco",
    "1515": "Outros óleos vegetais fixos",
    "1601": "Enchidos e produtos semelhantes",
    "1604": "Peixe preparado ou conservado",
    "1803": "Pasta de cacau",
    "1806": "Chocolate e preparações com cacau",
    "1901": "Preparações para alimentação infantil",
    "1902": "Massas alimentícias",
    "1905": "Waffles e bolachas",
    "2001": "Preparações de legumes e frutos",
    "2002": "Tomate preparado ou conservado",
    "2008": "Frutos e sementes preparados",
    "2009": "Sumos de frutos",
    "2101": "Extratos de café e chicória",
    "2102": "Leveduras",
    "2103": "Molhos e condimentos",
    "2104": "Sopas e caldos",
    "2106": "Outras preparações alimentares",
    "2201": "Águas minerais e gaseificadas",
    "2202": "Bebidas não alcoólicas",
    "2206": "Bebidas fermentadas (sidra, hidromel)",
    "2208": "Bebidas espirituosas",
    "2301": "Farinhas de carne ou de peixe",
    "2304": "Resíduos da extração de óleo de soja",
    "2309": "Alimentos para animais",
    "2505": "Areias naturais",
    "2515": "Mármore e travertino",
    "2516": "Granito",
    "2523": "Cimento",
    "2606": "Minério de alumínio",
    "2614": "Minério de titânio",
    "2615": "Minério de zircónio",
    "2701": "Carvão mineral",
    "2703": "Turfa",
    "2704": "Coque",
    "2707": "Produtos da destilação do alcatrão",
    "2716": "Energia elétrica",
    "2809": "Ácido fosfórico",
    "2818": "Óxido de alumínio",
    "2826": "Fluoretos",
    "2901": "Hidrocarbonetos acíclicos",
    "2905": "Álcoois acíclicos",
    "2909": "Éteres e derivados",
    "2933": "Compostos heterocíclicos",
    "2942": "Outros compostos orgânicos",
    "3002": "Sangue, vacinas e produtos imunológicos",
    "3003": "Medicamentos (sem doses unitárias)",
    "3102": "Fertilizantes azotados",
    "3104": "Fertilizantes potássicos",
    "3105": "Outros fertilizantes",
    "3208": "Tintas e vernizes",
    "3401": "Sabão",
    "3802": "Produtos minerais ativados",
    "3815": "Catalisadores",
    "3823": "Ácidos gordos industriais",
    "3824": "Outros produtos químicos",
    "3902": "Polímeros de propileno",
    "3907": "Poliésteres em formas primárias",
    "3917": "Tubos de plástico",
    "3923": "Artigos de plástico para embalagem",
    "3924": "Artigos de plástico domésticos",
    "3925": "Artigos de plástico para construção",
    "3926": "Outros artigos de plástico",
    "4001": "Borracha natural",
    "4005": "Borracha não vulcanizada composta",
    "4011": "Pneus novos",
    "4015": "Luvas e vestuário de borracha",
    "4202": "Malas, bolsas e carteiras",
    "4401": "Lenha e resíduos de madeira",
    "4408": "Folhas de madeira para folheados",
    "4413": "Madeira densificada",
    "4418": "Portas e artigos de carpintaria",
    "4503": "Rolhas de cortiça",
    "4504": "Cortiça aglomerada",
    "4602": "Artigos de cestaria",
    "4703": "Pasta de madeira química",
    "4801": "Papel de jornal",
    "4802": "Papel para escrita e impressão",
    "4805": "Outros papéis não revestidos",
    "4901": "Livros e brochuras",
    "4907": "Selos e títulos de valor",
    "4911": "Outros impressos",
    "5001": "Seda e casulos",
    "5203": "Algodão cardado ou penteado",
    "5702": "Tapetes tecidos",
    "5705": "Outros tapetes",
    "6107": "Roupa interior de malha (homem)",
    "6109": "T-shirts e camisetas de malha",
    "6203": "Calças e fatos (homem)",
    "6204": "Calças, conjuntos e casacos (mulher)",
    "6205": "Camisas (homem)",
    "6210": "Vestuário de tecidos impermeáveis",
    "6211": "Outro vestuário",
    "6304": "Artigos de decoração têxteis",
    "6307": "Outros artigos têxteis confecionados",
    "6309": "Vestuário usado",
    "6403": "Calçado de couro",
    "6406": "Partes de calçado",
    "6702": "Flores artificiais",
    "6704": "Perucas e artigos semelhantes",
    "6807": "Artigos asfálticos em rolos",
    "6810": "Artigos de cimento e betão",
    "6904": "Materiais cerâmicos de construção",
    "6908": "Azulejos e ladrilhos cerâmicos",
    "6911": "Louça de porcelana",
    "7020": "Outros artigos de vidro",
    "7103": "Rubis, safiras e esmeraldas",
    "7202": "Ferro-ligas",
    "7204": "Sucata ferrosa",
    "7207": "Produtos semi-acabados de ferro ou aço",
    "7209": "Laminados planos a frio",
    "7210": "Laminados planos revestidos",
    "7214": "Varões de ferro ou aço",
    "7215": "Outros varões de ferro ou aço",
    "7225": "Laminados planos de aços-liga",
    "7226": "Outros laminados de aços-liga",
    "7228": "Varões de aços-liga",
    "7301": "Perfis de ferro ou aço soldados",
    "7304": "Tubos sem costura (petróleo/gás)",
    "7305": "Tubos para oleodutos e gasodutos",
    "7306": "Outros tubos de ferro ou aço",
    "7307": "Acessórios para tubos",
    "7308": "Estruturas de ferro ou aço",
    "7311": "Recipientes para gás comprimido",
    "7315": "Correntes de ferro ou aço",
    "7316": "Âncoras e ferros de amarração",
    "7323": "Artigos domésticos de aço inox",
    "7326": "Outros artigos de ferro ou aço",
    "7408": "Fios de cobre",
    "7602": "Sucata de alumínio",
    "7604": "Varões e perfis de alumínio",
    "7605": "Fios de alumínio",
    "7614": "Cabos de alumínio",
    "7801": "Chumbo em bruto",
    "8201": "Ferramentas agrícolas manuais",
    "8205": "Martelos e ferramentas manuais",
    "8307": "Tubos flexíveis de metal",
    "8403": "Caldeiras de aquecimento central",
    "8407": "Motores de ignição por faísca",
    "8408": "Motores diesel",
    "8409": "Partes de motores",
    "8411": "Turborreatores e turbinas a gás",
    "8413": "Bombas para líquidos",
    "8414": "Bombas e compressores de ar",
    "8419": "Esterilizadores e autoclaves",
    "8421": "Máquinas de filtrar líquidos",
    "8422": "Máquinas de embalar",
    "8424": "Máquinas de projeção de jatos",
    "8426": "Gruas e guindastes",
    "8428": "Outras máquinas de elevação",
    "8429": "Buldózeres e niveladoras",
    "8430": "Máquinas de perfuração e escavação",
    "8431": "Partes de máquinas de terraplanagem",
    "8433": "Cortadores de relva",
    "8441": "Máquinas para papel e cartão",
    "8462": "Máquinas-ferramenta de forja e estampagem",
    "8467": "Ferramentas pneumáticas e portáteis",
    "8471": "Computadores e unidades",
    "8473": "Partes de computadores",
    "8474": "Máquinas de triagem de minerais",
    "8479": "Máquinas de funções diversas",
    "8480": "Moldes para borracha ou plástico",
    "8481": "Válvulas e torneiras",
    "8483": "Engrenagens e transmissões",
    "8484": "Juntas e gaxetas",
    "8501": "Motores e geradores elétricos",
    "8502": "Grupos geradores",
    "8503": "Partes de máquinas elétricas",
    "8504": "Conversores elétricos estáticos",
    "8507": "Acumuladores elétricos",
    "8509": "Eletrodomésticos",
    "8516": "Aparelhos eletrotérmicos",
    "8517": "Aparelhos de telecomunicações",
    "8523": "Suportes de gravação",
    "8525": "Aparelhos de transmissão e câmaras",
    "8527": "Recetores de rádio",
    "8528": "Aparelhos de televisão",
    "8529": "Partes de aparelhos de rádio e TV",
    "8532": "Condensadores elétricos",
    "8533": "Resistências elétricas",
    "8534": "Circuitos impressos",
    "8536": "Aparelhos de proteção de circuitos",
    "8537": "Quadros de controlo e distribuição",
    "8538": "Partes de aparelhos elétricos",
    "8541": "Díodos e células fotovoltaicas",
    "8542": "Circuitos integrados",
    "8544": "Fios e cabos elétricos isolados",
    "8548": "Partes elétricas diversas",
    "8602": "Locomotivas diesel-elétricas",
    "8609": "Contentores de transporte",
    "8701": "Tratores rodoviários",
    "8702": "Autocarros",
    "8705": "Veículos especiais (gruas, oficinas)",
    "8708": "Partes e acessórios de veículos",
    "8711": "Motociclos",
    "8716": "Reboques e outros veículos",
    "8802": "Helicópteros e aviões",
    "8803": "Partes de aeronaves",
    "8807": "Partes de aviões e helicópteros",
    "8902": "Navios de pesca",
    "8903": "Iates e barcos de recreio",
    "8904": "Rebocadores",
    "8905": "Plataformas e dragas",
    "8906": "Outros navios",
    "8908": "Navios para demolição",
    "9004": "Óculos",
    "9007": "Câmaras cinematográficas",
    "9015": "Instrumentos de topografia",
    "9018": "Instrumentos médico-cirúrgicos",
    "9026": "Instrumentos de medição de fluidos",
    "9027": "Instrumentos de análise físico-química",
    "9029": "Contadores e tacómetros",
    "9030": "Instrumentos para telecomunicações",
    "9031": "Outros instrumentos de medição",
    "9032": "Instrumentos de regulação automática",
    "9033": "Partes de instrumentos de precisão",
    "9201": "Pianos e instrumentos de teclado",
    "9207": "Instrumentos amplificados eletricamente",
    "9301": "Armas militares",
    "9304": "Outras armas de fogo",
    "9305": "Partes de armas",
    "9306": "Munições",
    "9401": "Assentos e partes",
    "9403": "Mobiliário",
    "9406": "Construções pré-fabricadas",
    "9507": "Anzóis",
    "9605": "Estojos de viagem",
    # pseudo HS code used by Comtrade for unclassified trade
    "999999": "Mercadorias não especificadas",
    # 6-digit disambiguation: codes whose 4-digit heading label collides with
    # a sibling somewhere in the site data (e.g. 100630/100640 both "Arroz").
    # Exact entries take precedence over the heading fallback in hs_label_pt.
    "100610": "Arroz com casca (paddy)",
    "100620": "Arroz descascado (integral)",
    "100630": "Arroz semibranqueado ou branqueado",
    "100640": "Arroz partido",
    "121220": "Algas para alimentação",
    "121299": "Outros produtos vegetais para alimentação",
    "760110": "Alumínio não ligado, em bruto",
    "760120": "Ligas de alumínio, em bruto",
    "851712": "Telemóveis",
    "851730": "Aparelhos de comutação telefónica",
    "851762": "Routers e aparelhos de dados",
    "851770": "Partes de telemóveis e telefones",
    "851779": "Partes de aparelhos de comunicação",
    "851790": "Partes de aparelhos de telecomunicação (ed. antiga)",
    "852520": "Aparelhos transmissores-recetores",
    "852560": "Aparelhos de transmissão para rádio e TV",
    "852580": "Câmaras de televisão e câmaras digitais",
    "392410": "Louça de plástico",
    "392490": "Artigos domésticos de plástico, outros",
    "870321": "Automóveis a gasolina até 1.000 cm³",
    "870322": "Automóveis a gasolina 1.000–1.500 cm³",
    "870323": "Automóveis a gasolina 1.500–3.000 cm³",
    "870324": "Automóveis a gasolina +3.000 cm³",
    "870331": "Automóveis diesel até 1.500 cm³",
    "870332": "Automóveis diesel 1.500–2.500 cm³",
    "870333": "Automóveis diesel +2.500 cm³",
    "870380": "Automóveis elétricos",
    "870390": "Outros automóveis de passageiros",
    "170111": "Açúcar de cana, em bruto",
    "170114": "Açúcar de cana, em bruto (outros)",
    "170191": "Açúcar com aromatizantes ou corantes",
    "170199": "Açúcar refinado",
    "090500": "Baunilha (ed. antiga)",
    "090510": "Baunilha não moída",
    "220830": "Whisky",
    "220840": "Rum e aguardente de cana",
    "220850": "Gin e genebra",
    "220890": "Outras bebidas espirituosas",
    "220210": "Águas com açúcar ou gaseificadas",
    "220290": "Bebidas não alcoólicas (ed. antiga)",
    "220299": "Outras bebidas não alcoólicas",
    "841440": "Compressores de ar móveis",
    "841480": "Outras bombas e compressores de ar",
    "841330": "Bombas de combustível para motores",
    "841381": "Outras bombas para líquidos",
    "841391": "Partes de bombas para líquidos",
    "400122": "Borracha natural tecnicamente especificada",
    "400129": "Borracha natural, outras formas",
    "842911": "Buldózeres de lagartas",
    "842919": "Outros buldózeres",
    "842920": "Niveladoras",
    "842940": "Compactadores e cilindros",
    "842951": "Pás carregadoras frontais",
    "842952": "Escavadoras de rotação 360°",
    "842959": "Outras escavadoras e pás carregadoras",
    "090111": "Café verde não descafeinado",
    "090112": "Café verde descafeinado",
    "090121": "Café torrado não descafeinado",
    "090190": "Cascas de café e sucedâneos",
    "640391": "Calçado de couro a cobrir o tornozelo",
    "640399": "Calçado de couro sem cobrir o tornozelo",
    "620342": "Calças de algodão (homem)",
    "620349": "Calças de outras fibras (homem)",
    "620423": "Conjuntos de fibras sintéticas (mulher)",
    "620433": "Casacos de fibras sintéticas (mulher)",
    "020712": "Galinhas inteiras congeladas",
    "020714": "Cortes e miudezas de galinha congelados",
    "270112": "Carvão betuminoso",
    "270119": "Outros carvões minerais",
    "180610": "Cacau em pó com açúcar",
    "180620": "Chocolate em tabletes +2 kg",
    "180631": "Chocolate em tabletes, recheado",
    "180632": "Chocolate em tabletes, não recheado",
    "180690": "Outras preparações de chocolate",
    "252310": "Clínquer",
    "252329": "Cimento Portland",
    "854221": "Circuitos integrados digitais (ed. antiga)",
    "854231": "Processadores e controladores",
    "854232": "Memórias",
    "854239": "Outros circuitos integrados",
    "854270": "Microconjuntos eletrónicos (ed. antiga)",
    "080111": "Coco desidratado",
    "080119": "Coco fresco ou seco, outros",
    "080131": "Castanha de caju com casca",
    "080132": "Castanha de caju sem casca",
    "271000": "Óleos de petróleo (ed. antiga)",
    "271011": "Óleos leves de petróleo (ed. antiga)",
    "271012": "Gasolinas e destilados leves",
    "271019": "Gasóleo e combustíveis médios e pesados",
    "847110": "Computadores analógicos e híbridos (ed. antiga)",
    "847130": "Computadores portáteis",
    "847141": "Computadores com CPU e ecrã integrados",
    "847160": "Unidades de entrada e saída de computadores",
    "847180": "Outras unidades de computadores",
    "030613": "Camarões congelados",
    "030619": "Outros crustáceos congelados",
    "030621": "Camarões frescos ou refrigerados",
    "710221": "Diamantes industriais em bruto",
    "710231": "Diamantes não industriais em bruto",
    "854140": "Díodos fotossensíveis (ed. antiga)",
    "854143": "Células fotovoltaicas em módulos",
    "730820": "Torres e mastros de ferro ou aço",
    "730840": "Andaimes e escoramentos",
    "730890": "Outras estruturas de ferro ou aço",
    "230110": "Farinhas de carne",
    "230120": "Farinhas de peixe",
    "030420": "Filetes de peixe congelados",
    "030489": "Filetes de peixe congelados, outros peixes",
    "854430": "Cablagens de ignição para veículos",
    "854449": "Condutores elétricos até 1.000 V",
    "854470": "Cabos de fibra ótica",
    "282612": "Fluoretos de alumínio",
    "282619": "Outros fluoretos",
    "080221": "Avelãs com casca",
    "080222": "Avelãs sem casca",
    "200819": "Frutos de casca rija preparados",
    "200820": "Ananás preparado ou conservado",
    "842619": "Pórticos e pontes rolantes",
    "842641": "Gruas autopropelidas sobre pneus",
    "842649": "Outras gruas autopropelidas",
    "850211": "Grupos geradores diesel até 75 kVA",
    "850213": "Grupos geradores diesel +375 kVA",
    "850220": "Grupos geradores a gasolina",
    "850239": "Outros grupos geradores",
    "271111": "Gás natural liquefeito (GNL)",
    "271112": "Propano liquefeito",
    "271113": "Butano liquefeito",
    "271119": "Outros gases de petróleo liquefeitos",
    "271121": "Gás natural em estado gasoso",
    "271129": "Outros hidrocarbonetos gasosos",
    "880211": "Helicópteros até 2.000 kg",
    "880212": "Helicópteros +2.000 kg",
    "880220": "Aviões até 2.000 kg",
    "880230": "Aviões 2.000–15.000 kg",
    "880240": "Aviões +15.000 kg",
    "890391": "Veleiros de recreio",
    "890399": "Outros barcos de recreio",
    "902710": "Aparelhos de análise de gases",
    "902780": "Outros instrumentos de análise físico-química",
    "902610": "Medidores de fluxo ou nível de líquidos",
    "902690": "Partes de instrumentos de medição",
    "901580": "Instrumentos de topografia",
    "901590": "Partes de instrumentos de topografia",
    "721041": "Laminados ondulados zincados",
    "721070": "Laminados pintados ou revestidos",
    "071333": "Feijão comum seco",
    "071390": "Outras leguminosas secas",
    "040221": "Leite em pó sem açúcar",
    "040229": "Leite em pó com açúcar",
    "040299": "Leite concentrado com açúcar, outros",
    "440310": "Madeira em bruto tratada",
    "440349": "Madeira tropical em bruto",
    "440399": "Outra madeira em bruto",
    "440710": "Madeira serrada de coníferas",
    "440729": "Madeira tropical serrada",
    "440791": "Madeira serrada de carvalho",
    "440792": "Madeira serrada de faia",
    "440799": "Outra madeira serrada",
    "420229": "Malas e bolsas de mão",
    "420231": "Carteiras e bolsas de bolso",
    "820520": "Martelos e malhos",
    "820559": "Outras ferramentas manuais",
    "190220": "Massas recheadas",
    "190230": "Outras massas preparadas",
    "300310": "Medicamentos com penicilina (sem doses)",
    "300390": "Outros medicamentos (sem doses)",
    "260111": "Minério de ferro não aglomerado",
    "260112": "Minério de ferro aglomerado",
    "940360": "Mobiliário de madeira, outros",
    "940380": "Mobiliário de outros materiais",
    "030729": "Vieiras",
    "030743": "Chocos e lulas congelados",
    "030749": "Chocos e lulas secos ou salgados",
    "030752": "Polvo congelado",
    "030759": "Polvo seco ou salgado",
    "871110": "Motociclos até 50 cm³",
    "871120": "Motociclos 50–250 cm³",
    "871190": "Outros motociclos",
    "840710": "Motores de aviação a faísca",
    "840790": "Outros motores de ignição por faísca",
    "840820": "Motores diesel para veículos",
    "840890": "Motores diesel, outros",
    "850131": "Motores e geradores DC até 750 W",
    "850134": "Motores e geradores DC +375 kW",
    "850161": "Alternadores até 75 kVA",
    "850164": "Alternadores +750 kVA",
    "847920": "Máquinas de extração de óleos vegetais",
    "847989": "Máquinas de funções diversas",
    "847990": "Partes de máquinas de funções diversas",
    "843010": "Bate-estacas",
    "843039": "Máquinas de abertura de túneis",
    "843041": "Máquinas de perfuração autopropelidas",
    "843049": "Outras máquinas de perfuração",
    "844180": "Máquinas para papel e cartão",
    "844190": "Partes de máquinas para papel",
    "890110": "Navios de cruzeiro",
    "890120": "Navios-tanque",
    "890190": "Navios de carga",
    "710812": "Ouro em bruto",
    "710813": "Ouro semimanufaturado",
    "120740": "Sementes de sésamo (gergelim)",
    "120799": "Outras sementes oleaginosas",
    "732619": "Artigos de ferro forjado ou estampado",
    "732620": "Artigos de arame de ferro ou aço",
    "732690": "Outros artigos de ferro ou aço",
    "890610": "Navios de guerra",
    "890690": "Outros navios (botes salva-vidas, etc.)",
    "880310": "Hélices e rotores de aeronaves",
    "880330": "Partes de aviões e helicópteros (ed. antiga)",
    "880390": "Partes de outras aeronaves (ed. antiga)",
    "852910": "Antenas e refletores",
    "852990": "Outras partes de aparelhos de rádio e TV",
    "930591": "Partes de armas militares",
    "930599": "Partes de outras armas de fogo",
    "880730": "Partes de aviões e helicópteros",
    "880790": "Outras partes de aeronaves",
    "840910": "Partes de motores de aviação",
    "840999": "Partes de motores diesel e outros",
    "843139": "Partes de máquinas de elevação (8428)",
    "843143": "Partes de máquinas de perfuração (8430)",
    "843149": "Partes de máquinas de terraplanagem",
    "870829": "Partes de carroçarias de veículos",
    "870840": "Caixas de velocidades e partes",
    "870892": "Silenciadores e tubos de escape",
    "870899": "Outras partes de veículos",
    "030314": "Trutas congeladas",
    "030319": "Outros salmonídeos congelados",
    "030333": "Linguado congelado",
    "030339": "Outros peixes chatos congelados",
    "030342": "Atum albacora (yellowfin) congelado",
    "030343": "Bonito (skipjack) congelado",
    "030344": "Atum patudo (bigeye) congelado",
    "030349": "Outros atuns congelados",
    "030351": "Arenque congelado",
    "030353": "Sardinha congelada",
    "030354": "Cavala congelada",
    "030355": "Carapau congelado",
    "030357": "Espadarte congelado",
    "030365": "Escamudo congelado",
    "030371": "Sardinha congelada (ed. antiga)",
    "030374": "Cavala congelada (ed. antiga)",
    "030379": "Outro peixe congelado (ed. antiga)",
    "030389": "Outro peixe congelado",
    "030211": "Trutas frescas ou refrigeradas",
    "030219": "Outros salmonídeos frescos",
    "030229": "Peixes chatos frescos",
    "030231": "Atum voador (albacora) fresco",
    "030269": "Outro peixe fresco (ed. antiga)",
    "160413": "Sardinha em conserva",
    "160414": "Atum e bonito em conserva",
    "160415": "Cavala em conserva",
    "160419": "Outro peixe em conserva",
    "160420": "Conservas de peixe picado ou preparado",
    "090411": "Pimenta do reino",
    "090420": "Piri-piri e pimentão, secos (ed. antiga)",
    "090421": "Piri-piri e pimentão, secos não moídos",
    "890510": "Dragas",
    "890520": "Plataformas de perfuração ou produção",
    "890590": "Navios-farol e outros auxiliares",
    "190110": "Preparações para alimentação infantil",
    "190190": "Preparações à base de farinha ou leite",
    "270740": "Naftaleno",
    "270799": "Outros óleos do alcatrão",
    "720712": "Semiacabados de ferro ou aço (baixo carbono)",
    "720720": "Semiacabados de ferro ou aço (alto carbono)",
    "853710": "Quadros elétricos até 1.000 V",
    "853720": "Quadros elétricos +1.000 V",
    "071410": "Mandioca",
    "071490": "Outras raízes e tubérculos",
    "852721": "Autorrádios",
    "852790": "Outros recetores de rádio",
    "610711": "Roupa interior de algodão (homem)",
    "610712": "Roupa interior de fibras sintéticas (homem)",
    "340119": "Sabão em barras e pastilhas",
    "340120": "Sabão, outras formas",
    "300210": "Soros e produtos imunológicos (ed. antiga)",
    "300215": "Produtos imunológicos em doses",
    "300220": "Vacinas para medicina humana",
    "130214": "Extrato de efedra",
    "130219": "Outros extratos vegetais",
    "120100": "Soja (ed. antiga)",
    "120190": "Soja, não para semente",
    "720410": "Sucata de ferro fundido",
    "720421": "Sucata de aço inox",
    "720429": "Sucata de aços-liga",
    "720449": "Outra sucata ferrosa",
    "610910": "T-shirts de algodão",
    "610990": "T-shirts de outras fibras",
    "240110": "Tabaco não destalado",
    "240120": "Tabaco destalado",
    "100110": "Trigo duro (ed. antiga)",
    "100119": "Trigo duro, não para semente",
    "100190": "Trigo comum (ed. antiga)",
    "100199": "Trigo comum, não para semente",
    "730511": "Tubos soldados para oleodutos e gasodutos",
    "730520": "Tubos de revestimento para perfuração",
    "730419": "Tubos sem costura para oleodutos",
    "730421": "Tubos sem costura de perfuração (ed. antiga)",
    "730429": "Tubos sem costura de revestimento",
    "841112": "Turborreatores +25 kN",
    "841182": "Turbinas a gás +5.000 kW",
    "841191": "Partes de turborreatores",
    "841199": "Partes de turbinas a gás",
    "722830": "Varões de aços-liga laminados a quente",
    "722860": "Outros varões de aços-liga",
    "721420": "Varões de ferro com saliências (betão armado)",
    "721491": "Varões de ferro retangulares",
    "721499": "Outros varões de ferro laminados a quente (pos. 7214)",
    "721590": "Outros varões de ferro ou aço, n.e. (pos. 7215)",
    "760410": "Varões e perfis de alumínio não ligado",
    "760429": "Varões e perfis de ligas de alumínio",
    "870421": "Camiões diesel até 5 t",
    "870422": "Camiões diesel 5–20 t",
    "870423": "Camiões diesel +20 t",
    "870490": "Outros veículos de mercadorias",
    "870510": "Camiões-grua",
    "870590": "Veículos especiais (varredouras, oficinas)",
    "220410": "Vinho espumante",
    "220421": "Vinho tranquilo até 2 L",
    "220422": "Vinho tranquilo 2–10 L",
    "220429": "Vinho tranquilo +10 L (a granel)",
    "848140": "Válvulas de segurança",
    "848180": "Válvulas e torneiras, outras",
    "848190": "Partes de válvulas",
    "151311": "Óleo de coco em bruto",
    "151319": "Óleo de coco refinado",
    "151110": "Óleo de palma em bruto",
    "151190": "Óleo de palma refinado",
    "150710": "Óleo de soja em bruto",
    "150790": "Óleo de soja refinado",
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("export_profiles")


def init_comtradetools():
    """Initialize comtradetools exactly like the notebooks do (from the repo root)."""
    os.chdir(REPO_ROOT)  # module uses relative paths (support/, cache/, config.ini)
    sys.path.insert(0, str(REPO_ROOT))
    import comtradetools as ctt

    ctt.setup()
    ctt.init(ctt.get_api_key())
    return ctt


def year_list(start: int, end: int) -> str:
    return ",".join(str(y) for y in range(start, end + 1))


def build_partner_names_pt(ctt) -> dict:
    """M49 code -> Portuguese partner name (curated dict, English fallback)."""
    code2pt = {}
    for en, pt in PARTNERS_EN2PT.items():
        code = ctt.encode_country(en)
        if isinstance(code, int):
            code2pt[code] = pt
        else:
            log.warning("PT partner mapping: could not encode '%s'", en)
    return code2pt


def partner_pt(code: int, code2pt: dict, ctt) -> str:
    if code in code2pt:
        return code2pt[code]
    name = ctt.decode_country(code)
    return name if isinstance(name, str) else str(code)


def hs_label_pt(ctt, code: str) -> str:
    """PT label for an HS6 code: exact curated match, else the curated 4-digit
    heading label, else the English HS description."""
    if code in HS_PT:
        return HS_PT[code]
    if code[:4] in HS_PT:
        return HS_PT[code[:4]]
    en = ctt.HS_CODES.get(code)
    return en if isinstance(en, str) else code


def fetch(ctt, label: str, period: str, period_size: int = 1, **kw) -> pd.DataFrame:
    """getFinalData with logging; returns empty DataFrame (never None).

    Follows the notebooks' own parameter conventions (includeDesc=True,
    period_size=1, single reporter/partner codes per call) so cache entries
    are shared with the notebooks instead of duplicated under different keys
    (cache keys are order-independent since 2026-07-21).
    """
    log.info("getFinalData %s (%s…)", label, period[:18])
    df = ctt.getFinalData(
        ctt.APIKEY,
        typeCode="C",
        freqCode="A",
        partner2Code=0,
        period=period,
        period_size=period_size,
        retry_if_empty=False,
        motCode=0,
        customsCode="C00",
        clCode="HS",
        includeDesc=True,
        **kw,
    )
    if df is None or df.empty:
        return pd.DataFrame()
    return df


def fetch_guarded(ctt, label: str, period: str, period_size: int = 1,
                  **kw) -> pd.DataFrame:
    """fetch() + record-cap guard for the (rare) potentially-large queries.

    getFinalData splits the period into <=period_size-period calls itself;
    the API record cap applies PER CALL, so only a total within ROW_CAP of
    the theoretical maximum (chunks x cap) can hide a truncated chunk.
    Anything smaller is complete by construction. Above it, refetch year by
    year (single-period calls can never hit the cap for these datasets).
    """
    df = fetch(ctt, label, period, period_size=period_size, **kw)
    n_periods = len(period.split(","))
    n_chunks = -(-n_periods // period_size)  # ceil
    if len(df) < n_chunks * ROW_CAP:
        return df
    log.warning("%s returned %d rows (>= %d chunks x %d) — possible per-call "
                "truncation, refetching year by year",
                label, len(df), n_chunks, ROW_CAP)
    yearly = [fetch(ctt, f"{label} [{y}]", y, **kw) for y in period.split(",")]
    yearly = [d for d in yearly if not d.empty]
    return pd.concat(yearly, ignore_index=True) if yearly else pd.DataFrame()


def fetch_shared_totals(ctt, start: int, end: int, slugs: list = None) -> dict:
    """Q1–Q4: TOTAL flows per PLP (direct and mirror sides).

    Fetched per country (single reporter/partner code per call) so the
    cache entries are shared with the per-country queries of
    country_trade_profile.ipynb — a batched PLP9 CSV call would be a
    different cache key the notebooks can never reuse. `slugs` limits the
    fetch to the countries being exported (their rows are all a
    single-country run uses).
    """
    period = year_list(start, end)
    selected = {s: COUNTRIES[s] for s in (slugs or COUNTRIES.keys())}
    queries: dict[str, list] = {"x_direct": [], "m_direct": [],
                                "x_mirror": [], "m_mirror": []}
    for slug, (code, name) in selected.items():
        queries["x_direct"].append(fetch(
            ctt, f"Q1 reporter={name} partner=all X TOTAL", period,
            reporterCode=code, partnerCode=None, flowCode="X", cmdCode="TOTAL"))
        queries["m_direct"].append(fetch(
            ctt, f"Q2 reporter={name} partner=all M TOTAL", period,
            reporterCode=code, partnerCode=None, flowCode="M", cmdCode="TOTAL"))
        queries["x_mirror"].append(fetch(
            ctt, f"Q3 reporter=all partner={name} M TOTAL", period,
            reporterCode=None, partnerCode=code, flowCode="M", cmdCode="TOTAL"))
        queries["m_mirror"].append(fetch(
            ctt, f"Q4 reporter=all partner={name} X TOTAL", period,
            reporterCode=None, partnerCode=code, flowCode="X", cmdCode="TOTAL"))
    shared = {}
    for key, frames in queries.items():
        frames = [d for d in frames if not d.empty]
        shared[key] = (pd.concat(frames, ignore_index=True)
                       if frames else pd.DataFrame())
    return shared


def world_total(df: pd.DataFrame, country_code: int, side: str) -> pd.DataFrame:
    """(year, total) series for a country from a shared TOTAL query.

    side='direct': rows reporterCode=country & partnerCode=0 (World row).
    side='mirror': rows partnerCode=country summed over reporters != 0
    (reporter=all responses carry no 'World' reporter row — verified
    2026-07-19 against cached Q3/Q4 chunks).
    """
    if df.empty:
        return pd.DataFrame(columns=["year", "total"])
    if side == "direct":
        sel = df[(df["reporterCode"] == country_code) & (df["partnerCode"] == 0)]
        g = sel.groupby("period")["primaryValue"].sum()
    else:
        sel = df[(df["partnerCode"] == country_code) & (df["reporterCode"] != 0)]
        g = sel.groupby("period")["primaryValue"].sum()
    out = g.reset_index().rename(columns={"period": "year", "primaryValue": "total"})
    out["year"] = out["year"].astype(int)
    return out


def build_d5(shared: dict, country_code: int, start: int, end: int) -> pd.DataFrame:
    """D5 trade balance, long format: year, basis, exports, imports, volume, balance."""
    xd = world_total(shared["x_direct"], country_code, "direct").set_index("year")["total"]
    md = world_total(shared["m_direct"], country_code, "direct").set_index("year")["total"]
    xm = world_total(shared["x_mirror"], country_code, "mirror").set_index("year")["total"]
    mm = world_total(shared["m_mirror"], country_code, "mirror").set_index("year")["total"]
    rows = []
    for year in range(start, end + 1):
        for basis, x, m in (("direct", xd, md), ("mirror", xm, mm)):
            if year not in x.index and year not in m.index:
                continue  # no report for this basis/year — omit the row;
                # fabricated zeros would read as "no trade" (e.g. Guinea-Bissau
                # stopped reporting direct data after 2019)
            e, i = int(x.get(year, 0)), int(m.get(year, 0))
            rows.append(dict(year=year, basis=basis, exports=e, imports=i,
                             trade_volume=e + i, balance=e - i))
    return pd.DataFrame(rows).sort_values(["year", "basis"]).reset_index(drop=True)


def build_d6(shared: dict, country_code: int, code2pt: dict, ctt,
             direction: str) -> pd.DataFrame:
    """D6 top partners (top-N per year/basis) for 'exports' or 'imports'.

    Direct: partner rows (partnerCode != 0) of the country's own X/M report;
    share vs the World (partnerCode=0) row. Mirror: reporter rows
    (reporterCode != 0) reporting M/X with the country as partner; share vs
    the sum over reporters (World reporter row excluded).
    """
    df = shared["x_direct" if direction == "exports" else "m_direct"]
    df_m = shared["x_mirror" if direction == "exports" else "m_mirror"]
    rows = []

    def emit(sub: pd.DataFrame, code_col: str, totals: pd.Series, basis: str):
        if sub.empty:
            return
        for year, grp in sub.groupby("period"):
            year = int(year)
            grp = grp.sort_values("primaryValue", ascending=False).head(TOP_N)
            total = totals.get(year, 0)
            for rank, (_, r) in enumerate(grp.iterrows(), start=1):
                code = int(r[code_col])
                rows.append(dict(
                    year=int(year), partner_code=code,
                    partner=partner_pt(code, code2pt, ctt),
                    value=int(round(r["primaryValue"])),
                    share_pct=round(r["primaryValue"] / total * 100, 3) if total else None,
                    rank=rank, basis=basis))

    d = df[(df["reporterCode"] == country_code) & (df["partnerCode"] != 0)]
    emit(d, "partnerCode",
         world_total(df, country_code, "direct").set_index("year")["total"], "direct")
    m = df_m[(df_m["partnerCode"] == country_code) & (df_m["reporterCode"] != 0)]
    emit(m, "reporterCode",
         world_total(df_m, country_code, "mirror").set_index("year")["total"], "mirror")

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out.dropna(subset=["share_pct"])  # years with no reported total
    out["share_pct"] = out["share_pct"].astype(float)
    return out.sort_values(["year", "basis", "rank"]).reset_index(drop=True)


def fetch_d7_direct_frames(ctt, slug: str, country_code: int, start: int,
                           end: int) -> dict:
    """D7 direct discovery — the country's own report with partner=all
    (partnerCode=None), AG6, keeping only the World row in memory.

    Matches the notebook's §2.2/§3.2 direct query shape
    (country_trade_profile.ipynb uses partnerCode=None at AG6), so the cache
    entry is shared; partnerCode==0 rows give exactly what a partnerCode=0
    call would have returned."""
    period = year_list(start, end)

    def world_only(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        return df[df["partnerCode"] == 0].reset_index(drop=True)

    return {
        "x": world_only(fetch_guarded(
            ctt, f"{slug} D7d reporter=C partner=all X AG6",
            period, reporterCode=country_code,
            partnerCode=None, flowCode="X", cmdCode="AG6")),
        "m": world_only(fetch_guarded(
            ctt, f"{slug} D7d reporter=C partner=all M AG6",
            period, reporterCode=country_code,
            partnerCode=None, flowCode="M", cmdCode="AG6")),
    }


def fetch_d7_mirror_full(ctt, slug: str, country_code: int, start: int,
                         end: int) -> dict:
    """D7 mirror discovery via a FULL reporter=all AG6 fetch (fallback for
    countries with weak direct reporting — their mirror trade is small).
    NOTE: reporter=all responses carry no 'World' reporter row (verified
    2026-07-19 against cached chunks) and reporterCode='0' returns empty,
    so summing individual reporters is the only mirror aggregate available."""
    period = year_list(start, end)
    return {
        "x": fetch_guarded(ctt, f"{slug} D7m reporter=all partner=C M AG6 (full)",
                           period, reporterCode=None, partnerCode=country_code,
                           flowCode="M", cmdCode="AG6"),
        "m": fetch_guarded(ctt, f"{slug} D7m reporter=all partner=C X AG6 (full)",
                           period, reporterCode=None, partnerCode=country_code,
                           flowCode="X", cmdCode="AG6"),
    }


def product_totals_from_d8(df: pd.DataFrame, side: str) -> pd.DataFrame:
    """(year, hs6, value) mirror product totals from a D8 frame (top-code
    restricted): sum over partner rows (reporterCode != 0)."""
    cols = ["year", "hs6", "value"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    sel = df[df["reporterCode"] != 0] if side == "mirror" else df[df["partnerCode"] != 0]
    if sel.empty:
        return pd.DataFrame(columns=cols)
    g = (sel.groupby(["period", "cmdCode"])["primaryValue"].sum().reset_index()
         .rename(columns={"period": "year", "cmdCode": "hs6", "primaryValue": "value"}))
    g["year"] = g["year"].astype(int)
    g["hs6"] = g["hs6"].astype(str)
    return g[g["value"] > 0].reset_index(drop=True)


def fetch_d8_frames(ctt, slug: str, country_code: int, direction: str,
                    top_codes: set, start: int, end: int) -> dict:
    """D8 product×partner detail, restricted to the top HS6 codes (small).

    direct: reporter=C, partner=all; mirror: reporter=all, partner=C.
    Kept to <= 2 x TOP_PRODUCTS codes per direction, so responses stay far
    below the API record cap (fetch_guarded still checks the result).
    """
    if not top_codes:
        return {"direct": pd.DataFrame(), "mirror": pd.DataFrame()}
    period = year_list(start, end)
    codes = ",".join(sorted(top_codes))
    if direction == "exports":   # direct: country reports X; mirror: partners report M
        direct_flow, mirror_flow = "X", "M"
    else:
        direct_flow, mirror_flow = "M", "X"
    return {
        "direct": fetch_guarded(
            ctt, f"{slug} D8d {direction} reporter=C partner=all AG6[{len(top_codes)}]",
            period, reporterCode=country_code, partnerCode=None,
            flowCode=direct_flow, cmdCode=codes),
        "mirror": fetch_guarded(
            ctt, f"{slug} D8m {direction} reporter=all partner=C AG6[{len(top_codes)}]",
            period, reporterCode=None, partnerCode=country_code,
            flowCode=mirror_flow, cmdCode=codes),
    }


def product_totals(df: pd.DataFrame) -> pd.DataFrame:
    """(year, hs6, value) world-level product totals from a D7 frame.

    D7 frames are already world-level (partner=World rows for direct; World
    reporter rows, or the fallback's reporters != 0, for mirror).
    """
    cols = ["year", "hs6", "value"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    g = (df.groupby(["period", "cmdCode"])["primaryValue"].sum().reset_index()
         .rename(columns={"period": "year", "cmdCode": "hs6", "primaryValue": "value"}))
    g["year"] = g["year"].astype(int)
    g["hs6"] = g["hs6"].astype(str)
    return g[g["value"] > 0].reset_index(drop=True)


def build_d7(prod: pd.DataFrame, world_totals: pd.Series, ctt) -> pd.DataFrame:
    """D7 top products (top-N per year/basis) from a product_totals frame."""
    rows = []
    for year, grp in prod.groupby("year"):
        grp = grp.sort_values("value", ascending=False).head(TOP_N)
        total = world_totals.get(year, 0)
        if not total:
            continue  # no reported total that year -> share would be NaN
        for rank, (_, r) in enumerate(grp.iterrows(), start=1):
            rows.append(dict(year=int(year), hs6=str(r["hs6"]),
                             description_pt=hs_label_pt(ctt, str(r["hs6"])),
                             value=int(round(r["value"])),
                             share_pct=round(r["value"] / total * 100, 3),
                             rank=rank))
    return pd.DataFrame(rows)


def top_products_alltime(prod_frames: list, n: int) -> set:
    """Union of the all-time top-N HS6 codes across the given product frames."""
    frames = [f for f in prod_frames if not f.empty]
    if not frames:
        return set()
    alltime = (pd.concat(frames).groupby("hs6")["value"].sum()
               .sort_values(ascending=False).head(n))
    return set(alltime.index)


def build_d8(df: pd.DataFrame, side: str, code2pt: dict, ctt) -> pd.DataFrame:
    """D8 product×partner detail from a D8 frame (already top-HS6-restricted).

    Keeps the top-D8_PARTNERS partners per (year, hs6). share_pct is the
    partner's share of the product-year total: the World rows of the same
    frame when present (partnerCode=0 direct / reporterCode=0 mirror), else
    the sum over partners.
    """
    if df.empty:
        return pd.DataFrame()
    if side == "direct":
        partners = df[(df["partnerCode"] != 0) & (df["primaryValue"] > 0)].copy()
        partners["partner_code"] = partners["partnerCode"]
        world = df[df["partnerCode"] == 0]
    else:
        partners = df[(df["reporterCode"] != 0) & (df["primaryValue"] > 0)].copy()
        partners["partner_code"] = partners["reporterCode"]
        world = df[df["reporterCode"] == 0]
    if partners.empty:
        return pd.DataFrame()
    base = world if not world.empty else partners
    totals = (base.groupby(["period", "cmdCode"])["primaryValue"].sum().reset_index())
    totals["period"] = totals["period"].astype(int)
    totals["cmdCode"] = totals["cmdCode"].astype(str)
    totals = totals.set_index(["period", "cmdCode"])["primaryValue"]
    rows = []
    for (year, hs6), grp in partners.groupby(["period", "cmdCode"]):
        year, hs6 = int(year), str(hs6)
        grp = grp.sort_values("primaryValue", ascending=False).head(D8_PARTNERS)
        total = totals.get((year, hs6), 0)
        if not total:
            continue
        for _, r in grp.iterrows():
            value = int(round(r["primaryValue"]))
            if value <= 0:
                continue  # sub-USD fractional rows round to zero — drop
            code = int(r["partner_code"])
            rows.append(dict(year=int(year), hs6=str(hs6),
                             description_pt=hs_label_pt(ctt, str(hs6)),
                             partner_code=code,
                             partner=partner_pt(code, code2pt, ctt),
                             value=value,
                             share_pct=round(r["primaryValue"] / total * 100, 3)))
    out = pd.DataFrame(rows)
    return out.sort_values(["year", "hs6", "value"],
                           ascending=[True, True, False]).reset_index(drop=True)


def competition_combos(d6: pd.DataFrame, d7: pd.DataFrame, ctt) -> tuple:
    """All-time top partners x products (direct basis) for the competition fetch.

    The partner list is restricted to valid Comtrade reporters — pseudo-partners
    such as 'Bunkers' cannot be queried as reporters. Combos come from the
    already-built D6/D7, so no extra discovery fetch is needed.
    """
    partners, products = [], []
    if not d6.empty:
        d = d6[d6["basis"] == "direct"]
        partners = (d.groupby("partner_code")["value"].sum()
                    .nlargest(D11_PARTNERS).index.tolist())
        valid = set(getattr(ctt, "REPORTER_CODES", {}) or {})
        partners = [int(c) for c in partners if int(c) in valid]
    if not d7.empty:
        d = d7[d7["basis"] == "direct"]
        products = [str(p) for p in (d.groupby("hs6")["value"].sum()
                                     .nlargest(D11_PRODUCTS).index.tolist())]
    return partners, products


def fetch_competition_frame(ctt, slug: str, direction: str, partners: list,
                            products: list, start: int, end: int) -> pd.DataFrame:
    """Notebook §2.5/§3.5 fetch: the partners' counterparties for `products`.

    exports (§2.5): the customers' imports from all suppliers
        (reporter=customers, flow=M, partner=all);
    imports (§3.5): the suppliers' exports to all clients
        (reporter=suppliers, flow=X, partner=all).
    """
    if not partners or not products:
        return pd.DataFrame()
    flow = "M" if direction == "exports" else "X"
    label = (f"{slug} competition-{direction} reporter=[{len(partners)}] "
             f"partner=all AG6[{len(products)}]")
    return fetch_guarded(ctt, label, year_list(start, end),
                         reporterCode=",".join(str(c) for c in partners),
                         partnerCode=None, flowCode=flow,
                         cmdCode=",".join(products))


def build_competition(df: pd.DataFrame, country_code: int, code2pt: dict,
                      ctt) -> pd.DataFrame:
    """Country's rank among each partner's counterparties (notebook §2.5/§3.5).

    Per (year, partner, hs6): the country's own row plus the top-D11_COMPETITORS
    counterparties. Ranking uses comtradetools.total_rank_perc — the same
    function as the notebook — so rank/share semantics are identical.
    share_pct is the counterparty's share of the partner's total trade in that
    product-year (market_total). World partner rows are excluded before
    ranking (they are the total, not a competitor).
    """
    if df.empty:
        return pd.DataFrame()
    # Exclude the World row (it is the total, not a competitor) and sub-USD
    # fractional rows (< 0.5 rounds to zero) BEFORE ranking, so that ranks,
    # shares and market totals are computed over exactly the emitted rows.
    df = df[(df["partnerCode"] != 0) & (df["primaryValue"] >= 0.5)].copy()
    if df.empty:
        return pd.DataFrame()
    df["period"] = df["period"].astype(int)
    df["cmdCode"] = df["cmdCode"].astype(str)
    ranked = ctt.total_rank_perc(
        df,
        groupby=["period", "flowCode", "reporterCode", "cmdCode", "partnerCode"],
        col="primaryValue", prefix="cmd_partner")
    # comtradetools.rank uses method="dense": tied values share a rank, so
    # "rank <= N" could select more than N rows. Keep a deterministic top-N
    # per market (rank, then value, then code); the country's row always added.
    ranked = ranked.sort_values(
        ["period", "reporterCode", "cmdCode", "cmd_partner_rank",
         "primaryValue", "partnerCode"],
        ascending=[True, True, True, True, False, True])
    keep = pd.concat([
        ranked[ranked["partnerCode"] != country_code]
        .groupby(["period", "reporterCode", "cmdCode"]).head(D11_COMPETITORS),
        ranked[ranked["partnerCode"] == country_code],
    ])
    rows = []
    for _, r in keep.iterrows():
        value = int(round(r["primaryValue"]))
        if value <= 0:
            continue  # sub-USD fractional rows round to zero — drop
        code = int(r["partnerCode"])
        rep = int(r["reporterCode"])
        rows.append(dict(year=int(r["period"]),
                         partner_code=rep,
                         partner=partner_pt(rep, code2pt, ctt),
                         hs6=str(r["cmdCode"]),
                         description_pt=hs_label_pt(ctt, str(r["cmdCode"])),
                         competitor_code=code,
                         competitor=partner_pt(code, code2pt, ctt),
                         value=value,
                         share_pct=round(r["cmd_partner_perc"] * 100, 3),
                         rank=int(r["cmd_partner_rank"]),
                         is_country=int(code == country_code),
                         market_total=int(round(r["cmd_partner_upper_sum"]))))
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["year", "partner_code", "hs6", "rank"]) \
        .reset_index(drop=True)


D5_COLS = ["year", "basis", "exports", "imports", "trade_volume", "balance"]
D6_COLS = ["year", "partner_code", "partner", "value", "share_pct", "rank", "basis"]
D7_COLS = ["year", "hs6", "description_pt", "value", "share_pct", "rank", "basis"]
D8_COLS = ["year", "hs6", "description_pt", "partner_code", "partner", "value",
           "share_pct", "basis"]
D11_COLS = ["year", "partner_code", "partner", "hs6", "description_pt",
           "competitor_code", "competitor", "value", "share_pct", "rank",
           "is_country", "market_total"]


def write_csv(df: pd.DataFrame, stem: str, cols: list) -> tuple:
    path = OUT_DIR / f"{stem}.csv"
    if df.empty:
        df = pd.DataFrame(columns=cols)
    df = df[cols]
    df.to_csv(path, index=False)
    log.info("wrote %s (%d rows)", path.name, len(df))
    return path, len(df)


def export_country(ctt, slug: str, shared: dict, code2pt: dict,
                   start: int, end: int) -> bool:
    country_code, name_pt = COUNTRIES[slug]
    log.info("=== %s (%s) ===", name_pt, slug)

    # D5 and D6 come from the shared TOTAL queries (already fetched).
    d5 = build_d5(shared, country_code, start, end)
    d6x = build_d6(shared, country_code, code2pt, ctt, "exports")
    d6m = build_d6(shared, country_code, code2pt, ctt, "imports")

    # D7 direct discovery (world-level, small responses).
    d7d = fetch_d7_direct_frames(ctt, slug, country_code, start, end)
    prod_xd = product_totals(d7d["x"])
    prod_md = product_totals(d7d["m"])
    strong_x = not prod_xd.empty and prod_xd["year"].nunique() >= STRONG_YEARS
    strong_m = not prod_md.empty and prod_md["year"].nunique() >= STRONG_YEARS

    if strong_x and strong_m:
        # Strong direct reporter: mirror product views are derived from the
        # D8 frames (restricted to the direct all-time top-D8_COVERAGE codes),
        # avoiding two full-detail mirror AG6 fetches.
        keep_x = top_products_alltime([prod_xd], D8_COVERAGE)
        keep_m = top_products_alltime([prod_md], D8_COVERAGE)
        d8fx = fetch_d8_frames(ctt, slug, country_code, "exports", keep_x, start, end)
        d8fm = fetch_d8_frames(ctt, slug, country_code, "imports", keep_m, start, end)
        prod_xm = product_totals_from_d8(d8fx["mirror"], "mirror")
        prod_mm = product_totals_from_d8(d8fm["mirror"], "mirror")
        mirror_scope = (f"mirror product views (D7-mirror, D8-mirror) cover the "
                        f"country's all-time top-{D8_COVERAGE} direct products; "
                        f"products outside that set are not shown on the mirror basis")
    else:
        # Weak direct reporter (e.g. long non-reporting gaps): the mirror side
        # is the primary view, so discover top products from a full mirror AG6
        # fetch (small for these countries; per-chunk cap guard still applies).
        log.warning("%s: weak direct AG6 reporting (X: %d years, M: %d years) — "
                    "using full mirror AG6 for top-product discovery", slug,
                    prod_xd["year"].nunique(), prod_md["year"].nunique())
        d7mf = fetch_d7_mirror_full(ctt, slug, country_code, start, end)
        prod_xm = product_totals(d7mf["x"])
        prod_mm = product_totals(d7mf["m"])
        keep_x = top_products_alltime([prod_xd, prod_xm], D8_COVERAGE)
        keep_m = top_products_alltime([prod_md, prod_mm], D8_COVERAGE)
        d8fx = fetch_d8_frames(ctt, slug, country_code, "exports", keep_x, start, end)
        d8fm = fetch_d8_frames(ctt, slug, country_code, "imports", keep_m, start, end)
        mirror_scope = None

    tot_xd = world_total(shared["x_direct"], country_code, "direct").set_index("year")["total"]
    tot_md = world_total(shared["m_direct"], country_code, "direct").set_index("year")["total"]
    tot_xm = world_total(shared["x_mirror"], country_code, "mirror").set_index("year")["total"]
    tot_mm = world_total(shared["m_mirror"], country_code, "mirror").set_index("year")["total"]

    d7x = pd.concat([build_d7(prod_xd, tot_xd, ctt).assign(basis="direct"),
                     build_d7(prod_xm, tot_xm, ctt).assign(basis="mirror")],
                    ignore_index=True)
    d7m_ = pd.concat([build_d7(prod_md, tot_md, ctt).assign(basis="direct"),
                      build_d7(prod_mm, tot_mm, ctt).assign(basis="mirror")],
                     ignore_index=True)
    if not d7x.empty:
        d7x = d7x.sort_values(["year", "basis", "rank"]).reset_index(drop=True)
    if not d7m_.empty:
        d7m_ = d7m_.sort_values(["year", "basis", "rank"]).reset_index(drop=True)

    # D8: product×partner rows come from the D8 frames fetched above.
    d8x = pd.concat([
        build_d8(d8fx["direct"], "direct", code2pt, ctt).assign(basis="direct"),
        build_d8(d8fx["mirror"], "mirror", code2pt, ctt).assign(basis="mirror")],
        ignore_index=True)
    d8m = pd.concat([
        build_d8(d8fm["direct"], "direct", code2pt, ctt).assign(basis="direct"),
        build_d8(d8fm["mirror"], "mirror", code2pt, ctt).assign(basis="mirror")],
        ignore_index=True)
    if not d8x.empty:
        d8x = d8x.sort_values(["year", "basis", "hs6", "value"],
                              ascending=[True, True, True, False]).reset_index(drop=True)
    if not d8m.empty:
        d8m = d8m.sort_values(["year", "basis", "hs6", "value"],
                              ascending=[True, True, True, False]).reset_index(drop=True)

    # D11/D12: competition analysis (notebook §2.5/§3.5), direct basis only.
    # Combos come from the D6/D7 frames built above (no extra discovery fetch).
    partners_x, products_x = competition_combos(d6x, d7x, ctt)
    partners_m, products_m = competition_combos(d6m, d7m_, ctt)
    d9 = build_competition(
        fetch_competition_frame(ctt, slug, "exports", partners_x, products_x,
                                start, end), country_code, code2pt, ctt)
    d10 = build_competition(
        fetch_competition_frame(ctt, slug, "imports", partners_m, products_m,
                                start, end), country_code, code2pt, ctt)

    span = f"{start}-{end}"
    stem = lambda s: f"{slug}_{s}_{span}"  # noqa: E731
    files = {}
    files["trade_balance"], n5 = write_csv(d5, stem("trade_balance"), D5_COLS)
    files["top_partners_exports"], n6x = write_csv(d6x, stem("top_partners_exports"), D6_COLS)
    files["top_partners_imports"], n6m = write_csv(d6m, stem("top_partners_imports"), D6_COLS)
    files["top_products_exports_HS-AG6"], n7x = write_csv(
        d7x, stem("top_products_exports_HS-AG6"), D7_COLS)
    files["top_products_imports_HS-AG6"], n7m = write_csv(
        d7m_, stem("top_products_imports_HS-AG6"), D7_COLS)
    files["products_partners_HS-AG6"], n8x = write_csv(
        d8x, stem("products_partners_HS-AG6"), D8_COLS)
    files["partners_products_HS-AG6"], n8m = write_csv(
        d8m, stem("partners_products_HS-AG6"), D8_COLS)
    files["competition_exports_HS-AG6"], n9 = write_csv(
        d9, stem("competition_exports_HS-AG6"), D11_COLS)
    files["competition_imports_HS-AG6"], n10 = write_csv(
        d10, stem("competition_imports_HS-AG6"), D11_COLS)

    if n5 == 0 or (n6x == 0 and n6m == 0) or (n7x == 0 and n7m == 0):
        log.error("%s: suspiciously empty datasets (D5=%d, D6=%d/%d, D7=%d/%d) — "
                  "check API/cache before committing", slug, n5, n6x, n6m, n7x, n7m)
        return False

    meta = {
        "dataset": f"{slug}_profile",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_notebook": SOURCE_NOTEBOOK,
        "country_code": country_code,
        "country_name_pt": name_pt,
        "units": "USD (current)",
        "flow_basis": "both — 'direct' (reported by the country) and 'mirror' "
                      "(reported by its partners; mirror totals sum the "
                      "individual reporters — reporter=all responses carry no "
                      "'World' reporter row, and reporter=0 returns no data)",
        "period": span,
        "files": {k: {"file": v.name, "rows": n}
                  for (k, v), n in zip(files.items(),
                                       [n5, n6x, n6m, n7x, n7m, n8x, n8m,
                                        n9, n10])},
        "notes": "From the country's own perspective: exports = country -> "
                 "partner. D6/D7 keep top-10 per (year, basis); D8 keeps "
                 f"all-time top-{D8_COVERAGE} products x top-{D8_PARTNERS} "
                 "partners per (year, hs6, basis). share_pct of D6/D7 uses "
                 "the year's world total of the same basis; D8 share_pct uses "
                 "the product-year total. description_pt: curated PT label "
                 "where available, else the English HS description. An "
                 "unreported flow/year contributes 0 (see export_site_data.py "
                 "notes)." + (f" NOTE: {mirror_scope}." if mirror_scope else ""),
    }
    meta_path = OUT_DIR / f"{slug}_profile_{span}.meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    log.info("wrote %s", meta_path.name)
    return True


def write_hs_labels(ctt):
    """Reference file: PT/EN labels for every HS6 code used in D7/D8 CSVs."""
    codes = set()
    for pattern in ("*_top_products_*_HS-AG6_*.csv", "*_products_partners_HS-AG6_*.csv",
                    "*_partners_products_HS-AG6_*.csv", "*_competition_*_HS-AG6_*.csv"):
        for csv in OUT_DIR.glob(pattern):
            if csv.name.startswith(("cn_", "mo_", "hk_")):
                continue
            try:
                codes.update(pd.read_csv(csv, usecols=["hs6"], dtype=str)["hs6"].unique())
            except (ValueError, pd.errors.EmptyDataError):
                continue  # csv without hs6 data
    rows = []
    missing_en = 0
    for code in sorted(codes):
        en = ctt.HS_CODES.get(code)
        if not isinstance(en, str):
            en, missing_en = code, missing_en + 1
        rows.append({"hs6": code, "en": en,
                     "pt": HS_PT.get(code, HS_PT.get(code[:4]))})
    path = OUT_DIR / "hs_ag6_labels.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    log.info("wrote %s (%d codes, %d without EN HS label)", path.name, len(rows), missing_en)
    collisions = {}
    for r in rows:
        if r["pt"]:
            collisions.setdefault(r["pt"], set()).add(r["hs6"])
    dup = {k: sorted(v) for k, v in collisions.items() if len(v) > 1}
    if dup:
        log.warning(
            "%d PT labels shared by multiple HS6 codes (indistinguishable series) "
            "— add exact 6-digit entries to HS_PT: %s",
            len(dup), "; ".join(f"{k} <- {', '.join(v)}" for k, v in sorted(dup.items())))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--countries", nargs="+", choices=COUNTRIES.keys(),
                    default=list(COUNTRIES.keys()),
                    help="country slugs to export (default: all 9)")
    ap.add_argument("--start", type=int, default=2003)
    ap.add_argument("--end", type=int, default=2024,
                    help="default 2024: consistent with the flows snapshots and "
                         "the validated Forum quadros")
    args = ap.parse_args()

    ctt = init_comtradetools()
    code2pt = build_partner_names_pt(ctt)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    shared = fetch_shared_totals(ctt, args.start, args.end, args.countries)
    if shared["x_direct"].empty and shared["x_mirror"].empty:
        log.error("shared TOTAL queries came back empty — aborting "
                      "(guard against partial API data)")
        sys.exit(1)

    ok = True
    for slug in args.countries:
        ok = export_country(ctt, slug, shared, code2pt, args.start, args.end) and ok

    write_hs_labels(ctt)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
