from locust import LoadTestShape


class RampUpDownSpikeUsers(LoadTestShape):
    """Ramp 0->target, then target->0, with one additive spike per phase."""

    def tick(self) -> tuple[int, int] | None:
        options = self.runner.environment.parsed_options
        phase_duration = options.phase_duration_seconds
        run_time = self.get_run_time()

        if run_time > phase_duration * 2:
            return None

        phase = 0 if run_time <= phase_duration else 1
        phase_time = run_time if phase == 0 else run_time - phase_duration
        progress = min(phase_time / phase_duration, 1.0)
        baseline = int(options.max_users * progress)
        if phase == 1:
            baseline = options.max_users - baseline

        spike_start = phase_duration / 2
        spike_end = spike_start + options.phase_spike_duration_seconds
        in_spike = spike_start <= phase_time < spike_end
        users = baseline + (options.phase_spike_users if in_spike else 0)

        return max(users, 1), options.pattern_spawn_rate
