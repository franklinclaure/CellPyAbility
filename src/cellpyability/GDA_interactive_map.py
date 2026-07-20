"""
Interactive Matplotlib plate-map editor for CellPyAbility.

The module provides long-form 96-well CSV helpers and compact 8x12 layout
parsing for reusable plate layouts.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import pandas as pd

from cellpyability.toolbox import (
    COLUMNS,
    ROWS,
    build_plate_dataframe,
    plate_wells,
    prepare_interactive_matplotlib_backend,
    split_well,
)

PLATE_MAP_COLUMNS = [
    "well",
    "row",
    "column",
    "genotype",
    "treatment_type",
    "drug",
    "gradient_id",
    "gradient_axis",
    "concentration_index",
    "replicate_group",
    "replicate_index",
    "is_vehicle",
    "notes",
]


def blank_plate_map() -> pd.DataFrame:
    """Create an empty plate map DataFrame in the canonical CSV schema."""
    return build_plate_dataframe(
        PLATE_MAP_COLUMNS,
        lambda well, row, column: {
            "well": well,
            "row": row,
            "column": int(column),
            "genotype": "",
            "treatment_type": "",
            "drug": "",
            "gradient_id": "",
            "gradient_axis": "",
            "concentration_index": "",
            "replicate_group": "",
            "replicate_index": "",
            "is_vehicle": False,
            "notes": "",
        },
    )


def default_gda_plate_map(
    genotype_1: str = "Genotype 1",
    genotype_2: str = "Genotype 2",
    drug: str = "Drug",
) -> pd.DataFrame:
    """Create a map matching CellPyAbility's historical GDA assumptions."""
    df = blank_plate_map()
    for idx, row in df.iterrows():
        genotype = genotype_1 if row["row"] in ["B", "C", "D"] else genotype_2
        column = int(row["column"])
        df.at[idx, "genotype"] = genotype
        df.at[idx, "drug"] = "Vehicle" if column == 2 else drug
        df.at[idx, "treatment_type"] = "vehicle" if column == 2 else "drug_gradient"
        df.at[idx, "gradient_id"] = "vehicle" if column == 2 else f"{drug}_horizontal"
        df.at[idx, "gradient_axis"] = "" if column == 2 else "horizontal"
        df.at[idx, "concentration_index"] = 0 if column == 2 else column - 2
        df.at[idx, "is_vehicle"] = column == 2
        df.at[idx, "replicate_group"] = f"{genotype}_vehicle" if column == 2 else f"{genotype}_{drug}_dose_{column - 2}"
    return add_replicate_indices(df)


def add_replicate_indices(df: pd.DataFrame) -> pd.DataFrame:
    """Assign 1-based replicate indices inside each replicate group."""
    df = df.copy()
    df["replicate_index"] = ""
    grouped = df[df["replicate_group"].astype(str).str.len() > 0].groupby("replicate_group", sort=False)
    for _, group in grouped:
        for replicate_idx, row_idx in enumerate(group.index, start=1):
            df.at[row_idx, "replicate_index"] = str(replicate_idx)
    return df


def save_plate_map(df: pd.DataFrame, output_csv: str | Path) -> Path:
    """Validate and save a plate map CSV."""
    output_path = Path(output_csv).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    validate_plate_map(df)
    df.to_csv(output_path, index=False, quoting=csv.QUOTE_MINIMAL)
    return output_path


def load_plate_map(input_csv: str | Path) -> pd.DataFrame:
    """Load and validate a long-form or compact plate map CSV."""
    df = pd.read_csv(input_csv)
    if set(PLATE_MAP_COLUMNS).issubset(df.columns):
        validate_plate_map(df)
        return df[PLATE_MAP_COLUMNS].copy()

    compact_df = pd.read_csv(input_csv, header=None, dtype=str, keep_default_na=False)
    return compact_plate_map_to_long(compact_df)


def compact_plate_map_to_long(compact_df: pd.DataFrame) -> pd.DataFrame:
    """Convert an 8x12 compact code grid into the canonical plate-map schema."""
    if compact_df.shape != (8, 12):
        raise ValueError(
            f"Compact plate map must be exactly 8 rows x 12 columns; found {compact_df.shape[0]} x {compact_df.shape[1]}."
        )

    records = []
    vehicle_pattern = re.compile(r"^g([12])v$")
    gradient_pattern = re.compile(r"^g([12])d([1-5])c([1-9])$")

    for row_idx, plate_row in enumerate(ROWS):
        for col_idx, plate_column in enumerate(COLUMNS):
            raw_code = str(compact_df.iat[row_idx, col_idx]).strip().lower()
            well = f"{plate_row}{plate_column}"
            record = {
                "well": well,
                "row": plate_row,
                "column": int(plate_column),
                "genotype": "",
                "treatment_type": "",
                "drug": "",
                "gradient_id": "",
                "gradient_axis": "",
                "concentration_index": "",
                "replicate_group": "",
                "replicate_index": "",
                "is_vehicle": False,
                "notes": raw_code,
            }

            if raw_code in {"", "0"}:
                records.append(record)
                continue

            vehicle_match = vehicle_pattern.match(raw_code)
            if vehicle_match:
                genotype_id = vehicle_match.group(1)
                genotype = f"g{genotype_id}"
                record.update(
                    {
                        "genotype": genotype,
                        "treatment_type": "vehicle",
                        "drug": "Vehicle",
                        "gradient_id": "vehicle",
                        "concentration_index": 0,
                        "replicate_group": f"{genotype}_vehicle",
                        "is_vehicle": True,
                    }
                )
                records.append(record)
                continue

            gradient_match = gradient_pattern.match(raw_code)
            if gradient_match:
                genotype_id, drug_id, concentration_id = gradient_match.groups()
                genotype = f"g{genotype_id}"
                drug = f"d{drug_id}"
                concentration_index = int(concentration_id)
                record.update(
                    {
                        "genotype": genotype,
                        "treatment_type": "drug_gradient",
                        "drug": drug,
                        "gradient_id": f"{genotype}_{drug}",
                        "gradient_axis": "compact",
                        "concentration_index": concentration_index,
                        "replicate_group": f"{genotype}_{drug}_c{concentration_index}",
                        "is_vehicle": False,
                    }
                )
                records.append(record)
                continue

            raise ValueError(
                f"Invalid compact plate-map code '{raw_code}' at {well}. "
                "Use 0, blank, g1v/g2v, or g1d1c1 through g2d5c9."
            )

    return add_replicate_indices(pd.DataFrame(records, columns=PLATE_MAP_COLUMNS))


def validate_plate_map(df: pd.DataFrame) -> None:
    """Raise ValueError if a DataFrame is not a valid CellPyAbility plate map."""
    missing = [column for column in PLATE_MAP_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Plate map is missing required columns: {', '.join(missing)}")

    wells = df["well"].astype(str).tolist()
    expected_wells = plate_wells()
    if sorted(wells) != sorted(expected_wells):
        raise ValueError("Plate map must contain exactly the 96 wells A-H and 1-12.")

    if len(wells) != len(set(wells)):
        raise ValueError("Plate map contains duplicate wells.")

    for _, row in df.iterrows():
        expected_row, expected_column = split_well(str(row["well"]))
        if row["row"] != expected_row or str(row["column"]) != expected_column:
            raise ValueError(f"Well metadata does not match well {row['well']}.")


def launch_plate_map_matplotlib(output_csv: str | Path | None = None) -> None:
    """Launch the default Matplotlib plate-map editor."""
    prepare_interactive_matplotlib_backend()

    from matplotlib import patheffects as path_effects
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from matplotlib.widgets import Button, CheckButtons, RadioButtons, TextBox

    colors = {
        "background": "#f5f7fb",
        "panel": "#ffffff",
        "border": "#c9d3df",
        "text": "#1f2933",
        "muted": "#5f6b7a",
        "unassigned": "#f8fafc",
        "genotype_1": "#6495ed",
        "genotype_2": "#ff2400",
        "vehicle_g1": "#d8e6ff",
        "vehicle_g2": "#ffd6cc",
        "vehicle_unknown": "#fef3c7",
        "drug_g1": "#b7caf7",
        "drug_g2": "#ffb3a3",
        "drug_unknown": "#f5d0fe",
        "gradient_g1_light": "#d8e6ff",
        "gradient_g1_dark": "#4f8fea",
        "gradient_g2_light": "#ffd6cc",
        "gradient_g2_dark": "#ff6048",
        "gradient_unknown_light": "#e9d5ff",
        "gradient_unknown_dark": "#a855f7",
        "active": "#ffd166",
        "active_border": "#2f80ed",
        "pattern": (0.19, 0.25, 0.33, 0.26),
        "pattern_icon": (0.19, 0.25, 0.33, 0.55),
    }
    rows = ROWS
    columns = COLUMNS
    output_base = Path(output_csv).expanduser() if output_csv else Path.cwd() / "plate_map.csv"
    output_dir = output_base.parent if output_base.suffix.lower() == ".csv" else output_base
    initial_layout_name = output_base.stem if output_base.suffix.lower() == ".csv" else "plate_map"

    data = {"df": blank_plate_map()}
    selected_wells: set[str] = set()
    state = {
        "dragging": False,
        "drag_start": None,
        "drag_end": None,
        "marquee": None,
        "confirm_reset": False,
        "drug_count": 3,
        "selected_drug": "Drug1",
        "gradient_axis": "horizontal",
        "reverse": False,
    }
    controls: dict[str, object] = {}

    # GUI layout/setup god
    fig = plt.figure(figsize=(14, 8), facecolor=colors["background"])
    fig.canvas.manager.set_window_title("CellPyAbility Plate Map")
    plate_ax = fig.add_axes([0.34, 0.17, 0.62, 0.72], facecolor=colors["panel"])
    detail_ax = fig.add_axes([0.34, 0.055, 0.62, 0.075], facecolor=colors["panel"])
    detail_ax.set_xticks([])
    detail_ax.set_yticks([])
    for spine in detail_ax.spines.values():
        spine.set_edgecolor(colors["border"])
    fig.text(0.34, 0.935, "96-Well Plate", fontsize=18, fontweight="bold", color=colors["text"])
    status_text = fig.text(0.105, 0.035, "Ready. Drag a rectangle over wells to highlight.", fontsize=10, color=colors["muted"])
    detail_text = detail_ax.text(
        0.02,
        0.5,
        "Hover over a well for details.",
        ha="left",
        va="center",
        color=colors["text"],
        fontsize=11,
        transform=detail_ax.transAxes,
    )

    def set_status(message: str) -> None:
        """Update the GUI status message."""
        status_text.set_text(message)
        fig.canvas.draw_idle()

    def set_detail(message: str) -> None:
        """Update the GUI hover/detail message."""
        detail_text.set_text(message)
        fig.canvas.draw_idle()

    def make_textbox(y: float, label: str, initial: str) -> TextBox:
        """Create a left-panel text input widget."""
        ax = fig.add_axes([0.105, y, 0.19, 0.035], facecolor=colors["panel"])
        ax.format_coord = lambda x, y: ""
        return TextBox(ax, label, initial=initial, color=colors["panel"], hovercolor="#eef3f8")

    controls["layout_name"] = make_textbox(0.885, "Layout name: ", initial_layout_name)
    set_g1_ax = fig.add_axes([0.105, 0.82, 0.19, 0.04])
    set_g2_ax = fig.add_axes([0.105, 0.765, 0.19, 0.04])
    vehicle_ax = fig.add_axes([0.105, 0.71, 0.19, 0.04])
    controls["drug_count"] = make_textbox(0.66, "Number of drugs: ", "3")
    fig.text(0.105, 0.615, "Drug Gradient Direction:", fontsize=11, fontweight="bold", color=colors["text"])
    direction_ax = fig.add_axes([0.105, 0.555, 0.12, 0.048], facecolor=colors["panel"])
    direction_ax.format_coord = lambda x, y: ""
    direction_radio = RadioButtons(direction_ax, ("Horizontal", "Vertical"), active=0, activecolor=colors["active_border"])
    controls["direction_radio"] = direction_radio
    reverse_ax = fig.add_axes([0.23, 0.561, 0.065, 0.035], facecolor=colors["panel"])
    reverse_ax.format_coord = lambda x, y: ""
    reverse_check = CheckButtons(reverse_ax, ("Reverse",), (False,))
    controls["reverse_check"] = reverse_check
    gradient_ax = fig.add_axes([0.105, 0.245, 0.19, 0.04])
    clear_ax = fig.add_axes([0.105, 0.19, 0.19, 0.04])
    reset_ax = fig.add_axes([0.105, 0.125, 0.19, 0.04])
    save_ax = fig.add_axes([0.105, 0.07, 0.19, 0.04])

    def textbox_value(key: str) -> str:
        """Return stripped text from a stored TextBox control."""
        return controls[key].text.strip()

    def row_df_index(well: str) -> int:
        """Return the DataFrame row index for one well."""
        df = data["df"]
        return int(df.index[df["well"] == well][0])

    def get_row(well: str) -> pd.Series:
        """Return the plate-map DataFrame row for one well."""
        return data["df"][data["df"]["well"] == well].iloc[0]

    def enabled_well(well: str) -> bool:
        """Return whether a well belongs to the editable plate grid."""
        row, column = split_well(well)
        return row in rows and column in columns

    def drug_labels() -> list[str]:
        """Build the active Drug1..DrugN labels from the drug-count control."""
        try:
            count = int(float(textbox_value("drug_count") or state["drug_count"]))
        except ValueError:
            count = int(state["drug_count"])
        count = max(1, min(12, count))
        state["drug_count"] = count
        labels = [f"Drug{i}" for i in range(1, count + 1)]
        if state["selected_drug"] not in labels:
            state["selected_drug"] = labels[0]
        return labels

    def drug_pattern(value: object) -> str:
        """Return the hatch pattern used to visually distinguish drugs."""
        text = str(value or "").strip()
        return {
            "Drug1": "..",
            "Drug2": "///",
            "Drug3": "|||",
            "Drug4": "---",
            "Drug5": "",
        }.get(text, "")

    def select_drug(label: str) -> None:
        """Store the selected drug and refresh the status text."""
        state["selected_drug"] = label
        direction = str(state["gradient_axis"]).capitalize()
        reverse = "reverse" if state["reverse"] else "forward"
        set_status(f"{label} selected: {direction}, {reverse}.")

    def refresh_drug_toggles(text: str | None = None) -> None:
        """Rebuild the drug radio buttons after the drug count changes."""
        for axis in controls.get("drug_axes", []):
            axis.remove()
        labels = drug_labels()
        display_labels = [label.replace("Drug", "Drug ") for label in labels]
        height = min(0.25, 0.026 * len(labels) + 0.018)
        drug_ax = fig.add_axes([0.105, 0.305, 0.145, height], facecolor=colors["panel"])
        drug_ax.format_coord = lambda x, y: ""
        drug_radio = RadioButtons(drug_ax, display_labels, active=labels.index(state["selected_drug"]), activecolor=colors["active_border"])
        drug_axes = [drug_ax]
        row_step = height / max(1, len(labels))
        icon_size = min(0.024, row_step * 0.75)
        for idx, label in enumerate(labels):
            icon_y = 0.305 + height - row_step * (idx + 0.72)
            icon_ax = fig.add_axes([0.27, icon_y, icon_size, icon_size], facecolor=colors["panel"])
            icon_ax.format_coord = lambda x, y: ""
            icon_ax.set_xticks([])
            icon_ax.set_yticks([])
            for spine in icon_ax.spines.values():
                spine.set_visible(False)
            icon_ax.add_patch(
                Rectangle(
                    (0.08, 0.08),
                    0.84,
                    0.84,
                    facecolor="#ffffff",
                    edgecolor=colors["pattern_icon"],
                    linewidth=0.8,
                    hatch=drug_pattern(label),
                )
            )
            icon_ax.set_xlim(0, 1)
            icon_ax.set_ylim(0, 1)
            drug_axes.append(icon_ax)

        def choose_drug(choice: str) -> None:
            select_drug(choice.replace(" ", ""))

        drug_radio.on_clicked(choose_drug)
        controls["drug_axes"] = drug_axes
        controls["drug_radio"] = drug_radio
        set_status(f"{len(labels)} drug toggle(s) available.")
        fig.canvas.draw_idle()

    controls["drug_count"].on_submit(refresh_drug_toggles)
    if hasattr(controls["drug_count"], "on_text_change"):
        controls["drug_count"].on_text_change(refresh_drug_toggles)

    def set_direction(choice: str) -> None:
        """Update whether new gradients are assigned horizontally or vertically."""
        state["gradient_axis"] = "vertical" if choice.startswith("Vertical") else "horizontal"
        select_drug(str(state["selected_drug"]))

    def set_reverse(_choice: str) -> None:
        """Toggle whether concentration indices increase in reverse order."""
        state["reverse"] = not state["reverse"]
        select_drug(str(state["selected_drug"]))

    direction_radio.on_clicked(set_direction)
    reverse_check.on_clicked(set_reverse)

    def blend_hex(start: str, end: str, amount: float) -> str:
        """Blend two hex colors for gradient-dose shading."""
        amount = max(0.0, min(1.0, amount))
        start_rgb = tuple(int(start[i : i + 2], 16) for i in (1, 3, 5))
        end_rgb = tuple(int(end[i : i + 2], 16) for i in (1, 3, 5))
        rgb = tuple(round(a + (b - a) * amount) for a, b in zip(start_rgb, end_rgb))
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def genotype_code(value: object) -> str:
        """Convert a genotype label into the compact CSV code prefix."""
        if value == "Genotype 1":
            return "g1"
        if value == "Genotype 2":
            return "g2"
        return "UN"

    def drug_code(value: object) -> str:
        """Convert a drug label into the compact CSV drug code."""
        text = str(value or "").strip()
        if not text or text == "Vehicle":
            return "UN"
        if text.lower().startswith("drug"):
            suffix = text[4:].strip()
            if suffix.isdigit():
                return f"d{suffix}"
        digits = "".join(character for character in text if character.isdigit())
        return f"d{digits}" if digits else "UN"

    def concentration_code(value: object) -> str:
        """Convert a concentration index into the compact CSV concentration code."""
        text = str(value or "").strip()
        return f"c{text}" if text.isdigit() else "UN"

    def well_codes(well: str) -> dict[str, str]:
        """Return compact-code components for one well."""
        row = get_row(well)
        g_code = genotype_code(row["genotype"])
        d_code = drug_code(row["drug"])
        c_code = concentration_code(row["concentration_index"]) if row["treatment_type"] == "drug_gradient" else "UN"
        v_code = "v" if bool(row["is_vehicle"]) or row["treatment_type"] == "vehicle" else "UN"
        if g_code == "UN" and d_code == "UN" and c_code == "UN" and v_code == "UN":
            compact = "0"
        elif g_code != "UN" and v_code == "v":
            compact = f"{g_code}v"
        elif g_code != "UN" and d_code != "UN" and c_code != "UN":
            compact = f"{g_code}{d_code}{c_code}"
        else:
            compact = "UN"
        return {"g": g_code, "d": d_code, "c": c_code, "v": v_code, "compact": compact}

    def compact_csv_value(well: str) -> str:
        """Return the compact CSV cell value for one well."""
        codes = well_codes(well)
        return codes["compact"] if codes["compact"] != "UN" else "0"

    def hover_detail(well: str | None) -> str:
        """Build the hover text shown in the detail panel."""
        if well is None:
            return "Hover over a well for details."
        codes = well_codes(well)
        return f"{well} | g: {codes['g']} | d: {codes['d']} | c: {codes['c']} | v: {codes['v']}"

    def well_text(well: str) -> str:
        """Build the text drawn inside one well cell."""
        codes = well_codes(well)
        if codes["compact"] not in {"0", "UN"}:
            return f"{well}\n{codes['compact']}"
        return well

    def well_pattern(well: str) -> str:
        """Return the hatch pattern drawn over one well cell."""
        row = get_row(well)
        if row["drug"] == "Vehicle":
            return ""
        return drug_pattern(row["drug"])

    def gradient_amount(row: pd.Series) -> float:
        """Calculate relative color intensity for a drug-gradient well."""
        try:
            concentration = int(row["concentration_index"])
        except (TypeError, ValueError):
            return 0.0
        df = data["df"]
        gradient_rows = df[
            (df["treatment_type"] == "drug_gradient")
            & (df["drug"] == row["drug"])
            & (df["gradient_axis"] == row["gradient_axis"])
            & (df["genotype"] == row["genotype"])
        ]
        concentrations = pd.to_numeric(gradient_rows["concentration_index"], errors="coerce").dropna()
        max_concentration = int(concentrations.max()) if not concentrations.empty else concentration
        if max_concentration <= 1:
            return 0.0
        return ((concentration - 1) / (max_concentration - 1)) * 0.82

    def well_color(well: str) -> str:
        """Choose the fill color for one well cell."""
        if well in selected_wells:
            return colors["active"]
        row = get_row(well)
        genotype = row["genotype"]
        if row["treatment_type"] == "vehicle":
            if genotype == "Genotype 1":
                return colors["vehicle_g1"]
            if genotype == "Genotype 2":
                return colors["vehicle_g2"]
            return colors["vehicle_unknown"]
        if row["treatment_type"] == "drug_gradient":
            amount = gradient_amount(row)
            if genotype == "Genotype 1":
                return blend_hex(colors["gradient_g1_light"], colors["gradient_g1_dark"], amount)
            if genotype == "Genotype 2":
                return blend_hex(colors["gradient_g2_light"], colors["gradient_g2_dark"], amount)
            return blend_hex(colors["gradient_unknown_light"], colors["gradient_unknown_dark"], amount)
        if row["drug"]:
            if genotype == "Genotype 1":
                return colors["drug_g1"]
            if genotype == "Genotype 2":
                return colors["drug_g2"]
            return colors["drug_unknown"]
        if genotype == "Genotype 1":
            return colors["genotype_1"]
        if genotype == "Genotype 2":
            return colors["genotype_2"]
        return colors["unassigned"]

    def row_index(row: str) -> int:
        """Return the display index for a plate row letter."""
        return rows.index(row)

    def ordered_wells(wells: list[str], axis: str, reverse: bool = False) -> list[str]:
        """Order selected wells for concentration assignment."""
        ordered = sorted(wells, key=lambda well: (row_index(well[0]), int(well[1:])))
        if axis == "horizontal":
            ordered = sorted(ordered, key=lambda well: (int(well[1:]), row_index(well[0])))
        if reverse:
            ordered = list(reversed(ordered))
        return ordered

    def concentration_indices(wells: list[str], axis: str, reverse: bool = False) -> dict[str, int]:
        """Assign concentration indices across selected wells."""
        if axis == "horizontal":
            ordered_columns = sorted({int(well[1:]) for well in wells}, reverse=reverse)
            lookup = {str(column): idx for idx, column in enumerate(ordered_columns, start=1)}
            return {well: lookup[well[1:]] for well in wells}
        ordered_rows = sorted({well[0] for well in wells}, key=row_index, reverse=reverse)
        lookup = {row: idx for idx, row in enumerate(ordered_rows, start=1)}
        return {well: lookup[well[0]] for well in wells}

    def well_from_event(event) -> str | None:
        """Convert a Matplotlib mouse event into a well ID."""
        if event.inaxes is not plate_ax or event.xdata is None or event.ydata is None:
            return None
        col_idx = int(event.xdata)
        row_idx = int(event.ydata)
        if 0 <= col_idx < len(columns) and 0 <= row_idx < len(rows):
            return f"{rows[row_idx]}{columns[col_idx]}"
        return None

    def wells_in_rectangle(start: tuple[float, float], end: tuple[float, float]) -> set[str]:
        """Return wells touched by the drag-selection rectangle."""
        x1, y1 = start
        x2, y2 = end
        xmin, xmax = sorted([x1, x2])
        ymin, ymax = sorted([y1, y2])
        hits = set()
        for row_idx, row in enumerate(rows):
            for col_idx, column in enumerate(columns):
                cell_x1, cell_x2 = col_idx, col_idx + 0.9
                cell_y1, cell_y2 = row_idx, row_idx + 0.9
                if xmax >= cell_x1 and xmin <= cell_x2 and ymax >= cell_y1 and ymin <= cell_y2:
                    hits.add(f"{row}{column}")
        return hits

    def redraw_plate() -> None:
        """Redraw the plate grid from the current DataFrame and selection."""
        plate_ax.clear()
        plate_ax.format_coord = lambda x, y: ""
        plate_ax.set_xlim(-0.7, len(columns))
        plate_ax.set_ylim(len(rows), -0.7)
        plate_ax.set_aspect("auto")
        plate_ax.axis("off")
        bbox = plate_ax.get_window_extent()
        fontsize = max(5, min(10, bbox.width / 132))
        label_fontsize = max(7, min(12, bbox.width / 120))
        for col_idx, column in enumerate(columns):
            plate_ax.text(col_idx + 0.45, -0.32, column, ha="center", va="center", color=colors["muted"], fontweight="bold", fontsize=label_fontsize)
        for row_idx, row in enumerate(rows):
            plate_ax.text(-0.35, row_idx + 0.45, row, ha="center", va="center", color=colors["muted"], fontweight="bold", fontsize=label_fontsize)
            for col_idx, column in enumerate(columns):
                well = f"{row}{column}"
                selected = well in selected_wells
                plate_ax.add_patch(
                    Rectangle(
                        (col_idx, row_idx),
                        0.9,
                        0.9,
                        facecolor=well_color(well),
                        edgecolor=colors["active_border"] if selected else colors["border"],
                        linewidth=3 if selected else 1,
                    )
                )
                pattern = well_pattern(well)
                if pattern:
                    plate_ax.add_patch(
                        Rectangle(
                            (col_idx, row_idx),
                            0.9,
                            0.9,
                            facecolor="none",
                            edgecolor=colors["pattern"],
                            linewidth=0,
                            hatch=pattern,
                            zorder=2,
                        )
                    )
                plate_ax.text(
                    col_idx + 0.45,
                    row_idx + 0.45,
                    well_text(well),
                    ha="center",
                    va="center",
                    color=colors["text"],
                    fontsize=fontsize,
                    linespacing=1.05,
                    zorder=5,
                    path_effects=[path_effects.withStroke(linewidth=2.0, foreground=(1, 1, 1, 0.72))],
                )
        fig.canvas.draw_idle()

    def draw_marquee(start: tuple[float, float], end: tuple[float, float]) -> None:
        """Draw the translucent drag-selection rectangle."""
        if state["marquee"] is not None:
            state["marquee"].remove()
        x1, y1 = start
        x2, y2 = end
        state["marquee"] = Rectangle(
            (min(x1, x2), min(y1, y2)),
            abs(x2 - x1),
            abs(y2 - y1),
            facecolor=colors["active_border"],
            edgecolor=colors["active_border"],
            alpha=0.18,
            linewidth=1.5,
            zorder=20,
        )
        plate_ax.add_patch(state["marquee"])
        fig.canvas.draw_idle()

    def set_wells(wells: list[str], **values: object) -> None:
        """Set one or more DataFrame columns for selected wells."""
        df = data["df"]
        for well in wells:
            idx = row_df_index(well)
            for key, value in values.items():
                df.at[idx, key] = value

    def set_vehicle(wells: list[str]) -> None:
        """Mark selected wells as vehicle controls in the DataFrame."""
        df = data["df"]
        for well in wells:
            idx = row_df_index(well)
            genotype = df.at[idx, "genotype"] or ""
            df.at[idx, "treatment_type"] = "vehicle"
            df.at[idx, "drug"] = "Vehicle"
            df.at[idx, "gradient_id"] = "vehicle"
            df.at[idx, "gradient_axis"] = ""
            df.at[idx, "concentration_index"] = 0
            df.at[idx, "replicate_group"] = f"{genotype}_vehicle" if genotype else "vehicle"
            df.at[idx, "is_vehicle"] = True

    def set_gradient(wells: list[str]) -> None:
        """Mark selected wells as a drug gradient in the DataFrame."""
        df = data["df"]
        drug = str(state["selected_drug"])
        axis = str(state["gradient_axis"])
        reverse = bool(state["reverse"])
        ordered = ordered_wells(wells, axis, reverse=reverse)
        lookup = concentration_indices(ordered, axis, reverse=reverse)
        for well in ordered:
            idx = row_df_index(well)
            genotype = df.at[idx, "genotype"] or ""
            concentration_index = lookup[well]
            row, column = split_well(well)
            replicate_key = column if axis == "horizontal" else row
            df.at[idx, "treatment_type"] = "drug_gradient"
            df.at[idx, "drug"] = drug
            df.at[idx, "gradient_id"] = f"{drug}_{axis}"
            df.at[idx, "gradient_axis"] = axis
            df.at[idx, "concentration_index"] = concentration_index
            df.at[idx, "replicate_group"] = f"{genotype}_{drug}_dose_{concentration_index}_{replicate_key}".strip("_")
            df.at[idx, "is_vehicle"] = False

    def clear_wells(wells: list[str]) -> None:
        """Clear assignment columns for selected wells."""
        df = data["df"]
        for well in wells:
            idx = row_df_index(well)
            for column in PLATE_MAP_COLUMNS:
                if column not in {"well", "row", "column"}:
                    df.at[idx, column] = False if column == "is_vehicle" else ""

    def apply_selection(mode: str):
        """Apply the chosen assignment mode to highlighted wells."""
        if not selected_wells:
            set_status("Highlight one or more wells first.")
            return
        wells = ordered_wells(list(selected_wells), str(state["gradient_axis"]), reverse=bool(state["reverse"])) if mode == "drug_gradient" else ordered_wells(list(selected_wells), "horizontal")
        if mode == "genotype_1":
            set_wells(wells, genotype="Genotype 1")
        elif mode == "genotype_2":
            set_wells(wells, genotype="Genotype 2")
        elif mode == "vehicle":
            set_vehicle(wells)
        elif mode == "drug_gradient":
            set_gradient(wells)
        elif mode == "clear":
            clear_wells(wells)
        count = len(selected_wells)
        selected_wells.clear()
        data["df"] = add_replicate_indices(data["df"])
        set_status(f"Applied {mode.replace('_', ' ')} to {count} well(s).")
        redraw_plate()

    def reset_all(event=None) -> None:
        """Reset every well after a confirmation click."""
        if not state["confirm_reset"]:
            state["confirm_reset"] = True
            set_status("Click Reset All again to confirm clearing every well.")
            return
        data["df"] = blank_plate_map()
        selected_wells.clear()
        state["confirm_reset"] = False
        set_detail("Hover over a well for details.")
        set_status("All wells reset.")
        redraw_plate()

    def sanitized_layout_name() -> str:
        """Return a filesystem-safe layout name from the text input."""
        name = textbox_value("layout_name") or "plate_map"
        cleaned = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in name).strip("_")
        return cleaned or "plate_map"

    def save_layout(event=None) -> None:
        """Write the current map as a compact 8x12 CSV."""
        output_dir.mkdir(parents=True, exist_ok=True)
        path = (output_dir / f"{sanitized_layout_name()}.csv").expanduser().resolve()
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            for row in rows:
                writer.writerow([compact_csv_value(f"{row}{column}") for column in columns])
        set_status(f"Saved layout to {path}")

    def on_press(event) -> None:
        """Start click or drag selection on the plate grid."""
        well = well_from_event(event)
        if well is None:
            return
        state["confirm_reset"] = False
        state["dragging"] = True
        state["drag_start"] = (event.xdata, event.ydata)
        state["drag_end"] = (event.xdata, event.ydata)

    def on_motion(event) -> None:
        """Update hover text or drag marquee while the mouse moves."""
        if event.inaxes is not plate_ax or event.xdata is None or event.ydata is None:
            if not state["dragging"]:
                set_detail(hover_detail(None))
            return
        if not state["dragging"]:
            set_detail(hover_detail(well_from_event(event)))
            return
        state["drag_end"] = (event.xdata, event.ydata)
        draw_marquee(state["drag_start"], state["drag_end"])

    def on_release(event) -> None:
        """Finish click or drag selection and update highlighted wells."""
        if not state["dragging"]:
            return
        state["dragging"] = False
        start = state["drag_start"]
        end = (event.xdata, event.ydata) if event.inaxes is plate_ax and event.xdata is not None and event.ydata is not None else state["drag_end"]
        if state["marquee"] is not None:
            state["marquee"].remove()
            state["marquee"] = None
        if start is None or end is None:
            redraw_plate()
            return
        if abs(start[0] - end[0]) < 0.05 and abs(start[1] - end[1]) < 0.05:
            well = well_from_event(event)
            if well:
                if well in selected_wells:
                    selected_wells.remove(well)
                else:
                    selected_wells.add(well)
        else:
            selected_wells.update(wells_in_rectangle(start, end))
        set_status(f"{len(selected_wells)} well(s) highlighted.")
        redraw_plate()

    controls["buttons"] = {
        "set_genotype_1": Button(set_g1_ax, "Set Genotype 1"),
        "set_genotype_2": Button(set_g2_ax, "Set Genotype 2"),
        "set_vehicle": Button(vehicle_ax, "Set Vehicle Controls"),
        "set_gradient": Button(gradient_ax, "Set Drug Gradient"),
        "clear": Button(clear_ax, "Clear Highlighted"),
        "reset": Button(reset_ax, "Reset All"),
        "save": Button(save_ax, "Save Layout"),
    }
    controls["buttons"]["set_genotype_1"].on_clicked(lambda event: apply_selection("genotype_1"))
    controls["buttons"]["set_genotype_2"].on_clicked(lambda event: apply_selection("genotype_2"))
    controls["buttons"]["set_vehicle"].on_clicked(lambda event: apply_selection("vehicle"))
    controls["buttons"]["set_gradient"].on_clicked(lambda event: apply_selection("drug_gradient"))
    controls["buttons"]["clear"].on_clicked(lambda event: apply_selection("clear"))
    controls["buttons"]["reset"].on_clicked(reset_all)
    controls["buttons"]["save"].on_clicked(save_layout)

    fig.canvas.mpl_connect("button_press_event", on_press)
    fig.canvas.mpl_connect("motion_notify_event", on_motion)
    fig.canvas.mpl_connect("button_release_event", on_release)
    fig.canvas.mpl_connect("resize_event", lambda event: redraw_plate())
    refresh_drug_toggles()
    redraw_plate()
    plt.show()


def launch_plate_map_gui(output_csv: str | Path | None = None) -> None:
    """Launch the interactive plate-map CSV editor."""
    launch_plate_map_matplotlib(output_csv=output_csv)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create or validate a CellPyAbility plate map CSV.")
    parser.add_argument("--output", help="Path for the plate map CSV created by the GUI or template.")
    parser.add_argument("--default", action="store_true", help="Write the current default GDA-style plate map without opening the GUI.")# This is for if the user decides they want to make their own plate map csv
    parser.add_argument("--validate", help="Validate an existing plate map CSV and exit.")
    args = parser.parse_args(argv)

    if args.validate:
        load_plate_map(args.validate)
        print(f"Valid plate map: {args.validate}")
        return

    if args.default:
        if not args.output:
            parser.error("--default requires --output")
        saved = save_plate_map(default_gda_plate_map(), args.output)
        print(f"Saved default plate map: {saved}")
        return

    launch_plate_map_gui(output_csv=args.output)


if __name__ == "__main__":
    main()
