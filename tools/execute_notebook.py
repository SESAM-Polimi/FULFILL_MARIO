"""Execute a notebook with the selected installed kernel and working directory."""
import argparse
from pathlib import Path
import nbformat
from nbclient import NotebookClient

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('notebook',type=Path)
parser.add_argument('--kernel',default='python3')
parser.add_argument('--cwd',type=Path,default=Path.cwd())
parser.add_argument('--output',type=Path)
args=parser.parse_args()
notebook=nbformat.read(args.notebook,as_version=4)
NotebookClient(notebook,kernel_name=args.kernel,timeout=1800,resources={'metadata':{'path':str(args.cwd.resolve())}}).execute()
nbformat.write(notebook,args.output or args.notebook)
print(f'Executed {sum(c.cell_type=="code" for c in notebook.cells)} code cells: {args.notebook.name}')
