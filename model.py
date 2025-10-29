# noise values range from .1 to 2
# how many e's do we need to generate?

import os
import json
import copy
import numpy as np
from simulation import run, gaussian_noise
from conditions import Condition

n_simulations = 1000

def process_conditions(conds_list):
    for i in conds_list:
        cond = Condition(i['angles'], [1, 2, 3, 4, 5], i['preemption'], i['unambiguous'], i['jitter'])
        run_condition(cond)
    

def run_condition(cond):

    actual_output=run(cond, record=False, counterfactual=None, headless=True)
    counterfactual = run(remove_ball(cond, 2),record=False, counterfactual=None, headless=True)
    print(collision_compare(actual_output, counterfactual))
    
    #whether(actual_output, cond, 2)
    #how(actual_output, cond, 2)
    #sufficient(cond, 2)
    #robust(actual_output, cond, 2)

    print(collision_compare(actual_output, counterfactual))

    # difference maker cause
    diff_maker_balls = []
    for c in range(cond.num_balls):
        diff_maker_balls += [difference_maker(actual_output, cond, c)]
            
    # whether cause
    whether_balls = []
    for c in range(cond.num_balls):
        whether_balls+= [whether(actual_output, cond, c)]

    # how cause
    how_balls = []
    for c in range(cond.num_balls):
        how_balls += [how(actual_output, cond, c, n_simulations)]
    
    # sufficient cause
    sufficient_balls = []
    for c in range(cond.num_balls):
        sufficient_balls += [sufficient(cond, c)]

    #robust cause
    robust_balls = []
    for c in range(cond.num_balls):
        robust_balls += [robust(actual_output, cond, c)]
    
    #test
    print("DM ", diff_maker_balls, "\n")
    print("HOW ", diff_maker_balls, "\n")
    print("WHETHER ", diff_maker_balls, "\n")
    print("SUFFICIENT ", diff_maker_balls, "\n")
    print("ROBUST ", diff_maker_balls, "\n")
    return


def difference_maker(actual_output, cond, c):
    new_cond = remove_ball(cond,c)
    outcomes = []
    for _ in range(0,n_simulations):
        output = run(new_cond, record=False, counterfactual=None, headless=False)
        outcomes.append((output['final_pos'], output['sim_time']) != (actual_output['final_pos'] , actual_output['sim_time']))
    return sum(outcomes)/float(n_simulations)
         
def whether(actual_output, cond, c):
    new_cond = remove_ball(cond,c)
    outcomes = []
    for _ in range(0,n_simulations):
        output = run(new_cond, record=False, counterfactual=None, headless=False)
        outcomes.append(actual_output['hit']!= output['hit'])
    return sum(outcomes)/float(n_simulations)
    
def how(actual_output, cond, c, n_simulations):
    new_cond = change_ball(cond,c)
    outcomes = []
    sum = 0
    for _ in range(0,n_simulations):
        #need to add noise to these, right now they are all identical
        output = run(new_cond, record=False, counterfactual=None, headless=False)
        outcomes.append(output['final_pos'], output['sim_time']) != (actual_output['final_pos'] , actual_output['sim_time'])
    return sum(outcomes)/float(n_simulations)

def sufficient(cond, c):
    new_cond = remove_others(cond, c)
    outcomes = []
    for _ in range(0,n_simulations):
        output = run(new_cond, record=False, counterfactual=None, headless=False)
        # this is effectively the whether cause, comparing to all cause balls removed (always false)
        outcomes.append(output['hit'])
    return sum(outcomes)/float(n_simulations)

def robust(actual_output, cond, c):
    new_cond = change_others(cond,c)
    outcomes = []
    for _ in range(0,n_simulations):
        output = run(new_cond, record=False, counterfactual=None, headless=False)
        # if goal still occurs when changing others
        outcomes.append(output['hit'])
    return sum(outcomes)/float(n_simulations)

def remove_ball(cond, c):
    new_cond = copy.deepcopy(cond)

    del new_cond.angles[c]
    del new_cond.y_positions[c]
    del new_cond.radians[c]
    del new_cond.jitter['x'][c]
    del new_cond.jitter['y'][c]
    new_cond.num_balls -= 1

    return new_cond

def remove_others(cond, c):
    new_cond = copy.deepcopy(cond)

    del new_cond.angles[:c]
    del new_cond.angles[c+1:]
    del new_cond.y_positions[:c]
    del new_cond.y_positions[c+1:]
    del new_cond.radians[:c]
    del new_cond.radians[c+1:]
    del new_cond.jitter['x'][:c]
    del new_cond.jitter['y'][:c]
    del new_cond.jitter['x'][c+1:]
    del new_cond.jitter['y'][c+1:]
    new_cond.num_balls = 1
    
    return new_cond

def change_ball(cond, c):
    new_cond = copy.deepcopy(cond)
    new_cond.angles[c] += gaussian_noise(0.0001)
    new_cond.radians[c] = new_cond.angles[c] * np.pi / 180
    return new_cond

def change_others(cond, c):
    new_cond = copy.deepcopy(cond)
    for i in range(cond.num_balls):
        if i == c : continue
        else:
            new_cond.angles[i] += gaussian_noise(10)
            new_cond.radians[i] = new_cond.angles[i] * np.pi / 180
    return new_cond


def collision_compare(output, counterfactual):
    i = 0 
    j = 0
    noisy_steps = []
    #is this an off by 1 error?, does it run when i == len(output?)
    while i < len(output['collisions']) and j < len(counterfactual['collisions']):
        #need to make fool proof by comparing objects too
        if output['collisions'][i] == counterfactual['collisions'][j]:
            i += 1
            j += 1
        elif output['collisions'][i]['step'] < counterfactual['collisions'][j]['step']:
            noisy_steps.append(output['collisions'][i]['step'])
            i += 1
        else:
            noisy_steps.append(counterfactual['collisions'][j]['step'])
            j += 1
        if i == len(output['collisions']) - 1:
            noisy_steps.extend(item['step'] for item in counterfactual['collisions'][j+1:])
        if j == len(counterfactual['collisions']) - 1:
            noisy_steps.extend(item['step'] for item in output['collisions'][i+1:])
    return noisy_steps

if __name__ == '__main__':
    filename = 'complex_conditions.json'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    
    process_conditions(data['one_dm'])