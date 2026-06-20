"""
================================================================================
MOCK FINANCIAL DATA  -  RM INTELLIGENCE PLATFORM
SwissHack / Julius Bär Challenge
================================================================================

Dati di mercato FINTI per lo sviluppo locale.
Quando (e se) collegherete una Financial API vera, basterà sostituire la
funzione get_market_news() mantenendo lo STESSO formato di output, così il
resto della pipeline non cambia di una riga.

I topic sono FISSI e scelti per matchare la demo + temi caldi di giugno 2026.
Ogni news ha solo: titolo + testo + data (come richiesto, niente sentiment/fonte).
================================================================================
"""

# =============================================================================
# DATABASE DI NEWS MOCK  -  chiave = topic, valore = lista di news
# =============================================================================
# I valori numerici riflettono lo scenario reale di metà giugno 2026,
# così la demo risulta credibile e attuale davanti alla giuria.

MOCK_NEWS = {

    "gold": [
        {
            "title": "Gold steadies near $4,100 as markets await Fed signal",
            "text": "Gold is trading around $4,100 per ounce after a sharp "
                    "correction from its earlier highs near $5,000. A stronger "
                    "dollar and elevated Treasury yields have weighed on the "
                    "metal, while investors await the Fed's next move under new "
                    "leadership.",
            "date": "2026-06-18",
        },
        {
            "title": "Safe-haven demand keeps gold supported amid Middle East tension",
            "text": "Despite the recent pullback, structural demand for gold "
                    "remains intact, driven by central bank buying and "
                    "persistent geopolitical stress. Analysts see the $4,000 "
                    "level as a key support zone.",
            "date": "2026-06-15",
        },
    ],

    "oil": [
        {
            "title": "Brent holds above $92 as Iran conflict disrupts supply",
            "text": "Crude oil remains elevated, with Brent trading above $92 "
                    "per barrel. War-driven supply disruptions and the risk "
                    "premium tied to the Strait of Hormuz continue to support "
                    "prices, raising fresh inflation concerns.",
            "date": "2026-06-19",
        },
        {
            "title": "Energy-driven inflation complicates Fed's path",
            "text": "Over 60% of May's CPI increase was driven by energy. With "
                    "oil supply shocks pushing prices higher, the Fed faces a "
                    "difficult balance between containing inflation and avoiding "
                    "recession.",
            "date": "2026-06-12",
        },
    ],

    "iran_war": [
        {
            "title": "Iran conflict drives geopolitical risk premium across markets",
            "text": "The ongoing war in Iran continues to ripple through global "
                    "markets, lifting oil forecasts and keeping safe-haven "
                    "assets in focus. Shipping routes through the Strait of "
                    "Hormuz remain a key concern for global energy supply.",
            "date": "2026-06-17",
        },
    ],

    "asian_equity": [
        {
            "title": "Asian equities volatile as regional tensions persist",
            "text": "Asian equity markets have seen heightened volatility as "
                    "investors weigh regional geopolitical risk against growth "
                    "prospects. Exposure to the region remains a topic of "
                    "caution for many portfolios.",
            "date": "2026-06-16",
        },
    ],

    "real_estate_dubai": [
        {
            "title": "Dubai property market stays resilient amid global uncertainty",
            "text": "The UAE real estate market continues to attract capital "
                    "seeking stability, with prime Dubai residential prices "
                    "holding firm. Demand from international investors remains "
                    "strong despite broader market turbulence.",
            "date": "2026-06-14",
        },
    ],

    "fed_rates": [
        {
            "title": "Markets brace for new Fed chair's first rate decision",
            "text": "The Federal Reserve's June meeting marks the first under "
                    "new leadership. With inflation above target but driven by "
                    "geopolitical factors, the rate path has become highly "
                    "uncertain, keeping markets on edge.",
            "date": "2026-06-13",
        },
    ],

    "inflation": [
        {
            "title": "Core inflation decelerates even as headline stays elevated",
            "text": "Core CPI rose just 0.2% month-over-month in May, down from "
                    "0.4% in April, suggesting underlying inflation is not "
                    "broadening. Most of the headline pressure came from energy "
                    "prices.",
            "date": "2026-06-11",
        },
    ],

    # -------------------------------------------------------------------------
    # TOPIC DI NICCHIA #1  -  COLLECTIBLES / PASSION ASSETS
    # Non "hot right now": un buon RM non li ha in testa nel dettaglio.
    # Plausibile che un cliente HNWI li tiri fuori (auto, vino, orologi, arte).
    # Qui il sistema dà valore servendo info che l'RM probabilmente non ha.
    # -------------------------------------------------------------------------
    "collectibles": [
        {
            "title": "Passion assets gain ground in HNWI portfolios",
            "text": "Fine art, rare wine, classic cars and luxury watches are "
                    "increasingly treated as part of a real-assets strategy for "
                    "diversification and long-term appreciation. These assets "
                    "act as inflation hedges and stores of value, but carry "
                    "valuation challenges, illiquidity, and require specialized "
                    "knowledge and authenticity verification.",
            "date": "2026-06-10",
        },
        {
            "title": "Collectibles: high entry barriers, niche liquidity",
            "text": "Unlike public markets, collectible assets trade thinly and "
                    "depend on a limited pool of buyers. Auction houses such as "
                    "Sotheby's and Christie's set reference valuations, but "
                    "pricing remains opaque. Advisors typically recommend "
                    "keeping such holdings a small share of total wealth.",
            "date": "2026-06-05",
        },
    ],

    # -------------------------------------------------------------------------
    # TOPIC DI NICCHIA #2  -  MUSIC ROYALTIES / INTELLECTUAL PROPERTY
    # Davvero non ovvio. Un cliente con background creativo o un imprenditore
    # potrebbe chiederne: l'RM medio resta spiazzato, il sistema lo copre.
    # -------------------------------------------------------------------------
    "music_royalties": [
        {
            "title": "Music royalties emerge as an uncorrelated income stream",
            "text": "Royalty income from music catalogs, patents, trademarks and "
                    "licensing is drawing interest as an alternative asset that "
                    "is largely uncorrelated to public markets. Catalogs can "
                    "generate steady cash flow, but valuation hinges on usage "
                    "trends, rights complexity, and contract structures.",
            "date": "2026-06-08",
        },
        {
            "title": "Intellectual property as a wealth-preservation tool",
            "text": "Beyond music, IP and royalty streams from books, patents and "
                    "licensing agreements are being structured into investable "
                    "vehicles. The appeal lies in predictable, inflation-linked "
                    "income, though liquidity is limited and specialized due "
                    "diligence is essential.",
            "date": "2026-06-03",
        },
    ],

    # -------------------------------------------------------------------------
    # TOPIC DI NICCHIA #3  -  FINE ART
    # Il più iconico per i clienti wealth. Dati reali (mercato, rendimenti,
    # costi di transazione). Il dettaglio sui costi 20-25% è ciò che un RM
    # tipicamente NON ha in testa.
    # -------------------------------------------------------------------------
    "fine_art": [
        {
            "title": "Fine art: a $1.7T market with long-term appreciation",
            "text": "The global art market is valued around $1.7 trillion with "
                    "annual sales above $68 billion. Historically fine art has "
                    "returned roughly 8.5% per year since 1950. Blue-chip art "
                    "in particular has outpaced many traditional assets, with "
                    "the Artprice100 index up around 56% since 2018.",
            "date": "2026-06-09",
        },
        {
            "title": "Art investing: prestige with hidden frictions",
            "text": "Despite strong headline returns, art carries high transaction "
                    "costs (often 20-25%), opaque pricing, and authenticity "
                    "risk. Valuations depend heavily on provenance and require "
                    "expert advisory or art funds. It suits long horizons and "
                    "should remain a measured share of total wealth.",
            "date": "2026-06-04",
        },
    ],

    # -------------------------------------------------------------------------
    # TOPIC DI NICCHIA #4  -  FINE WINE
    # Tra i top performer dell'indice Knight Frank, tracciato da Liv-ex.
    # -------------------------------------------------------------------------
    "fine_wine": [
        {
            "title": "Fine wine draws growing UHNWI interest",
            "text": "Fine wine has risen more than 37% over ten years and is "
                    "attracting ultra-high-net-worth investors, with over a "
                    "third already active owners per global surveys. The market "
                    "is tracked in real time by Liv-ex, offering institutional"
                    "-grade price indices and trading data.",
            "date": "2026-06-09",
        },
        {
            "title": "Wine correction opens entry points",
            "text": "A recent correction in fine wine prices has created more "
                    "attractive entry levels for long-term buyers. Bordeaux's "
                    "classification dates to 1855 and the secondary market spans "
                    "generations, but liquidity depends on auction houses and "
                    "collector networks.",
            "date": "2026-06-02",
        },
    ],

    # -------------------------------------------------------------------------
    # TOPIC DI NICCHIA #5  -  WHISKY (cask-aged)
    # Spesso il miglior performer assoluto dell'indice. Poco commerciale.
    # -------------------------------------------------------------------------
    "whisky": [
        {
            "title": "Cask whisky: appreciation while it matures",
            "text": "Rare and aged whisky has been among the strongest luxury "
                    "asset performers. Cask-aged whisky is especially attractive "
                    "because the spirit continues to mature and gain value while "
                    "stored. Limited bottlings from prestigious distilleries "
                    "command premium prices.",
            "date": "2026-06-07",
        },
    ],

    # -------------------------------------------------------------------------
    # TOPIC DI NICCHIA #6  -  LUXURY WATCHES
    # Crescita decennale più alta tra le categorie dell'indice (+125%).
    # -------------------------------------------------------------------------
    "luxury_watches": [
        {
            "title": "Luxury watches lead luxury-asset returns",
            "text": "Watches have appreciated around 125% over ten years, the "
                    "strongest gain among tracked luxury categories. Vintage "
                    "Patek Philippe, Rolex and Audemars Piguet pieces drive much "
                    "of the demand, though condition, rarity and provenance are "
                    "decisive for value.",
            "date": "2026-06-06",
        },
    ],

    # -------------------------------------------------------------------------
    # TOPIC DI NICCHIA #7  -  CLASSIC CARS
    # Trend attuale: auto fine anni '80 / primi 2000 entrano in collezione.
    # -------------------------------------------------------------------------
    "classic_cars": [
        {
            "title": "Modern classics enter collectible territory",
            "text": "Classic cars from the late 1980s to early 2000s are now "
                    "entering collectible territory, often outperforming "
                    "traditional classics. The segment rewards specialist "
                    "knowledge, with condition, originality and restoration "
                    "history heavily influencing value.",
            "date": "2026-06-06",
        },
    ],

    # -------------------------------------------------------------------------
    # TOPIC DI NICCHIA #8  -  FANCY COLOR DIAMONDS
    # Ultra-esclusivo. Aste a 8 cifre. Tocco di prestigio per la demo.
    # -------------------------------------------------------------------------
    "color_diamonds": [
        {
            "title": "Fancy color diamonds prized for rarity",
            "text": "Fancy color diamonds remain a store of value sought by "
                    "collectors for their rarity. Recent landmark auction sales "
                    "include a 9.51-carat blue diamond at $25.6 million. More "
                    "maisons are entering the market as clients seek stones that "
                    "hold value, though the segment is highly illiquid.",
            "date": "2026-06-01",
        },
    ],
}


# =============================================================================
# FUNZIONE DI ACCESSO  -  da usare nella pipeline al posto della Financial API
# =============================================================================

def get_market_news(topics: list[str]) -> str:
    """
    Riceve la lista di financial_topics estratti da GPT-4o e restituisce
    le news mock corrispondenti, già formattate come testo pronto per il prompt
    o per la UI.

    Il matching è semplice: normalizza il topic e cerca chiavi simili.
    Se un topic non ha news mock, viene semplicemente ignorato.

    QUANDO COLLEGHERETE L'API VERA: sostituite solo il corpo di questa
    funzione, mantenendo input (list[str]) e output (str) identici.
    """
    output_lines = []

    for topic in topics:
        key = _match_topic(topic)
        if key and key in MOCK_NEWS:
            output_lines.append(f"\n### NEWS for '{topic}':")
            for news in MOCK_NEWS[key]:
                output_lines.append(f"- [{news['date']}] {news['title']}")
                output_lines.append(f"  {news['text']}")

    if not output_lines:
        return "No relevant market news found for the given topics."

    return "\n".join(output_lines)


def get_market_news_raw(topics: list[str]) -> dict:
    """
    Variante che restituisce i dati GREZZI (dizionario) invece del testo.
    Utile per la UI, che può mappare ogni news a un widget senza fare parsing.
    """
    result = {}
    for topic in topics:
        key = _match_topic(topic)
        if key and key in MOCK_NEWS:
            result[topic] = MOCK_NEWS[key]
    return result


# =============================================================================
# HELPER  -  matching grezzo tra il topic estratto e le chiavi del mock
# =============================================================================

def _match_topic(topic: str) -> str | None:
    """
    Mappa un topic in linguaggio naturale (come lo estrae GPT-4o) a una chiave
    del database mock. È volutamente semplice: per la demo basta.
    """
    t = topic.lower()

    if "gold" in t or "oro" in t:
        return "gold"
    if "oil" in t or "petrol" in t or "crude" in t or "brent" in t:
        return "oil"
    if "iran" in t or "war" in t or "guerra" in t or "hormuz" in t:
        return "iran_war"
    if "asia" in t or "asian" in t or "china" in t or "cina" in t:
        return "asian_equity"
    if "dubai" in t or "uae" in t or "real estate" in t or "property" in t:
        return "real_estate_dubai"
    if "fed" in t or "rate" in t or "tassi" in t:
        return "fed_rates"
    if "inflation" in t or "cpi" in t or "inflazione" in t:
        return "inflation"
    if ("collectible" in t or "passion asset" in t):
        return "collectibles"
    if ("art" in t or "arte" in t or "painting" in t or "sculpture" in t
            or "artprice" in t or "artwork" in t):
        return "fine_art"
    if ("wine" in t or "vino" in t or "bordeaux" in t or "liv-ex" in t
            or "vintage wine" in t):
        return "fine_wine"
    if ("whisky" in t or "whiskey" in t or "cask" in t or "scotch" in t):
        return "whisky"
    if ("watch" in t or "orolog" in t or "patek" in t or "rolex" in t
            or "audemars" in t):
        return "luxury_watches"
    if ("classic car" in t or "vintage car" in t or "ferrari" in t
            or "auto d'epoca" in t or "collector car" in t):
        return "classic_cars"
    if ("diamond" in t or "diamant" in t or "gemstone" in t
            or "colored stone" in t or "fancy color" in t):
        return "color_diamonds"
    if ("royalt" in t or "music" in t or "intellectual property" in t
            or "ip " in t or "patent" in t or "licensing" in t
            or "musica" in t or "brevett" in t):
        return "music_royalties"

    return None


# =============================================================================
# TEST RAPIDO
# =============================================================================

if __name__ == "__main__":
    topics = ["gold exposure", "Asian equity markets", "Iran war", "something random"]
    print(get_market_news(topics))
    print("\n--- RAW ---")
    import json
    print(json.dumps(get_market_news_raw(topics), indent=2, ensure_ascii=False))
