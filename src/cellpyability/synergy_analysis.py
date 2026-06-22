"""
Synergy analysis module for dose response analysis of one cell line and two drugs.
Calculates relative viability matrices and surface map with Bliss independence as heat.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go

from . import toolbox as tb

# Initialize toolbox
logger, base_dir = tb.logger, tb.base_dir


def _evaluate_selected_logistic(comparison, concentrations):
    """Evaluate the selected 4PL or 5PL model at arbitrary concentrations."""
    params = comparison["selected_fit"]["params"]
    if comparison["selected_model"] == "5PL":
        return tb.fivePL(
            concentrations,
            params["Max"],
            params["Slope"],
            params["Infl."],
            params["Min"],
            params["Asym"],
        )
    return tb.fourPL(
        concentrations,
        params["Max"],
        params["Slope"],
        params["Infl."],
        params["Min"],
    )


def _evaluate_at_tested_doses(comparison, doses, zero_value):
    """Evaluate a selected model at tested doses while preserving the measured zero dose."""
    doses = np.asarray(doses, dtype=float)
    values = np.empty(doses.shape, dtype=float)
    positive = doses > 0
    values[positive] = _evaluate_selected_logistic(comparison, doses[positive])
    values[~positive] = zero_value
    return values


def _fit_synergy_direction(viability_matrix, x_doses, y_doses, direction, visual_zero):
    """Fit every matrix slice in one direction and build its dense viability surface."""
    slice_results = []
    if direction == "horizontal":
        for row_idx, fixed_dose in enumerate(y_doses):
            comparison = tb.fit_response_models(
                x_doses,
                viability_matrix.iloc[row_idx].to_numpy(dtype=float),
                f"horizontal y={fixed_dose:.6g}",
            )
            if comparison is None:
                return None
            slice_results.append((fixed_dose, comparison))

        dense_axis = np.insert(slice_results[0][1]["selected_fit"]["x_fit"], 0, visual_zero)
        fitted_values = np.vstack([
            _evaluate_selected_logistic(comparison, dense_axis)
            for _, comparison in slice_results
        ])
        fitted_x = dense_axis
        fitted_y = np.asarray(y_doses, dtype=float)
    else:
        for column_idx, fixed_dose in enumerate(x_doses):
            comparison = tb.fit_response_models(
                y_doses,
                viability_matrix.iloc[:, column_idx].to_numpy(dtype=float),
                f"vertical x={fixed_dose:.6g}",
            )
            if comparison is None:
                return None
            slice_results.append((fixed_dose, comparison))

        dense_axis = np.insert(slice_results[0][1]["selected_fit"]["x_fit"], 0, visual_zero)
        fitted_values = np.column_stack([
            _evaluate_selected_logistic(comparison, dense_axis)
            for _, comparison in slice_results
        ])
        fitted_x = np.asarray(x_doses, dtype=float)
        fitted_y = dense_axis

    return {
        "direction": direction,
        "slices": slice_results,
        "viability": fitted_values,
        "x_plot": fitted_x,
        "y_plot": fitted_y,
        "supports_5pl": any(
            comparison["selected_model"] == "5PL"
            for _, comparison in slice_results
        ),
        "five_rss_sum": (
            sum(comparison["five_pl"]["RSS"] for _, comparison in slice_results)
            if all(comparison["five_pl"] is not None for _, comparison in slice_results)
            else np.inf
        ),
        "four_rss_sum": (
            sum(comparison["four_pl"]["RSS"] for _, comparison in slice_results)
            if all(comparison["four_pl"] is not None for _, comparison in slice_results)
            else np.inf
        ),
    }


def _choose_synergy_fit_direction(
    viability_matrix,
    x_doses,
    y_doses,
    x_visual_zero,
    y_visual_zero,
):
    """Choose a complete horizontal or vertical fitted surface."""
    horizontal_points = viability_matrix.shape[1]
    vertical_points = viability_matrix.shape[0]

    horizontal = None
    vertical = None
    if horizontal_points > vertical_points:
        horizontal = _fit_synergy_direction(
            viability_matrix, x_doses, y_doses, "horizontal", x_visual_zero
        )
        if horizontal is not None:
            return horizontal
        return _fit_synergy_direction(
            viability_matrix, x_doses, y_doses, "vertical", y_visual_zero
        )

    if vertical_points > horizontal_points:
        vertical = _fit_synergy_direction(
            viability_matrix, x_doses, y_doses, "vertical", y_visual_zero
        )
        if vertical is not None:
            return vertical
        return _fit_synergy_direction(
            viability_matrix, x_doses, y_doses, "horizontal", x_visual_zero
        )

    horizontal = _fit_synergy_direction(
        viability_matrix, x_doses, y_doses, "horizontal", x_visual_zero
    )
    vertical = _fit_synergy_direction(
        viability_matrix, x_doses, y_doses, "vertical", y_visual_zero
    )
    if horizontal is None:
        return vertical
    if vertical is None:
        return horizontal

    if horizontal["supports_5pl"] != vertical["supports_5pl"]:
        return horizontal if horizontal["supports_5pl"] else vertical
    if horizontal["supports_5pl"]:
        return (
            horizontal
            if horizontal["five_rss_sum"] <= vertical["five_rss_sum"]
            else vertical
        )
    return (
        horizontal
        if horizontal["four_rss_sum"] <= vertical["four_rss_sum"]
        else vertical
    )


def _synergy_fit_diagnostics(selected_surface, x_drug, y_drug):
    """Create one diagnostics row per selected-direction concentration slice."""
    rows = []
    direction = selected_surface["direction"]
    fixed_drug = y_drug if direction == "horizontal" else x_drug
    for fixed_dose, comparison in selected_surface["slices"]:
        selected_fit = comparison["selected_fit"]
        selected_params = selected_fit["params"]
        rows.append(
            {
                "Direction": direction,
                "Fixed Drug": fixed_drug,
                "Fixed Drug Concentration": fixed_dose,
                "Selected Direction": direction,
                "Selected Model": comparison["selected_model"],
                "4PL RSS": (
                    comparison["four_pl"]["RSS"]
                    if comparison["four_pl"] is not None
                    else "NA"
                ),
                "5PL RSS": (
                    comparison["five_pl"]["RSS"]
                    if comparison["five_pl"] is not None
                    else "NA"
                ),
                "F Statistic": (
                    comparison["F Statistic"]
                    if np.isfinite(comparison["F Statistic"])
                    else "NA"
                ),
                "p-value": (
                    comparison["F p-value"]
                    if np.isfinite(comparison["F p-value"])
                    else "NA"
                ),
                "Iterations": selected_fit["Iterations"],
                "Max": selected_params["Max"],
                "Infl.": selected_params["Infl."],
                "Min": selected_params["Min"],
                "Slope": selected_params["Slope"],
                "Asym": selected_params.get("Asym", "NA"),
                "IC50": selected_params["IC50"],
                "AUC": np.trapz(selected_fit["y_fit"], selected_fit["x_fit"]),
            }
        )
    return pd.DataFrame(rows)


def _save_synergy_curve_plot(
    title_name,
    selected_surface,
    viability_matrix,
    x_doses,
    y_doses,
    x_drug,
    y_drug,
    synergy_output_dir,
):
    """Save every selected 4PL/5PL slice as a GDA-style dose-response panel."""
    direction = selected_surface["direction"]
    slices = selected_surface["slices"]
    panel_count = len(slices)
    column_count = min(3, panel_count)
    row_count = int(np.ceil(panel_count / column_count))
    fig, axes = plt.subplots(
        row_count,
        column_count,
        figsize=(5 * column_count, 4 * row_count),
        squeeze=False,
    )
    axes = axes.ravel()

    curve_doses = np.asarray(
        x_doses if direction == "horizontal" else y_doses,
        dtype=float,
    )
    positive = curve_doses > 0
    curve_drug = x_drug if direction == "horizontal" else y_drug
    fixed_drug = y_drug if direction == "horizontal" else x_drug
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    for panel_index, (fixed_dose, comparison) in enumerate(slices):
        axis = axes[panel_index]
        selected_fit = comparison["selected_fit"]
        selected_model = comparison["selected_model"]
        measured = (
            viability_matrix.iloc[panel_index].to_numpy(dtype=float)
            if direction == "horizontal"
            else viability_matrix.iloc[:, panel_index].to_numpy(dtype=float)
        )
        color = colors[panel_index % len(colors)]

        axis.plot(
            selected_fit["x_fit"],
            selected_fit["y_fit"],
            color=color,
            label=f"{selected_model} fit",
        )
        axis.scatter(
            curve_doses[positive],
            measured[positive],
            color=color,
            label="Measured viability",
            zorder=3,
        )
        axis.set_xscale("log")
        axis.set_xlabel(f"{curve_drug} Concentration (M)")
        axis.set_ylabel("Relative Cell Survival")
        axis.set_title(f"{fixed_drug} = {fixed_dose:.2e} M")
        axis.text(
            0.04,
            0.06,
            f"{selected_model} IC50 = {selected_fit['params']['IC50']:.2e}",
            color=color,
            transform=axis.transAxes,
        )
        axis.legend()

    for axis in axes[panel_count:]:
        axis.remove()

    fig.suptitle(f"{title_name} Synergy Curve Fits ({direction})")
    fig.tight_layout()
    fig.savefig(
        synergy_output_dir / f"{title_name}_synergy_curve_fits.png",
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(fig)


def _build_tested_fitted_matrices(
    selected_surface,
    viability_matrix,
    x_doses,
    y_doses,
):
    """Evaluate selected curves at tested doses and calculate combination-only Bliss."""
    x_doses = np.asarray(x_doses, dtype=float)
    y_doses = np.asarray(y_doses, dtype=float)
    measured = viability_matrix.to_numpy(dtype=float)
    fitted = measured.copy()

    if selected_surface["direction"] == "horizontal":
        for row_idx, (_, comparison) in enumerate(selected_surface["slices"]):
            fitted[row_idx, :] = _evaluate_at_tested_doses(
                comparison,
                x_doses,
                measured[row_idx, 0],
            )
        x_alone_comparison = selected_surface["slices"][0][1]
        y_alone_comparison = tb.fit_response_models(
            y_doses,
            measured[:, 0],
            "fitted Bliss Drug Y alone",
        )
    else:
        for column_idx, (_, comparison) in enumerate(selected_surface["slices"]):
            fitted[:, column_idx] = _evaluate_at_tested_doses(
                comparison,
                y_doses,
                measured[0, column_idx],
            )
        x_alone_comparison = tb.fit_response_models(
            x_doses,
            measured[0, :],
            "fitted Bliss Drug X alone",
        )
        y_alone_comparison = selected_surface["slices"][0][1]

    fitted_x_alone = (
        _evaluate_at_tested_doses(
            x_alone_comparison,
            x_doses,
            measured[0, 0],
        )
        if x_alone_comparison is not None
        else measured[0, :].copy()
    )
    fitted_y_alone = (
        _evaluate_at_tested_doses(
            y_alone_comparison,
            y_doses,
            measured[0, 0],
        )
        if y_alone_comparison is not None
        else measured[:, 0].copy()
    )
    if x_alone_comparison is None or y_alone_comparison is None:
        logger.warning(
            "A single-drug edge could not be fit; measured edge viability was used "
            "for the fitted Bliss expectation."
        )

    fitted[0, :] = fitted_x_alone
    fitted[:, 0] = fitted_y_alone
    fitted[0, 0] = measured[0, 0]

    fitted_expected = np.outer(fitted_y_alone, fitted_x_alone)
    fitted_bliss = fitted_expected - fitted
    fitted_bliss[0, :] = np.nan
    fitted_bliss[:, 0] = np.nan
    return fitted, fitted_bliss, fitted_x_alone, fitted_y_alone


def _save_fitted_synergy_surface(
    title_name,
    x_drug,
    y_drug,
    x_dilution,
    y_dilution,
    viability_matrix,
    x_doses,
    y_doses,
    synergy_output_dir,
    show_plot,
):
    """Fit the synergy surface, save modeled matrices, diagnostics, and Plotly output."""
    x_doses = np.asarray(x_doses, dtype=float)
    y_doses = np.asarray(y_doses, dtype=float)
    x_min_nonzero = np.min(x_doses[x_doses > 0])
    y_min_nonzero = np.min(y_doses[y_doses > 0])
    visual_dilution = max(x_dilution, y_dilution)
    x_visual_zero = x_min_nonzero / visual_dilution
    y_visual_zero = y_min_nonzero / visual_dilution

    horizontal_zero = x_visual_zero
    vertical_zero = y_visual_zero
    selected_surface = _choose_synergy_fit_direction(
        viability_matrix,
        x_doses,
        y_doses,
        horizontal_zero,
        vertical_zero,
    )
    if selected_surface is None:
        raise tb.DataValidationError("Could not create a complete fitted synergy surface.")

    if selected_surface["direction"] == "horizontal":
        fitted_x_plot = selected_surface["x_plot"]
        fitted_y_plot = np.where(y_doses == 0, y_visual_zero, y_doses)
    else:
        fitted_x_plot = np.where(x_doses == 0, x_visual_zero, x_doses)
        fitted_y_plot = selected_surface["y_plot"]

    (
        tested_fitted_viability,
        tested_fitted_bliss,
        tested_fitted_x_alone,
        tested_fitted_y_alone,
    ) = _build_tested_fitted_matrices(
        selected_surface,
        viability_matrix,
        x_doses,
        y_doses,
    )

    dense_fitted_viability = selected_surface["viability"].copy()
    if selected_surface["direction"] == "horizontal":
        dense_fitted_viability[:, 0] = tested_fitted_y_alone
        dense_fitted_x_alone = dense_fitted_viability[0, :]
        dense_fitted_y_alone = tested_fitted_y_alone
    else:
        dense_fitted_viability[0, :] = tested_fitted_x_alone
        dense_fitted_x_alone = tested_fitted_x_alone
        dense_fitted_y_alone = dense_fitted_viability[:, 0]
    dense_fitted_viability[0, 0] = viability_matrix.iloc[0, 0]
    dense_fitted_expected = np.outer(dense_fitted_y_alone, dense_fitted_x_alone)
    dense_fitted_bliss = dense_fitted_expected - dense_fitted_viability
    dense_fitted_bliss[0, :] = np.nan
    dense_fitted_bliss[:, 0] = np.nan

    fitted_viability_out = pd.DataFrame(
        tested_fitted_viability,
        index=y_doses,
        columns=x_doses,
    )
    fitted_viability_out.index.name = f"{y_drug} (M)"
    fitted_viability_out.columns.name = f"{x_drug} (M)"
    fitted_bliss_out = pd.DataFrame(
        tested_fitted_bliss,
        index=y_doses,
        columns=x_doses,
    )
    fitted_bliss_out.index.name = f"{y_drug} (M)"
    fitted_bliss_out.columns.name = f"{x_drug} (M)"

    fitted_viability_out.to_csv(
        synergy_output_dir / f"{title_name}_synergy_FittedViabilityMatrix.csv"
    )
    fitted_bliss_out.to_csv(
        synergy_output_dir / f"{title_name}_synergy_FittedBlissMatrix.csv",
        na_rep="NA",
    )
    _synergy_fit_diagnostics(selected_surface, x_drug, y_drug).to_csv(
        synergy_output_dir / f"{title_name}_synergy_curve_fits.csv",
        index=False,
    )
    _save_synergy_curve_plot(
        title_name=title_name,
        selected_surface=selected_surface,
        viability_matrix=viability_matrix,
        x_doses=x_doses,
        y_doses=y_doses,
        x_drug=x_drug,
        y_drug=y_drug,
        synergy_output_dir=synergy_output_dir,
    )

    direction_rss = (
        selected_surface["five_rss_sum"]
        if selected_surface["supports_5pl"]
        else selected_surface["four_rss_sum"]
    )
    logger.info(
        "Synergy fitted surface direction: %s; direction RSS total: %s",
        selected_surface["direction"],
        direction_rss,
    )

    fig = go.Figure(data=[
        go.Surface(
            z=dense_fitted_viability,
            x=fitted_x_plot,
            y=fitted_y_plot,
            surfacecolor=dense_fitted_bliss,
            colorscale="jet_r",
            cmin=-0.3,
            cmax=0.3,
            colorbar=dict(title="Fitted Bliss Independence"),
        ),
    ])
    fig.update_layout(
        title=f"{title_name} ({selected_surface['direction']} logistic surface)",
        scene=dict(
            xaxis=dict(
                title=x_drug,
                type="log",
                tickvals=np.where(x_doses == 0, x_visual_zero, x_doses),
                ticktext=["0" if value == 0 else f"{value:.1e}" for value in x_doses],
            ),
            yaxis=dict(
                title=y_drug,
                type="log",
                tickvals=np.where(y_doses == 0, y_visual_zero, y_doses),
                ticktext=["0" if value == 0 else f"{value:.1e}" for value in y_doses],
            ),
            zaxis=dict(title="Relative Cell Survival", range=[0, 1.1]),
        ),
    )
    fig.write_html(synergy_output_dir / f"{title_name}_synergy_plot.html")
    if show_plot:
        fig.show()


def run_synergy(title_name, x_drug, x_top_conc, x_dilution, y_drug, y_top_conc, y_dilution, image_dir, show_plot=True, counts_file=None, output_dir=None, plate_map_file=None):
    """
    Run synergy analysis for drug combination experiments.
    
    Parameters:
    -----------
    title_name : str
        Title of the experiment
    x_drug : str
        Drug name for horizontal gradient (Columns)
    x_top_conc : float
        Horizontal top concentration in molar
    x_dilution : float
        Horizontal dilution factor
    y_drug : str
        Drug name for vertical gradient (Rows)
    y_top_conc : float
        Vertical top concentration in molar
    y_dilution : float
        Vertical dilution factor
    image_dir : str
        Directory containing images for 60 wells (180 images total with triplicates)
    show_plot : bool
        Whether to display the plot (default: True)
    counts_file : str, optional
        Path to pre-existing counts CSV file (for testing)
    output_dir : str, optional
        Custom output directory. If None, uses current working directory.
    plate_map_file : str, optional
        Compact synergy map CSV. If provided, code-based mapped synergy outputs
        are produced instead of the historical fixed B-G / 2-11 matrix.
    """
    
    # Calculate concentration gradients (NumPy arrays)
    x_doses = tb.gen_dose_range(x_top_conc, x_dilution, 9) # 9 doses without vehicle (cols 3-11)
    y_doses = tb.gen_dose_range(y_top_conc, y_dilution, 5) # 5 doses without vehicle (rows C-G)
    
    # Run CellProfiler
    df_cp, cp_csv = tb.run_cellprofiler(image_dir, counts_file=counts_file, output_dir=output_dir)
    
    # Standardize CellProfiler counts columns and map to our 96-well plate
    df_cp = tb.standardize_counts_dataframe(df_cp)
    df_cp['well'] = df_cp['well'].apply(lambda x: tb.rename_wells(x))

    if plate_map_file is not None:
        return _run_synergy_from_plate_map(
            title_name=title_name,
            x_drug=x_drug,
            x_top_conc=x_top_conc,
            x_dilution=x_dilution,
            y_drug=y_drug,
            y_top_conc=y_top_conc,
            y_dilution=y_dilution,
            df_cp=df_cp,
            cp_csv=cp_csv,
            plate_map_file=plate_map_file,
            show_plot=show_plot,
            output_dir=output_dir,
        )
    
    # Extract rows and columns
    df_cp[['Row','Column']] = df_cp['well'].str.extract(r'^([B-G])(\d+)$')
    if df_cp[['Row', 'Column']].isnull().any().any():
        raise tb.DataValidationError(
            "Could not extract expected well coordinates (B-G, 2-11) from one or more filenames."
        )
    
    # Create viability matrix so each cell in the 2D array represents a well
    # Pivot all replicates into a wide format (rows B-G x cols 2-11)
    # We take the mean of technical replicates automatically via pivot_table
    viability_matrix_raw = df_cp.pivot_table(index='Row', columns='Column', values='nuclei', aggfunc='mean')
    
    # Ensure standard sorting (rows B-G, cols 2-11 as strings)
    row_order = ['B','C','D','E','F','G']
    col_order = [str(i) for i in range(2,12)]
    viability_matrix_raw = viability_matrix_raw.reindex(index=row_order, columns=col_order)
    
    # Normalize entire matrix to the vehicle (B2)
    vehicle_val = viability_matrix_raw.loc['B', '2']
    viability_matrix = viability_matrix_raw / vehicle_val
    logger.debug('Viability matrix calculated and normalized to B2.')
    
    # Map concentrations to cols and rows (for labels)
    all_x_doses = np.insert(x_doses, 0, 0) # Add 0 for vehicle
    all_y_doses = np.insert(y_doses, 0, 0) # Add 0 for vehicle
    
    # Map index/columns to concentrations
    conc_map_x = dict(zip(col_order, all_x_doses))
    conc_map_y = dict(zip(row_order, all_y_doses))
    
    # Create detailed statistics DataFrame for CSV export
    # We use groupby to get mean and std for every well, identifying replicates by 'well' name
    df_stats = df_cp.groupby('well')['nuclei'].agg(['mean', 'std']).reset_index()
    df_stats['normalized_mean'] = df_stats['mean'] / vehicle_val
    
    # Map concentrations to the stats dataframe
    df_stats['Row Drug Concentration'] = df_stats['well'].str[0].map(conc_map_y)
    df_stats['Column Drug Concentration'] = df_stats['well'].str[1:].map(conc_map_x)
    
    # Rename columns for final output
    df_stats = df_stats.rename(columns={
        'well': 'Well', 
        'mean': 'Mean', 
        'std': 'Standard Deviation',
        'normalized_mean': 'Normalized Mean'
    })
    
    # Bliss Independence calculation
    # Row B represents "Drug X Alone" (since Drug Y is 0 in row B)
    drug_x_alone = viability_matrix.loc['B'].values # Shape (10,)
    
    # Column 2 represents "Drug Y Alone" (since Drug X is 0 in col 2)
    drug_y_alone = viability_matrix['2'].values     # Shape (6,)
    
    # Calculate expected independent effect by taking outer product
    # If P(A) is prob survival with drug A, and P(B) is prob survival with drug B
    # Expected survival = P(A) * P(B)
    expected_matrix = pd.DataFrame(
        np.outer(drug_y_alone, drug_x_alone),
        index=viability_matrix.index,
        columns=viability_matrix.columns
    )
    
    # Bliss = Expected Survival - Observed Survival
    # Positive Bliss score = Synergy (more killing than independence expects)
    bliss_matrix = expected_matrix - viability_matrix
    logger.debug('Bliss scores calculated via vectorized outer product.')

    # Setup output directories
    output_base = tb.get_output_base_dir(output_dir)
    synergy_output_dir = output_base / 'synergy_output'
    synergy_output_dir.mkdir(exist_ok=True)
    
    # Save the detailed stats file
    stats_cols = ['Well', 'Mean', 'Standard Deviation', 'Normalized Mean', 'Row Drug Concentration', 'Column Drug Concentration']
    df_stats[stats_cols].to_csv(synergy_output_dir / f'{title_name}_synergy_stats.csv', index=False)
    logger.info(f'{title_name} synergy stats saved to {synergy_output_dir}')
    
    # Save the matrices with experiment labels
    viability_out = viability_matrix.copy()
    viability_out.index = viability_out.index.map(conc_map_y)
    viability_out.columns = viability_out.columns.map(conc_map_x)
    viability_out.index.name = f'{y_drug} (M)'
    viability_out.columns.name = f'{x_drug} (M)'
    
    bliss_out = bliss_matrix.copy()
    bliss_out.index = viability_out.index
    bliss_out.columns = viability_out.columns
    
    viability_out.to_csv(synergy_output_dir / f'{title_name}_synergy_ViabilityMatrix.csv')
    bliss_out.to_csv(synergy_output_dir / f'{title_name}_synergy_BlissMatrix.csv')
    logger.info(f'{title_name} matrices saved.')

    _save_fitted_synergy_surface(
        title_name=title_name,
        x_drug=x_drug,
        y_drug=y_drug,
        x_dilution=x_dilution,
        y_dilution=y_dilution,
        viability_matrix=viability_matrix,
        x_doses=all_x_doses,
        y_doses=all_y_doses,
        synergy_output_dir=synergy_output_dir,
        show_plot=show_plot,
    )
    logger.info(f'{title_name} plot saved.')
    
    # Rename raw counts for easier tracking
    tb.rename_counts(cp_csv, synergy_output_dir / f'{title_name}_synergy_counts.csv')

def _well_sort_key(well):
    row_order = {row: idx for idx, row in enumerate("ABCDEFGH")}
    text = str(well)
    return (row_order.get(text[:1], 99), int(text[1:]) if text[1:].isdigit() else 99)


def _assignment_text(assignments):
    assignments = assignments or {}
    parts = []
    for drug in sorted(assignments, key=lambda value: int(str(value).removeprefix("d"))):
        concentration = assignments[drug].get("concentration_index", "")
        parts.append(f"{drug}:c{concentration}")
    return ";".join(parts)


def _code_drug_count(code):
    if code in {"0", "control"}:
        return 0
    return len(str(code).split("+"))


def _code_concentration_for_drug(code, drug):
    if code in {"0", "control"}:
        return 0
    for part in str(code).split("+"):
        if part.startswith(f"{drug}c"):
            return int(part.split("c", 1)[1])
    return 0


def _dose_lookup(top_conc, dilution, max_index):
    lookup = {0: 0.0}
    if max_index > 0:
        lookup.update({
            idx: dose
            for idx, dose in enumerate(tb.gen_dose_range(top_conc, dilution, max_index), start=1)
        })
    return lookup


def _try_create_mapped_bliss_outputs(
    title_name,
    x_drug,
    x_top_conc,
    x_dilution,
    y_drug,
    y_top_conc,
    y_dilution,
    grouped,
    synergy_output_dir,
    show_plot,
):
    """Create Bliss outputs only when mapped codes form a complete two-drug grid."""
    non_control = grouped[grouped["code"] != "control"].copy()
    if non_control.empty:
        logger.warning("Mapped synergy plot skipped: no non-control codes were found.")
        return

    drugs = sorted(
        {
            part.split("c", 1)[0]
            for code in non_control["code"].astype(str)
            for part in code.split("+")
        },
        key=lambda value: int(value.removeprefix("d")),
    )
    if len(drugs) != 2:
        logger.warning("Mapped synergy plot skipped: Bliss output requires exactly two drugs.")
        return

    x_code_drug, y_code_drug = drugs
    x_indices = sorted({0} | {_code_concentration_for_drug(code, x_code_drug) for code in non_control["code"]})
    y_indices = sorted({0} | {_code_concentration_for_drug(code, y_code_drug) for code in non_control["code"]})
    if not x_indices or not y_indices:
        logger.warning("Mapped synergy plot skipped: no concentration indices were found.")
        return

    required_codes = {
        "+".join(
            part
            for part in [
                f"{x_code_drug}c{x_idx}" if x_idx else "",
                f"{y_code_drug}c{y_idx}" if y_idx else "",
            ]
            if part
        )
        if x_idx or y_idx
        else "control"
        for y_idx in y_indices
        for x_idx in x_indices
    }
    observed_codes = set(grouped["code"].astype(str))
    missing = sorted(required_codes - observed_codes)
    if missing:
        logger.warning(
            "Mapped synergy plot skipped: codes do not form a complete Bliss grid. Missing: %s",
            ", ".join(missing),
        )
        return

    viability_lookup = dict(zip(grouped["code"], grouped["Normalized Mean"]))
    viability_matrix = pd.DataFrame(
        [
            [
                viability_lookup[
                    "+".join(
                        part
                        for part in [
                            f"{x_code_drug}c{x_idx}" if x_idx else "",
                            f"{y_code_drug}c{y_idx}" if y_idx else "",
                        ]
                        if part
                    )
                    if x_idx or y_idx
                    else "control"
                ]
                for x_idx in x_indices
            ]
            for y_idx in y_indices
        ],
        index=y_indices,
        columns=x_indices,
    )

    drug_x_alone = viability_matrix.loc[0].values
    drug_y_alone = viability_matrix[0].values
    expected_matrix = pd.DataFrame(
        np.outer(drug_y_alone, drug_x_alone),
        index=viability_matrix.index,
        columns=viability_matrix.columns,
    )
    bliss_matrix = expected_matrix - viability_matrix

    x_dose_lookup = _dose_lookup(x_top_conc, x_dilution, max(x_indices))
    y_dose_lookup = _dose_lookup(y_top_conc, y_dilution, max(y_indices))

    viability_out = viability_matrix.copy()
    viability_out.index = [y_dose_lookup[idx] for idx in viability_out.index]
    viability_out.columns = [x_dose_lookup[idx] for idx in viability_out.columns]
    viability_out.index.name = f"{y_drug} (M)"
    viability_out.columns.name = f"{x_drug} (M)"

    bliss_out = bliss_matrix.copy()
    bliss_out.index = viability_out.index
    bliss_out.columns = viability_out.columns

    viability_out.to_csv(synergy_output_dir / f"{title_name}_synergy_ViabilityMatrix.csv")
    bliss_out.to_csv(synergy_output_dir / f"{title_name}_synergy_BlissMatrix.csv")

    x_vals = np.array([x_dose_lookup[idx] for idx in x_indices], dtype=float)
    y_vals = np.array([y_dose_lookup[idx] for idx in y_indices], dtype=float)
    try:
        _save_fitted_synergy_surface(
            title_name=title_name,
            x_drug=x_drug,
            y_drug=y_drug,
            x_dilution=x_dilution,
            y_dilution=y_dilution,
            viability_matrix=viability_matrix,
            x_doses=x_vals,
            y_doses=y_vals,
            synergy_output_dir=synergy_output_dir,
            show_plot=show_plot,
        )
    except tb.DataValidationError as exc:
        logger.warning("Mapped fitted synergy surface skipped: %s", exc)


def _run_synergy_from_plate_map(
    title_name,
    x_drug,
    x_top_conc,
    x_dilution,
    y_drug,
    y_top_conc,
    y_dilution,
    df_cp,
    cp_csv,
    plate_map_file,
    show_plot=True,
    output_dir=None,
):
    """Run synergy analysis using compact synergy-map codes."""
    from . import synergy_interactive_map

    plate_map = synergy_interactive_map.load_synergy_map(plate_map_file)
    df = df_cp.merge(plate_map, on="well", how="left", validate="many_to_one")
    if df["code"].isna().any():
        missing_wells = df.loc[df["code"].isna(), "well"].tolist()
        raise ValueError(f"Counts contain wells not present in synergy map: {missing_wells}")

    df = df[df["code"].astype(str).ne("0")].copy()
    if df.empty:
        raise ValueError("Synergy map does not assign any wells for analysis.")
    if not (df["code"] == "control").any():
        raise ValueError("Synergy map must include at least one control well.")

    vehicle_val = df.loc[df["code"] == "control", "nuclei"].mean()
    if not np.isfinite(vehicle_val) or vehicle_val == 0:
        raise ValueError("Synergy control mean must be finite and non-zero.")
    df["normalized_nuclei"] = df["nuclei"] / vehicle_val
    df["assignment_text"] = df["assignments"].apply(_assignment_text)
    df["drug_count"] = df["code"].apply(_code_drug_count)

    output_base = tb.get_output_base_dir(output_dir)
    synergy_output_dir = output_base / "synergy_output"
    synergy_output_dir.mkdir(exist_ok=True)

    grouped = (
        df.groupby("code", sort=False)
        .agg(
            **{
                "Well(s)": ("well", lambda wells: ",".join(sorted(set(wells), key=_well_sort_key))),
                "Mean": ("nuclei", "mean"),
                "Standard Deviation": ("nuclei", "std"),
                "Normalized Mean": ("normalized_nuclei", "mean"),
                "N": ("well", "count"),
            }
        )
        .reset_index()
    )
    max_column_index = int(grouped["code"].apply(lambda code: _code_concentration_for_drug(code, "d1")).max())
    max_row_index = int(grouped["code"].apply(lambda code: _code_concentration_for_drug(code, "d2")).max())
    column_dose_lookup = _dose_lookup(x_top_conc, x_dilution, max_column_index)
    row_dose_lookup = _dose_lookup(y_top_conc, y_dilution, max_row_index)
    grouped["Column Drug Concentration"] = grouped["code"].apply(
        lambda code: column_dose_lookup[_code_concentration_for_drug(code, "d1")]
    )
    grouped["Row Drug Concentration"] = grouped["code"].apply(
        lambda code: row_dose_lookup[_code_concentration_for_drug(code, "d2")]
    )
    grouped = grouped[
        [
            "Well(s)",
            "code",
            "Mean",
            "Standard Deviation",
            "Normalized Mean",
            "Row Drug Concentration",
            "Column Drug Concentration",
            "N",
        ]
    ]
    grouped.to_csv(synergy_output_dir / f"{title_name}_synergy_stats.csv", index=False)
    logger.info(f"{title_name} mapped synergy stats saved to {synergy_output_dir}")

    bywell = df[
        [
            "well",
            "row",
            "column",
            "code",
            "is_control",
            "assignment_text",
            "drug_count",
            "nuclei",
            "normalized_nuclei",
        ]
    ].sort_values(["row", "column"])
    bywell.to_csv(synergy_output_dir / f"{title_name}_synergy_bywell.csv", index=False)

    _try_create_mapped_bliss_outputs(
        title_name=title_name,
        x_drug=x_drug,
        x_top_conc=x_top_conc,
        x_dilution=x_dilution,
        y_drug=y_drug,
        y_top_conc=y_top_conc,
        y_dilution=y_dilution,
        grouped=grouped,
        synergy_output_dir=synergy_output_dir,
        show_plot=show_plot,
    )

    tb.rename_counts(cp_csv, synergy_output_dir / f"{title_name}_synergy_counts.csv")
