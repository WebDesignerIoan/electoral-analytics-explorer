from pathlib import Path

import pandas as pd

# Find the project root regardless of where this script is run from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Location of the official FEC 2022 election-results workbook.
RESULTS_FILE = PROJECT_ROOT / "data" / "raw" / "federalelections2022.xlsx"

SENATE_SHEET = "7. US Senate Results by State"


# Read the workbook structure first.
workbook = pd.ExcelFile(RESULTS_FILE)

print("Sheets in the FEC 2022 election results workbook:")

for sheet_name in workbook.sheet_names:
    print("-", sheet_name)


# ---------------------------------------------------------
# READ THE SENATE RESULTS AS A PROPER TABLE
# ---------------------------------------------------------

# Row 0 contains the real column names, so we now let pandas
# use it as the header.
senate_df = pd.read_excel(
    RESULTS_FILE,
    sheet_name=SENATE_SHEET,
    header=0,
)

# Remove accidental leading/trailing whitespace from column names
# This prevents source formatting issues such as "GENERAL VOTES "
# from causing column lookup errors.
senate_df = senate_df.rename(
    columns=lambda column: (  # lambda is an anonymous function
        column.strip() if isinstance(column, str) else column
    )  # we use str because we only want the modification on strings
)

print("\nColumns in the Senate results dataset:")
print(senate_df.columns.tolist())


# ---------------------------------------------------------
# INSPECT THE 2022 PENNSYLVANIA SENATE RACE
# ---------------------------------------------------------

# Select only rows belonging to Pennsylvania.
pennsylvania_df = senate_df[senate_df["STATE ABBREVIATION"] == "PA"].copy()

# Summary rows such as "Party Votes" and "Total State Votes" do not have an FEC candidate ID. We remove those so that
# each remaining row represents an actual candidate
# OBS: Keep actual general-election candidates. Primary-only candidates have no value in GENERAL VOTES.
pennsylvania_candidates = pennsylvania_df[
    pennsylvania_df["FEC ID"].notna() & pennsylvania_df["GENERAL VOTES"].notna()
].copy()

# Keep only the fields currently relevant to our analysis.
columns_to_show = [
    "FEC ID",
    "CANDIDATE NAME",
    "PARTY",
    "(I) INCUMBENT INDICATOR",
    "GENERAL VOTES",
    "GENERAL %",
    "GE WINNER INDICATOR",
]

print("\n2022 Pennsylvania Senate candidates:")
print(pennsylvania_candidates[columns_to_show].to_string(index=False))


# ---------------------------------------------------------
# CREATE AN ANALYSIS-READY RESULTS DATAFRAME
# ---------------------------------------------------------

# Keep only the fields we need and rename them so that our internal
# dataset does not depend on the exact column names used by the FEC workbook.
results_df = pennsylvania_candidates[
    [
        "FEC ID",
        "CANDIDATE NAME",
        "PARTY",
        "(I) INCUMBENT INDICATOR",
        "GENERAL VOTES",
        "GENERAL %",
        "GE WINNER INDICATOR",
    ]
].rename(
    columns={
        "FEC ID": "fec_candidate_id",
        "CANDIDATE NAME": "name",
        "PARTY": "party",
        "(I) INCUMBENT INDICATOR": "incumbent_indicator",
        "GENERAL VOTES": "votes",
        "GENERAL %": "vote_share",
        "GE WINNER INDICATOR": "winner_indicator",
    }
)

# Convert the FEC's winner indicator into a Boolean value:
# W -> True, blank -> False.
results_df["won"] = results_df["winner_indicator"].eq("W")

# The workbook marks incumbents with "(I)".
# Blank values therefore become False.
results_df["incumbent"] = results_df["incumbent_indicator"].eq("(I)")

# Votes should be stored as whole numbers rather than floats.
results_df["votes"] = results_df["votes"].astype(int)

# Add information that applies to every row in this dataset.
results_df["year"] = 2022
results_df["state"] = "PA"

# We no longer need the original indicator columns after converting them.
results_df = results_df.drop(columns=["winner_indicator", "incumbent_indicator"])

print("\nAnalysis-ready election result data:")
print(results_df.to_string(index=False))

# This is to further clean the data, so that the only two presented entries are the major party candidates, that finished first and second
major_party_results = results_df[results_df["party"].isin(["D", "R"])].copy()

print("\nMajor-party candidates:")
print(major_party_results.to_string(index=False))
