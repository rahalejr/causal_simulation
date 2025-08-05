# noise values range from .1 to 2

import os
import json
from simulation import run
from conditions import Condition


def process_conditions(conds_list):
    for c in conds_list:
        cond = Condition(c['angles'], c['preemption'], c['unambiguous'], c['jitter'])
        run_condition(cond)
    pass


def run_condition(cond):

    # example for how to run the simulation for a single condition
    sim = run(cond, record=False, counterfactual=None, headless=True)
    
    # difference maker


    # whether


    # how


    # sufficient


    #robust




if __name__ == '__main__':
    filename = 'video_meta.json'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    
    process_conditions(data)