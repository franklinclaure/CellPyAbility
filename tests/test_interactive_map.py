"""
Tests for the reusable CellPyAbility plate-map CSV helpers.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cellpyability import interactive_map, synergy_interactive_map


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
    assert loaded.shape == (96, len(interactive_map.PLATE_MAP_COLUMNS))
    assert loaded["well"].tolist() == interactive_map.inner_wells()

    a2 = loaded[loaded["well"] == "A2"].iloc[0]
    b2 = loaded[loaded["well"] == "B2"].iloc[0]
    b3 = loaded[loaded["well"] == "B3"].iloc[0]
    e11 = loaded[loaded["well"] == "E11"].iloc[0]

    assert a2["genotype"] == "Cell Line B"
    assert a2["treatment_type"] == "vehicle"
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

    with pytest.raises(ValueError, match="exactly the 96 wells"):
        interactive_map.validate_plate_map(df)


def test_load_compact_plate_map(tmp_path):
    compact = tmp_path / "compact_plate_map.csv"
    compact.write_text(
        "\n".join(
            [
                "0,g1v,g1v,,,,,g2v,g2v,,,0",
                "g1d1c1,g1d1c1,,,,,g2d1c1,g2d1c1,,,,",
                "g1d1c2,g1d1c2,,,,,g2d1c2,g2d1c2,,,g1d1c9,",
                "g1d2c1,g1d2c1,,,,,,,,,,",
                ",,,,,,,,,,,",
                ",,,,,,,,,,,",
                ",,,,,,,,,,,",
                "0,0,0,0,0,0,0,0,0,0,0,0",
            ]
        )
    )

    loaded = interactive_map.load_plate_map(compact)

    assert loaded.shape == (96, len(interactive_map.PLATE_MAP_COLUMNS))
    assert loaded.loc[loaded["well"] == "A1", "genotype"].iloc[0] == ""
    assert loaded.loc[loaded["well"] == "A2", "genotype"].iloc[0] == "g1"
    assert loaded.loc[loaded["well"] == "A2", "treatment_type"].iloc[0] == "vehicle"
    assert loaded.loc[loaded["well"] == "B1", "drug"].iloc[0] == "d1"
    assert loaded.loc[loaded["well"] == "B1", "concentration_index"].iloc[0] == 1
    assert loaded.loc[loaded["well"] == "C11", "concentration_index"].iloc[0] == 9
    assert loaded.loc[loaded["well"] == "D1", "drug"].iloc[0] == "d2"
    assert loaded.loc[loaded["well"] == "H12", "genotype"].iloc[0] == ""


def test_load_compact_plate_map_rejects_invalid_code(tmp_path):
    compact = tmp_path / "bad_compact_plate_map.csv"
    rows = [",".join([""] * 12) for _ in range(8)]
    rows[0] = "g3v," + ",".join([""] * 11)
    compact.write_text("\n".join(rows))

    with pytest.raises(ValueError, match="Invalid compact plate-map code 'g3v' at A1"):
        interactive_map.load_plate_map(compact)


def test_synergy_blank_map_saves_zero_compact_grid(tmp_path):
    df = synergy_interactive_map.blank_synergy_map()

    assert df.shape == (96, len(synergy_interactive_map.MAP_COLUMNS))
    assert df["well"].tolist() == synergy_interactive_map.inner_wells()
    assert synergy_interactive_map.compact_grid(df) == [["0"] * 12 for _ in range(8)]

    saved = synergy_interactive_map.save_compact_grid(df, tmp_path / "synergy_map.csv")
    assert saved.read_text().splitlines()[0] == ",".join(["0"] * 12)


def test_synergy_compact_grid_uses_drug_concentration_codes():
    df = synergy_interactive_map.blank_synergy_map()
    idx = df.index[df["well"] == "A1"][0]
    df.at[idx, "assignments"] = {
        "d1": {"gradient_axis": "horizontal", "concentration_index": 2},
        "d2": {"gradient_axis": "vertical", "concentration_index": 3},
    }

    grid = synergy_interactive_map.compact_grid(df)

    assert len(grid) == 8
    assert len(grid[0]) == 12
    assert grid[0][0] == "d1c2+d2c3"
    assert grid[0][1] == "0"
    assert grid[7][11] == "0"


def test_load_compact_synergy_map(tmp_path):
    compact = tmp_path / "synergy_map.csv"
    compact.write_text(
        "\n".join(
            [
                "control,d2c3+d1c2,0,,,,,,,,,",
                ",,,,,,,,,,,",
                ",,,,,,,,,,,",
                ",,,,,,,,,,,",
                ",,,,,,,,,,,",
                ",,,,,,,,,,,",
                ",,,,,,,,,,,",
                ",,,,,,,,,,,",
            ]
        )
    )

    loaded = synergy_interactive_map.load_synergy_map(compact)

    assert loaded.shape[0] == 96
    assert loaded.loc[loaded["well"] == "A1", "code"].iloc[0] == "control"
    assert bool(loaded.loc[loaded["well"] == "A1", "is_control"].iloc[0]) is True
    a2 = loaded[loaded["well"] == "A2"].iloc[0]
    assert a2["code"] == "d1c2+d2c3"
    assert a2["assignments"] == {
        "d1": {"concentration_index": 2},
        "d2": {"concentration_index": 3},
    }
    assert loaded.loc[loaded["well"] == "A3", "code"].iloc[0] == "0"


def test_load_compact_synergy_map_rejects_invalid_code(tmp_path):
    compact = tmp_path / "bad_synergy_map.csv"
    rows = [",".join([""] * 12) for _ in range(8)]
    rows[0] = "d1x2," + ",".join([""] * 11)
    compact.write_text("\n".join(rows))

    with pytest.raises(ValueError, match="Invalid compact synergy-map code 'd1x2' at A1"):
        synergy_interactive_map.load_synergy_map(compact)
