"""
/api/opportunities — list active opportunities, ordered by Radar Score.
/api/opportunities/<id>/outcome — update WIN/LOSS when position closes.
"""
from datetime import date
from flask import Blueprint, jsonify, request, abort

from app import db, cache
from app.models.opportunity import Opportunity
from app.models.stock import Stock

opps_bp = Blueprint("opportunities", __name__)

VALID_OUTCOMES = {"WIN", "LOSS", "EXPIRED"}


@opps_bp.get("/api/opportunities")
@cache.cached(timeout=120, key_prefix="opportunities_active")
def list_opportunities():
    limit  = min(int(request.args.get("limit",  20)), 50)
    offset = int(request.args.get("offset", 0))
    sharia_only = request.args.get("sharia") == "1"

    query = (Opportunity.query
             .join(Stock)
             .filter(Opportunity.outcome == "PENDING", Opportunity.is_active == True)
             .order_by(Opportunity.radar_score.desc()))

    if sharia_only:
        query = query.filter(Stock.is_sharia == True)

    total = query.count()
    items = query.offset(offset).limit(limit).all()

    return jsonify({
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_opp_dict(o) for o in items],
    })


@opps_bp.patch("/api/opportunities/<int:opp_id>/outcome")
def update_outcome(opp_id: int):
    opp = Opportunity.query.get_or_404(opp_id)
    data = request.get_json(silent=True) or {}

    outcome    = data.get("outcome", "").upper()
    exit_price = data.get("exit_price")

    if outcome not in VALID_OUTCOMES:
        abort(400, description=f"outcome must be one of: {', '.join(VALID_OUTCOMES)}")

    opp.outcome    = outcome
    opp.closed_at  = date.today()
    opp.is_active  = False

    if exit_price is not None:
        opp.exit_price = float(exit_price)
        opp.pnl_pct    = round((opp.exit_price - opp.entry_price) / opp.entry_price * 100, 2)

    db.session.commit()
    cache.delete("opportunities_active")

    return jsonify({"id": opp.id, "outcome": opp.outcome, "pnl_pct": opp.pnl_pct})


def _opp_dict(o: Opportunity) -> dict:
    return {
        "id":             o.id,
        "symbol":         o.stock.symbol,
        "name_ar":        o.stock.name_ar,
        "is_sharia":      o.stock.is_sharia,
        "type":           o.opp_type,
        "radar_score":    o.radar_score,
        "signal_quality": o.signal_quality,
        "run_date":       o.run_date.isoformat(),
        "levels": {
            "entry": o.entry_price,
            "tp1":   o.tp1_price,
            "tp2":   o.tp2_price,
            "sl":    o.sl_price,
            "rr":    round(o.rr_ratio, 2) if o.rr_ratio else None,
            "max_hold_days": o.max_hold_days,
        },
    }
