# Logical block sections mapped to SUMO edge IDs
# Interpretation:
# - A -> J1 has two logical blocks: B1, B2
# - J1 -> B has two logical blocks: B3, B4
# - J1 -> C has two logical blocks: B5, B6
#
# Station approach edges E1, E6, E9 are not treated as logical blocks here.

BLOCKS = {
    "B1_up": ["E2"],
    "B1_down": ["-E2"],

    "B2_up": ["E3"],
    "B2_down": ["-E3"],

    "B3_up": ["E4"],
    "B3_down": ["-E4"],

    "B4_up": ["E5"],
    "B4_down": ["-E5"],

    "B5_up": ["E7"],
    "B5_down": ["-E7"],

    "B6_up": ["E8"],
    "B6_down": ["-E8"],
}

# Fast lookup: edge -> logical block
EDGE_TO_BLOCK = {}
for block, edges in BLOCKS.items():
    for edge in edges:
        EDGE_TO_BLOCK[edge] = block

UP_BLOCKS = [b for b in BLOCKS if b.endswith("_up")]
DOWN_BLOCKS = [b for b in BLOCKS if b.endswith("_down")]

# J1 traffic light / rail signal
J1_TLS_ID = "J1"

# Block signal IDs
BLOCK_TLS = {
    "B1": "TLS1",
    "B2": "TLS2",
    "B3": "TLS3",
    "B4": "TLS4",
    "B5": "TLS5",
    "B6": "TLS6",
}

# For all these 2-link block signals, use:
# link 0 = down direction
# link 1 = up direction
BLOCK_SIGNAL_STATES = {
    "ALL_RED": "rr",
    "UP_GREEN": "rG",
    "DOWN_GREEN": "Gr",
    "BOTH_GREEN": "GG",
    "UP_YELLOW": "ry",
    "DOWN_YELLOW": "yr",
}



B5_TLS_ID = "TLS5"

# J10 link order:
# 0 = -E8 -> -E7   (C -> J1 direction)
# 1 =  E7 -> E8    (J1 -> C direction)
B5_STATES = {
    "CLEAR": "GG",
    "WARN_C_TO_A": "yG",
}

APPROACH_SPEED = 0.5
# Link order at J1:
# 0 = -E4 -> -E3   (B -> A)
# 1 = -E7 -> -E3   (C -> A)
# 2 =  E3 -> E7    (A -> C)
# 3 =  E3 -> E4    (A -> B)
J1_STATES = {
    "ALL_RED": "rrrr",
    "ALL_GREEN": "GGGG",
    "B_to_A":  "Grrr",
    "C_to_A":  "rGrr",
    "A_to_C":  "rrGr",
    "A_to_B":  "rrrG",
}

# Which blocks must be free before a route can be granted
ROUTE_REQUIREMENTS = {
    "A_to_B": ["B3_up"],
    "A_to_C": ["B5_up"],
    "B_to_A": ["B2_down"],
    "C_to_A": ["B2_down"],
}

# Route from CURRENT edge onward
TRAIN_ROUTE_EDGES = {
    "A_to_B": ["E3", "E4", "E5", "E6"],
    "A_to_C": ["E3", "E7", "E8", "E9"],
    "B_to_A": ["-E4", "-E3", "-E2", "-E1"],
    "C_to_A": ["-E7", "-E3", "-E2", "-E1"],
}

# When the train leaves this zone, J1 can be released again
J1_RELEASE_ZONES = {
    "A_to_B": {"B2_up", "B3_up"},
    "A_to_C": {"B2_up", "B5_up"},
    "B_to_A": {"B3_down", "B2_down"},
    "C_to_A": {"B5_down", "B2_down"},
}

