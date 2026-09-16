from pathlib import Path

import pandas as pd

# Find the project root regardless of where this script is run from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Location of the official FEC 2022 election-results workbook.
RESULTS_FILE = PROJECT_ROOT / "data" / "raw" / "federalelections2022.xlsx"

SENATE_SHEET = "7. US Senate Results by State"


def get_senate_results(state):
    """
    Read and clean the 2022 Senate general-election results
    for one state and return them as a DataFrame.
    """

    # Read the Senate results sheet.
    senate_df = pd.read_excel(
        RESULTS_FILE,
        sheet_name=SENATE_SHEET,
        header=0,
    )

    # Remove accidental leading/trailing whitespace from column names.
    senate_df = senate_df.rename(
        columns=lambda column: (column.strip() if isinstance(column, str) else column)
    )

    # Keep candidates from the requested state who actually appeared
    # in the general election.
    state_candidates = senate_df[
        (senate_df["STATE ABBREVIATION"] == state)
        & senate_df["FEC ID"].notna()
        & senate_df["GENERAL VOTES"].notna()
    ].copy()

    # Keep and rename the fields relevant to our analysis.
    results_df = state_candidates[
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

    # Convert FEC indicators into Boolean values.
    results_df["won"] = results_df["winner_indicator"].eq("W")
    results_df["incumbent"] = results_df["incumbent_indicator"].eq("(I)")

    # Votes should be stored as whole numbers.
    results_df["votes"] = results_df["votes"].astype(int)

    # Add information that applies to every row.
    results_df["year"] = 2022
    results_df["state"] = state

    # We no longer need the original FEC indicator columns.
    results_df = results_df.drop(columns=["winner_indicator", "incumbent_indicator"])

    return results_df


if __name__ == "__main__":
    pennsylvania_results = get_senate_results("PA")

    print("\n2022 Pennsylvania Senate results:")
    print(pennsylvania_results.to_string(index=False))
