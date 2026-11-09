from locust import events


@events.init_command_line_parser.add_listener
def add_load_pattern_options(parser) -> None:
    parser.add_argument(
        "--pattern-duration-seconds",
        type=int,
        env_var="LOCUST_PATTERN_DURATION_SECONDS",
        default=300,
        help="Total duration of the selected load pattern in seconds.",
    )
    parser.add_argument(
        "--pattern-spawn-rate",
        type=int,
        env_var="LOCUST_PATTERN_SPAWN_RATE",
        default=10,
        help="Users to spawn per second when changing load.",
    )
    parser.add_argument(
        "--target-users",
        type=int,
        env_var="LOCUST_TARGET_USERS",
        default=100,
        help="Target users for rampUsers.",
    )
    parser.add_argument(
        "--ramp-duration-seconds",
        type=int,
        env_var="LOCUST_RAMP_DURATION_SECONDS",
        default=300,
        help="Ramp duration for rampUsers.",
    )
    parser.add_argument(
        "--constant-users",
        type=int,
        env_var="LOCUST_CONSTANT_USERS",
        default=50,
        help="Fixed user count for constantUsers.",
    )
    parser.add_argument(
        "--concurrent-users",
        type=int,
        env_var="LOCUST_CONCURRENT_USERS",
        default=50,
        help="Fixed concurrent user count for constantConcurrentUsers.",
    )
    parser.add_argument(
        "--spike-users",
        type=int,
        env_var="LOCUST_SPIKE_USERS",
        default=200,
        help="User count during each spike.",
    )
    parser.add_argument(
        "--spike-duration-seconds",
        type=int,
        env_var="LOCUST_SPIKE_DURATION_SECONDS",
        default=10,
        help="How long each spike stays active.",
    )
    parser.add_argument(
        "--spike-frequency-seconds",
        type=int,
        env_var="LOCUST_SPIKE_FREQUENCY_SECONDS",
        default=60,
        help="Approximate time between spike starts.",
    )
    parser.add_argument(
        "--jitter-seconds",
        type=int,
        env_var="LOCUST_JITTER_SECONDS",
        default=10,
        help="Random plus/minus variance applied to spike frequency.",
    )
    parser.add_argument(
        "--initial-delay-seconds",
        type=int,
        env_var="LOCUST_INITIAL_DELAY_SECONDS",
        default=15,
        help="Delay before the selected pattern starts producing load.",
    )
    parser.add_argument(
        "--step-duration-seconds",
        type=int,
        env_var="LOCUST_STEP_DURATION_SECONDS",
        default=60,
        help="Duration of each step for stepUsers.",
    )
    parser.add_argument(
        "--step-users",
        type=int,
        env_var="LOCUST_STEP_USERS",
        default=50,
        help="Users added at each step for stepUsers.",
    )
    parser.add_argument(
        "--max-users",
        type=int,
        env_var="LOCUST_MAX_USERS",
        default=250,
        help="Maximum users for stepUsers.",
    )
    parser.add_argument(
        "--phase-duration-seconds",
        type=int,
        env_var="LOCUST_PHASE_DURATION_SECONDS",
        default=300,
        help="Duration of each ramp-up or ramp-down phase.",
    )
    parser.add_argument(
        "--phase-spike-users",
        type=int,
        env_var="LOCUST_PHASE_SPIKE_USERS",
        default=50,
        help="Additional users during the spike in each phase.",
    )
    parser.add_argument(
        "--phase-spike-duration-seconds",
        type=int,
        env_var="LOCUST_PHASE_SPIKE_DURATION_SECONDS",
        default=30,
        help="Duration of the spike in each phase.",
    )
    parser.add_argument(
        "--baseline-users",
        type=int,
        env_var="LOCUST_BASELINE_USERS",
        default=100,
        help="Steady user count before and after a burst.",
    )
    parser.add_argument(
        "--burst-users",
        type=int,
        env_var="LOCUST_BURST_USERS",
        default=250,
        help="Peak user count during a burst.",
    )
    parser.add_argument(
        "--burst-ramp-seconds",
        type=int,
        env_var="LOCUST_BURST_RAMP_SECONDS",
        default=60,
        help="Time to ramp from zero to the baseline user count.",
    )
    parser.add_argument(
        "--baseline-hold-seconds",
        type=int,
        env_var="LOCUST_BASELINE_HOLD_SECONDS",
        default=120,
        help="Time to hold baseline load before the burst.",
    )
    parser.add_argument(
        "--burst-duration-seconds",
        type=int,
        env_var="LOCUST_BURST_DURATION_SECONDS",
        default=30,
        help="Time to hold the burst user count.",
    )
    parser.add_argument(
        "--recovery-seconds",
        type=int,
        env_var="LOCUST_RECOVERY_SECONDS",
        default=60,
        help="Time to return from burst load to baseline.",
    )
    parser.add_argument(
        "--recovery-hold-seconds",
        type=int,
        env_var="LOCUST_RECOVERY_HOLD_SECONDS",
        default=120,
        help="Time to observe the system at baseline after recovery.",
    )
    parser.add_argument(
        "--target-rps",
        type=int,
        env_var="LOCUST_TARGET_RPS",
        default=100,
        help="Approximate target requests per second for constantUsersPerSec.",
    )
    parser.add_argument(
        "--estimated-rps-per-user",
        type=int,
        env_var="LOCUST_ESTIMATED_RPS_PER_USER",
        default=1,
        help="Estimated requests per second produced by one user.",
    )
