from pathlib import Path

import pandas as pd

from inspect_fec_api import get_candidate_record

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RESULTS_FILE = PROJECT_ROOT / "data" / "raw" / "federalelections2022.xlsx"
SENATE_SHEET = "7. US Senate Results by State"


# ---------------------------------------------------------
# CAMPAIGN FINANCE DATA
# ---------------------------------------------------------

fetterman = get_candidate_record("Fetterman", 2022, "PA")
oz = get_candidate_record("Mehmet Oz", 2022, "PA")

finance_df = pd.DataFrame([fetterman, oz])


# ---------------------------------------------------------
# ELECTION RESULT DATA
# ---------------------------------------------------------

results_df = pd.read_excel(
    RESULTS_FILE,
    sheet_name=SENATE_SHEET,
    header=0,
)

# Clean accidental whitespace from the FEC workbook's column names.
results_df = results_df.rename(
    columns=lambda column: column.strip() if isinstance(column, str) else column
)

# Keep Pennsylvania candidates who actually appeared in the general election.
results_df = results_df[
    (results_df["STATE ABBREVIATION"] == "PA")
    & results_df["FEC ID"].notna()
    & results_df["GENERAL VOTES"].notna()
].copy()

# Keep only the major-party candidates for this comparison.
results_df = results_df[results_df["PARTY"].isin(["D", "R"])].copy()

# Select and rename the result fields needed for the analysis.
results_df = results_df[
    [
        "FEC ID",
        "GENERAL VOTES",
        "GENERAL %",
        "GE WINNER INDICATOR",
    ]
].rename(
    columns={
        "FEC ID": "fec_candidate_id",
        "GENERAL VOTES": "votes",
        "GENERAL %": "vote_share",
        "GE WINNER INDICATOR": "winner_indicator",
    }
)

results_df["won"] = results_df["winner_indicator"].eq("W")
results_df["votes"] = results_df["votes"].astype(int)

results_df = results_df.drop(columns=["winner_indicator"])


# ---------------------------------------------------------
# MERGE MONEY + RESULT DATA
# ---------------------------------------------------------

comparison_df = finance_df.merge(
    results_df,
    on="fec_candidate_id",
    how="inner",
)

print("\n2022 Pennsylvania Senate — money and results:")
print(comparison_df.to_string(index=False))
