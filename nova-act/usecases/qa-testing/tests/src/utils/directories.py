import os


script_dir = os.path.dirname(os.path.abspath(__file__))
tests_root_dir = os.path.dirname(os.path.dirname(script_dir))
user_data_dir = os.path.join(tests_root_dir, ".nova_act", "user_data_dir")
logs_dir = os.path.join(tests_root_dir, ".nova_act", "logs")


def initialize_nova_act_directories(test_id: str):
    test_logs_dir = os.path.join(logs_dir, test_id)
    test_user_data_dir = os.path.join(user_data_dir, test_id)
    os.makedirs(test_logs_dir, exist_ok=True)
    os.makedirs(test_user_data_dir, exist_ok=True)

    return test_logs_dir, test_user_data_dir
