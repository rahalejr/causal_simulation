import os
import json
import numpy as np
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

    filtered = get_conditions('conditions.json')

    counts = {
        '5True': 0,
        '5False': 0,
        '2True': 0,
        '2False': 0,
        '3True': 0,
        '3False': 0
    }
    kept = []
    for c in filtered:
        if counts[f"{c['num_balls']}{c['preemption']}"] > 3:
            continue
        cond = Condition(angles=c['angles'], preemption=c['preemption'], jitter=c['jitter'])
        run(cond, record=False, counterfactual=None, headless=False)
        if input("Keep?: ").upper() == 'Y':
            if input("Play Counterfactual?: ").upper() == 'Y':
                run(cond, record=False, counterfactual={'remove': c['cause_ball'], 'diverge': 0, 'noise_ball': 'blue'}, headless=False)
            kept.append(c)
            counts[f"{c['num_balls']}{c['preemption']}"] += 1

    add_conditions(kept, filename="training_conditions.json", append=True)

def record_conditions():

    for j in ['training_conditions.json']:
        conditions = get_conditions(j)
        for i, c in enumerate(conditions):
            cond = Condition(c['angles'], c['preemption'], c['unambiguous'], c['jitter'])
            info = run(cond, record=True, counterfactual=None, headless=False, clip_num=i)
            conditions[i]['file_name'] = info['file_name']
            conditions[i]['colors'] = info['colors']
    add_conditions(conditions, filename='video_meta.json')

if __name__ == '__main__':
    # generate_conditions()
    # play_conditions()
    record_conditions()
    # simple_info()


