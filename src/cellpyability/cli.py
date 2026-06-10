"""
Command-line interface for CellPyAbility.

This module provides CLI commands to run the three main modules:
- gda: dose-response analysis
- synergy: drug combination synergy analysis
- simple: nuclei count matrix
"""

import argparse
import csv
import sys

from ._version import __version__
from .toolbox import CellPyAbilityError


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
        required=True,
        help='Name for upper cell condition (rows B-D)'
    )
    gda_parser.add_argument(
        '-l', '--lower-name',
        required=True,
        help='Name for lower cell condition (rows E-G)'
    )
    gda_parser.add_argument(
        '-c', '--top-conc',
        type=float,
        required=True,
        help='Top concentration in molar (e.g., 0.000001 for 1 µM)'
    )
    gda_parser.add_argument(
        '-d', '--dilution',
        type=float,
        required=True,
        help='Dilution factor between columns (e.g., 3 for 3-fold dilution)'
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
    # Import here to avoid circular imports and GUI loading
    from cellpyability import gda_analysis
    
    gda_analysis.run_gda(
        title_name=args.title,
        upper_name=args.upper_name,
        lower_name=args.lower_name,
        top_conc=args.top_conc,
        dilution=args.dilution,
        image_dir=args.image_dir,
        show_plot=not args.no_plot,
        counts_file=getattr(args, 'counts_file', None),
        output_dir=getattr(args, 'output_dir', None)
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
        output_dir=getattr(args, 'output_dir', None)
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


def run_batch(args):
    """Run batch processing from a CSV file."""
    from cellpyability import gda_analysis, synergy_analysis
    
    output_dir = getattr(args, 'output_dir', None)
    no_plot = getattr(args, 'no_plot', False)
    
    try:
        with open(args.input_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                module = row.get('module', '').strip().lower()
                title = row.get('title')
                image_dir = row.get('dir') or row.get('image_dir')
                
                if not module:
                    print(f"Skipping row with no module specified: {row}")
                    continue
                
                if module == 'gda':
                    print(f"\n--- Running GDA: {title} ---")
                    gda_analysis.run_gda(
                        title_name=title,
                        upper_name=row.get('upper') or row.get('upper_name'),
                        lower_name=row.get('lower') or row.get('lower_name'),
                        top_conc=float(row.get('conc') or row.get('top_conc')),
                        dilution=float(row.get('dil') or row.get('dilution')),
                        image_dir=image_dir,
                        show_plot=not no_plot,
                        output_dir=output_dir
                    )
                elif module == 'synergy':
                    print(f"\n--- Running Synergy: {title} ---")
                    synergy_analysis.run_synergy(
                        title_name=title,
                        x_drug=row.get('xdrug') or row.get('x_drug'),
                        x_top_conc=float(row.get('xconc') or row.get('x_top_conc')),
                        x_dilution=float(row.get('xdil') or row.get('x_dilution')),
                        y_drug=row.get('ydrug') or row.get('y_drug'),
                        y_top_conc=float(row.get('yconc') or row.get('y_top_conc')),
                        y_dilution=float(row.get('ydil') or row.get('y_dilution')),
                        image_dir=image_dir,
                        show_plot=not no_plot,
                        output_dir=output_dir
                    )
                else:
                    print(f"Unknown module '{module}' in row: {row}")
                    
    except FileNotFoundError:
        raise CellPyAbilityError(f"Batch input file not found: {args.input_file}")
    except Exception as e:
        raise CellPyAbilityError(f"Error during batch processing: {e}")


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
