"""
Generates a pbi-tools PbixProj source folder from the exported CSV files,
then compiles it into a .pbix using pbi-tools.
"""

import os, json, uuid, subprocess, sys

BASE      = r"C:\Users\norma\used-vehicle-market-pipeline\powerbi"
DATA_DIR  = os.path.join(BASE, "data")
PROJ_DIR  = os.path.join(BASE, "project")
PBITOOLS  = os.path.join(BASE, "pbi-tools", "pbi-tools.exe")
OUT_PBIX  = os.path.join(BASE, "UsedVehicleMarket.pbix")

def g(): return str(uuid.uuid4())

# ── Column definitions for each table ─────────────────────────────────────────
TABLES = {
    "Q1_Depreciation": {
        "csv": "q1_depreciation.csv",
        "columns": [
            ("manufacturer",     "string",  "none",    None),
            ("age_bracket",      "string",  "none",    None),
            ("listing_count",    "int64",   "sum",     "#,0"),
            ("avg_price",        "double",  "average", r"\$#,0"),
            ("pct_of_benchmark", "double",  "average", "0.0"),
            ("avg_price_per_mile","double", "average", "0.0000"),
        ],
    },
    "Q2_SweetSpot": {
        "csv": "q2_sweet_spot.csv",
        "columns": [
            ("age_bracket",          "string", "none",    None),
            ("mileage_bucket",       "string", "none",    None),
            ("listing_count",        "int64",  "sum",     "#,0"),
            ("avg_price",            "double", "average", r"\$#,0"),
            ("avg_pct_of_benchmark", "double", "average", "0.0"),
            ("great_deal_count",     "int64",  "sum",     "#,0"),
            ("great_deal_pct",       "double", "average", "0.0"),
        ],
    },
    "Q3_Arbitrage": {
        "csv": "q3_arbitrage.csv",
        "columns": [
            ("state",                  "string", "none",    None),
            ("manufacturer",           "string", "none",    None),
            ("state_avg_price",        "double", "average", r"\$#,0"),
            ("national_median_price",  "double", "average", r"\$#,0"),
            ("pct_vs_national",        "double", "average", "0.0"),
            ("state_count",            "int64",  "sum",     "#,0"),
        ],
    },
    "Q4_Condition": {
        "csv": "q4_condition.csv",
        "columns": [
            ("manufacturer",    "string", "none",    None),
            ("condition",       "string", "none",    None),
            ("listing_count",   "int64",  "sum",     "#,0"),
            ("avg_price",       "double", "average", r"\$#,0"),
            ("pct_of_make_avg", "double", "average", "0.0"),
        ],
    },
    "Q5_MarketConcentration": {
        "csv": "q5_market_concentration.csv",
        "columns": [
            ("state",           "string", "none",    None),
            ("total_listings",  "int64",  "sum",     "#,0"),
            ("avg_price",       "double", "average", r"\$#,0"),
            ("median_price",    "double", "average", r"\$#,0"),
            ("great_deals",     "int64",  "sum",     "#,0"),
            ("great_deal_pct",  "double", "average", "0.0"),
            ("inventory_rank",  "int64",  "none",    "#,0"),
            ("price_rank",      "int64",  "none",    "#,0"),
        ],
    },
    "Q6_DealQuality": {
        "csv": "q6_deal_quality.csv",
        "columns": [
            ("manufacturer",        "string", "none",    None),
            ("state",               "string", "none",    None),
            ("total_listings",      "int64",  "sum",     "#,0"),
            ("great_deals",         "int64",  "sum",     "#,0"),
            ("good_deals",          "int64",  "sum",     "#,0"),
            ("fair_deals",          "int64",  "sum",     "#,0"),
            ("overpriced",          "int64",  "sum",     "#,0"),
            ("pct_good_or_better",  "double", "average", "0.0"),
        ],
    },
    "Q7_Outliers": {
        "csv": "q7_outliers.csv",
        "columns": [
            ("manufacturer",      "string", "none",    None),
            ("state",             "string", "none",    None),
            ("price",             "double", "average", r"\$#,0"),
            ("condition",         "string", "none",    None),
            ("vehicle_age",       "double", "average", "0"),
            ("odometer",          "double", "average", "#,0"),
            ("cohort_avg_price",  "double", "average", r"\$#,0"),
            ("z_score",           "double", "average", "0.00"),
            ("outlier_flag",      "string", "none",    None),
        ],
    },
    "Q8_Duplicates": {
        "csv": "q8_duplicates.csv",
        "columns": [
            ("price",            "double", "average", r"\$#,0"),
            ("manufacturer",     "string", "none",    None),
            ("model",            "string", "none",    None),
            ("odometer",         "double", "average", "#,0"),
            ("state",            "string", "none",    None),
            ("duplicate_count",  "int64",  "sum",     "#,0"),
        ],
    },
}

# ── M type map ────────────────────────────────────────────────────────────────
M_TYPES = {
    "string": "type text",
    "int64":  "Int64.Type",
    "double": "type number",
}

def m_query(table_name, csv_filename, columns):
    col_count = len(columns)
    type_list = ", ".join(f'{{"{c[0]}", {M_TYPES[c[1]]}}}' for c in columns)
    csv_path  = os.path.join(DATA_DIR, csv_filename).replace("\\", "\\\\")
    lines = [
        "let",
        f'    Source = Csv.Document(File.Contents("{csv_path}"), [Delimiter=",", Columns={col_count}, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
        '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
        f'    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{{type_list}}})',
        "in",
        '    #"Changed Type"',
    ]
    return "\n".join(lines)

# ── Write TMDL files ───────────────────────────────────────────────────────────
def write_tmdl():
    model_dir  = os.path.join(PROJ_DIR, "Model")
    tables_dir = os.path.join(model_dir, "tables")
    os.makedirs(tables_dir, exist_ok=True)

    # database.tmdl
    with open(os.path.join(model_dir, "database.tmdl"), "w") as f:
        f.write(f"database UsedVehicleMarket\n\tcompatibilityLevel: 1550\n")

    # model.tmdl
    table_refs = "\n".join(f"\tref table {name}" for name in TABLES)
    with open(os.path.join(model_dir, "model.tmdl"), "w") as f:
        f.write(f"model Model\n\tculture: en-US\n\n{table_refs}\n")

    # one .tmdl per table
    for tname, tdef in TABLES.items():
        lines = [f"table '{tname}'", f"\tlineageTag: {g()}", ""]
        for cname, ctype, sumby, fmt in tdef["columns"]:
            lines += [
                f"\tcolumn '{cname}'",
                f"\t\tdataType: {ctype}",
                f"\t\tlineageTag: {g()}",
                f"\t\tsummarizeBy: {sumby}",
                f"\t\tsourceColumn: {cname}",
            ]
            if fmt:
                lines.append(f'\t\tformatString: {fmt}')
            lines.append("")

        # partition with M expression (indented with tabs)
        mq = m_query(tname, tdef["csv"], tdef["columns"])
        mq_indented = "\n".join("\t\t\t" + l for l in mq.splitlines())
        lines += [
            f"\tpartition '{tname}-Partition' = m",
            f"\t\tmode: import",
            f"\t\tsource",
            mq_indented,
            "",
            f"\tannotation PBI_ResultType = Table",
            "",
        ]
        tmdl_path = os.path.join(tables_dir, f"{tname}.tmdl")
        with open(tmdl_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"  wrote {tname}.tmdl")

# ── Report Layout (4 pages) ────────────────────────────────────────────────────
def visual_config(name, vtype, projections, proto_select, proto_from,
                  title="", x=20, y=60, w=1230, h=600):
    proj_json = json.dumps(projections)
    proto = {"Version": 2, "From": proto_from, "Select": proto_select}
    proto_json = json.dumps(proto)
    title_obj = {}
    if title:
        title_obj = {
            "title": {"properties": {
                "show": {"expr": {"Literal": {"Value": "true"}}},
                "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
                "fontSize": {"expr": {"Literal": {"Value": "14D"}}},
                "fontFamily": {"expr": {"Literal": {"Value": "'Segoe UI'"}}}
            }}
        }
    inner = {
        "name": name,
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0,
                                            "width": w, "height": h, "tabOrder": 0}}],
        "singleVisual": {
            "visualType": vtype,
            "projections": projections,
            "prototypeQuery": proto,
            "vcObjects": title_obj,
            "drillFilterOtherVisuals": True,
        }
    }
    return {
        "id": abs(hash(name)) % 10000,
        "position": {"x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": 0},
        "config": json.dumps(inner),
        "filters": "[]",
    }

def page_config(bg="#FAFAFA"):
    return json.dumps({"relationships": None,
                        "background": {"color": {"solid": {"color": bg}}}})

def make_layout():
    pages = []

    # ── Page 1: Depreciation & Value ──────────────────────────────────────────
    p1_visuals = [
        visual_config(
            name="depr_line", vtype="lineChart",
            title="Avg Price by Age Bracket — Top Makes",
            projections={
                "Category": [{"queryRef": "Q1_Depreciation.age_bracket", "active": True}],
                "Series":   [{"queryRef": "Q1_Depreciation.manufacturer", "active": True}],
                "Y":        [{"queryRef": "Average(Q1_Depreciation.avg_price)", "active": True}],
            },
            proto_from=[{"Name": "q", "Entity": "Q1_Depreciation", "Type": 0}],
            proto_select=[
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "age_bracket"},
                 "Name": "Q1_Depreciation.age_bracket"},
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "manufacturer"},
                 "Name": "Q1_Depreciation.manufacturer"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "avg_price"}}, "Function": 1},
                 "Name": "Average(Q1_Depreciation.avg_price)"},
            ],
            x=20, y=60, w=750, h=580,
        ),
        visual_config(
            name="depr_table", vtype="tableEx",
            title="Depreciation Data",
            projections={"Values": [
                {"queryRef": "Q1_Depreciation.manufacturer", "active": True},
                {"queryRef": "Q1_Depreciation.age_bracket",  "active": True},
                {"queryRef": "Average(Q1_Depreciation.avg_price)", "active": True},
                {"queryRef": "Average(Q1_Depreciation.pct_of_benchmark)", "active": True},
            ]},
            proto_from=[{"Name": "q", "Entity": "Q1_Depreciation", "Type": 0}],
            proto_select=[
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "manufacturer"},
                 "Name": "Q1_Depreciation.manufacturer"},
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "age_bracket"},
                 "Name": "Q1_Depreciation.age_bracket"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "avg_price"}}, "Function": 1},
                 "Name": "Average(Q1_Depreciation.avg_price)"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "pct_of_benchmark"}}, "Function": 1},
                 "Name": "Average(Q1_Depreciation.pct_of_benchmark)"},
            ],
            x=790, y=60, w=460, h=580,
        ),
    ]
    pages.append({"id": 0, "name": "PageDepreciation", "displayName": "Depreciation & Value",
                  "filters": "[]", "ordinal": 0, "visualContainers": p1_visuals,
                  "config": page_config(), "width": 1280, "height": 720})

    # ── Page 2: Deal Finder ────────────────────────────────────────────────────
    p2_visuals = [
        visual_config(
            name="sweet_matrix", vtype="matrix",
            title="Sweet Spot — Avg % of Benchmark (age × mileage)",
            projections={
                "Rows":    [{"queryRef": "Q2_SweetSpot.age_bracket",    "active": True}],
                "Columns": [{"queryRef": "Q2_SweetSpot.mileage_bucket", "active": True}],
                "Values":  [{"queryRef": "Average(Q2_SweetSpot.avg_pct_of_benchmark)", "active": True}],
            },
            proto_from=[{"Name": "q", "Entity": "Q2_SweetSpot", "Type": 0}],
            proto_select=[
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "age_bracket"},
                 "Name": "Q2_SweetSpot.age_bracket"},
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "mileage_bucket"},
                 "Name": "Q2_SweetSpot.mileage_bucket"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "avg_pct_of_benchmark"}}, "Function": 1},
                 "Name": "Average(Q2_SweetSpot.avg_pct_of_benchmark)"},
            ],
            x=20, y=60, w=600, h=280,
        ),
        visual_config(
            name="deal_quality_bar", vtype="clusteredBarChart",
            title="Deal Quality Distribution by Manufacturer / State",
            projections={
                "Category": [{"queryRef": "Q6_DealQuality.manufacturer", "active": True}],
                "Y": [
                    {"queryRef": "Sum(Q6_DealQuality.great_deals)", "active": True},
                    {"queryRef": "Sum(Q6_DealQuality.good_deals)",  "active": True},
                    {"queryRef": "Sum(Q6_DealQuality.overpriced)",  "active": True},
                ],
            },
            proto_from=[{"Name": "q", "Entity": "Q6_DealQuality", "Type": 0}],
            proto_select=[
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "manufacturer"},
                 "Name": "Q6_DealQuality.manufacturer"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "great_deals"}}, "Function": 0},
                 "Name": "Sum(Q6_DealQuality.great_deals)"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "good_deals"}}, "Function": 0},
                 "Name": "Sum(Q6_DealQuality.good_deals)"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "overpriced"}}, "Function": 0},
                 "Name": "Sum(Q6_DealQuality.overpriced)"},
            ],
            x=640, y=60, w=620, h=280,
        ),
        visual_config(
            name="sweet_table", vtype="tableEx",
            title="Sweet Spot Detail",
            projections={"Values": [
                {"queryRef": "Q2_SweetSpot.age_bracket",            "active": True},
                {"queryRef": "Q2_SweetSpot.mileage_bucket",         "active": True},
                {"queryRef": "Average(Q2_SweetSpot.avg_pct_of_benchmark)", "active": True},
                {"queryRef": "Average(Q2_SweetSpot.great_deal_pct)", "active": True},
                {"queryRef": "Sum(Q2_SweetSpot.listing_count)",      "active": True},
            ]},
            proto_from=[{"Name": "q", "Entity": "Q2_SweetSpot", "Type": 0}],
            proto_select=[
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "age_bracket"},
                 "Name": "Q2_SweetSpot.age_bracket"},
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "mileage_bucket"},
                 "Name": "Q2_SweetSpot.mileage_bucket"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "avg_pct_of_benchmark"}}, "Function": 1},
                 "Name": "Average(Q2_SweetSpot.avg_pct_of_benchmark)"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "great_deal_pct"}}, "Function": 1},
                 "Name": "Average(Q2_SweetSpot.great_deal_pct)"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "listing_count"}}, "Function": 0},
                 "Name": "Sum(Q2_SweetSpot.listing_count)"},
            ],
            x=20, y=360, w=1230, h=300,
        ),
    ]
    pages.append({"id": 1, "name": "PageDealFinder", "displayName": "Deal Finder",
                  "filters": "[]", "ordinal": 1, "visualContainers": p2_visuals,
                  "config": page_config(), "width": 1280, "height": 720})

    # ── Page 3: Regional Intelligence ─────────────────────────────────────────
    p3_visuals = [
        visual_config(
            name="arb_bar", vtype="clusteredBarChart",
            title="Regional Arbitrage — % vs National Median (top 30)",
            projections={
                "Category": [{"queryRef": "Q3_Arbitrage.state",        "active": True},
                              {"queryRef": "Q3_Arbitrage.manufacturer", "active": True}],
                "Y":        [{"queryRef": "Average(Q3_Arbitrage.pct_vs_national)", "active": True}],
            },
            proto_from=[{"Name": "q", "Entity": "Q3_Arbitrage", "Type": 0}],
            proto_select=[
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "state"},
                 "Name": "Q3_Arbitrage.state"},
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "manufacturer"},
                 "Name": "Q3_Arbitrage.manufacturer"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "pct_vs_national"}}, "Function": 1},
                 "Name": "Average(Q3_Arbitrage.pct_vs_national)"},
            ],
            x=20, y=60, w=750, h=580,
        ),
        visual_config(
            name="market_scatter", vtype="scatterChart",
            title="Inventory vs Price by State",
            projections={
                "X":       [{"queryRef": "Sum(Q5_MarketConcentration.total_listings)", "active": True}],
                "Y":       [{"queryRef": "Average(Q5_MarketConcentration.median_price)", "active": True}],
                "Details": [{"queryRef": "Q5_MarketConcentration.state", "active": True}],
            },
            proto_from=[{"Name": "q", "Entity": "Q5_MarketConcentration", "Type": 0}],
            proto_select=[
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "total_listings"}}, "Function": 0},
                 "Name": "Sum(Q5_MarketConcentration.total_listings)"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "median_price"}}, "Function": 1},
                 "Name": "Average(Q5_MarketConcentration.median_price)"},
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "state"},
                 "Name": "Q5_MarketConcentration.state"},
            ],
            x=790, y=60, w=460, h=580,
        ),
    ]
    pages.append({"id": 2, "name": "PageRegional", "displayName": "Regional Intelligence",
                  "filters": "[]", "ordinal": 2, "visualContainers": p3_visuals,
                  "config": page_config(), "width": 1280, "height": 720})

    # ── Page 4: Inventory Quality ──────────────────────────────────────────────
    p4_visuals = [
        visual_config(
            name="cond_bar", vtype="clusteredColumnChart",
            title="Condition Premium — Avg Price by Make & Condition",
            projections={
                "Category": [{"queryRef": "Q4_Condition.manufacturer", "active": True}],
                "Series":   [{"queryRef": "Q4_Condition.condition",    "active": True}],
                "Y":        [{"queryRef": "Average(Q4_Condition.avg_price)", "active": True}],
            },
            proto_from=[{"Name": "q", "Entity": "Q4_Condition", "Type": 0}],
            proto_select=[
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "manufacturer"},
                 "Name": "Q4_Condition.manufacturer"},
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "condition"},
                 "Name": "Q4_Condition.condition"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "avg_price"}}, "Function": 1},
                 "Name": "Average(Q4_Condition.avg_price)"},
            ],
            x=20, y=60, w=750, h=280,
        ),
        visual_config(
            name="outlier_table", vtype="tableEx",
            title="Top Bargains — Z-Score Outliers",
            projections={"Values": [
                {"queryRef": "Q7_Outliers.manufacturer",     "active": True},
                {"queryRef": "Q7_Outliers.state",            "active": True},
                {"queryRef": "Average(Q7_Outliers.price)",           "active": True},
                {"queryRef": "Average(Q7_Outliers.cohort_avg_price)","active": True},
                {"queryRef": "Average(Q7_Outliers.z_score)",         "active": True},
                {"queryRef": "Q7_Outliers.outlier_flag",     "active": True},
            ]},
            proto_from=[{"Name": "q", "Entity": "Q7_Outliers", "Type": 0}],
            proto_select=[
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "manufacturer"},
                 "Name": "Q7_Outliers.manufacturer"},
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "state"},
                 "Name": "Q7_Outliers.state"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "price"}}, "Function": 1},
                 "Name": "Average(Q7_Outliers.price)"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "cohort_avg_price"}}, "Function": 1},
                 "Name": "Average(Q7_Outliers.cohort_avg_price)"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "z_score"}}, "Function": 1},
                 "Name": "Average(Q7_Outliers.z_score)"},
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "outlier_flag"},
                 "Name": "Q7_Outliers.outlier_flag"},
            ],
            x=20, y=360, w=750, h=300,
        ),
        visual_config(
            name="dup_bar", vtype="clusteredBarChart",
            title="Duplicate Listings by Manufacturer",
            projections={
                "Category": [{"queryRef": "Q8_Duplicates.manufacturer",      "active": True}],
                "Y":        [{"queryRef": "Sum(Q8_Duplicates.duplicate_count)", "active": True}],
            },
            proto_from=[{"Name": "q", "Entity": "Q8_Duplicates", "Type": 0}],
            proto_select=[
                {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "manufacturer"},
                 "Name": "Q8_Duplicates.manufacturer"},
                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "q"}},
                  "Property": "duplicate_count"}}, "Function": 0},
                 "Name": "Sum(Q8_Duplicates.duplicate_count)"},
            ],
            x=790, y=60, w=460, h=580,
        ),
    ]
    pages.append({"id": 3, "name": "PageInventory", "displayName": "Inventory Quality",
                  "filters": "[]", "ordinal": 3, "visualContainers": p4_visuals,
                  "config": page_config(), "width": 1280, "height": 720})

    layout = {
        "id": 0,
        "resourcePackages": [],
        "sections": pages,
        "config": json.dumps({
            "version": "5.54",
            "themeCollection": {"baseTheme": {"name": "CY24SU10", "version": "5.54", "type": 2}},
        }),
        "layoutOptimization": 0,
    }
    report_dir = os.path.join(PROJ_DIR, "Report")
    os.makedirs(report_dir, exist_ok=True)
    with open(os.path.join(report_dir, "Layout"), "w", encoding="utf-8") as f:
        json.dump(layout, f)
    print("  wrote Report/Layout")

    # config.json
    with open(os.path.join(report_dir, "config.json"), "w") as f:
        json.dump({"version": "5.54", "themeCollection": {}}, f)
    print("  wrote Report/config.json")


def write_pbixproj():
    cfg = {
        "version": "1.0",
        "type": "pbix",
        "model": {"format": "TMDL"},
        "report": {"customVisuals": []},
        "queries": {"generateDataSources": False},
    }
    with open(os.path.join(PROJ_DIR, ".pbixproj.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    print("  wrote .pbixproj.json")


# ── Main ───────────────────────────────────────────────────────────────────────
os.makedirs(PROJ_DIR, exist_ok=True)
print("Building project source files...")
write_pbixproj()
write_tmdl()
make_layout()
print("\nAll source files written.")
print(f"\nProject folder: {PROJ_DIR}")
print(f"Output target:  {OUT_PBIX}")
