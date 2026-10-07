"""
Build UsedVehicleMarket.pbit directly as a ZIP archive.
A .pbit is an Open Packaging format ZIP containing JSON files only (no binary Vertipaq).
This bypasses pbi-tools entirely, avoiding the pbi-tools 1.2 / PBI Desktop 2.158 version mismatch.
"""
import json, zipfile, uuid, os, textwrap

BASE   = r"C:\Users\norma\used-vehicle-market-pipeline\powerbi"
OUT    = os.path.join(BASE, "UsedVehicleMarket.pbit")
DATA   = os.path.join(BASE, "data")

# ── helpers ──────────────────────────────────────────────────────────────────

def g(): return str(uuid.uuid4())

def col(name, dtype, summarize, fmt=None, src=None):
    c = {
        "name": name,
        "dataType": dtype,
        "lineageTag": g(),
        "summarizeBy": summarize,
        "sourceColumn": src or name,
        "annotations": [{"name": "SummarizationSetBy", "value": "User"}]
    }
    if fmt:
        c["formatString"] = fmt
    return c

def partition(table_name, m_expr):
    return {
        "name": f"{table_name}-Partition",
        "mode": "import",
        "source": {"type": "m", "expression": m_expr}
    }

def m_query(csv_file, columns):
    """Build a Power Query M expression (array format required by PBI Desktop)."""
    col_pairs = ", ".join(f'{{"{n}", {t}}}' for n, t in columns)
    n_cols    = len(columns)
    csv_path  = os.path.join(DATA, csv_file).replace("\\", "\\\\")
    return [
        "let",
        f'    Source = Csv.Document(File.Contents("{csv_path}"), '
        f'[Delimiter=",", Columns={n_cols}, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
        f'    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
        f'    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{{col_pairs}}})',
        "in",
        '    #"Changed Type"'
    ]

def table(name, cols_def, csv_file, m_cols):
    return {
        "name": name,
        "lineageTag": g(),
        "columns": [col(*c) for c in cols_def],
        "partitions": [partition(name, m_query(csv_file, m_cols))],
        "annotations": [{"name": "PBI_ResultType", "value": "Table"}]
    }

# ── table definitions ─────────────────────────────────────────────────────────
# (name, dataType, summarizeBy, formatString-or-None, sourceColumn-or-None)

TABLES = [
    table(
        "Q1_Depreciation",
        [
            ("manufacturer",      "string", "none"),
            ("age_bracket",       "string", "none"),
            ("listing_count",     "int64",  "sum",     "#,0"),
            ("avg_price",         "double", "average", "\\$#,0"),
            ("pct_of_benchmark",  "double", "average", "0.0"),
            ("avg_price_per_mile","double", "average", "0.0000"),
        ],
        "q1_depreciation.csv",
        [("manufacturer","type text"),("age_bracket","type text"),
         ("listing_count","Int64.Type"),("avg_price","type number"),
         ("pct_of_benchmark","type number"),("avg_price_per_mile","type number")]
    ),
    table(
        "Q2_SweetSpot",
        [
            ("age_bracket",          "string", "none"),
            ("mileage_bucket",       "string", "none"),
            ("listing_count",        "int64",  "sum",     "#,0"),
            ("avg_price",            "double", "average", "\\$#,0"),
            ("avg_pct_of_benchmark", "double", "average", "0.0"),
            ("great_deal_count",     "int64",  "sum",     "#,0"),
            ("great_deal_pct",       "double", "average", "0.0"),
        ],
        "q2_sweet_spot.csv",
        [("age_bracket","type text"),("mileage_bucket","type text"),
         ("listing_count","Int64.Type"),("avg_price","type number"),
         ("avg_pct_of_benchmark","type number"),
         ("great_deal_count","Int64.Type"),("great_deal_pct","type number")]
    ),
    table(
        "Q3_Arbitrage",
        [
            ("state",                "string", "none"),
            ("manufacturer",         "string", "none"),
            ("state_avg_price",      "double", "average", "\\$#,0"),
            ("national_median_price","double", "average", "\\$#,0"),
            ("pct_vs_national",      "double", "average", "0.0"),
            ("state_count",          "int64",  "sum",     "#,0"),
        ],
        "q3_arbitrage.csv",
        [("state","type text"),("manufacturer","type text"),
         ("state_avg_price","type number"),("national_median_price","type number"),
         ("pct_vs_national","type number"),("state_count","Int64.Type")]
    ),
    table(
        "Q4_Condition",
        [
            ("manufacturer",    "string", "none"),
            ("condition",       "string", "none"),
            ("listing_count",   "int64",  "sum",     "#,0"),
            ("avg_price",       "double", "average", "\\$#,0"),
            ("pct_of_make_avg", "double", "average", "0.0"),
        ],
        "q4_condition.csv",
        [("manufacturer","type text"),("condition","type text"),
         ("listing_count","Int64.Type"),("avg_price","type number"),
         ("pct_of_make_avg","type number")]
    ),
    table(
        "Q5_MarketConcentration",
        [
            ("state",            "string", "none"),
            ("total_listings",   "int64",  "sum",     "#,0"),
            ("avg_price",        "double", "average", "\\$#,0"),
            ("median_price",     "double", "average", "\\$#,0"),
            ("great_deals",      "int64",  "sum",     "#,0"),
            ("great_deal_pct",   "double", "average", "0.0"),
            ("inventory_rank",   "int64",  "none"),
            ("price_rank",       "int64",  "none"),
        ],
        "q5_market_concentration.csv",
        [("state","type text"),("total_listings","Int64.Type"),
         ("avg_price","type number"),("median_price","type number"),
         ("great_deals","Int64.Type"),("great_deal_pct","type number"),
         ("inventory_rank","Int64.Type"),("price_rank","Int64.Type")]
    ),
    table(
        "Q6_DealQuality",
        [
            ("manufacturer",      "string", "none"),
            ("state",             "string", "none"),
            ("total_listings",    "int64",  "sum",     "#,0"),
            ("great_deals",       "int64",  "sum",     "#,0"),
            ("good_deals",        "int64",  "sum",     "#,0"),
            ("fair_deals",        "int64",  "sum",     "#,0"),
            ("overpriced",        "int64",  "sum",     "#,0"),
            ("pct_good_or_better","double", "average", "0.0"),
        ],
        "q6_deal_quality.csv",
        [("manufacturer","type text"),("state","type text"),
         ("total_listings","Int64.Type"),("great_deals","Int64.Type"),
         ("good_deals","Int64.Type"),("fair_deals","Int64.Type"),
         ("overpriced","Int64.Type"),("pct_good_or_better","type number")]
    ),
    table(
        "Q7_Outliers",
        [
            ("manufacturer",     "string", "none"),
            ("state",            "string", "none"),
            ("price",            "double", "average", "\\$#,0"),
            ("condition",        "string", "none"),
            ("vehicle_age",      "int64",  "none"),
            ("odometer",         "double", "none",    "#,0"),
            ("cohort_avg_price", "double", "average", "\\$#,0"),
            ("z_score",          "double", "average", "0.00"),
            ("outlier_flag",     "string", "none"),
        ],
        "q7_outliers.csv",
        [("manufacturer","type text"),("state","type text"),
         ("price","type number"),("condition","type text"),
         ("vehicle_age","Int64.Type"),("odometer","type number"),
         ("cohort_avg_price","type number"),("z_score","type number"),
         ("outlier_flag","type text")]
    ),
    table(
        "Q8_Duplicates",
        [
            ("price",            "double", "average", "\\$#,0"),
            ("manufacturer",     "string", "none"),
            ("model",            "string", "none"),
            ("odometer",         "double", "none",    "#,0"),
            ("state",            "string", "none"),
            ("duplicate_count",  "int64",  "sum",     "#,0"),
        ],
        "q8_duplicates.csv",
        [("price","type number"),("manufacturer","type text"),
         ("model","type text"),("odometer","type number"),
         ("state","type text"),("duplicate_count","Int64.Type")]
    ),
]

# ── DataModelSchema ───────────────────────────────────────────────────────────

DATA_MODEL_SCHEMA = {
    "name": "SemanticModel",
    "compatibilityLevel": 1550,
    "model": {
        "name": "Model",
        "culture": "en-US",
        "dataAccessOptions": {
            "legacyRedirects": True,
            "returnErrorValuesAsNull": True
        },
        "defaultPowerBIDataSourceVersion": "powerBI_V3",
        "sourceQueryCulture": "en-US",
        "tables": TABLES
    }
}

# ── Report/Layout (4 pages, full visuals) ─────────────────────────────────────

def vc(vid, x, y, w, h, vtype, name, projections, from_clause, selects, title_text):
    config = {
        "name": name,
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": 0}}],
        "singleVisual": {
            "visualType": vtype,
            "projections": projections,
            "prototypeQuery": {
                "Version": 2,
                "From": from_clause,
                "Select": selects
            },
            "vcObjects": {
                "title": {"properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "text": {"expr": {"Literal": {"Value": f"'{title_text}'"}}},
                    "fontSize": {"expr": {"Literal": {"Value": "14D"}}},
                    "fontFamily": {"expr": {"Literal": {"Value": "'Segoe UI'"}}}
                }}
            },
            "drillFilterOtherVisuals": True
        }
    }
    return {
        "id": vid, "filters": "[]",
        "position": {"x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": 0},
        "config": json.dumps(config)
    }

def src(alias, entity):
    return {"Name": alias, "Entity": entity, "Type": 0}

def sel_col(alias, entity, prop, name_str):
    return {"Column": {"Expression": {"SourceRef": {"Source": alias}}, "Property": prop}, "Name": name_str}

def sel_agg(alias, entity, prop, func, name_str):
    # func: 0=Sum, 1=Avg
    return {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": alias}}, "Property": prop}}, "Function": func}, "Name": name_str}

def proj_cat(qref):   return {"Category": [{"queryRef": qref, "active": True}]}
def proj_y(*qrefs):   return {"Y": [{"queryRef": q, "active": True} for q in qrefs]}
def proj_series(qref): return {"Series": [{"queryRef": qref, "active": True}]}
def proj_vals(*qrefs): return {"Values": [{"queryRef": q, "active": True} for q in qrefs]}
def merge(*dicts):
    r = {}
    for d in dicts: r.update(d)
    return r

PAGE_BG = json.dumps({"relationships": None, "background": {"color": {"solid": {"color": "#FAFAFA"}}}})

pages = [
    # ── Page 1: Depreciation & Value ─────────────────────────────────────────
    {
        "id": 0, "name": "PageDepreciation", "displayName": "Depreciation & Value",
        "filters": "[]", "ordinal": 0, "width": 1280, "height": 720, "config": PAGE_BG,
        "visualContainers": [
            vc(1, 20, 60, 750, 580, "lineChart",
               "depr_line",
               merge(proj_cat("Q1_Depreciation.age_bracket"),
                     proj_series("Q1_Depreciation.manufacturer"),
                     proj_y("Average(Q1_Depreciation.avg_price)")),
               [src("q","Q1_Depreciation")],
               [sel_col("q","Q1_Depreciation","age_bracket","Q1_Depreciation.age_bracket"),
                sel_col("q","Q1_Depreciation","manufacturer","Q1_Depreciation.manufacturer"),
                sel_agg("q","Q1_Depreciation","avg_price",1,"Average(Q1_Depreciation.avg_price)")],
               "Avg Price by Age Bracket — Top Makes"),
            vc(2, 790, 60, 460, 580, "tableEx",
               "depr_table",
               proj_vals("Q1_Depreciation.manufacturer","Q1_Depreciation.age_bracket",
                         "Average(Q1_Depreciation.avg_price)","Average(Q1_Depreciation.pct_of_benchmark)"),
               [src("q","Q1_Depreciation")],
               [sel_col("q","Q1_Depreciation","manufacturer","Q1_Depreciation.manufacturer"),
                sel_col("q","Q1_Depreciation","age_bracket","Q1_Depreciation.age_bracket"),
                sel_agg("q","Q1_Depreciation","avg_price",1,"Average(Q1_Depreciation.avg_price)"),
                sel_agg("q","Q1_Depreciation","pct_of_benchmark",1,"Average(Q1_Depreciation.pct_of_benchmark)")],
               "Depreciation Data"),
        ]
    },
    # ── Page 2: Deal Finder ───────────────────────────────────────────────────
    {
        "id": 1, "name": "PageDealFinder", "displayName": "Deal Finder",
        "filters": "[]", "ordinal": 1, "width": 1280, "height": 720, "config": PAGE_BG,
        "visualContainers": [
            vc(3, 20, 60, 600, 280, "matrix",
               "sweet_matrix",
               {"Rows": [{"queryRef":"Q2_SweetSpot.age_bracket","active":True}],
                "Columns": [{"queryRef":"Q2_SweetSpot.mileage_bucket","active":True}],
                "Values": [{"queryRef":"Average(Q2_SweetSpot.avg_pct_of_benchmark)","active":True}]},
               [src("q","Q2_SweetSpot")],
               [sel_col("q","Q2_SweetSpot","age_bracket","Q2_SweetSpot.age_bracket"),
                sel_col("q","Q2_SweetSpot","mileage_bucket","Q2_SweetSpot.mileage_bucket"),
                sel_agg("q","Q2_SweetSpot","avg_pct_of_benchmark",1,"Average(Q2_SweetSpot.avg_pct_of_benchmark)")],
               "Sweet Spot — Avg % of Benchmark (age × mileage)"),
            vc(4, 640, 60, 620, 280, "clusteredBarChart",
               "deal_quality_bar",
               merge(proj_cat("Q6_DealQuality.manufacturer"),
                     proj_y("Sum(Q6_DealQuality.great_deals)","Sum(Q6_DealQuality.good_deals)","Sum(Q6_DealQuality.overpriced)")),
               [src("q","Q6_DealQuality")],
               [sel_col("q","Q6_DealQuality","manufacturer","Q6_DealQuality.manufacturer"),
                sel_agg("q","Q6_DealQuality","great_deals",0,"Sum(Q6_DealQuality.great_deals)"),
                sel_agg("q","Q6_DealQuality","good_deals",0,"Sum(Q6_DealQuality.good_deals)"),
                sel_agg("q","Q6_DealQuality","overpriced",0,"Sum(Q6_DealQuality.overpriced)")],
               "Deal Quality by Manufacturer"),
            vc(5, 20, 360, 1230, 300, "tableEx",
               "sweet_table",
               proj_vals("Q2_SweetSpot.age_bracket","Q2_SweetSpot.mileage_bucket",
                         "Average(Q2_SweetSpot.avg_pct_of_benchmark)","Average(Q2_SweetSpot.great_deal_pct)",
                         "Sum(Q2_SweetSpot.listing_count)"),
               [src("q","Q2_SweetSpot")],
               [sel_col("q","Q2_SweetSpot","age_bracket","Q2_SweetSpot.age_bracket"),
                sel_col("q","Q2_SweetSpot","mileage_bucket","Q2_SweetSpot.mileage_bucket"),
                sel_agg("q","Q2_SweetSpot","avg_pct_of_benchmark",1,"Average(Q2_SweetSpot.avg_pct_of_benchmark)"),
                sel_agg("q","Q2_SweetSpot","great_deal_pct",1,"Average(Q2_SweetSpot.great_deal_pct)"),
                sel_agg("q","Q2_SweetSpot","listing_count",0,"Sum(Q2_SweetSpot.listing_count)")],
               "Sweet Spot Detail"),
        ]
    },
    # ── Page 3: Regional Intelligence ────────────────────────────────────────
    {
        "id": 2, "name": "PageRegional", "displayName": "Regional Intelligence",
        "filters": "[]", "ordinal": 2, "width": 1280, "height": 720, "config": PAGE_BG,
        "visualContainers": [
            vc(6, 20, 60, 750, 580, "clusteredBarChart",
               "arb_bar",
               merge(proj_cat("Q3_Arbitrage.state"),
                     {"Series": [{"queryRef":"Q3_Arbitrage.manufacturer","active":True}]},
                     proj_y("Average(Q3_Arbitrage.pct_vs_national)")),
               [src("q","Q3_Arbitrage")],
               [sel_col("q","Q3_Arbitrage","state","Q3_Arbitrage.state"),
                sel_col("q","Q3_Arbitrage","manufacturer","Q3_Arbitrage.manufacturer"),
                sel_agg("q","Q3_Arbitrage","pct_vs_national",1,"Average(Q3_Arbitrage.pct_vs_national)")],
               "Regional Arbitrage — % vs National Median"),
            vc(7, 790, 60, 460, 580, "scatterChart",
               "market_scatter",
               {"X": [{"queryRef":"Sum(Q5_MarketConcentration.total_listings)","active":True}],
                "Y": [{"queryRef":"Average(Q5_MarketConcentration.median_price)","active":True}],
                "Details": [{"queryRef":"Q5_MarketConcentration.state","active":True}]},
               [src("q","Q5_MarketConcentration")],
               [sel_agg("q","Q5_MarketConcentration","total_listings",0,"Sum(Q5_MarketConcentration.total_listings)"),
                sel_agg("q","Q5_MarketConcentration","median_price",1,"Average(Q5_MarketConcentration.median_price)"),
                sel_col("q","Q5_MarketConcentration","state","Q5_MarketConcentration.state")],
               "Inventory vs Price by State"),
        ]
    },
    # ── Page 4: Inventory Quality ─────────────────────────────────────────────
    {
        "id": 3, "name": "PageInventory", "displayName": "Inventory Quality",
        "filters": "[]", "ordinal": 3, "width": 1280, "height": 720, "config": PAGE_BG,
        "visualContainers": [
            vc(8, 20, 60, 750, 280, "clusteredColumnChart",
               "cond_bar",
               merge(proj_cat("Q4_Condition.manufacturer"),
                     proj_series("Q4_Condition.condition"),
                     proj_y("Average(Q4_Condition.avg_price)")),
               [src("q","Q4_Condition")],
               [sel_col("q","Q4_Condition","manufacturer","Q4_Condition.manufacturer"),
                sel_col("q","Q4_Condition","condition","Q4_Condition.condition"),
                sel_agg("q","Q4_Condition","avg_price",1,"Average(Q4_Condition.avg_price)")],
               "Condition Premium — Avg Price by Make & Condition"),
            vc(9, 20, 360, 750, 300, "tableEx",
               "outlier_table",
               proj_vals("Q7_Outliers.manufacturer","Q7_Outliers.state",
                         "Average(Q7_Outliers.price)","Average(Q7_Outliers.cohort_avg_price)",
                         "Average(Q7_Outliers.z_score)","Q7_Outliers.outlier_flag"),
               [src("q","Q7_Outliers")],
               [sel_col("q","Q7_Outliers","manufacturer","Q7_Outliers.manufacturer"),
                sel_col("q","Q7_Outliers","state","Q7_Outliers.state"),
                sel_agg("q","Q7_Outliers","price",1,"Average(Q7_Outliers.price)"),
                sel_agg("q","Q7_Outliers","cohort_avg_price",1,"Average(Q7_Outliers.cohort_avg_price)"),
                sel_agg("q","Q7_Outliers","z_score",1,"Average(Q7_Outliers.z_score)"),
                sel_col("q","Q7_Outliers","outlier_flag","Q7_Outliers.outlier_flag")],
               "Top Bargains — Z-Score Outliers"),
            vc(10, 790, 60, 460, 580, "clusteredBarChart",
               "dup_bar",
               merge(proj_cat("Q8_Duplicates.manufacturer"),
                     proj_y("Sum(Q8_Duplicates.duplicate_count)")),
               [src("q","Q8_Duplicates")],
               [sel_col("q","Q8_Duplicates","manufacturer","Q8_Duplicates.manufacturer"),
                sel_agg("q","Q8_Duplicates","duplicate_count",0,"Sum(Q8_Duplicates.duplicate_count)")],
               "Duplicate Listings by Manufacturer"),
        ]
    },
]

REPORT_LAYOUT = {
    "id": 0,
    "resourcePackages": [],
    "sections": pages,
    "config": json.dumps({
        "version": "5.54",
        "themeCollection": {
            "baseTheme": {"name": "CY24SU10", "version": "5.54", "type": 2}
        }
    }),
    "layoutOptimization": 0
}

# ── DiagramLayout ─────────────────────────────────────────────────────────────

DIAGRAM_LAYOUT = {
    "version": 1,
    "diagrams": [
        {
            "ordinal": 0,
            "nodes": [
                {"nodeIndex": i, "name": t["name"],
                 "x": 100 + (i % 4) * 260, "y": 80 + (i // 4) * 200}
                for i, t in enumerate(TABLES)
            ],
            "relationships": []
        }
    ]
}

# ── Content_Types.xml ─────────────────────────────────────────────────────────

CONTENT_TYPES = textwrap.dedent("""\
    <?xml version="1.0" encoding="utf-8"?>
    <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
      <Default Extension="json" ContentType="application/json" />
      <Override PartName="/DataModelSchema" ContentType="application/json" />
      <Override PartName="/DiagramLayout" ContentType="application/json" />
      <Override PartName="/Report/Layout" ContentType="application/json" />
      <Override PartName="/Version" ContentType="application/octet-stream" />
    </Types>
    """)

# ── Assemble PBIT ─────────────────────────────────────────────────────────────

def to_bytes(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml",  CONTENT_TYPES)
    z.writestr("Version",              "3.0")
    z.writestr("DataModelSchema",      to_bytes(DATA_MODEL_SCHEMA))
    z.writestr("DiagramLayout",        to_bytes(DIAGRAM_LAYOUT))
    z.writestr("Report/Layout",        to_bytes(REPORT_LAYOUT))

print(f"Written: {OUT}")
print(f"Size:    {os.path.getsize(OUT):,} bytes")
