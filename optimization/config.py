DEFAULT_CONFIG = {

    "algorithms": [
        "greedy",
        "priority_greedy",
        "best_fit",
        "randomized_greedy",
        "simulated_annealing",
        "genetic",
        "cp_sat"
    ],

    "objective_weights": {

        "rehandling": 100.0,

        "weight_imbalance": 1.0,

        "longitudinal_balance": 1000.0,

        "unassigned": 1000000.0,

        "destination_mixing": 20.0,

        "priority": 5.0
    },

    "simulated_annealing": {

        "iterations": 3000,

        "initial_temperature": 1000.0,

        "cooling": 0.995
    },

    "genetic_algorithm": {

        "population_size": 30,

        "generations": 100,

        "mutation_rate": 0.10
    },

    "cp_sat": {

        "time_limit_seconds": 30
    }
}