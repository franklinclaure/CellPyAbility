"""
Command-line interface for CellPyAbility.

This module provides CLI commands to run the three main modules:
- gda: dose-response analysis
- synergy: drug combination synergy analysis
- simple: nuclei count matrix
- gda-map: interactive GDA plate map CSV builder
- synergy-map: interactive synergy plate map CSV builder
- batch: batch processing from a CSV configuration file
"""

import argparse
import sys

from ._version import __version__
from .toolbox import CellPyAbilityError, build_gda_drug_params


def create_parser():
    """Create the argument parser for CellPyAbility CLI."""
    parser = argparse.ArgumentParser(
        prog='cellpyability',
        description='CellPyAbility: Cell viability and dose-response analysis tool'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    subparsers = parser.add_subparsers(
        title='modules',
        description='Available analysis modules',
        dest='module',
        required=True
    )
    
    # GDA module parser
    gda_parser = subparsers.add_parser(
        'gda',
        help='Growth Delay Assay: dose-response analysis of two cell lines (B-D, E-G) and one treatment (2-11)'
    )
    gda_parser.add_argument(
        '-t', '--title',
        required=True,
        help='Title of the experiment (e.g., 20250101_CellLine_Drug)'
    )
    gda_parser.add_argument(
        '-u', '--upper-name',
        help='Name for upper cell condition (rows B-D); required unless --plate-map is provided'
    )
    gda_parser.add_argument(
        '-l', '--lower-name',
        help='Name for lower cell condition (rows E-G); required unless --plate-map is provided'
    )
    gda_parser.add_argument(
        '-c', '--top-conc',
        type=float,
        help='Top concentration in molar for normal GDA or drug 1 in plate-map mode (e.g., 0.000001 for 1 µM)'
    )
    gda_parser.add_argument(
        '-d', '--dilution',
        type=float,
        help='Dilution factor for normal GDA or drug 1 in plate-map mode (e.g., 3 for 3-fold dilution)'
    )
    gda_parser.add_argument(
        '--drug-name',
        type=str,
        help='Name for drug 1 in plate-map GDA mode'
    )
    gda_parser.add_argument(
        '-i', '--image-dir',
        required=True,
        type=str,
        help='Directory containing the 60 well images'
    )
    gda_parser.add_argument(
        '-n', '--no-plot',
        action='store_true',
        help='Skip displaying the plot (still saves it)'
    )
    gda_parser.add_argument(
        '-f', '--counts-file',
        type=str,
        help='Path to pre-existing counts CSV file (for testing, bypasses CellProfiler)'
    )
    gda_parser.add_argument(
        '-o', '--output-dir',
        type=str,
        help='Custom output directory (default: ./cellpyability_output/ in current working directory)'
    )
    gda_parser.add_argument(
        '-m',
        '--plate-map',
        type=str,
        help='Optional CellPyAbility plate map CSV for custom genotype, vehicle, gradient, and replicate assignments'
    )
    gda_parser.add_argument(
        '--genotype-1-name',
        type=str,
        help='Display name for g1 in plate-map GDA mode'
    )
    gda_parser.add_argument(
        '--genotype-2-name',
        type=str,
        help='Display name for g2 in plate-map GDA mode'
    )
    for drug_number in range(2, 6):
        gda_parser.add_argument(
            f'--drug-name-{drug_number}',
            type=str,
            help=f'Name for drug {drug_number} in plate-map GDA mode'
        )
        gda_parser.add_argument(
            f'--top-conc-{drug_number}',
            f'--top-concentration-{drug_number}',
            type=float,
            help=f'Top concentration in molar for drug {drug_number} in plate-map GDA mode'
        )
        gda_parser.add_argument(
            f'--dilution-{drug_number}',
            type=float,
            help=f'Dilution factor for drug {drug_number} in plate-map GDA mode'
        )
    
    # Synergy module parser
    synergy_parser = subparsers.add_parser(
        'synergy',
        help='Synergy analysis: dose response analysis for one cell line and two treatments (row gradient and column gradient)'
    )
    synergy_parser.add_argument(
        '-t', '--title',
        required=True,
        help='Title of the experiment'
    )
    synergy_parser.add_argument(
        '-x', '--x-drug',
        required=True,
        help='Drug name for horizontal gradient (increases along row)'
    )
    synergy_parser.add_argument(
        '-c', '--x-top-conc',
        type=float,
        required=True,
        help='Horizontal top concentration in molar'
    )
    synergy_parser.add_argument(
        '-d', '--x-dilution',
        type=float,
        required=True,
        help='Horizontal dilution factor'
    )
    synergy_parser.add_argument(
        '-y', '--y-drug',
        required=True,
        help='Drug name for vertical gradient (increases along column)'
    )
    synergy_parser.add_argument(
        '-C', '--y-top-conc',
        type=float,
        required=True,
        help='Vertical top concentration in molar'
    )
    synergy_parser.add_argument(
        '-D', '--y-dilution',
        type=float,
        required=True,
        help='Vertical dilution factor'
    )
    synergy_parser.add_argument(
        '-i', '--image-dir',
        required=True,
        type=str,
        help='Directory containing the 180 well images'
    )
    synergy_parser.add_argument(
        '-n', '--no-plot',
        action='store_true',
        help='Skip displaying the plot (still saves it)'
    )
    synergy_parser.add_argument(
        '-f', '--counts-file',
        type=str,
        help='Path to pre-existing counts CSV file (for testing, bypasses CellProfiler)'
    )
    synergy_parser.add_argument(
        '-o', '--output-dir',
        type=str,
        help='Custom output directory (default: ./cellpyability_output/ in current working directory)'
    )
    synergy_parser.add_argument(
        '-m',
        '--plate-map',
        type=str,
        help='Optional compact synergy map CSV for code-based grouped analysis'
    )
    
    # Simple module parser
    simple_parser = subparsers.add_parser(
        'simple',
        help='Simple nuclei counting: 96-well count matrix without analysis'
    )
    simple_parser.add_argument(
        '-t', '--title',
        required=True,
        help='Title of the experiment'
    )
    simple_parser.add_argument(
        '-i', '--image-dir',
        required=True,
        type=str,
        help='Directory containing the well images'
    )
    simple_parser.add_argument(
        '-f', '--counts-file',
        type=str,
        help='Path to pre-existing counts CSV file (for testing, bypasses CellProfiler)'
    )
    simple_parser.add_argument(
        '-o', '--output-dir',
        type=str,
        help='Custom output directory (default: ./cellpyability_output/ in current working directory)'
    )

    # GDA map parser
    gda_map_parser = subparsers.add_parser(
        'gda-map',
        help='Create or validate a reusable GDA plate map CSV'
    )
    gda_map_parser.add_argument(
        '--output',
        type=str,
        help='Path for the GDA plate map CSV created by the GUI or default template'
    )
    gda_map_parser.add_argument(
        '--default',
        action='store_true',
        help='Write the current default GDA-style map without opening the GUI'
    )
    gda_map_parser.add_argument(
        '--validate',
        type=str,
        help='Validate an existing GDA plate map CSV and exit'
    )

    # Synergy map parser
    synergy_map_parser = subparsers.add_parser(
        'synergy-map',
        help='Create a compact synergy plate map CSV'
    )
    synergy_map_parser.add_argument(
        '--output',
        type=str,
        help='Path for the synergy map CSV created by the GUI'
    )
    
    # Batch module parser
    batch_parser = subparsers.add_parser(
        'batch',
        help='Run batch processing of multiple experiments from a CSV configuration file'
    )
    batch_parser.add_argument(
        '-i', '--input-file',
        required=True,
        type=str,
        help='Path to the batch configuration CSV file'
    )
    batch_parser.add_argument(
        '-n', '--no-plot',
        action='store_true',
        help='Skip displaying the plots (still saves them)'
    )
    batch_parser.add_argument(
        '-o', '--output-dir',
        type=str,
        help='Custom output directory'
    )

    return parser


def run_gda(args):
    """Run the GDA module with CLI arguments."""
    if not getattr(args, 'plate_map', None) and (not args.upper_name or not args.lower_name):
        raise ValueError("--upper-name and --lower-name are required unless --plate-map is provided")
    if not getattr(args, 'plate_map', None) and (args.top_conc is None or args.dilution is None):
        raise ValueError("--top-conc and --dilution are required unless --plate-map uses numbered drug arguments")

    drug_params = None
    genotype_names = None
    top_conc = args.top_conc
    dilution = args.dilution

    if getattr(args, 'plate_map', None):
        from cellpyability import GDA_interactive_map
        
        plate_map = GDA_interactive_map.load_plate_map(args.plate_map)
        # Creates a dataframe that only contrains columns that were part of a drug gradient
        gradient_rows = plate_map[
            plate_map['treatment_type'].astype(str).eq('drug_gradient')
        ]
        drug_codes = gradient_rows['drug'].astype(str).str.strip()
        number_of_drugs = drug_codes[drug_codes.str.len().gt(0)].nunique()
        if number_of_drugs > 5:
            raise ValueError(f"Plate map contains {number_of_drugs} drugs, but CLI supports up to 5.")

        supplied_drug_numbers = set()
        if args.drug_name or args.top_conc is not None or args.dilution is not None:
            supplied_drug_numbers.add(1)
        for drug_number in range(2, 6):
            if (
                getattr(args, f'drug_name_{drug_number}', None)
                or getattr(args, f'top_conc_{drug_number}', None) is not None
                or getattr(args, f'dilution_{drug_number}', None) is not None
            ):
                supplied_drug_numbers.add(drug_number)
        if supplied_drug_numbers != set(range(1, number_of_drugs + 1)):
            raise ValueError("Number of drug arguments does not match plate map.")

        drug_params = build_gda_drug_params(
            args.plate_map,
            number_of_drugs,
            lambda drug_number: args.drug_name if drug_number == 1 else getattr(args, f'drug_name_{drug_number}', None),
            lambda drug_number: args.top_conc if drug_number == 1 else getattr(args, f'top_conc_{drug_number}', None),
            lambda drug_number: args.dilution if drug_number == 1 else getattr(args, f'dilution_{drug_number}', None),
        )

        top_conc = drug_params[0]['top_conc']
        dilution = drug_params[0]['dilution']
        genotype_names = {
            genotype_code: genotype_name
            for genotype_code, genotype_name in (
                ('g1', getattr(args, 'genotype_1_name', None)),
                ('g2', getattr(args, 'genotype_2_name', None)),
            )
            if genotype_name
        }

    # Import here to avoid circular imports and GUI loading before validation.
    from cellpyability import gda_analysis

    gda_analysis.run_gda(
        title_name=args.title,
        upper_name=args.upper_name,
        lower_name=args.lower_name,
        top_conc=top_conc,
        dilution=dilution,
        image_dir=args.image_dir,
        show_plot=not args.no_plot,
        counts_file=getattr(args, 'counts_file', None),
        output_dir=getattr(args, 'output_dir', None),
        plate_map_file=getattr(args, 'plate_map', None),
        drug_params=drug_params,
        genotype_names=genotype_names,
    )


def run_synergy(args):
    """Run the synergy module with CLI arguments."""
    from cellpyability import synergy_analysis

    synergy_analysis.run_synergy(
        title_name=args.title,
        x_drug=args.x_drug,
        x_top_conc=args.x_top_conc,
        x_dilution=args.x_dilution,
        y_drug=args.y_drug,
        y_top_conc=args.y_top_conc,
        y_dilution=args.y_dilution,
        image_dir=args.image_dir,
        show_plot=not args.no_plot,
        counts_file=getattr(args, 'counts_file', None),
        output_dir=getattr(args, 'output_dir', None),
        plate_map_file=getattr(args, 'plate_map', None)
    )


def run_simple(args):
    """Run the simple module with CLI arguments."""
    from cellpyability import simple_analysis

    simple_analysis.run_simple(
        title=args.title,
        image_dir=args.image_dir,
        counts_file=getattr(args, 'counts_file', None),
        output_dir=getattr(args, 'output_dir', None)
    )


def run_gda_map(args):
    """Run the gda-map GUI or non-interactive helpers."""
    from cellpyability import GDA_interactive_map

    if args.validate:
        GDA_interactive_map.load_plate_map(args.validate)
        print(f"Valid plate map: {args.validate}")
        return

    if args.default:
        if not args.output:
            raise ValueError("--default requires --output")
        saved = GDA_interactive_map.save_plate_map(GDA_interactive_map.default_gda_plate_map(), args.output)
        print(f"Saved default plate map: {saved}")
        return

    GDA_interactive_map.launch_plate_map_gui(output_csv=args.output)


def run_synergy_map(args):
    """Run the synergy-map GUI."""
    from cellpyability import synergy_interactive_map

    synergy_interactive_map.launch_synergy_map_gui(output_csv=args.output)


def run_batch(args):
    """Run the batch module with CLI arguments."""
    from cellpyability import batch_analysis

    batch_analysis.run_batch(
        input_file=args.input_file,
        show_plot=not args.no_plot,
        output_dir=getattr(args, 'output_dir', None),
    )


def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        if args.module == 'gda':
            run_gda(args)
        elif args.module == 'synergy':
            run_synergy(args)
        elif args.module == 'simple':
            run_simple(args)
        elif args.module == 'gda-map':
            run_gda_map(args)
        elif args.module == 'synergy-map':
            run_synergy_map(args)
        elif args.module == 'batch':
            run_batch(args)
        else:
            parser.print_help()
            sys.exit(1)
    except CellPyAbilityError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
