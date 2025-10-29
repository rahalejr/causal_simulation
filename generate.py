import os
import json
import numpy as np
from random import shuffle, sample
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
    
    indices = {'True': 1, 'False': 1}

    for _ in range(2000):
        sd = 30
        num_angles = 3
        raw_angles = np.random.normal(loc=180, scale=sd, size=num_angles)
        clipped_angles = np.clip(raw_angles, 110, 250)
        angles = [round(ang) for ang in clipped_angles.tolist()]
        ball_positions = sample([1,2,3,4,5], 3)
        ball_positions.sort()
        cond = Condition(angles, ball_positions)

        sim = run(cond, record=False, counterfactual=None, headless=True)

        if sim['hit']:

            colls = sim['cause_collisions']
            if colls:
                names = [c['name'] for c in colls if c['name'] != 'wall']
                difference_makers = len(set(names[:names.index('effect')])) + 1
                effect_collisions = [c['name'] for c in sim['effect_collisions'] if c['name'] != 'wall']
                if difference_makers == 3 and len(effect_collisions) == 1:
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


                    while True:
                        if input('replay: ').upper() != 'Y':
                            break
                        run(cond, record=False, counterfactual=None, headless=False)

                    if input('keep? :') != 'y':
                        continue
                    

                    info = {
                        "index": indices[str(sim['hit'])],
                        "num_balls": 3,
                        "ball_positions": ball_positions,
                        "angles": angles,
                        "last_collision": time_diff,
                        "cause_ball": sim["cause_ball"] if sim["cause_ball"] else None,
                        "duration": round(sim["duration"], 2),
                        "difference_makers": difference_makers,
                        "jitter": cond.jitter
                    }

                    kept_conditions.append(info)
                    indices[str(sim['hit'])] += 1

    add_conditions(kept_conditions, filename="newconds.json")


def play_conditions():

    filtered = get_conditions('complex_conditions.json')
    kept = []

    for c in filtered['five_candidate']:

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
    conditions = get_conditions('newconds.json')
    counter = 0
    for c in conditions:
        filename = f"videos/bin/sim_{c['index']}.mp4"
        cond = Condition(c['angles'], c['ball_positions'], jitter=c['jitter'], filename=filename)
        output = run(cond, actual_data = None, noise = .01, cause_color = colors[counter % 5], cause_index = 1, record=True, counterfactual=None, headless=False)
        counter += 1

if __name__ == '__main__':
    # generate_conditions()
    # play_conditions()
    record_conditions()
    # simple_info()


