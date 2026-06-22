import csv
import os

import numpy as np
import tifffile
from skimage.draw import disk
from skimage.filters import gaussian


OUTPUT_DIR = "fake_96_well_images"
IMAGE_SIZE = 1000
NUCLEUS_RADIUS = 5

TOP_CONC = 0.000001
DILUTION_FACTOR = 3
NUM_CONCENTRATIONS = 7

VEHICLE_COUNT = 1000
BOTTOM_COUNT = 50
IC50 = 1e-7
HILL = 1.2

ROWS = "ABCDEFGH"
COLS = range(1, 13)


def build_plate_layout():
    layout = []
    for row in ROWS:
        if row == "A":
            layout.append(["g1v"] * 6 + ["g2v"] * 6)
            continue

        concentration_index = ROWS.index(row)
        genotype_1 = [
            f"g1d1c{concentration_index}",
            f"g1d1c{concentration_index}",
            f"g1d2c{concentration_index}",
            f"g1d2c{concentration_index}",
            f"g1d3c{concentration_index}",
            f"g1d3c{concentration_index}",
        ]
        genotype_2 = [
            f"g2d1c{concentration_index}",
            f"g2d1c{concentration_index}",
            f"g2d2c{concentration_index}",
            f"g2d2c{concentration_index}",
            f"g2d3c{concentration_index}",
            f"g2d3c{concentration_index}",
        ]
        layout.append(genotype_1 + genotype_2)

    return layout


def concentration_index_from_code(code):
    if code.endswith("v"):
        return 0
    return int(code.split("c")[-1])


def concentration_from_index(concentration_index):
    if concentration_index == 0:
        return 0
    return TOP_CONC / (DILUTION_FACTOR ** (NUM_CONCENTRATIONS - concentration_index))


def expected_nuclei_count(concentration):
    if concentration == 0:
        return VEHICLE_COUNT

    count = BOTTOM_COUNT + (VEHICLE_COUNT - BOTTOM_COUNT) / (
        1 + (concentration / IC50) ** HILL
    )
    return int(count)


def make_fake_cell_image(n_cells):
    img = np.random.normal(0.02, 0.003, (IMAGE_SIZE, IMAGE_SIZE))

    for _ in range(n_cells):
        row = np.random.randint(NUCLEUS_RADIUS, IMAGE_SIZE - NUCLEUS_RADIUS)
        col = np.random.randint(NUCLEUS_RADIUS, IMAGE_SIZE - NUCLEUS_RADIUS)
        rr, cc = disk((row, col), NUCLEUS_RADIUS, shape=img.shape)
        img[rr, cc] += np.random.uniform(0.75, 0.95)

    img = gaussian(img, sigma=0.8)
    img += np.random.normal(0, 0.004, img.shape)
    img = np.clip(img, 0, 1)

    return (img * 255).astype(np.uint8)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    layout = build_plate_layout()
    metadata_path = os.path.join(OUTPUT_DIR, "plate_metadata.csv")

    with open(metadata_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "well",
            "map_code",
            "concentration_index",
            "concentration",
            "expected_nuclei",
            "actual_nuclei",
            "filename",
        ])

        for row_idx, row in enumerate(ROWS):
            for col_idx, col in enumerate(COLS):
                well = f"{row}{col:02d}"
                code = layout[row_idx][col_idx]
                concentration_index = concentration_index_from_code(code)
                concentration = concentration_from_index(concentration_index)
                expected_count = expected_nuclei_count(concentration)
                actual_count = int(np.random.normal(expected_count, expected_count * 0.05))
                actual_count = max(actual_count, 0)

                img = make_fake_cell_image(actual_count)
                filename = f"{well}_{code}_conc_{concentration:.2e}.tif"
                filepath = os.path.join(OUTPUT_DIR, filename)
                tifffile.imwrite(filepath, img)

                writer.writerow([
                    well,
                    code,
                    concentration_index,
                    concentration,
                    expected_count,
                    actual_count,
                    filename,
                ])

                print(well, code, concentration, actual_count)


if __name__ == "__main__":
    main()
