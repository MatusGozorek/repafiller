from pathlib import Path

# resolves to wherever parser.py lives
BASE_DIR = Path(__file__).resolve().parents[2]

def load_inventory(path: Path = BASE_DIR / "inventory.txt"):
    inventory = {}
    current = None
    
    with Path(path).open() as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                current = line[1:-1]
                inventory[current] = []
            elif line and current:
                inventory[current].append(line)
    return inventory

