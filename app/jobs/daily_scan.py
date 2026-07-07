"""
Background job: scan all active stocks, compute Radar Scores, detect Opportunities.
Runs at 15:30 Cairo (after regime_job has committed today's regime).
"""
import logging
from datetime import date

logger = logging.getLogger(__name__)


def run_daily_scan(app) -> None:
    with app.app_context():
        try:
            from app import db
            from app.models.stock import Stock
            from app.models.score import RadarScoreHistory
            from app.models.opportunity import Opportunity
            from app.models.regime import MarketRegimeHistory
            from app.services.indicators import compute_indicators
            from app.services.radar_score import compute_radar_score
            from app.services.opportunity import compute_opportunity
            from app.services.explain import generate_explain
            from app.utils.data_fetcher import fetch_ohlcv, compute_adt, assess_data_quality

            today = date.today()

            regime_rec = (
                MarketRegimeHistory.query
                .order_by(MarketRegimeHistory.run_date.desc())
                .first()
            )
            regime = regime_rec.regime if regime_rec else "SIDEWAYS"

            stocks = Stock.query.filter_by(is_active=True).all()
            logger.info("daily_scan: %d stocks to scan (regime=%s)", len(stocks), regime)

            success = skip = fail = 0

            for stock in stocks:
                try:
                    if RadarScoreHistory.query.filter_by(stock_id=stock.id, run_date=today).first():
                        skip += 1
                        continue

                    df = fetch_ohlcv(stock.symbol)
                    if df is None:
                        logger.warning("daily_scan: no data for %s", stock.symbol)
                        fail += 1
                        continue

                    quality = assess_data_quality(df, stock.symbol)
                    adt     = compute_adt(df)
                    ind     = compute_indicators(df, quality)

                    if ind is None:
                        logger.warning("daily_scan: insufficient data for %s", stock.symbol)
                        fail += 1
                        continue

                    bd         = compute_radar_score(ind, adt, regime=regime)
                    explain    = generate_explain(ind, bd, regime)
                    opp_result = compute_opportunity(ind, bd, is_sharia=stock.is_sharia, regime=regime)

                    score_rec = RadarScoreHistory(
                        stock_id          = stock.id,
                        run_date          = today,
                        score             = bd.final_score,
                        trend_score       = bd.trend_score,
                        momentum_score    = bd.momentum_score,
                        liquidity_score   = bd.liquidity_score,
                        volume_score      = bd.volume_score,
                        sector_score      = bd.sector_score,
                        fundamental_score = bd.fundamental_score,
                        risk_penalty      = bd.risk_penalty,
                        regime_multiplier = bd.regime_multiplier,
                        adx               = ind.adx,
                        rsi               = ind.rsi,
                        macd              = ind.macd,
                        macd_signal       = ind.macd_signal,
                        atr_pct           = ind.atr_pct,
                        rvol              = ind.rvol,
                        ma20              = ind.ma20,
                        ma50              = ind.ma50,
                        ma200             = ind.ma200,
                        obv_trend         = ind.obv_trend,
                        explain_ar        = explain["ar"],
                        explain_en        = explain["en"],
                        data_quality      = quality,
                    )
                    db.session.add(score_rec)

                    if opp_result:
                        db.session.add(Opportunity(
                            stock_id      = stock.id,
                            run_date      = today,
                            opp_type      = opp_result.opp_type,
                            entry_price   = opp_result.entry_price,
                            tp1_price     = opp_result.tp1_price,
                            tp2_price     = opp_result.tp2_price,
                            sl_price      = opp_result.sl_price,
                            rr_ratio      = opp_result.rr_ratio,
                            max_hold_days = opp_result.max_hold_days,
                            radar_score   = bd.final_score,
                            signal_quality = opp_result.signal_quality,
                            outcome       = "PENDING",
                        ))

                    db.session.commit()
                    success += 1

                except Exception:
                    db.session.rollback()
                    logger.warning("daily_scan: error for %s", stock.symbol, exc_info=True)
                    fail += 1

            logger.info(
                "daily_scan: done — success=%d, skip=%d, fail=%d",
                success, skip, fail,
            )

        except Exception:
            logger.exception("daily_scan: top-level error")
