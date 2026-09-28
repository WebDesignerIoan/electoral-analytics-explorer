from pathlib import Path

import pandas as pd

# Find the project root regardless of where this script is run from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Location of the official FEC 2022 election-results workbook.
RESULTS_FILE = PROJECT_ROOT / "data" / "raw" / "federalelections2022.xlsx"

SENATE_SHEET = "7. US Senate Results by State"


def get_senate_results(state, district):
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
        & (senate_df["DISTRICT"] == district)
        & senate_df["FEC ID"].notna()
        & senate_df["GENERAL VOTES"].notna()
    ].copy()

    # Keep and rename the fields relevant to our analysis.
    results_df = state_candidates[
        [
            "FEC ID",
            "CANDIDATE NAME",
            "PARTY",
            "DISTRICT",
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
            "DISTRICT": "district",
            "(I) INCUMBENT INDICATOR": "incumbent_indicator",
            "GENERAL VOTES": "votes",
            "GENERAL %": "vote_share",
            "GE WINNER INDICATOR": "winner_indicator",
        }
    )

    # Remove accidental whitespace from important text fields.

    # This also removes invisible whitespace such as tabs around FEC IDs.
    for column in ["fec_candidate_id", "name", "party"]:
        results_df[column] = results_df[column].str.strip()

    # Clean the fields used to identify a specific Senate race --> we can have different types of senate races for same state
    senate_df["STATE ABBREVIATION"] = senate_df["STATE ABBREVIATION"].str.strip()
    senate_df["DISTRICT"] = senate_df["DISTRICT"].str.strip()

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


def classify_major_party(party_lines):
    """
    Classify a candidate into the Democratic or Republican
    analytical group based on their ballot-line party codes.

    Return None when the candidate does not belong to either
    major-party group used in our analysis.
    """

    democratic_codes = {
        "D",
        "D*",
        "DNL",
        "D/IP",
    }

    republican_codes = {
        "R",
        "R*",
        "R/CON",
    }

    # A candidate may appear under multiple ballot lines.
    # If any of those lines identifies the candidate with one
    # of our recognised Democratic codes, classify them as D.
    if any(code in democratic_codes for code in party_lines):
        return "D"

    # Apply the same logic for recognised Republican codes.
    if any(code in republican_codes for code in party_lines):
        return "R"

    # Other candidates remain outside the D/R comparison.
    return None


def aggregate_candidate_results(results_df):
    """
    Combine multiple ballot-line rows belonging to the same candidate
    into one candidate-level row.
    """

    # A candidate can appear more than once in the election results
    # when the same FEC candidate ID is listed under multiple party lines.
    #
    # Example:
    # Schumer may appear once as D and once as WF,
    # but both rows refer to the same candidate.
    aggregated_df = results_df.groupby(
        "fec_candidate_id",
        as_index=False,
    ).agg(
        # These fields should be the same for every row belonging
        # to the same FEC candidate ID, so keeping the first value
        # is sufficient.
        name=("name", "first"),
        district=("district", "first"),
        year=("year", "first"),
        state=("state", "first"),
        # Preserve every ballot-line party code for now.
        # We will decide how to map these to our analytical
        # Democratic/Republican categories in a later step.
        party_lines=("party", lambda values: list(values)),
        # Votes received by the same candidate on different
        # ballot lines belong to the same candidate-level total.
        votes=("votes", "sum"),
        # A candidate should count as the winner if any of their
        # ballot-line rows is marked as winning.
        won=("won", "any"),
        # Likewise, incumbency applies to the candidate rather
        # than to an individual ballot line.
        incumbent=("incumbent", "any"),
    )

    # Recalculate candidate vote share from the aggregated vote totals
    # rather than adding the percentages provided by the source.
    # This avoids carrying forward any rounding differences in the
    # ballot-line percentages.
    aggregated_df["vote_share"] = aggregated_df["votes"] / aggregated_df["votes"].sum()

    # Create the simplified D/R classification used by the analysis
    # while preserving the original ballot-line party codes.
    aggregated_df["major_party"] = aggregated_df["party_lines"].apply(
        classify_major_party
    )

    return aggregated_df


# This reads the Senate sheet, keeps rows that contain general-election vote totals, extracts the unique state abbreviations and returns them in sorted order
def get_senate_states():
    """
    Return the state abbreviations that contain 2022
    Senate general-election results in the FEC workbook.
    """

    senate_df = pd.read_excel(
        RESULTS_FILE,
        sheet_name=SENATE_SHEET,
        header=0,
    )

    senate_df = senate_df.rename(
        columns=lambda column: (column.strip() if isinstance(column, str) else column)
    )  # clean column names from extra whitespaces (if column name is actually a string)

    # This gets the unique state abbreviations for rows that contain general-election vote totals
    # notna() creates a boolean filter, that is True when GENERAL VOTES has a value
    # and then from the rows where general-election votes exist, keep only the STATE ABBREVIATION column
    # dropna() removes any missing state abbreviations
    # unique() removes duplicates, leaving one entry per state
    states = (
        senate_df.loc[
            senate_df["GENERAL VOTES"].notna(),
            "STATE ABBREVIATION",
        ]
        .dropna()
        .unique()
    )

    return sorted(states)


def get_senate_races():
    """
    Return the unique 2022 Senate races that contain
    general-election results.
    """

    senate_df = pd.read_excel(
        RESULTS_FILE,
        sheet_name=SENATE_SHEET,
        header=0,
    )

    # Clean column names.
    senate_df = senate_df.rename(
        columns=lambda column: (column.strip() if isinstance(column, str) else column)
    )

    # Clean the two fields that together identify a Senate race.
    # This is important because values such as "S " and "S" should represent the same district/contest type
    senate_df["STATE ABBREVIATION"] = senate_df["STATE ABBREVIATION"].str.strip()

    senate_df["DISTRICT"] = senate_df["DISTRICT"].str.strip()

    # Keep only rows that contain general-election vote totals,
    # because those are the rows relevant to our race-level analysis.
    # We select both STATE ABBREVIATION and DISTRICT because a state
    # can contain more than one Senate contest in the same year
    # (for example, a full-term and an unexpired-term election)
    races = (
        senate_df.loc[
            senate_df["GENERAL VOTES"].notna(),
            ["STATE ABBREVIATION", "DISTRICT"],
        ]
        .dropna()
        .drop_duplicates()
        .sort_values(["STATE ABBREVIATION", "DISTRICT"])
    )

    # Convert the two-column DataFrame into a list of tuples such as:
    # [("AL", "S"), ("CA", "S-Full Term"), ("CA", "S-Unexpired Term")]

    return list(races.itertuples(index=False, name=None))


# STRUCTURE
# Read the official FEC Senate results workbook
#        >
# Clean source fields and identifiers
#        >
# Identify distinct Senate races using state + district
#        >
# Select the rows belonging to one race
#        >
# Aggregate multiple ballot lines for the same candidate
#        >
# Classify candidates into D/R analytical groups
#        >
# Return candidate-level election results
