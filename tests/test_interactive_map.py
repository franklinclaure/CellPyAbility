"""
Tests for the reusable CellPyAbility plate-map CSV helpers.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cellpyability import interactive_map


def test_default_gda_plate_map_round_trips(tmp_path):
    output_csv = tmp_path / "plate_map.csv"

    df = interactive_map.default_gda_plate_map(
        genotype_1="Cell Line A",
        genotype_2="Cell Line B",
        drug="Drug X",
    )
    saved = interactive_map.save_plate_map(df, output_csv)
    loaded = interactive_map.load_plate_map(saved)

    assert saved == output_csv.resolve()
    assert loaded.shape == (60, len(interactive_map.PLATE_MAP_COLUMNS))
    assert loaded["well"].tolist() == interactive_map.inner_wells()

    b2 = loaded[loaded["well"] == "B2"].iloc[0]
    b3 = loaded[loaded["well"] == "B3"].iloc[0]
    e11 = loaded[loaded["well"] == "E11"].iloc[0]

    assert b2["genotype"] == "Cell Line A"
    assert b2["treatment_type"] == "vehicle"
    assert b2["concentration_index"] == 0
    assert b3["drug"] == "Drug X"
    assert b3["gradient_axis"] == "horizontal"
    assert b3["concentration_index"] == 1
    assert e11["genotype"] == "Cell Line B"
    assert e11["concentration_index"] == 9


def test_validate_plate_map_requires_all_inner_wells():
    df = interactive_map.default_gda_plate_map()
    df = df[df["well"] != "B2"]

    with pytest.raises(ValueError, match="exactly the inner wells"):
        interactive_map.validate_plate_map(df)
