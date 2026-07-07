"""
/api/stocks/:symbol
Returns latest Radar Score, indicators, explain, and opportunity for a stock.
"""
from datetime import date
from flask import Blueprint, jsonify, abort

from app import db, cache
from app.models.stock import Stock
from app.models.score import RadarScoreHistory
from app.models.regime import MarketRegimeHistory
from app.models.opportunity import Opportunity
from app.services.indicators import compute_indicators
from app.services.radar_score import compute_radar_score
from app.services.explain import generate_explain
from app.services.opportunity import compute_opportunity
from app.utils.data_fetcher import fetch_ohlcv, compute_adt, assess_data_quality

stocks_bp = Blueprint("stocks", __name__)


@stocks_bp.get("/api/stocks/<symbol>")
@cache.cached(timeout=300, key_prefix=lambda: f"stock_{request_symbol()}")
def get_stock(symbol: str):
    symbol = symbol.upper().strip()

    stock = Stock.query.filter_by(symbol=symbol).first()
    if not stock:
        abort(404, description=f"Stock '{symbol}' not found in database")

    # ── Latest score from DB (prefer cached) ──────────────────────────
    today = date.today()
    score_rec = (RadarScoreHistory.query
                 .filter_by(stock_id=stock.id, run_date=today)
                 .first())

    if score_rec:
        return jsonify(_build_response(stock, score_rec))

    # ── Live compute (no cached score for today) ──────────────────────
    df = fetch_ohlcv(symbol)
    if df is None:
        abort(503, description=f"Unable to fetch market data for '{symbol}'")

    quality = assess_data_quality(df, symbol)
    adt     = compute_adt(df)
    ind     = compute_indicators(df, quality)

    if ind is None:
        abort(503, description=f"Insufficient historical data for '{symbol}'")

    # Get current regime from DB
    regime_rec = (MarketRegimeHistory.query
                  .order_by(MarketRegimeHistory.run_date.desc())
                  .first())
    regime = regime_rec.regime if regime_rec else "SIDEWAYS"

    bd = compute_radar_score(ind, adt, regime=regime)
    explain = generate_explain(ind, bd, regime)
    opp_result = compute_opportunity(ind, bd, is_sharia=stock.is_sharia, regime=regime)

    # Persist
    score_rec = RadarScoreHistory(
        stock_id=stock.id,
        run_date=today,
        score=bd.final_score,
        trend_score=bd.trend_score,
        momentum_score=bd.momentum_score,
        liquidity_score=bd.liquidity_score,
        volume_score=bd.volume_score,
        sector_score=bd.sector_score,
        fundamental_score=bd.fundamental_score,
        risk_penalty=bd.risk_penalty,
        regime_multiplier=bd.regime_multiplier,
        adx=ind.adx,
        rsi=ind.rsi,
        macd=ind.macd,
        macd_signal=ind.macd_signal,
        atr_pct=ind.atr_pct,
        rvol=ind.rvol,
        ma20=ind.ma20,
        ma50=ind.ma50,
        ma200=ind.ma200,
        obv_trend=ind.obv_trend,
        explain_ar=explain["ar"],
        explain_en=explain["en"],
        data_quality=quality,
    )
    db.session.add(score_rec)

    if opp_result:
        opp = Opportunity(
            stock_id=stock.id,
            run_date=today,
            opp_type=opp_result.opp_type,
            entry_price=opp_result.entry_price,
            tp1_price=opp_result.tp1_price,
            tp2_price=opp_result.tp2_price,
            sl_price=opp_result.sl_price,
            rr_ratio=opp_result.rr_ratio,
            max_hold_days=opp_result.max_hold_days,
            radar_score=bd.final_score,
            signal_quality=opp_result.signal_quality,
            outcome="PENDING",
        )
        db.session.add(opp)

    db.session.commit()

    return jsonify(_build_response(stock, score_rec, opp_result=opp_result))


def _build_response(stock, score_rec, opp_result=None):
    base = {
        "symbol":   stock.symbol,
        "name_ar":  stock.name_ar,
        "name_en":  stock.name_en,
        "sector":   stock.sector,
        "is_sharia": stock.is_sharia,
        **score_rec.to_dict(),
    }

    if opp_result:
        base["opportunity"] = {
            "type":        opp_result.opp_type,
            "entry":       opp_result.entry_price,
            "tp1":         opp_result.tp1_price,
            "tp2":         opp_result.tp2_price,
            "sl":          opp_result.sl_price,
            "rr":          opp_result.rr_ratio,
            "max_hold_days": opp_result.max_hold_days,
            "signal_quality": opp_result.signal_quality,
            "reason": {"ar": opp_result.reason_ar, "en": opp_result.reason_en},
        }
    else:
        base["opportunity"] = None

    return base


def request_symbol():
    """Cache key helper — extracts symbol from request path."""
    from flask import request
    return request.path.split("/")[-1].upper()
