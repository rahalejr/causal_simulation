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

def simple_info(filename='selected_videos.json'):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)
            for j in (data['five_ball'], data['two_ball']):
                for i in j:
                    del i['angles']
                    del i['jitter']
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

    for j in [2]:
        for _ in range(2000 if j == 5 else 1000):

            num_angles = j
            raw_angles = np.random.normal(loc=180, scale=30, size=num_angles)
            clipped_angles = np.clip(raw_angles, 120, 240)
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

                if cond.preemption:
                    kept_conditions.append(cond.info())
                    print(cond.info())
            print(_)

        add_conditions(kept_conditions)


def play_conditions():

    conditions = get_conditions('conditions.json')
    filtered = [cond for cond in conditions if cond['num_balls'] == 2 and cond['unambiguous'] and cond['preemption']]

    kept = []
    for c in filtered:
        cond = Condition(c['angles'], c['preemption'])
        run(cond, record=False, counterfactual=None, headless=False)
        if input("Keep?: ").upper() == 'Y':
            if input("Play Counterfactual?: ").upper() == 'Y':
                run(cond, record=False, counterfactual={'remove': c['cause_ball'], 'diverge': 0, 'noise_ball': 'blue'}, headless=False)
            kept.append(c)

    add_conditions(kept, filename="preempt2ball.json", append=False)

def record_conditions():

    for j in ['preempt2ball.json']:
        conditions = get_conditions(j)
        for i, c in enumerate(conditions):
            cond = Condition(c['angles'], c['preemption'], c['unambiguous'])
            info = run(cond, record=True, counterfactual=None, headless=False, clip_num=i)
            conditions[i]['file_name'] = info['file_name']
            conditions[i]['colors'] = info['colors']
    add_conditions(conditions, filename='video_meta.json')

if __name__ == '__main__':
    # generate_conditions()
    # play_conditions()
    # record_conditions()
    simple_info()


