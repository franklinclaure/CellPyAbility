"""
Test that CLI modules produce output matching expected test files.

This test verifies that running the analysis modules with test count files
produces output that matches the expected Stats files.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from cellpyability import gda_analysis, synergy_analysis, simple_analysis, toolbox as tb


def compare_csv_files(output_file, expected_file, tolerance=1e-6):
    """
    Compare two CSV files for equality, allowing for floating point tolerance.
    
    Returns:
        tuple: (bool, str) - (files_match, error_message)
    """
    try:
        df_output = pd.read_csv(output_file, index_col=0)
        df_expected = pd.read_csv(expected_file, index_col=0)
        
        # Check shape
        if df_output.shape != df_expected.shape:
            return False, f"Shape mismatch: {df_output.shape} vs {df_expected.shape}"
        
        # Check column names
        if not df_output.columns.equals(df_expected.columns):
            return False, f"Column mismatch: {df_output.columns.tolist()} vs {df_expected.columns.tolist()}"
        
        # Check index
        if not df_output.index.equals(df_expected.index):
            return False, f"Index mismatch: {df_output.index.tolist()} vs {df_expected.index.tolist()}"
        
        # Compare values with tolerance for floats
        for col in df_output.columns:
            for idx in df_output.index:
                val_out = df_output.loc[idx, col]
                val_exp = df_expected.loc[idx, col]
                
                # Handle string comparisons
                if isinstance(val_out, str) or isinstance(val_exp, str):
                    if str(val_out) != str(val_exp):
                        return False, f"String mismatch at [{idx}, {col}]: '{val_out}' vs '{val_exp}'"
                else:
                    # Numeric comparison with tolerance
                    try:
                        if not np.isclose(float(val_out), float(val_exp), rtol=tolerance, atol=tolerance):
                            return False, f"Value mismatch at [{idx}, {col}]: {val_out} vs {val_exp}"
                    except (ValueError, TypeError):
                        if val_out != val_exp:
                            return False, f"Value mismatch at [{idx}, {col}]: {val_out} vs {val_exp}"
        
        return True, "Files match"
    except Exception as e:
        return False, f"Error comparing files: {str(e)}"


def test_gda_module():
    """Test gda module with test counts file."""
    print("\n" + "="*80)
    print("Testing gda Module")
    print("="*80)
    
    test_data_dir = Path(__file__).parent / "data"
    counts_file = test_data_dir / "test_gda_counts.csv"
    expected_stats = test_data_dir / "test_gda_Stats.csv"
    
    # Run gda analysis (output goes to ./cellpyability_output/gda_output/)
    print(f"Running gda analysis with counts file: {counts_file}")
    gda_analysis.run_gda(
        title_name="test",
        upper_name="Cell Line A",
        lower_name="Cell Line B",
        top_conc=0.000001,
        dilution=3,
        image_dir="/tmp/dummy",
        show_plot=False,
        counts_file=str(counts_file)
    )
    
    # Check output file (in current working directory)
    output_stats = Path.cwd() / "cellpyability_output/gda_output/test_gda_Stats.csv"
    
    try:
        if not output_stats.exists():
            print(f"[FAIL] FAILED: Output file not created: {output_stats}")
            return False
        
        print(f"Output file created: {output_stats}")
        
        # Compare files
        match, message = compare_csv_files(output_stats, expected_stats)
        
        if match:
            print(f"[PASS] PASSED: GDA Stats output matches expected file")
            print(f"   {message}")
            result = True
        else:
            print(f"[FAIL] FAILED: GDA Stats output does not match")
            print(f"   {message}")
            
            # Show first few rows for debugging
            print("\n   First rows of output:")
            df_out = pd.read_csv(output_stats, index_col=0)
            print(df_out.head())
            print("\n   First rows of expected:")
            df_exp = pd.read_csv(expected_stats, index_col=0)
            print(df_exp.head())
            
            result = False
    finally:
        # Clean up output files - use ignore_errors for Windows compatibility
        if output_stats.exists():
            try:
                shutil.rmtree(output_stats.parent, ignore_errors=True)
            except Exception as e:
                print(f"Warning: Could not clean up output directory: {e}")
    
    return result


def test_fit_response_curve_compares_4pl_and_5pl():
    """Both logistic models are fit and the compatibility wrapper returns the selected one."""
    x = np.geomspace(1e-9, 1e-6, 9)
    y = tb.fivePL(x, 1.0, 1.2, 1e-7, 0.05, 3.0)

    comparison = tb.fit_response_models(x, y, "test")
    x_fit, y_fit, ic50, params = tb.fit_response_curve(x, y, "test", return_params=True)

    assert comparison["four_pl"] is not None
    assert comparison["five_pl"] is not None
    assert comparison["four_pl"]["RSS"] >= 0
    assert comparison["five_pl"]["RSS"] >= 0
    assert comparison["selected_model"] in {"4PL", "5PL"}
    assert params["Model"] == comparison["selected_model"]
    assert np.isclose(params["RSS"], comparison["selected_fit"]["RSS"])
    assert len(x_fit) == len(y_fit)
    assert np.isclose(params["IC50"], ic50, equal_nan=True)
    assert params["Min"] >= 0
    if params["Model"] == "5PL":
        assert 0.1 <= params["Asym"] <= 10


def test_fit_response_curve_uses_trf_and_logistic_bounds(monkeypatch):
    captured = []

    def fake_curve_fit(function, x, y, p0, **kwargs):
        captured.append({"function": function, "p0": p0, **kwargs})
        return np.asarray(p0, dtype=float), np.eye(len(p0)), {"nfev": 7}, "ok", 1

    monkeypatch.setattr(tb, "curve_fit", fake_curve_fit)
    x = np.geomspace(1e-9, 1e-6, 7)
    y = tb.fivePL(x, 1.0, 1.2, 1e-7, 0.05, 1.0)

    comparison = tb.fit_response_models(x, y, "test")
    assert comparison is not None
    assert [call["function"] for call in captured] == [tb.fivePL, tb.fourPL]
    assert all(call["method"] == "trf" for call in captured)
    assert captured[0]["bounds"] == (
        [1e-18, 0.1, 1e-18, 1e-18, 0.1],
        [2, 10, 1, 2, 10.0],
    )
    assert captured[1]["bounds"] == (
        [1e-18, 0.1, 1e-18, 1e-18],
        [2, 10, 1, 2],
    )
    assert captured[0]["p0"] == [np.max(y), 1.0, captured[0]["p0"][2], np.min(y), 1.0]
    assert captured[1]["p0"] == [np.max(y), 1.0, captured[1]["p0"][2], np.min(y)]


def test_fit_response_models_uses_f_test_for_model_selection(monkeypatch):
    x = np.geomspace(1e-9, 1e-6, 9)
    five_params = np.array([1.0, 1.2, 1e-7, 0.05, 3.0])
    y = tb.fivePL(x, *five_params)

    def significant_curve_fit(function, x_values, y_values, p0, **kwargs):
        if function is tb.fourPL:
            return np.array([1.0, 1.0, 1e-7, 0.05]), np.eye(4), {"nfev": 8}, "ok", 1
        return five_params, np.eye(5), {"nfev": 6}, "ok", 1

    monkeypatch.setattr(tb, "curve_fit", significant_curve_fit)
    significant = tb.fit_response_models(x, y, "significant")

    assert significant["selected_model"] == "5PL"
    assert significant["F p-value"] < 0.05

    four_params = np.array([1.0, 1.2, 1e-7, 0.05])
    y_four = tb.fourPL(x, *four_params)

    def nonsignificant_curve_fit(function, x_values, y_values, p0, **kwargs):
        if function is tb.fourPL:
            return four_params, np.eye(4), {"nfev": 5}, "ok", 1
        return np.append(four_params, 1.0), np.eye(5), {"nfev": 5}, "ok", 1

    monkeypatch.setattr(tb, "curve_fit", nonsignificant_curve_fit)
    nonsignificant = tb.fit_response_models(x, y_four, "nonsignificant")

    assert nonsignificant["selected_model"] == "4PL"
    assert nonsignificant["F p-value"] == 1.0


def test_gda_compact_plate_map_normalizes_and_groups_by_genotype_drug(tmp_path, monkeypatch):
    """Compact plate maps drive vehicles, means, normalization, and curve grouping."""
    def fake_fit_response_models(x, y, name):
        x_fit = np.asarray(x, dtype=float)
        y_fit = np.asarray(y, dtype=float)
        ic50 = 1e-7
        four_fit = {
            "params": {
                "Max": 4.0,
                "Infl.": ic50,
                "Min": 0.1,
                "Slope": 1.0,
                "IC50": ic50,
            },
            "RSS": 2.0,
            "Iterations": 8,
            "x_fit": x_fit,
            "y_fit": y_fit,
        }
        five_fit = {
            "params": {
                "Max": 5.0,
                "Infl.": ic50,
                "Min": 0.05,
                "Slope": 1.0,
                "Asym": 2.0,
                "IC50": ic50,
            },
            "RSS": 1.0,
            "Iterations": 6,
            "x_fit": x_fit,
            "y_fit": y_fit,
        }
        selected_model = "4PL" if name == "g1 d1" else "5PL"
        selected_fit = four_fit if selected_model == "4PL" else five_fit
        f_statistic = 0.5 if selected_model == "4PL" else 4.0
        return {
            "selected_model": selected_model,
            "selected_fit": selected_fit,
            "four_pl": four_fit,
            "five_pl": five_fit,
            "F Statistic": f_statistic,
            "F p-value": 0.5 if selected_model == "4PL" else 0.04,
            "alpha": 0.05,
            "n": len(x),
        }

    monkeypatch.setattr(gda_analysis.tb, "fit_response_models", fake_fit_response_models)

    compact_map = tmp_path / "compact_plate_map.csv"
    compact_map.write_text(
        "\n".join(
            [
                "g1v,g1v,,,,,g2v,g2v,,,,",
                "g1d1c1,g1d1c1,g1d2c1,g1d2c1,,,g2d1c1,g2d1c1,,,,",
                "g1d1c2,g1d1c2,g1d2c2,g1d2c2,,,g2d1c2,g2d1c2,,,,",
                "g1d1c3,g1d1c3,g1d2c3,g1d2c3,,,g2d1c3,g2d1c3,,,,",
                ",,,,,,,,,,,",
                ",,,,,,,,,,,",
                ",,,,,,,,,,,",
                ",,,,,,,,,,,",
            ]
        )
    )
    counts_file = tmp_path / "counts.csv"
    counts = pd.DataFrame(
        [
            ("A1", 100),
            ("A2", 120),
            ("A7", 200),
            ("A8", 220),
            ("B1", 55),
            ("B2", 55),
            ("C1", 33),
            ("C2", 44),
            ("D1", 22),
            ("D2", 22),
            ("B3", 88),
            ("B4", 99),
            ("C3", 66),
            ("C4", 77),
            ("D3", 44),
            ("D4", 55),
            ("B7", 105),
            ("B8", 105),
            ("C7", 84),
            ("C8", 84),
            ("D7", 42),
            ("D8", 42),
        ],
        columns=["FileName_DAPI", "Count_Nuclei"],
    )
    counts.to_csv(counts_file, index=False)

    gda_analysis.run_gda(
        title_name="compact",
        upper_name=None,
        lower_name=None,
        top_conc=0.000001,
        dilution=10,
        image_dir="/tmp/dummy",
        show_plot=False,
        counts_file=str(counts_file),
        output_dir=str(tmp_path),
        plate_map_file=str(compact_map),
    )

    stats = pd.read_csv(tmp_path / "gda_output/compact_gda_Stats.csv")
    viability = pd.read_csv(tmp_path / "gda_output/compact_gda_bywell.csv")
    fitted_params = pd.read_csv(
        tmp_path / "gda_output/compact_gda_fitted_params.csv",
        index_col=0,
        keep_default_na=False,
    )

    assert set(stats["Drug"]) == {"Vehicle", "d1", "d2"}
    assert "d5" not in set(stats["Drug"])

    g1_d1_c1 = stats[
        (stats["Genotype"] == "g1")
        & (stats["Drug"] == "d1")
        & (stats["Concentration Index"] == 1)
    ].iloc[0]
    assert np.isclose(g1_d1_c1["Mean"], 55)
    assert np.isclose(g1_d1_c1["Normalized Mean"], 0.5)
    assert g1_d1_c1["Wells"] == "B1;B2"

    g1_d2_c1 = stats[
        (stats["Genotype"] == "g1")
        & (stats["Drug"] == "d2")
        & (stats["Concentration Index"] == 1)
    ].iloc[0]
    assert np.isclose(g1_d2_c1["Mean"], 93.5)
    assert np.isclose(g1_d2_c1["Normalized Mean"], 93.5 / 110)

    g2_d1_c1 = stats[
        (stats["Genotype"] == "g2")
        & (stats["Drug"] == "d1")
        & (stats["Concentration Index"] == 1)
    ].iloc[0]
    assert np.isclose(g2_d1_c1["Mean"], 105)
    assert np.isclose(g2_d1_c1["Normalized Mean"], 0.5)

    assert set(viability["map_code"]) >= {"g1v", "g2v", "g1d1c1", "g1d2c1", "g2d1c1"}
    assert list(fitted_params.columns) == [
        "Max", "Infl.", "Min", "Slope", "Asym", "IC50", "RSS", "AUC",
        "Iterations", "5PL F Statistic", "p-value",
    ]
    assert set(fitted_params.index) == {"g1 d1", "g1 d2", "g2 d1"}
    assert fitted_params.loc["g1 d1", "Asym"] == "NA"
    assert fitted_params.loc["g1 d1", "RSS"] == 2.0
    assert fitted_params.loc["g1 d1", "Iterations"] == 8
    assert fitted_params.loc["g1 d1", "5PL F Statistic"] == "0.5 (not used)"
    assert fitted_params.loc["g1 d1", "p-value"] == "0.5 (not stat significant)"
    assert fitted_params.loc["g1 d2", "Asym"] == "2.0"
    assert fitted_params.loc["g1 d2", "RSS"] == 1.0
    assert fitted_params.loc["g1 d2", "Iterations"] == 6
    assert fitted_params.loc["g1 d2", "5PL F Statistic"] == "4 (used)"
    assert fitted_params.loc["g1 d2", "p-value"] == "0.04 (stat significant)"
    assert np.isfinite(fitted_params["AUC"]).all()


def test_synergy_module():
    """Test synergy module with test counts file."""
    print("\n" + "="*80)
    print("Testing synergy Module")
    print("="*80)
    
    test_data_dir = Path(__file__).parent / "data"
    counts_file = test_data_dir / "test_synergy_counts.csv"
    expected_bliss = test_data_dir / "test_synergy_BlissMatrix.csv"
    
    # Run Synergy analysis (output goes to ./cellpyability_output/synergy_output/)
    print(f"Running Synergy analysis with counts file: {counts_file}")
    synergy_analysis.run_synergy(
        title_name="test",
        x_drug="Drug X",
        x_top_conc=0.0004,
        x_dilution=4,
        y_drug="Drug Y",
        y_top_conc=0.0001,
        y_dilution=4,
        image_dir="/tmp/dummy",
        show_plot=False,
        counts_file=str(counts_file)
    )
    
    # Check output file (in current working directory)
    output_bliss = Path.cwd() / "cellpyability_output/synergy_output/test_synergy_BlissMatrix.csv"
    output_dir = output_bliss.parent
    
    try:
        if not output_bliss.exists():
            print(f"[FAIL] FAILED: Output file not created: {output_bliss}")
            return False
        
        print(f"Output file created: {output_bliss}")
        
        # Compare files
        match, message = compare_csv_files(output_bliss, expected_bliss, tolerance=1e-10)
        
        if match:
            print(f"[PASS] PASSED: Synergy BlissMatrix output matches expected file")
            print(f"   {message}")
            assert (output_dir / "test_synergy_FittedViabilityMatrix.csv").exists()
            assert (output_dir / "test_synergy_FittedBlissMatrix.csv").exists()
            assert (output_dir / "test_synergy_curve_fits.csv").exists()
            assert (output_dir / "test_synergy_curve_fits.png").exists()
            assert (output_dir / "test_synergy_plot.html").exists()
            measured_viability = pd.read_csv(
                output_dir / "test_synergy_ViabilityMatrix.csv",
                index_col=0,
            )
            fitted_viability = pd.read_csv(
                output_dir / "test_synergy_FittedViabilityMatrix.csv",
                index_col=0,
            )
            fitted_bliss = pd.read_csv(
                output_dir / "test_synergy_FittedBlissMatrix.csv",
                index_col=0,
            )
            assert "NA" in (
                output_dir / "test_synergy_FittedBlissMatrix.csv"
            ).read_text()
            assert fitted_viability.shape == measured_viability.shape
            assert fitted_bliss.shape == measured_viability.shape
            assert fitted_viability.index.equals(measured_viability.index)
            assert fitted_viability.columns.equals(measured_viability.columns)
            assert fitted_bliss.index.equals(measured_viability.index)
            assert fitted_bliss.columns.equals(measured_viability.columns)
            assert fitted_bliss.iloc[0, :].isna().all()
            assert fitted_bliss.iloc[:, 0].isna().all()
            expected_fitted = np.outer(
                fitted_viability.iloc[:, 0],
                fitted_viability.iloc[0, :],
            )
            np.testing.assert_allclose(
                fitted_bliss.iloc[1:, 1:].to_numpy(dtype=float),
                (
                    expected_fitted[1:, 1:]
                    - fitted_viability.iloc[1:, 1:].to_numpy(dtype=float)
                ),
            )
            fit_diagnostics = pd.read_csv(output_dir / "test_synergy_curve_fits.csv")
            assert set(fit_diagnostics["Direction"]) == {"horizontal"}
            assert len(fit_diagnostics) == 6
            result = True
        else:
            print(f"[FAIL] FAILED: Synergy BlissMatrix output does not match")
            print(f"   {message}")
            
            # Show first few rows for debugging
            print("\n   First rows of output:")
            df_out = pd.read_csv(output_bliss)
            print(df_out.head())
            print("\n   First rows of expected:")
            df_exp = pd.read_csv(expected_bliss)
            print(df_exp.head())
            
            result = False
    finally:
        # Clean up output files - use ignore_errors for Windows compatibility
        if output_bliss.exists():
            try:
                shutil.rmtree(output_bliss.parent, ignore_errors=True)
            except Exception as e:
                print(f"Warning: Could not clean up output directory: {e}")
    
    return result


def test_synergy_compact_plate_map_groups_by_code_and_normalizes(tmp_path):
    """Compact synergy maps group repeated wells and repeated images by code."""
    compact_map = tmp_path / "synergy_map.csv"
    compact_map.write_text(
        "\n".join(
            [
                "control,control,d1c1,d1c1,d2c1,d1c1+d2c1,,,,,,",
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
    counts_file = tmp_path / "counts.csv"
    counts = pd.DataFrame(
        [
            ("A1", 100),
            ("A1", 110),
            ("A2", 90),
            ("A3", 50),
            ("A4", 70),
            ("A4", 80),
            ("A5", 80),
            ("A6", 25),
        ],
        columns=["FileName_DAPI", "Count_Nuclei"],
    )
    counts.to_csv(counts_file, index=False)

    synergy_analysis.run_synergy(
        title_name="mapped_synergy",
        x_drug="Drug X",
        x_top_conc=0.0004,
        x_dilution=4,
        y_drug="Drug Y",
        y_top_conc=0.0001,
        y_dilution=4,
        image_dir="/tmp/dummy",
        show_plot=False,
        counts_file=str(counts_file),
        output_dir=str(tmp_path),
        plate_map_file=str(compact_map),
    )

    stats = pd.read_csv(tmp_path / "synergy_output/mapped_synergy_synergy_stats.csv")
    bywell = pd.read_csv(tmp_path / "synergy_output/mapped_synergy_synergy_bywell.csv")

    assert list(stats.columns) == [
        "Well(s)",
        "code",
        "Mean",
        "Standard Deviation",
        "Normalized Mean",
        "Row Drug Concentration",
        "Column Drug Concentration",
        "N",
    ]

    control = stats[stats["code"] == "control"].iloc[0]
    assert control["Well(s)"] == "A1,A2"
    assert np.isclose(control["Mean"], 100)
    assert np.isclose(control["Normalized Mean"], 1.0)
    assert np.isclose(control["Row Drug Concentration"], 0.0)
    assert np.isclose(control["Column Drug Concentration"], 0.0)

    d1c1 = stats[stats["code"] == "d1c1"].iloc[0]
    assert d1c1["Well(s)"] == "A3,A4"
    assert np.isclose(d1c1["Mean"], (50 + 70 + 80) / 3)
    assert np.isclose(d1c1["Normalized Mean"], ((50 + 70 + 80) / 3) / 100)
    assert np.isclose(d1c1["Row Drug Concentration"], 0.0)
    assert np.isclose(d1c1["Column Drug Concentration"], 0.0004)
    assert int(d1c1["N"]) == 3

    combo = stats[stats["code"] == "d1c1+d2c1"].iloc[0]
    assert np.isclose(combo["Row Drug Concentration"], 0.0001)
    assert np.isclose(combo["Column Drug Concentration"], 0.0004)

    assert set(bywell["code"]) == {"control", "d1c1", "d2c1", "d1c1+d2c1"}
    a6 = bywell[bywell["well"] == "A6"].iloc[0]
    assert np.isclose(a6["normalized_nuclei"], 0.25)
    assert (tmp_path / "synergy_output/mapped_synergy_synergy_BlissMatrix.csv").exists()
    assert not (tmp_path / "synergy_output/mapped_synergy_synergy_plot.html").exists()
    assert not (tmp_path / "synergy_output/mapped_synergy_synergy_FittedViabilityMatrix.csv").exists()


def test_synergy_compact_plate_map_skips_bliss_for_irregular_map(tmp_path):
    compact_map = tmp_path / "irregular_synergy_map.csv"
    compact_map.write_text(
        "\n".join(
            [
                "control,d1c1,,,,,,,,,,",
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
    counts_file = tmp_path / "counts.csv"
    pd.DataFrame(
        [("A1", 100), ("A2", 50)],
        columns=["FileName_DAPI", "Count_Nuclei"],
    ).to_csv(counts_file, index=False)

    synergy_analysis.run_synergy(
        title_name="irregular_synergy",
        x_drug="Drug X",
        x_top_conc=0.0004,
        x_dilution=4,
        y_drug="Drug Y",
        y_top_conc=0.0001,
        y_dilution=4,
        image_dir="/tmp/dummy",
        show_plot=False,
        counts_file=str(counts_file),
        output_dir=str(tmp_path),
        plate_map_file=str(compact_map),
    )

    output_dir = tmp_path / "synergy_output"
    assert (output_dir / "irregular_synergy_synergy_stats.csv").exists()
    assert (output_dir / "irregular_synergy_synergy_bywell.csv").exists()
    assert not (output_dir / "irregular_synergy_synergy_BlissMatrix.csv").exists()
    assert not (output_dir / "irregular_synergy_synergy_plot.html").exists()


def test_synergy_equal_grid_direction_selection(monkeypatch):
    matrix = pd.DataFrame(np.ones((6, 6)))
    x_doses = np.arange(6, dtype=float)
    y_doses = np.arange(6, dtype=float)

    def candidate(direction, supports_5pl, five_rss, four_rss):
        return {
            "direction": direction,
            "supports_5pl": supports_5pl,
            "five_rss_sum": five_rss,
            "four_rss_sum": four_rss,
        }

    scenarios = {
        "horizontal": candidate("horizontal", True, 5.0, 8.0),
        "vertical": candidate("vertical", False, 2.0, 4.0),
    }
    monkeypatch.setattr(
        synergy_analysis,
        "_fit_synergy_direction",
        lambda *args: scenarios[args[3]],
    )
    selected = synergy_analysis._choose_synergy_fit_direction(
        matrix, x_doses, y_doses, 0.1, 0.1
    )
    assert selected["direction"] == "horizontal"

    scenarios["vertical"] = candidate("vertical", True, 3.0, 4.0)
    selected = synergy_analysis._choose_synergy_fit_direction(
        matrix, x_doses, y_doses, 0.1, 0.1
    )
    assert selected["direction"] == "vertical"

    scenarios["horizontal"] = candidate("horizontal", False, np.inf, 3.0)
    scenarios["vertical"] = candidate("vertical", False, np.inf, 4.0)
    selected = synergy_analysis._choose_synergy_fit_direction(
        matrix, x_doses, y_doses, 0.1, 0.1
    )
    assert selected["direction"] == "horizontal"


def test_synergy_preferred_direction_falls_back(monkeypatch):
    matrix = pd.DataFrame(np.ones((6, 10)))
    calls = []

    def fake_fit(*args):
        direction = args[3]
        calls.append(direction)
        if direction == "horizontal":
            return None
        return {
            "direction": "vertical",
            "supports_5pl": False,
            "five_rss_sum": np.inf,
            "four_rss_sum": 1.0,
        }

    monkeypatch.setattr(synergy_analysis, "_fit_synergy_direction", fake_fit)
    selected = synergy_analysis._choose_synergy_fit_direction(
        matrix,
        np.arange(10, dtype=float),
        np.arange(6, dtype=float),
        0.1,
        0.1,
    )

    assert calls == ["horizontal", "vertical"]
    assert selected["direction"] == "vertical"


def test_simple_module():
    """Test simple module with test counts file."""
    print("\n" + "="*80)
    print("Testing simple Module")
    print("="*80)
    
    test_data_dir = Path(__file__).parent / "data"
    # Use gda counts for simple module test
    counts_file = test_data_dir / "test_gda_counts.csv"
    expected_output = test_data_dir / "test_simple_CountMatrix.csv"
    
    # Run Simple analysis (output goes to ./cellpyability_output/simple_output/)
    print(f"Running Simple analysis with counts file: {counts_file}")
    simple_analysis.run_simple(
        title="test",
        image_dir="/tmp/dummy",
        counts_file=str(counts_file)
    )
    
    # Check output file (in current working directory)
    output_matrix = Path.cwd() / "cellpyability_output/simple_output/test_simple_CountMatrix.csv"
    
    try:
        if not output_matrix.exists():
            print(f"[FAIL] FAILED: Output file not created: {output_matrix}")
            return False
        
        print(f"Output file created: {output_matrix}")
        
        # Compare files
        match, message = compare_csv_files(output_matrix, expected_output)
        
        if match:
            print(f"[PASS] PASSED: Simple CountMatrix output matches expected file")
            print(f"   {message}")
            result = True
        else:
            print(f"[FAIL] FAILED: Simple CountMatrix output does not match")
            print(f"   {message}")
            
            # Show files for debugging
            print("\n   Output:")
            df_out = pd.read_csv(output_matrix, index_col=0)
            print(df_out)
            print("\n   Expected:")
            df_exp = pd.read_csv(expected_output, index_col=0)
            print(df_exp)
            
            result = False
    finally:
        # Clean up output files - use ignore_errors for Windows compatibility
        if output_matrix.exists():
            try:
                shutil.rmtree(output_matrix.parent, ignore_errors=True)
            except Exception as e:
                print(f"Warning: Could not clean up output directory: {e}")
    
    return result


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("CellPyAbility Module Output Validation Tests")
    print("="*80)
    print("Testing that analysis modules produce expected output from test count files")
    
    results = {
        'gda': test_gda_module(),
        'synergy': test_synergy_module(),
        'simple': test_simple_module()
    }
    
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    
    all_passed = True
    for module, passed in results.items():
        status = "[PASS] PASSED" if passed else "[FAIL] FAILED"
        print(f"{module:15} {status}")
        if not passed:
            all_passed = False
    
    print("="*80)
    
    if all_passed:
        print("\nAll tests passed! Outputs match expected files.")
        return 0
    else:
        print("\n[WARNING] Some tests failed. See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
