import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont, ImageTk

import CellPyAbility_GDA_app
import CellPyAbility_simple_app
import CellPyAbility_synergy_app
import CellPyAbility_batch_app

# Define temporary directory so logo can be accessed later
if getattr(sys, 'frozen', False):
    temp_dir = Path(sys._MEIPASS) # PyInstaller's temporary folder
else:
    temp_dir = Path(__file__).resolve().parent


LOGO_SIZE = (500, 500)
TRANSITION_DELAY_MS = 650
TRANSITION_DURATION_MS = 1600
TRANSITION_FRAMES = 48
FINAL_BACKGROUND = "#ffffff"


def _rgb(widget, color):
    """Return an 8-bit RGB tuple for a Tk color name."""
    return tuple(value // 257 for value in widget.winfo_rgb(color))


def _hex_color(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _blend_color(start, end, progress):
    return _hex_color(tuple(
        round(start_value + (end_value - start_value) * progress)
        for start_value, end_value in zip(start, end)
    ))


def _fit_logo(image, size):
    """Center an image inside the fixed logo area without stretching it."""
    image = image.convert("RGBA")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    offset = ((size[0] - image.width) // 2, (size[1] - image.height) // 2)
    canvas.alpha_composite(image, offset)
    return canvas


def _version_font(size):
    for font_name in (
        "Arial Bold.ttf",
        "Arial.ttf",
        "DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _add_version_mark(image, opacity):
    """Fade a 2.0 mark in beside the CellPyAbility name."""
    marked = image.copy()
    overlay = Image.new("RGBA", marked.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.text(
        (398, 118),
        "2.0",
        fill=(20, 64, 170, round(255 * opacity)),
        font=_version_font(27),
        stroke_width=1,
        stroke_fill=(255, 255, 255, round(210 * opacity)),
    )
    return Image.alpha_composite(marked, overlay)


def _build_logo_frames(initial_background):
    old_logo = _fit_logo(
        Image.open(temp_dir / "CellPyAbilityLogo.png"),
        LOGO_SIZE,
    )
    new_logo = _fit_logo(
        Image.open(temp_dir / "Potential_New_Logo.png"),
        LOGO_SIZE,
    )

    old_background = Image.new("RGBA", LOGO_SIZE, initial_background + (255,))
    old_background.alpha_composite(old_logo)
    new_background = Image.new("RGBA", LOGO_SIZE, (255, 255, 255, 255))
    new_background.alpha_composite(new_logo)

    frames = []
    for frame_index in range(TRANSITION_FRAMES + 1):
        progress = frame_index / TRANSITION_FRAMES
        blended = Image.blend(old_background, new_background, progress)
        blended = _add_version_mark(blended, max(0.0, (progress - 0.35) / 0.65))
        frames.append(ImageTk.PhotoImage(blended))
    return frames


def _animate_rebrand(root, logo_label, button_frame, buttons):
    initial_background = _rgb(root, root.cget("background"))
    final_background = _rgb(root, FINAL_BACKGROUND)

    try:
        logo_frames = _build_logo_frames(initial_background)
    except Exception as error:
        print("Could not prepare logo transition:", error)
        return

    # Keep the images alive for the lifetime of the window.
    root.logo_frames = logo_frames

    def show_frame(frame_index):
        progress = frame_index / TRANSITION_FRAMES
        background = _blend_color(
            initial_background,
            final_background,
            progress,
        )

        root.configure(background=background)
        logo_label.configure(
            image=logo_frames[frame_index],
            background=background,
        )
        button_frame.configure(background=background)

        for button in buttons:
            button.configure(
                background=background,
                activebackground=background,
                highlightbackground=background,
            )

        if frame_index < TRANSITION_FRAMES:
            frame_time = max(
                1,
                TRANSITION_DURATION_MS // TRANSITION_FRAMES,
            )
            root.after(frame_time, show_frame, frame_index + 1)
        else:
            root.title("CellPyAbility 2.0 Analysis Menu")

    root.after(TRANSITION_DELAY_MS, show_frame, 0)

# Gives user info on scripts when hovering over GUI buttons
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        # Calculate position for the tooltip window
        x, y, _cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        # Create a top-level window that appears above other windows
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Remove window decorations
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#ffffe0", foreground="#000000",
            relief=tk.SOLID, borderwidth=1,
            font=("tahoma", "8", "normal")
        )
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

def launch_gui():
    # Establish GUI window
    global root
    root = tk.Tk()
    root.title("CellPyAbility Analysis Menu")
    root.geometry("540x740") # If it fits, it ships

    initial_background = root.cget("background")

    # Load the original logo so the menu opens exactly as it did before.
    try:
        logo_image = ImageTk.PhotoImage(
            _fit_logo(
                Image.open(temp_dir / "CellPyAbilityLogo.png"),
                LOGO_SIZE,
            )
        )
        logo_label = tk.Label(
            root,
            image=logo_image,
            background=initial_background,
        )
    except Exception as e: # if it doesn't work, load in text title
        print("Could not load logo image:", e)
        logo_image = None
        logo_label = tk.Label(
            root,
            text="CellPyAbility\nBindra Lab",
            font=("tahoma", 24),
            background=initial_background,
        )

    if logo_image is not None:
        logo_label.image = logo_image
    logo_label.pack(pady=10)

    # Create buttons for each script option, along with tooltip dialogue
    button_frame = tk.Frame(root, background=initial_background)
    button_frame.pack(pady=20)

    btn_plate_map = tk.Button(button_frame, text="Make a Plate Map", width=28,
                              command=lambda: run_script(5))
    btn_plate_map.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
    ToolTip(btn_plate_map, "Create a plate-map CSV for GDA or synergy analysis")

    btn_gda = tk.Button(button_frame, text="GDA", width=12,
                        command=lambda: run_script(1))
    btn_gda.grid(row=1, column=0, padx=5, pady=5)
    ToolTip(btn_gda, "Dose-response analysis of two cell lines in response to one treatment")

    btn_synergy = tk.Button(button_frame, text="Synergy", width=12,
                            command=lambda: run_script(2))
    btn_synergy.grid(row=1, column=1, padx=5, pady=5)
    ToolTip(btn_synergy, "Dose-response analysis of one cell line in response to two treatments in combination")

    btn_batch = tk.Button(button_frame, text="Batch", width=12,
                          command=lambda: run_script(4))
    btn_batch.grid(row=2, column=0, padx=5, pady=5)
    ToolTip(btn_batch, "Run multiple experiments from a CSV configuration file")

    btn_simple = tk.Button(button_frame, text="Simple", width=12,
                           command=lambda: run_script(3))
    btn_simple.grid(row=2, column=1, padx=5, pady=5)
    ToolTip(btn_simple, "Raw nuclei count matrix")

    btn_exit = tk.Button(root, text="Exit", command=root.quit)
    ToolTip(btn_exit, "Close the program")
    btn_exit.pack(pady=(0, 10))

    _animate_rebrand(
        root,
        logo_label,
        button_frame,
        [btn_plate_map, btn_gda, btn_synergy, btn_batch, btn_simple, btn_exit],
    )

    root.mainloop()


def make_plate_map():
    chooser = tk.Tk()
    chooser.title("Make a plate map")
    chooser.geometry("320x150")
    choice = {"map_type": None}

    tk.Label(chooser, text="Choose plate-map type:").pack(pady=10)

    def choose(map_type):
        choice["map_type"] = map_type
        chooser.destroy()

    tk.Button(chooser, text="GDA Plate Map", width=18,
              command=lambda: choose("gda")).pack(pady=4)
    tk.Button(chooser, text="Synergy Plate Map", width=18,
              command=lambda: choose("synergy")).pack(pady=4)
    chooser.mainloop()

    if choice["map_type"] is None:
        return

    temp_root = tk.Tk()
    temp_root.withdraw()
    output_csv = filedialog.asksaveasfilename(
        title="Save Plate Map CSV",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    temp_root.destroy()
    if not output_csv:
        return

    if getattr(sys, 'frozen', False):
        from cellpyability import GDA_interactive_map, synergy_interactive_map

        if choice["map_type"] == "gda":
            GDA_interactive_map.launch_plate_map_gui(output_csv=output_csv)
        else:
            synergy_interactive_map.launch_synergy_map_gui(output_csv=output_csv)
        return

    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    )
    module_name = "gda-map" if choice["map_type"] == "gda" else "synergy-map"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "cellpyability.cli",
            module_name,
            "--output",
            output_csv,
        ],
        cwd=repo_root,
        env=env,
        check=True,
    )


# Runs script based on user input from GUI
def run_script(script_number):
    global root
    root.destroy() # Close window after choosing script
    
    try:
        if script_number == 1:
            CellPyAbility_GDA_app.run()
        elif script_number == 2:
            CellPyAbility_synergy_app.run()
        elif script_number == 3:
            CellPyAbility_simple_app.run()
        elif script_number == 4:
            CellPyAbility_batch_app.run()
        elif script_number == 5:
            make_plate_map()
        else:
            raise ValueError("Invalid script selection.")
    except Exception as e:
        temp_root = tk.Tk()
        temp_root.withdraw()
        messagebox.showerror("CellPyAbility Error", str(e))
        temp_root.destroy()
    
    # Ask user if they wish to perform an additonal analysis
    temp_root = tk.Tk()
    temp_root.withdraw()
    response = messagebox.askyesno(
        "CellPyAbility",
        "Would you like to perform another analysis?"
    )
    temp_root.destroy()

    if response:
        launch_gui() # If yes, re-launch GUI
    else:
        sys.exit() # Else, exit application
    
launch_gui()
