"""Build the anonymous working draft; never upload or declare submission readiness."""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def build(render_schematics=False):
    paper = ROOT / 'overleaf'
    out = paper / 'build'
    out.mkdir(exist_ok=True)
    commands = [
        ['pdflatex', '-interaction=nonstopmode', '-halt-on-error', '-output-directory=build', 'main.tex'],
        ['bibtex', 'build/main'],
        ['pdflatex', '-interaction=nonstopmode', '-halt-on-error', '-output-directory=build', 'main.tex'],
        ['pdflatex', '-interaction=nonstopmode', '-halt-on-error', '-output-directory=build', 'main.tex'],
    ]
    # Published PDFs include the recorded experimental figures and showcase.
    # Compiling the paper must not silently replace any figure or its provenance.
    if render_schematics:
        commands.insert(0, [sys.executable, str(paper / 'figures/src/render_figures.py')])
    for i, command in enumerate(commands):
        result = subprocess.run(command, cwd=paper, capture_output=True)
        (out / f'build_step_{i}.log').write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f'Build failed: {command[0]}; see build_step_{i}.log')
    print(out / 'main.pdf')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render-schematics', action='store_true',
                        help='Explicitly regenerate the two method/platform schematics before compilation')
    build(parser.parse_args().render_schematics)
