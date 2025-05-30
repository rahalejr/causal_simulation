import numpy as np
from simulation import run


num_angles = 4
raw_angles = np.random.normal(loc=180, scale=30, size=num_angles)
clipped_angles = np.clip(raw_angles, 100, 260)
angles = clipped_angles.tolist()

