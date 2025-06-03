import os
import json
import numpy as np
from simulation import run
from conditions import Condition

def get_conditions(filename='conditions.json'):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    return data

def add_conditions(new_data, filename='conditions.json'):
    conditions = get_conditions()
    
    # append new data
    if isinstance(new_data, list):
        conditions.extend(new_data)
    else:
        conditions.append(new_data)
    
    # write back to file
    with open(filename, 'w') as f:
        json.dump(conditions, f, indent=2)

def generate_conditions():
    kept_conditions = []

    for _ in range(1000):

        num_angles = 4
        raw_angles = np.random.normal(loc=180, scale=30, size=num_angles)
        clipped_angles = np.clip(raw_angles, 100, 260)
        angles = clipped_angles.tolist()
        cond = Condition(angles, False)

        sim = run(cond, record=False, counterfactual=None, headless=True)

        if sim['hit']:
            counterfactual = run(cond, record=False, counterfactual={'remove': sim['cause_ball'], 'diverge': 150, 'noise_ball': sim['noise_ball']}, headless=True)
            
            cond.preemption = counterfactual['hit']
            cond.collisions = sim['collisions']
            cond.cause_ball = sim['cause_ball']
            cond.sim_time = sim['sim_time']
            cond.unambiguous = sim['clear_cut']
            cond.noise_ball = sim['noise_ball']
            cond.diverge = sim['diverge']

            kept_conditions.append(cond.info())
            print(cond.info())
        print(_)

    add_conditions(kept_conditions)


def play_conditions():

    conditions = get_conditions()
    filtered = [cond for cond in conditions if cond['preemption'] and cond['unambiguous']]

    kept = []
    for c in filtered:
        cond = Condition(cond['angles'], cond['preemption'])
        run(cond, record=False, counterfactual=None, headless=False)
        if input("Keep?: ").upper() == 'Y':
            if input("Play Counterfactual?: ").upper() == 'Y':
                run(cond, record=False, counterfactual={'remove': c['cause_ball'], 'diverge': c['diverge'], 'noise_ball': c['noise_ball']}, headless=False)
            kept.append(c)

    add_conditions(kept, filename="preempted_clean.json")


if __name__ == '__main__':
    generate_conditions()
    # play_conditions()



