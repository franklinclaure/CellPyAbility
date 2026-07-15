"""
Interactive Matplotlib synergy plate-map editor for CellPyAbility.

The GUI saves a compact 8x12 CSV where unassigned wells are 0, single-drug
wells use codes such as d1c1, and combination wells use codes such as
d1c2+d2c3.
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
)

MAP_COLUMNS = ["well", "row", "column", "control", "assignments"]


def blank_synergy_map() -> pd.DataFrame:
    """Create an empty 96-well synergy map."""
    return build_plate_dataframe(
        MAP_COLUMNS,
        lambda well, row, column: {
            "well": well,
            "row": row,
            "column": int(column),
            "control": False,
            "assignments": {},
        },
    )


def compact_code(row: pd.Series) -> str:
    """Return the compact CSV code for one mapped well."""
    if bool(row.get("control", False)):
        return "control"
    assignments = row.get("assignments") or {}
    if not assignments:
        return "0"
    codes = []
    for drug in sorted(assignments, key=lambda value: int(str(value).removeprefix("d"))):
        concentration = str(assignments[drug].get("concentration_index", "")).strip()
        if concentration:
            codes.append(f"{drug}c{concentration}")
    return "+".join(codes) if codes else "0"


def compact_grid(df: pd.DataFrame) -> list[list[str]]:
    """Convert a synergy map DataFrame into an 8x12 compact grid."""
    lookup = {row["well"]: compact_code(row) for _, row in df.iterrows()}
    return [[lookup[f"{row}{column}"] for column in COLUMNS] for row in ROWS]


def save_compact_grid(df: pd.DataFrame, output_csv: str | Path) -> Path:
    """Save a synergy map DataFrame as an 8x12 compact CSV."""
    output_path = Path(output_csv).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(compact_grid(df))
    return output_path


def parse_synergy_code(raw_code: str, well: str) -> tuple[str, bool, dict[str, dict[str, int]]]:
    """Parse one compact synergy map code into normalized analysis fields."""
    code = str(raw_code).strip().lower()
    if code in {"", "0"}:
        return "0", False, {}
    if code == "control":
        return "control", True, {}

    assignments = {}
    code_pattern = re.compile(r"^d([1-9]\d*)c([1-9]\d*)$")
    for part in code.split("+"):
        match = code_pattern.match(part.strip())
        if not match:
            raise ValueError(
                f"Invalid compact synergy-map code '{raw_code}' at {well}. "
                "Use 0, control, d1c1, or combinations like d1c1+d2c3."
            )
        drug_id, concentration_id = match.groups()
        drug = f"d{int(drug_id)}"
        if drug in assignments:
            raise ValueError(
                f"Invalid compact synergy-map code '{raw_code}' at {well}. "
                f"Drug {drug} appears more than once."
            )
        assignments[drug] = {"concentration_index": int(concentration_id)}

    normalized_parts = [
        f"{drug}c{assignments[drug]['concentration_index']}"
        for drug in sorted(assignments, key=lambda value: int(value.removeprefix("d")))
    ]
    return "+".join(normalized_parts), False, assignments


def load_synergy_map(input_csv: str | Path) -> pd.DataFrame:
    """Load an 8x12 compact synergy map CSV into one row per well."""
    compact_df = pd.read_csv(input_csv, header=None, dtype=str, keep_default_na=False)
    if compact_df.shape != (8, 12):
        raise ValueError(
            f"Compact synergy map must be exactly 8 rows x 12 columns; found {compact_df.shape[0]} x {compact_df.shape[1]}."
        )

    records = []
    for row_idx, row in enumerate(ROWS):
        for col_idx, column in enumerate(COLUMNS):
            well = f"{row}{column}"
            code, is_control, assignments = parse_synergy_code(compact_df.iat[row_idx, col_idx], well)
            records.append(
                {
                    "well": well,
                    "row": row,
                    "column": int(column),
                    "code": code,
                    "is_control": is_control,
                    "assignments": assignments,
                }
            )
    return pd.DataFrame(records)


def launch_synergy_map_matplotlib(output_csv: str | Path | None = None) -> None:
    """Launch the interactive synergy plate-map editor."""
    prepare_interactive_matplotlib_backend()

    from matplotlib import patheffects as path_effects
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from matplotlib.widgets import Button, RadioButtons, TextBox

    colors = {
        "background": "#f5f7fb",
        "panel": "#ffffff",
        "border": "#c9d3df",
        "text": "#1f2933",
        "muted": "#5f6b7a",
        "unassigned": "#f8fafc",
        "control": "#7dd3fc",
        "active": "#ffd166",
        "active_border": "#2f80ed",
    }
    drug_colors = {
        "d1": "#2f80ed",
        "d2": "#eb5757",
        "d3": "#27ae60",
        "d4": "#9b51e0",
        "d5": "#f2994a",
        "d6": "#00a8a8",
        "d7": "#d946ef",
        "d8": "#7f8c8d",
        "d9": "#f2c94c",
        "d10": "#34495e",
        "d11": "#e84393",
        "d12": "#16a085",
    }

    output_base = Path(output_csv).expanduser() if output_csv else Path.cwd() / "synergy_map.csv"
    output_dir = output_base.parent if output_base.suffix.lower() == ".csv" else output_base
    initial_layout_name = output_base.stem if output_base.suffix.lower() == ".csv" else "synergy_map"

    data = {"df": blank_synergy_map()}
    selected_wells: set[str] = set()
    state = {
        "dragging": False,
        "drag_start": None,
        "drag_end": None,
        "marquee": None,
        "confirm_reset": False,
        "drug_count": 3,
        "selected_drug": "d1",
        "drug_directions": {"d1": "horizontal", "d2": "vertical", "d3": "horizontal"},
        "undo_stack": [],
    }
    controls: dict[str, object] = {}

    fig = plt.figure(figsize=(14, 8), facecolor=colors["background"])
    fig.canvas.manager.set_window_title("CellPyAbility Synergy Map")
    plate_ax = fig.add_axes([0.34, 0.17, 0.62, 0.72], facecolor=colors["panel"])
    detail_ax = fig.add_axes([0.34, 0.055, 0.62, 0.075], facecolor=colors["panel"])
    detail_ax.set_xticks([])
    detail_ax.set_yticks([])
    for spine in detail_ax.spines.values():
        spine.set_edgecolor(colors["border"])

    fig.text(0.34, 0.935, "96-Well Synergy Plate", fontsize=18, fontweight="bold", color=colors["text"])
    status_text = fig.text(0.105, 0.015, "Ready. Drag a rectangle over wells to highlight.", fontsize=10, color=colors["muted"])
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
        status_text.set_text(message)
        fig.canvas.draw_idle()

    def set_detail(message: str) -> None:
        detail_text.set_text(message)
        fig.canvas.draw_idle()

    def make_textbox(y: float, label: str, initial: str) -> TextBox:
        ax = fig.add_axes([0.105, y, 0.19, 0.035], facecolor=colors["panel"])
        ax.format_coord = lambda x, y: ""
        return TextBox(ax, label, initial=initial, color=colors["panel"], hovercolor="#eef3f8")

    controls["layout_name"] = make_textbox(0.885, "Layout name: ", initial_layout_name)
    controls["drug_count"] = make_textbox(0.815, "Number of Drugs: ", "3")
    fig.text(0.105, 0.705, "Drugs | Gradient Direction", fontsize=11, fontweight="bold", color=colors["text"])

    control_ax = fig.add_axes([0.105, 0.755, 0.19, 0.04])
    assign_ax = fig.add_axes([0.105, 0.25, 0.19, 0.04])
    clear_ax = fig.add_axes([0.105, 0.195, 0.19, 0.04])
    undo_ax = fig.add_axes([0.105, 0.14, 0.19, 0.04])
    reset_ax = fig.add_axes([0.105, 0.085, 0.19, 0.04])
    save_ax = fig.add_axes([0.105, 0.035, 0.19, 0.04])

    def textbox_value(key: str) -> str:
        return controls[key].text.strip()

    def drug_labels() -> list[str]:
        try:
            count = int(float(textbox_value("drug_count") or state["drug_count"]))
        except ValueError:
            count = int(state["drug_count"])
        count = max(1, min(12, count))
        state["drug_count"] = count
        labels = [f"d{idx}" for idx in range(1, count + 1)]
        for label in labels:
            state["drug_directions"].setdefault(label, "horizontal")
        if state["selected_drug"] not in labels:
            state["selected_drug"] = labels[0]
        return labels

    def row_df_index(well: str) -> int:
        df = data["df"]
        return int(df.index[df["well"] == well][0])

    def get_row(well: str) -> pd.Series:
        return data["df"][data["df"]["well"] == well].iloc[0]

    def row_index(row: str) -> int:
        return ROWS.index(row)

    def assignments_for_row(row: pd.Series) -> dict[str, dict[str, object]]:
        return dict(row.get("assignments") or {})

    def assignments_for_well(well: str) -> dict[str, dict[str, object]]:
        return assignments_for_row(get_row(well))

    def is_control_well(well: str) -> bool:
        return bool(get_row(well).get("control", False))

    def blend_hex(start: str, end: str, amount: float) -> str:
        amount = max(0.0, min(1.0, amount))
        start_rgb = tuple(int(start[i : i + 2], 16) for i in (1, 3, 5))
        end_rgb = tuple(int(end[i : i + 2], 16) for i in (1, 3, 5))
        rgb = tuple(round(a + (b - a) * amount) for a, b in zip(start_rgb, end_rgb))
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def average_hex(hex_colors: list[str]) -> str:
        rgbs = [
            tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
            for color in hex_colors
        ]
        if not rgbs:
            return colors["unassigned"]
        mixed = tuple(round(sum(rgb[channel] for rgb in rgbs) / len(rgbs)) for channel in range(3))
        return "#{:02x}{:02x}{:02x}".format(*mixed)

    def ordered_wells(wells: list[str], axis: str) -> list[str]:
        if axis == "horizontal":
            return sorted(wells, key=lambda well: (int(well[1:]), row_index(well[0])))
        return sorted(wells, key=lambda well: (row_index(well[0]), int(well[1:])))

    def concentration_indices(wells: list[str], axis: str) -> dict[str, int]:
        if axis == "horizontal":
            ordered_columns = sorted({int(well[1:]) for well in wells})
            lookup = {str(column): idx for idx, column in enumerate(ordered_columns, start=1)}
            return {well: lookup[well[1:]] for well in wells}
        ordered_rows = sorted({well[0] for well in wells}, key=row_index)
        lookup = {row: idx for idx, row in enumerate(ordered_rows, start=1)}
        return {well: lookup[well[0]] for well in wells}

    def well_from_event(event) -> str | None:
        if event.inaxes is not plate_ax or event.xdata is None or event.ydata is None:
            return None
        col_idx = int(event.xdata)
        row_idx = int(event.ydata)
        if 0 <= col_idx < len(COLUMNS) and 0 <= row_idx < len(ROWS):
            return f"{ROWS[row_idx]}{COLUMNS[col_idx]}"
        return None

    def wells_in_rectangle(start: tuple[float, float], end: tuple[float, float]) -> set[str]:
        x1, y1 = start
        x2, y2 = end
        xmin, xmax = sorted([x1, x2])
        ymin, ymax = sorted([y1, y2])
        hits = set()
        for row_idx, row in enumerate(ROWS):
            for col_idx, column in enumerate(COLUMNS):
                cell_x1, cell_x2 = col_idx, col_idx + 0.9
                cell_y1, cell_y2 = row_idx, row_idx + 0.9
                if xmax >= cell_x1 and xmin <= cell_x2 and ymax >= cell_y1 and ymin <= cell_y2:
                    hits.add(f"{row}{column}")
        return hits

    def hover_detail(well: str | None) -> str:
        if well is None:
            return "Hover over a well for details."
        row = get_row(well)
        assignments = assignments_for_row(row)
        parts = [well, f"Code: {compact_code(row)}"]
        if bool(row.get("control", False)):
            parts.append("Control")
        for drug in drug_labels():
            drug_number = drug.removeprefix("d")
            concentration = str(assignments.get(drug, {}).get("concentration_index", "")).strip()
            value = f"c{concentration}" if concentration else "NA"
            parts.append(f"Drug {drug_number}: {value}")
        return " | ".join(parts)

    def well_text(well: str) -> str:
        return well

    def gradient_amount(well: str) -> float:
        assignments = assignments_for_well(well)
        if not assignments:
            return 0.0
        df = data["df"]
        amounts = []
        for drug, assignment in assignments.items():
            try:
                concentration = int(assignment.get("concentration_index", ""))
            except (TypeError, ValueError):
                continue
            axis = assignment.get("gradient_axis", "")
            concentrations = []
            for _, row in df.iterrows():
                row_assignment = assignments_for_row(row).get(drug)
                if row_assignment and row_assignment.get("gradient_axis") == axis:
                    try:
                        concentrations.append(int(row_assignment.get("concentration_index", "")))
                    except (TypeError, ValueError):
                        pass
            max_concentration = max(concentrations) if concentrations else concentration
            if max_concentration > 1:
                amounts.append(((concentration - 1) / (max_concentration - 1)) * 0.82)
        return max(amounts, default=0.0)

    def well_color(well: str) -> str:
        if well in selected_wells:
            return colors["active"]
        if is_control_well(well):
            return colors["control"]
        assignments = assignments_for_well(well)
        if assignments:
            base_color = average_hex([drug_colors.get(drug, colors["active_border"]) for drug in assignments])
            gradient_color = blend_hex("#ffffff", base_color, 0.42 + gradient_amount(well))
            return gradient_color
        return colors["unassigned"]

    def redraw_plate() -> None:
        plate_ax.clear()
        plate_ax.format_coord = lambda x, y: ""
        plate_ax.set_xlim(-0.7, len(COLUMNS))
        plate_ax.set_ylim(len(ROWS), -0.7)
        plate_ax.set_aspect("auto")
        plate_ax.axis("off")
        bbox = plate_ax.get_window_extent()
        fontsize = max(5, min(10, bbox.width / 132))
        label_fontsize = max(7, min(12, bbox.width / 120))
        for col_idx, column in enumerate(COLUMNS):
            plate_ax.text(col_idx + 0.45, -0.32, column, ha="center", va="center", color=colors["muted"], fontweight="bold", fontsize=label_fontsize)
        for row_idx, row in enumerate(ROWS):
            plate_ax.text(-0.35, row_idx + 0.45, row, ha="center", va="center", color=colors["muted"], fontweight="bold", fontsize=label_fontsize)
            for col_idx, column in enumerate(COLUMNS):
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

    def push_undo() -> None:
        state["undo_stack"].append(data["df"].copy(deep=True))
        if len(state["undo_stack"]) > 25:
            state["undo_stack"].pop(0)

    def undo_last(event=None) -> None:
        """Restore the live plate-map DataFrame from the most recent undo snapshot."""
        if not state["undo_stack"]:
            set_status("Nothing to undo.")
            return
        data["df"] = state["undo_stack"].pop()
        selected_wells.clear()
        state["confirm_reset"] = False
        set_status("Undid last layout action.")
        redraw_plate()

    def assign_gradient(event=None) -> None:
        """Write the selected drug, gradient axis, and concentration index into selected DataFrame rows."""
        if not selected_wells:
            set_status("Highlight one or more wells first.")
            return
        push_undo()
        drug = str(state["selected_drug"])
        axis = str(state["drug_directions"].get(drug, "horizontal"))
        wells = ordered_wells(list(selected_wells), axis)
        lookup = concentration_indices(wells, axis)
        df = data["df"]
        for well in wells:
            idx = row_df_index(well)
            assignments = dict(df.at[idx, "assignments"] or {})
            assignments[drug] = {
                "gradient_axis": axis,
                "concentration_index": lookup[well],
            }
            df.at[idx, "control"] = False
            df.at[idx, "assignments"] = assignments
        count = len(selected_wells)
        selected_wells.clear()
        set_status(f"Assigned {drug} {axis} gradient to {count} well(s).")
        redraw_plate()

    def assign_control(event=None) -> None:
        """Mark selected DataFrame rows as controls and remove any drug assignments."""
        if not selected_wells:
            set_status("Highlight one or more wells first.")
            return
        push_undo()
        df = data["df"]
        for well in selected_wells:
            idx = row_df_index(well)
            df.at[idx, "control"] = True
            df.at[idx, "assignments"] = {}
        count = len(selected_wells)
        selected_wells.clear()
        set_status(f"Assigned {count} control well(s).")
        redraw_plate()

    def clear_highlighted(event=None) -> None:
        """Clear control flags and drug assignments from selected DataFrame rows."""
        if not selected_wells:
            set_status("Highlight one or more wells first.")
            return
        push_undo()
        df = data["df"]
        for well in selected_wells:
            idx = row_df_index(well)
            df.at[idx, "control"] = False
            df.at[idx, "assignments"] = {}
        count = len(selected_wells)
        selected_wells.clear()
        set_status(f"Cleared {count} well(s).")
        redraw_plate()

    def reset_all(event=None) -> None:
        """Replace the live plate-map DataFrame with a new blank synergy map after confirmation."""
        if not state["confirm_reset"]:
            state["confirm_reset"] = True
            set_status("Click Reset All again to confirm clearing every well.")
            return
        push_undo()
        data["df"] = blank_synergy_map()
        selected_wells.clear()
        state["confirm_reset"] = False
        set_detail("Hover over a well for details.")
        set_status("All wells reset.")
        redraw_plate()

    def sanitized_layout_name() -> str:
        name = textbox_value("layout_name") or "synergy_map"
        cleaned = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in name).strip("_")
        return cleaned or "synergy_map"

    def save_layout(event=None) -> None:
        """Saves the format of the plate map for repeat use"""
        output_dir.mkdir(parents=True, exist_ok=True)
        path = (output_dir / f"{sanitized_layout_name()}.csv").expanduser().resolve()
        save_compact_grid(data["df"], path)
        set_status(f"Saved layout to {path}")

    def select_drug(label: str) -> None:
        state["selected_drug"] = label.replace("Drug ", "d")
        direction = state["drug_directions"].get(state["selected_drug"], "horizontal")
        set_status(f"{state['selected_drug']} selected: {direction}.")

    def refresh_drug_controls(text: str | None = None) -> None:
        for axis in controls.get("drug_axes", []):
            axis.remove()
        labels = drug_labels()
        controls["drug_axes"] = []
        controls["direction_buttons"] = {}
        top = 0.665
        row_height = min(0.052, 0.36 / max(1, len(labels)))
        height = row_height * len(labels)
        drug_ax = fig.add_axes([0.105, top - height + row_height * 0.2, 0.085, height], facecolor=colors["panel"])
        drug_ax.format_coord = lambda x, y: ""
        drug_radio = RadioButtons(
            drug_ax,
            [label.replace("d", "Drug ") for label in labels],
            active=labels.index(state["selected_drug"]),
            activecolor=drug_colors.get(state["selected_drug"], colors["active_border"]),
        )
        controls["drug_axes"].append(drug_ax)
        controls["drug_radio"] = drug_radio

        def update_drug_radio_colors() -> None:
            circles = getattr(drug_radio, "circles", [])
            for circle, drug in zip(circles, labels):
                drug_color = drug_colors.get(drug, colors["active_border"])
                circle.set_edgecolor(drug_color)
                circle.set_facecolor(drug_color if drug == state["selected_drug"] else colors["panel"])
            buttons = getattr(drug_radio, "_buttons", None)
            if buttons is not None and hasattr(buttons, "set_facecolors"):
                edgecolors = [drug_colors.get(drug, colors["active_border"]) for drug in labels]
                facecolors = [
                    drug_colors.get(drug, colors["active_border"])
                    if drug == state["selected_drug"]
                    else colors["panel"]
                    for drug in labels
                ]
                buttons.set_edgecolors(edgecolors)
                buttons.set_facecolors(facecolors)

        def choose_drug(label: str) -> None:
            select_drug(label)
            update_drug_radio_colors()
            fig.canvas.draw_idle()

        drug_radio.on_clicked(choose_drug)

        def update_direction_button_colors(selected_drug: str) -> None:
            buttons = controls["direction_buttons"].get(selected_drug, {})
            active_direction = state["drug_directions"].get(selected_drug, "horizontal")
            for direction, button in buttons.items():
                selected = direction == active_direction
                facecolor = colors["active_border"] if selected else colors["panel"]
                hovercolor = colors["active_border"] if selected else "#eef3f8"
                button.color = facecolor
                button.hovercolor = hovercolor
                button.ax.set_facecolor(facecolor)
                button.ax.patch.set_facecolor(facecolor)
                button.label.set_color("#ffffff" if selected else colors["text"])
            fig.canvas.draw_idle()

        for idx, drug in enumerate(labels):
            row_center = top - (idx + 0.5) * row_height
            horiz_ax = fig.add_axes([0.2, row_center - 0.018, 0.045, 0.036], facecolor=colors["panel"])
            vert_ax = fig.add_axes([0.25, row_center - 0.018, 0.045, 0.036], facecolor=colors["panel"])
            horiz_ax.format_coord = lambda x, y: ""
            vert_ax.format_coord = lambda x, y: ""
            horiz_button = Button(horiz_ax, "Horiz", color=colors["panel"], hovercolor="#eef3f8")
            vert_button = Button(vert_ax, "Vert", color=colors["panel"], hovercolor="#eef3f8")
            controls["direction_buttons"][drug] = {
                "horizontal": horiz_button,
                "vertical": vert_button,
            }

            def choose_direction(_event=None, direction_drug: str = drug, direction: str = "horizontal") -> None:
                state["drug_directions"][direction_drug] = direction
                update_direction_button_colors(direction_drug)
                set_status(f"{direction_drug} direction set to {state['drug_directions'][direction_drug]}.")

            horiz_button.on_clicked(lambda event, direction_drug=drug: choose_direction(event, direction_drug, "horizontal"))
            vert_button.on_clicked(lambda event, direction_drug=drug: choose_direction(event, direction_drug, "vertical"))
            update_direction_button_colors(drug)
            controls["drug_axes"].extend([horiz_ax, vert_ax])
        update_drug_radio_colors()
        fig.canvas.draw_idle()

    controls["drug_count"].on_submit(refresh_drug_controls)
    if hasattr(controls["drug_count"], "on_text_change"):
        controls["drug_count"].on_text_change(refresh_drug_controls)

    def on_press(event) -> None:
        well = well_from_event(event)
        if well is None:
            return
        state["confirm_reset"] = False
        state["dragging"] = True
        state["drag_start"] = (event.xdata, event.ydata)
        state["drag_end"] = (event.xdata, event.ydata)

    def on_motion(event) -> None:
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
        "control": Button(control_ax, "Assign Control"),
        "assign": Button(assign_ax, "Assign Drug and Gradient"),
        "clear": Button(clear_ax, "Clear Highlighted"),
        "undo": Button(undo_ax, "Undo"),
        "reset": Button(reset_ax, "Reset All"),
        "save": Button(save_ax, "Save Layout"),
    }
    controls["buttons"]["control"].on_clicked(assign_control)
    controls["buttons"]["assign"].on_clicked(assign_gradient)
    controls["buttons"]["clear"].on_clicked(clear_highlighted)
    controls["buttons"]["undo"].on_clicked(undo_last)
    controls["buttons"]["reset"].on_clicked(reset_all)
    controls["buttons"]["save"].on_clicked(save_layout)

    fig.canvas.mpl_connect("button_press_event", on_press)
    fig.canvas.mpl_connect("motion_notify_event", on_motion)
    fig.canvas.mpl_connect("button_release_event", on_release)
    fig.canvas.mpl_connect("resize_event", lambda event: redraw_plate())
    refresh_drug_controls()
    redraw_plate()
    plt.show()


def launch_synergy_map_gui(output_csv: str | Path | None = None) -> None:
    """Launch the interactive synergy plate-map CSV editor."""
    launch_synergy_map_matplotlib(output_csv=output_csv)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create a CellPyAbility synergy plate map CSV.")
    parser.add_argument("--output", help="Path for the synergy map CSV created by the GUI.")
    args = parser.parse_args(argv)
    launch_synergy_map_gui(output_csv=args.output)


if __name__ == "__main__":
    main()
