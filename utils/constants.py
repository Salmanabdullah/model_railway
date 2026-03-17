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

LOGICAL_BLOCKS = {
    "B1": ["B1_up", "B1_down"],
    "B2": ["B2_up", "B2_down"],
    "B3": ["B3_up", "B3_down"],
    "B4": ["B4_up", "B4_down"],
    "B5": ["B5_up", "B5_down"],
    "B6": ["B6_up", "B6_down"],
}

JUNCTION = "J1"

TRAINS = ["train_1", "train_2"]