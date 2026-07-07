"""
Seed EGX stocks into the database.
Run: python scripts/seed_stocks.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db
from app.models.stock import Stock

EGX_STOCKS = [
    # Symbol     name_ar                           name_en                              Sector               Sharia
    ("COMI",  "بنك القاهرة التجاري",              "Commercial International Bank",     "البنوك",            False),
    ("CIEB",  "البنك التجاري الدولي",             "CIB",                               "البنوك",            False),
    ("QNBE",  "بنك قطر الوطني - مصر",            "QNB Alahli",                        "البنوك",            False),
    ("HTLF",  "بنك هيرميس المالية",              "EFG Hermes",                        "البنوك",            False),
    ("EFIH",  "هيرميس القابضة",                  "EFG Hermes Holding",                "المالية",           False),
    ("TMGH",  "طلعت مصطفى القابضة",             "Talaat Moustafa Group",             "العقارات",          False),
    ("MNHD",  "مدينة نصر للإسكان والتعمير",     "Madinet Nasr Housing",              "العقارات",          False),
    ("SWDY",  "شركة سوديك",                     "SODIC",                             "العقارات",          False),
    ("PHDC",  "القاهرة للإسكان والتعمير",        "Palm Hills Developments",           "العقارات",          False),
    ("CLHO",  "سيتي إيدج للتطوير العقاري",      "City Edge Developments",            "العقارات",          False),
    ("ETEL",  "المصرية للاتصالات",              "Telecom Egypt",                     "الاتصالات",         False),
    ("ORWE",  "أوراسكوم للاستثمار",             "Orascom Investment Holding",        "الاستثمار",         False),
    ("OCDI",  "أوراسكوم للتطوير",              "Orascom Development",               "السياحة والترفيه",  False),
    ("FWRY",  "فوري للتكنولوجيا والمدفوعات",    "Fawry",                             "التكنولوجيا",       False),
    ("AMOC",  "الإسكندرية لزيوت المعادن",       "Alexandria Mineral Oils",           "البتروكيماويات",    False),
    ("SKPC",  "سيدي كرير للبتروكيماويات",       "Sidi Kerir Petrochemicals",         "البتروكيماويات",    True),
    ("IRON",  "الإسكندرية للحديد والصلب",       "Alexandria National Iron & Steel",  "الصناعات الأساسية", False),
    ("ISPH",  "مستشفيات المقاولون العرب",       "ISPH",                              "الرعاية الصحية",    False),
    ("ALCN",  "الكان للصناعة",                  "Alkan",                             "الصناعات الهندسية", False),
    ("DOMT",  "دومتي",                          "Domty",                             "الغذاء والشراب",    False),
    ("MCQE",  "ماكرو للصحة والجمال",            "Macro Group",                       "التجزئة",           False),
    ("AMER",  "أمريكانا ريستورانتس",            "Americana Restaurants",             "الغذاء والشراب",    True),
    ("KIMA",  "كيما - أسوان للأسمدة",           "Kima",                              "الصناعات الكيماوية", False),
    ("SPIN",  "سبينيس مصر",                     "Spinneys Egypt",                    "التجزئة",           False),
    ("ISGC",  "الإسكندرية للزجاج والكريستال",   "International Glass",               "مواد البناء",       False),
    ("POUL",  "قها للدواجن",                    "Cairo Poultry",                     "الغذاء والشراب",    True),
    ("ABUK",  "أبوقير للأسمدة والصناعات الكيماوية", "Abu Qir Fertilizers",           "الصناعات الكيماوية", True),
    ("EGCH",  "إيجيبت كير للرعاية الصحية",     "Egypt Care",                        "الرعاية الصحية",    False),
    ("GTHE",  "شركة جرين تك",                  "GreenTech",                         "التكنولوجيا",       False),
    ("HRHO",  "هيرميس القابضة",                "Hermes Holding",                    "المالية",           False),
]


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()
        added = skipped = 0

        for symbol, name_ar, name_en, sector, is_sharia in EGX_STOCKS:
            if Stock.query.filter_by(symbol=symbol).first():
                skipped += 1
                continue

            db.session.add(Stock(
                symbol    = symbol,
                name_ar   = name_ar,
                name_en   = name_en,
                sector    = sector,
                is_sharia = is_sharia,
                is_active = True,
            ))
            added += 1

        db.session.commit()
        print(f"Seed complete: {added} added, {skipped} already existed.")


if __name__ == "__main__":
    seed()
