from locust import LoadTestShape


class BurstRecoveryUsers(LoadTestShape):
    """Ramp to baseline, burst above it, recover, then observe steady state."""

    def tick(self) -> tuple[int, int] | None:
        options = self.runner.environment.parsed_options
        run_time = self.get_run_time()

        ramp_end = options.burst_ramp_seconds
        baseline_end = ramp_end + options.baseline_hold_seconds
        burst_end = baseline_end + options.burst_duration_seconds
        recovery_end = burst_end + options.recovery_seconds
        test_end = recovery_end + options.recovery_hold_seconds

        if run_time >= test_end:
            return None

        if run_time < ramp_end:
            progress = run_time / max(options.burst_ramp_seconds, 1)
            users = int(options.baseline_users * progress)
        elif run_time < baseline_end:
            users = options.baseline_users
        elif run_time < burst_end:
            users = options.burst_users
        elif run_time < recovery_end:
            progress = (run_time - burst_end) / max(options.recovery_seconds, 1)
            excess_users = options.burst_users - options.baseline_users
            users = int(options.burst_users - (excess_users * progress))
        else:
            users = options.baseline_users

        return max(users, 1), options.pattern_spawn_rate
