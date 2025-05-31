import os
import json
import numpy as np
from simulation import run
from conditions import Condition


def append_to_json(new_data, filename='conditions.json'):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    
    # append new data
    if isinstance(new_data, list):
        data.extend(new_data)
    else:
        data.append(new_data)
    
    # write back to file
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == '__main__':
    kept_conditions = []

    for _ in range(1000):

        num_angles = 4
        raw_angles = np.random.normal(loc=180, scale=30, size=num_angles)
        clipped_angles = np.clip(raw_angles, 100, 260)
        angles = clipped_angles.tolist()
        cond = Condition(angles, False)

        sim = run(cond, record=False, counterfactual=None, headless=True)

        if sim['hit']:
            counterfactual = run(cond, record=False, counterfactual={'remove': sim['cause_ball'], 'divergence': 150, 'noise_ball': 'blue'}, headless=True)
            cond.preemption, cond.num_collisions, cond.cause_ball = counterfactual['hit'], sim['collisions'], sim['cause_ball']
            kept_conditions.append(cond.info())
            print(cond.info())
        print(_)

    append_to_json(kept_conditions)
    



