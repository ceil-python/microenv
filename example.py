from micro_env import micro_env


if __name__ == "__main__":
    micro_env = micro_env({"prop_a": 1, "prop_b": 2}, {"id": "my_env"})
    print(micro_env)
