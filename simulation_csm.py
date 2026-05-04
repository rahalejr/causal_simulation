from simulation_engine import gaussian_noise, run_simple


def run(
    condition,
    pause=10,
    actual_data=None,
    noise=6,
    cause_color="red",
    cause_ball=1,
    record=False,
    counterfactual=None,
    headless=False,
    clip_num=1,
    is_cf=False,
    max_time=6.0,
):
    return run_simple(
        condition=condition,
        pause=pause,
        actual_data=actual_data,
        noise=noise,
        cause_color=cause_color,
        cause_ball=cause_ball,
        record=record,
        counterfactual=counterfactual,
        headless=headless,
        clip_num=clip_num,
        is_cf=is_cf,
        max_time=max_time,
    )


if __name__ == "__main__":
    pass
