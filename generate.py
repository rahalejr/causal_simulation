import os
import json
import numpy as np
from random import shuffle
from simulation import run
from conditions import Condition
from videos.qualpaths import paths

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

def simple_info(filename='kept_video_meta.json'):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)
            for i in data:
                del i['angles']
                del i['jitter']
                sim_number = int(i['file_name'].split('simulation')[-1].split('.')[0])
                i['qual_path'] = paths[sim_number]
            add_conditions(data, filename='cleaned_video_meta.json', append=False)

def add_conditions(new_data, filename='conditions.json', append=True):
    conditions = get_conditions(filename) if append else []
    
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

    for j in [4]:
        for _ in range(200):
            sd = 30 if j==2 else 20
            num_angles = j
            raw_angles = np.random.normal(loc=180, scale=sd, size=num_angles)
            clipped_angles = np.clip(raw_angles, 110, 250)
            angles = clipped_angles.tolist()
            cond = Condition(angles, False)

            sim = run(cond, record=False, counterfactual=None, headless=True)

            if sim['hit'] and sim['clear_cut']:
                counterfactual = run(cond, record=False, counterfactual={'remove': sim['cause_ball'], 'diverge': 150, 'noise_ball': sim['noise_ball']}, headless=True)
                
                cond.preemption = counterfactual['hit']
                cond.collisions = sim['collisions']
                cond.cause_ball = sim['cause_ball']
                cond.sim_time = sim['sim_time']
                cond.unambiguous = sim['clear_cut']
                cond.noise_ball = sim['noise_ball']
                cond.diverge = sim['diverge']

                kept_conditions.append(cond.info())
                if cond.preemption:
                    print(cond.info())
            print(_)

        add_conditions(kept_conditions, append=False)


def play_conditions():

    filtered = get_conditions('complex_conditions.json')
    kept = []

    for c in filtered['training']:

        cond = Condition(angles=c['angles'], preemption=c['preemption'], jitter=c['jitter'], ball_positions=c['ball_positions'], filename=c['file_name'])
        output = run(cond, 'red', cause_ball = c['cause_ball'], record=False, counterfactual=None, headless=False)
        if input("Keep?: ").upper() == 'Y':
            if input("Play Counterfactual?: ").upper() == 'Y':
                run(cond, 'red', record=False, counterfactual={'remove': c['cause_ball'], 'diverge': 0, 'noise_ball': 'blue'}, headless=False)
            kept.append(c)

    add_conditions(kept, filename="training.json", append=True)

def record_conditions():

    colors = ['red', 'green', 'yellow', 'blue', 'purple']
    shuffle(colors)
    conditions = get_conditions('complex_conditions.json')['three_dm']
    for c in conditions:
        cond = Condition(angles=c['angles'], preemption=c['preemption'], jitter=c['jitter'], ball_positions=c['ball_positions'], filename=c['file_name'])
        output = run(cond, colors[(c['index'] -1)], cause_ball = c['cause_ball'], record=True, counterfactual=None, headless=False)
        colls = output['cause_collisions']
        times = []
        for i in colls:
            times.append(i['time'])
            if i['name'] == 'effect':
                break
        if len(times) > 1:
            time_diff = times[-1] - times[-2]
        else:
            time_diff = times[-1]
        time_diff = round(time_diff, 2)
        print(output)

if __name__ == '__main__':
    # generate_conditions()
    # play_conditions()
    record_conditions()
    # simple_info()


