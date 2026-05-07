import os
import json
import numpy as np
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from random import shuffle
from simulation_engine import run_simple as run
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
    
    if isinstance(new_data, list):
        conditions.extend(new_data)
    else:
        conditions.append(new_data)
    
    with open(filename, 'w') as f:
        json.dump(conditions, f, indent=2)

def generate_conditions():
    kept_conditions = []

    for j in [1]:
        for _ in range(200):
            sd = 30
            num_angles = j
            raw_angles = np.random.normal(loc=180, scale=sd, size=num_angles)
            clipped_angles = np.clip(raw_angles, 110, 250)
            angles = clipped_angles.tolist()
            ball_positions = list(range(1, num_angles + 1))
            cond = Condition(angles=angles, ball_positions=ball_positions)

            sim = run(cond, record=False, counterfactual=None, headless=True)

            if sim['hit'] and sim['cause_ball'] is not None:
                counterfactual = run(
                    cond,
                    record=False,
                    counterfactual={'remove': sim['cause_ball']},
                    headless=True
                )
                
                cond.preemption = counterfactual['hit']
                cond.collisions = sim['collisions']
                cond.cause_ball = sim['cause_ball']
                cond.sim_time = sim['sim_time']
                cond.unambiguous = True

                kept_conditions.append(cond.info())
                if cond.preemption:
                    print(cond.info())
            print(_)

        add_conditions(kept_conditions, append=False)

def play_conditions():
    collisions = get_conditions('new_coll.json')
    post = []

    for interval in [25, 40, 70]:
        # shuffle(collisions)

        for c in collisions:
            cond = Condition(angles=c['angles'], jitter=c['jitter'], ball_positions=c['ball_positions'], filename=c['filename'], shape=c.get('shape', 'ball'))
            output = run(cond, pause=interval, actual_data=None, cause_color='red', cause_ball=c['cause_ball'], record=False, counterfactual=None, headless=False)
            post.append({**c, 'pause': interval})

    add_conditions(post, filename="calibrated.json", append=True)

def record_conditions():
    colors = ['red', 'green', 'yellow', 'blue', 'purple']
    shuffle(colors)
    conditions = get_conditions('complex_conditions.json')['three_dm']
    for c in conditions:
        cond = Condition(angles=c['angles'], preemption=c['preemption'], jitter=c['jitter'], ball_positions=c['ball_positions'], filename=c['file_name'], shape=c.get('shape', 'ball'))
        output = run(cond, cause_color=colors[(c['index'] - 1)], cause_ball=c['cause_ball'], record=True, counterfactual=None, headless=False)
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

def _noise_worker(args):
    noise, conditions, repeats = args
    results = []

    for idx, c in enumerate(conditions):
        hits = 0

        for _ in range(repeats):
            cond = Condition(
                angles=c['angles'],
                jitter=c['jitter'],
                ball_positions=c['ball_positions'],
                filename=c['filename'],
                shape=c.get('shape', 'ball')
            )

            output = run(
                cond,
                pause=c['pause'],
                actual_data=None,
                cause_color='red',
                cause_ball=c['cause_ball'],
                record=False,
                counterfactual=None,
                headless=True,
                noise=noise
            )

            hits += int(output['hit'])

        results.append((idx, noise, hits / repeats))

    return results

def set_noise():
    conditions = get_conditions('calibrated.json')
    noises = [10.0, 8.0, 7.0, 6.0, 5.0, 3.0]
    repeats = 100

    ctx = mp.get_context('spawn')

    with ProcessPoolExecutor(max_workers=len(noises), mp_context=ctx) as executor:
        jobs = [(noise, conditions, repeats) for noise in noises]

        for noise_results in executor.map(_noise_worker, jobs):
            for idx, noise, hit_rate in noise_results:
                conditions[idx][f'noise_{noise}'] = hit_rate

    add_conditions(conditions, filename='noise_calibration.json', append=False)

if __name__ == '__main__':
    # generate_conditions()
    play_conditions()
    # set_noise()
    # record_conditions()
    # simple_info()
