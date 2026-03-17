# Blocks mapped to SUMO edge IDs
BLOCKS = {
    "B1_up": ["E1"],
    "B1_down": ["-E1"],
    "B2_up": ["E1"],
    "B2_down": ["-E1"],
    "B3_up": ["E1"],
    "B3_down": ["-E1"],
    "B4_up": ["E1"],
    "B4_down": ["-E1"],
    "B5_up": ["E1"],
    "B5_down": ["-E1"],
    "B6_up": ["E1"],
    "B6_down": ["-E1"],
}

# Map edges → blocks (VERY IMPORTANT for fast lookup)
EDGE_TO_BLOCK = {}
for block, edges in BLOCKS.items():
    for e in edges:
        EDGE_TO_BLOCK[e] = block

# Direction detection
UP_BLOCKS = [b for b in BLOCKS if "_up" in b]
DOWN_BLOCKS = [b for b in BLOCKS if "_down" in b]